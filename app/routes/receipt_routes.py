from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from app.services.accounting_service import accounting_service

receipt_bp = Blueprint('receipts', __name__)


def _next_txn_no(conn, prefix, txn_type):
    from datetime import datetime
    cur = conn.execute(
        """SELECT COUNT(*) as n FROM stock_transactions
           WHERE transaction_type=? AND strftime('%Y', created_at)=strftime('%Y','now')""",
        (txn_type,)
    )
    n = cur.fetchone()['n'] + 1
    return f"{prefix}-{datetime.now().year}-{n:06d}"


def _get_base_quantity(conn, item_id, uom_id, quantity):
    item = conn.execute(
        "SELECT base_uom_id, medium_uom_id, medium_to_minor_factor, major_uom_id, major_to_medium_factor FROM items WHERE id=?",
        (item_id,)
    ).fetchone()
    if not item:
        return None, None
    if int(uom_id) == int(item['base_uom_id']):
        factor = 1.0
    elif item['medium_uom_id'] and int(uom_id) == int(item['medium_uom_id']):
        factor = float(item['medium_to_minor_factor'] or 1)
    elif item['major_uom_id'] and int(uom_id) == int(item['major_uom_id']):
        factor = float(item['major_to_medium_factor'] or 1) * float(item['medium_to_minor_factor'] or 1)
    else:
        return None, None
    return factor, float(quantity) * factor


def _is_invoiced(conn, tid):
    """هل الإذن مفوتَر؟"""
    row = conn.execute(
        "SELECT id FROM purchase_invoices WHERE receipt_id=?", (tid,)
    ).fetchone()
    return row is not None


# ============================================================
# قائمة الأذون
# ============================================================
@receipt_bp.route('/', methods=['GET'])
def list_receipts():
    rows = db.query("""
        SELECT t.*, w.name_ar as warehouse_name
        FROM stock_transactions t
        LEFT JOIN warehouses w ON t.to_warehouse_id = w.id
        WHERE t.transaction_type='RECEIPT'
        ORDER BY t.id DESC LIMIT 100
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


# ============================================================
# تفاصيل إذن
# ============================================================
@receipt_bp.route('/<int:tid>', methods=['GET'])
def get_receipt(tid):
    txn = db.query("SELECT * FROM stock_transactions WHERE id=?", (tid,), one=True)
    if not txn:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT l.*, 
                  i.name_ar as item_name, 
                  i.code as item_code,
                  i.is_taxable,
                  i.default_tax_rate
           FROM stock_transaction_lines l
           JOIN items i ON l.item_id = i.id
           WHERE l.transaction_id=? ORDER BY l.line_no""",
        (tid,)
    )
    txn['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(txn)})


# ============================================================
# تفاصيل الإذن + حالة الفوترة
# ============================================================
@receipt_bp.route('/<int:tid>/details', methods=['GET'])
def receipt_details(tid):
    txn = db.query("""
        SELECT 
            st.*,
            w.code as warehouse_code,
            w.name_ar as warehouse_name,
            je.entry_no as journal_entry_no
        FROM stock_transactions st
        LEFT JOIN warehouses w ON st.to_warehouse_id = w.id
        LEFT JOIN journal_entries je ON st.journal_entry_id = je.id
        WHERE st.id = ? AND st.transaction_type = 'RECEIPT'
    """, (tid,), one=True)
    
    if not txn:
        return jsonify({'success': False, 'message': 'الإذن غير موجود'}), 404
    
    lines = db.query("""
        SELECT 
            l.*,
            i.code as item_code,
            i.name_ar as item_name,
            u.name_ar as uom_name
        FROM stock_transaction_lines l
        LEFT JOIN items i ON l.item_id = i.id
        LEFT JOIN units_of_measure u ON l.uom_id = u.id
        WHERE l.transaction_id = ?
        ORDER BY l.line_no
    """, (tid,))
    
    invoice = db.query("""
        SELECT id, invoice_no, invoice_date, total_amount, status
        FROM purchase_invoices
        WHERE receipt_id = ?
    """, (tid,), one=True)
    
    txn = dict(txn)
    txn['lines'] = [dict(l) for l in lines]
    txn['invoice'] = dict(invoice) if invoice else None
    txn['is_invoiced'] = invoice is not None
    
    return jsonify({'success': True, 'data': json_safe(txn)})


# ============================================================
# إنشاء إذن (كميات فقط)
# ============================================================
@receipt_bp.route('/', methods=['POST'])
def create_receipt():
    d = request.get_json() or {}
    if not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        txn_no = _next_txn_no(conn, 'REC', 'RECEIPT')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                to_warehouse_id, reference_type, reference_no,
                status, notes, created_by, movement_code)
               VALUES (?, 'RECEIPT', ?, ?, ?, ?, 'DRAFT', ?, 1, 'RECV')""",
            (txn_no, d.get('transaction_date', '2026-01-01'),
             d['warehouse_id'], d.get('reference_type'),
             d.get('reference_no'), d.get('notes'))
        )
        txn_id = cur.lastrowid

        total_qty = 0
        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(
                conn, line['item_id'], line['uom_id'], line['quantity']
            )
            if base_qty is None:
                return jsonify({'success': False, 'message': f'الوحدة غير مرتبطة بالصنف #{line["item_id"]}'}), 400

            qty = to_decimal(line['quantity'])
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity,
                    base_quantity, unit_cost, total_cost, batch_no)
                   VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 float(qty), float(base_qty), line.get('batch_no') or '')
            )
            total_qty += base_qty

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=0 WHERE id=?",
            (total_qty, txn_id)
        )

    return jsonify({'success': True, 'data': {'id': txn_id, 'transaction_no': txn_no}}), 201


# ============================================================
# تعديل إذن (مسودة أو مُرحّل غير مفوتَر)
# ============================================================
@receipt_bp.route('/<int:tid>', methods=['PUT'])
def update_receipt(tid):
    d = request.get_json() or {}
    
    with db.transaction() as conn:
        txn = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND transaction_type='RECEIPT'",
            (tid,)
        ).fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الإذن غير موجود'}), 404
        
        # ✅ تحقق: إذا الإذن مفوتَر → منع التعديل
        if _is_invoiced(conn, tid):
            return jsonify({'success': False, 'message': 'لا يمكن تعديل إذن مفوتَر. احذف الفاتورة أولاً.'}), 400
        
        # لو الإذن مُرحّل → نرجع الكميات من المخزون أولاً
        if txn['status'] == 'POSTED':
            old_lines = conn.execute(
                "SELECT * FROM stock_transaction_lines WHERE transaction_id=?", (tid,)
            ).fetchall()
            
            for line in old_lines:
                conn.execute("""
                    UPDATE stock_balances 
                    SET quantity = quantity - ?
                    WHERE warehouse_id=? AND item_id=? AND batch_no=''
                """, (line['base_quantity'] or line['quantity'], 
                      txn['to_warehouse_id'], line['item_id']))
        
        # امسح السطور القديمة
        conn.execute("DELETE FROM stock_transaction_lines WHERE transaction_id=?", (tid,))
        
        # حدّث الرأس
        conn.execute("""
            UPDATE stock_transactions
            SET transaction_date=?, reference_no=?, notes=?, status='DRAFT'
            WHERE id=?
        """, (d.get('transaction_date', txn['transaction_date']),
              d.get('reference_no'), d.get('notes'), tid))
        
        # أضف السطور الجديدة
        total_qty = 0
        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(
                conn, line['item_id'], line['uom_id'], line['quantity']
            )
            if base_qty is None:
                return jsonify({'success': False, 'message': f'الوحدة غير مرتبطة'}), 400
            
            conn.execute("""
                INSERT INTO stock_transaction_lines
                (transaction_id, line_no, item_id, uom_id, quantity,
                 base_quantity, unit_cost, total_cost, batch_no)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
            """, (tid, i, line['item_id'], line['uom_id'],
                  line['quantity'], base_qty, line.get('batch_no') or ''))
            total_qty += base_qty
        
        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=0 WHERE id=?",
            (total_qty, tid)
        )
    
    return jsonify({'success': True, 'message': 'تم التعديل'})


# ============================================================
# ترحيل الإذن
# ============================================================
@receipt_bp.route('/<int:tid>/post', methods=['POST'])
def post_receipt(tid):
    with db.transaction() as conn:
        cur = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND status='DRAFT'", (tid,)
        )
        txn = cur.fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الحركة غير موجودة أو مرحّلة'}), 404
        txn = dict(txn)

        cur = conn.execute(
            """SELECT l.*, i.item_type FROM stock_transaction_lines l
               LEFT JOIN items i ON l.item_id = i.id
               WHERE l.transaction_id=?""",
            (tid,)
        )
        lines = [dict(r) for r in cur.fetchall()]

        # إضافة الكميات للمخزون + إنشاء دفعات
        agg = {}
        for line in lines:
            key = line['item_id']
            if key not in agg:
                agg[key] = {'qty': 0.0, 'lines': []}
            agg[key]['qty'] += float(line['base_quantity'] or line['quantity'])
            agg[key]['lines'].append(line)

        for item_id, a in agg.items():
            cur = conn.execute(
                """SELECT id, quantity FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (txn['to_warehouse_id'], item_id)
            )
            existing = cur.fetchone()
            if existing:
                new_qty = float(existing['quantity']) + a['qty']
                conn.execute(
                    "UPDATE stock_balances SET quantity=? WHERE id=?",
                    (new_qty, existing['id'])
                )
            else:
                conn.execute(
                    """INSERT INTO stock_balances
                       (warehouse_id, item_id, batch_no, quantity, average_cost, total_value)
                       VALUES (?, ?, '', ?, 0, 0)""",
                    (txn['to_warehouse_id'], item_id, a['qty'])
                )
            
            # ✅ إنشاء دفعات لكل سطر
            for line in a['lines']:
                qty = float(line['base_quantity'] or line['quantity'])
                unit_cost = float(line.get('unit_cost') or 0)
                total_cost = qty * unit_cost
                
                conn.execute("""
                    INSERT INTO stock_batches
                    (warehouse_id, item_id, receipt_id, receipt_line_id,
                     batch_no, receipt_date, quantity_in, quantity_remaining,
                     unit_cost, total_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    txn['to_warehouse_id'],
                    item_id,
                    txn['id'],
                    line['id'],
                    line.get('batch_no') or '',
                    txn['transaction_date'],
                    qty, qty,
                    unit_cost, total_cost
                ))

        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP WHERE id=?",
            (tid,)
        )

    return jsonify({'success': True, 'message': 'تم الترحيل'})


# ============================================================
# فك الترحيل (للتعديل)
# ============================================================
@receipt_bp.route('/<int:tid>/unpost', methods=['POST'])
def unpost_receipt(tid):
    with db.transaction() as conn:
        txn = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND transaction_type='RECEIPT'",
            (tid,)
        ).fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الإذن غير موجود'}), 404
        txn = dict(txn)
        
        if txn['status'] != 'POSTED':
            return jsonify({'success': False, 'message': 'الإذن مش مرحّل'}), 400
        
        # ✅ تحقق: إذا الإذن مفوتَر → منع فك الترحيل
        if _is_invoiced(conn, tid):
            return jsonify({
                'success': False, 
                'message': 'لا يمكن فك ترحيل إذن مفوتَر. احذف الفاتورة أولاً.'
            }), 400
        
        # اخصم الكميات من المخزون
        lines = conn.execute(
            "SELECT * FROM stock_transaction_lines WHERE transaction_id=?", (tid,)
        ).fetchall()
        
        for line in lines:
            conn.execute("""
                UPDATE stock_balances 
                SET quantity = quantity - ?
                WHERE warehouse_id=? AND item_id=? AND batch_no=''
            """, (line['base_quantity'] or line['quantity'], 
                  txn['to_warehouse_id'], line['item_id']))
        
        # رجّع الحالة لمسودة
        conn.execute("""
            UPDATE stock_transactions 
            SET status='DRAFT', posted_at=NULL 
            WHERE id=?
        """, (tid,))
    
    return jsonify({'success': True, 'message': 'تم فك الترحيل'})


# ============================================================
# حذف إذن (مسودة أو مُرحّل غير مفوتَر)
# ============================================================
@receipt_bp.route('/<int:tid>', methods=['DELETE'])
def delete_receipt(tid):
    with db.transaction() as conn:
        txn = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND transaction_type='RECEIPT'",
            (tid,)
        ).fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الإذن غير موجود'}), 404
        txn = dict(txn)
        
        # ✅ تحقق: إذا الإذن مفوتَر → منع الحذف
        if _is_invoiced(conn, tid):
            return jsonify({
                'success': False, 
                'message': 'لا يمكن حذف إذن مفوتَر. احذف الفاتورة أولاً.'
            }), 400
        
        # لو الإذن مُرحّل → نرجع الكميات من المخزون أولاً
        if txn['status'] == 'POSTED':
            lines = conn.execute(
                "SELECT * FROM stock_transaction_lines WHERE transaction_id=?", (tid,)
            ).fetchall()
            
            for line in lines:
                conn.execute("""
                    UPDATE stock_balances 
                    SET quantity = quantity - ?
                    WHERE warehouse_id=? AND item_id=? AND batch_no=''
                """, (line['base_quantity'] or line['quantity'], 
                      txn['to_warehouse_id'], line['item_id']))
        
        # امسح السطور
        conn.execute("DELETE FROM stock_transaction_lines WHERE transaction_id=?", (tid,))
        
        # امسح الرأس
        conn.execute("DELETE FROM stock_transactions WHERE id=?", (tid,))
    
    return jsonify({'success': True, 'message': 'تم الحذف'})

