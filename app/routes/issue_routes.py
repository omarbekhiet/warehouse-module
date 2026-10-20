from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from app.services.accounting_service import accounting_service
from app.services.cost_engine import cost_engine

issue_bp = Blueprint('issues', __name__)


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


# ============================================================
# قائمة الأذون
# ============================================================
@issue_bp.route('/', methods=['GET'])
def list_issues():
    rows = db.query(
        """SELECT t.*, w.name_ar as warehouse_name
           FROM stock_transactions t
           LEFT JOIN warehouses w ON t.from_warehouse_id = w.id
           WHERE t.transaction_type='ISSUE'
           ORDER BY t.id DESC LIMIT 100"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@issue_bp.route('/<int:tid>', methods=['GET'])
def get_issue(tid):
    txn = db.query("SELECT * FROM stock_transactions WHERE id=?", (tid,), one=True)
    if not txn:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    lines = db.query(
        """SELECT l.*, i.name_ar as item_name, i.code as item_code
           FROM stock_transaction_lines l
           JOIN items i ON l.item_id = i.id
           WHERE l.transaction_id=? ORDER BY l.line_no""",
        (tid,)
    )
    txn['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(txn)})


# ============================================================
# معاينة التكلفة قبل الحفظ
# ============================================================
@issue_bp.route('/preview-cost', methods=['POST'])
def preview_cost():
    """معاينة تكلفة الصرف حسب السياسة"""
    d = request.get_json() or {}
    
    warehouse_id = d.get('warehouse_id')
    item_id = d.get('item_id')
    qty = d.get('quantity')
    
    if not warehouse_id or not item_id or not qty:
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    with db.get_connection() as conn:
        result = cost_engine.calculate_issue_cost(
            conn, int(warehouse_id), int(item_id), float(qty)
        )
    
    return jsonify(result)


# ============================================================
# إنشاء إذن صرف (مع حساب التكلفة حسب السياسة)
# ============================================================
@issue_bp.route('/', methods=['POST'])
def create_issue():
    d = request.get_json() or {}
    if not d.get('warehouse_id') or not d.get('lines'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    movement_code = d.get('movement_code', 'ISSUE')

    with db.transaction() as conn:
        txn_no = _next_txn_no(conn, 'ISS', 'ISSUE')
        cur = conn.execute(
            """INSERT INTO stock_transactions
               (transaction_no, transaction_type, transaction_date,
                from_warehouse_id, reference_type, reference_no,
                status, notes, created_by, movement_code)
               VALUES (?, 'ISSUE', ?, ?, ?, ?, 'DRAFT', ?, 1, ?)""",
            (txn_no, d.get('transaction_date', '2026-01-01'),
             d['warehouse_id'], d.get('reference_type'),
             d.get('reference_no'), d.get('notes'), movement_code)
        )
        txn_id = cur.lastrowid

        total_qty = 0
        total_val = 0
        for i, line in enumerate(d['lines'], start=1):
            factor, base_qty = _get_base_quantity(
                conn, line['item_id'], line['uom_id'], line['quantity']
            )
            if base_qty is None:
                return jsonify({'success': False, 'message': f'الوحدة غير مرتبطة بالصنف #{line["item_id"]}'}), 400

            # ✅ احسب الكمية المعلّقة (بانتظار الفاتورة)
            pending = conn.execute("""
                SELECT COALESCE(SUM(stl.base_quantity), 0) as pending_qty
                FROM stock_transaction_lines stl
                JOIN stock_transactions st ON stl.transaction_id = st.id
                WHERE st.transaction_type = 'RECEIPT'
                  AND st.status = 'POSTED'
                  AND stl.item_id = ?
                  AND st.to_warehouse_id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM purchase_invoices pi 
                      WHERE pi.receipt_id = st.id
                  )
            """, (line['item_id'], d['warehouse_id'])).fetchone()
            
            pending_qty = float(pending['pending_qty'] or 0)
            
            # جيب الرصيد الكلي
            bal = conn.execute("""
                SELECT quantity FROM stock_balances
                WHERE warehouse_id=? AND item_id=? AND batch_no=''
            """, (d['warehouse_id'], line['item_id'])).fetchone()
            
            if not bal:
                return jsonify({'success': False, 'message': f'لا يوجد رصيد للصنف #{line["item_id"]}'}), 400
            
            total_available = float(bal['quantity'] or 0)
            available_qty = total_available - pending_qty
            
            if base_qty > available_qty:
                return jsonify({
                    'success': False,
                    'message': f'الكمية المطلوبة ({base_qty}) تتجاوز الرصيد القابل للصرف ({available_qty}). '
                              f'يوجد {pending_qty} وحدة بانتظار الفاتورة.'
                }), 400
            
            # ✅ احسب التكلفة حسب السياسة (FIFO / LIFO / Average)
            cost_result = cost_engine.calculate_issue_cost(
                conn, d['warehouse_id'], line['item_id'], base_qty
            )
            
            if not cost_result['success']:
                return jsonify({
                    'success': False,
                    'message': cost_result.get('message', 'خطأ في حساب التكلفة')
                }), 400
            
            unit_cost = cost_result['unit_cost']
            total_cost = cost_result['total_cost']
            
            # سجّل الدفعات المستخدمة (للخصم عند الترحيل)
            batches_used_json = None
            if cost_result.get('batches_used'):
                import json
                batches_used_json = json.dumps(cost_result['batches_used'], ensure_ascii=False)
            
            conn.execute(
                """INSERT INTO stock_transaction_lines
                   (transaction_id, line_no, item_id, uom_id, quantity,
                    base_quantity, unit_cost, total_cost, batch_no, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (txn_id, i, line['item_id'], line['uom_id'],
                 float(line['quantity']), float(base_qty), unit_cost,
                 float(total_cost), line.get('batch_no') or '',
                 batches_used_json)  # ← حفظ تفاصيل الدفعات
            )
            total_qty += base_qty
            total_val += float(total_cost)

        conn.execute(
            "UPDATE stock_transactions SET total_qty=?, total_value=? WHERE id=?",
            (total_qty, round(total_val, 4), txn_id)
        )

    return jsonify({'success': True, 'data': {'id': txn_id, 'transaction_no': txn_no}}), 201


# ============================================================
# ترحيل إذن الصرف (خصم الدفعات + المخزون + القيد)
# ============================================================
@issue_bp.route('/<int:tid>/post', methods=['POST'])
def post_issue(tid):
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

        # ✅ اخصم من المخزون + من الدفعات
        for line in lines:
            # خصم من stock_balances
            cur = conn.execute(
                """SELECT id, quantity, total_value FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (txn['from_warehouse_id'], line['item_id'])
            )
            existing = cur.fetchone()
            if existing:
                new_qty = float(existing['quantity']) - float(line['base_quantity'] or line['quantity'])
                new_val = float(existing['total_value']) - float(line['total_cost'])
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute(
                    "UPDATE stock_balances SET quantity=?, total_value=?, average_cost=? WHERE id=?",
                    (new_qty, new_val, new_avg, existing['id'])
                )
            
            # ✅ خصم من الدفعات (لو محفوظة)
            if line.get('notes'):
                try:
                    import json
                    batches_used = json.loads(line['notes'])
                    cost_engine.consume_batches_in_db(conn, batches_used)
                except Exception as e:
                    print(f"⚠️ Error consuming batches: {e}")

        # توليد القيد المحاسبي
        je_id = accounting_service.create_journal_entry(conn, txn, lines)

        conn.execute(
            "UPDATE stock_transactions SET status='POSTED', posted_at=CURRENT_TIMESTAMP, journal_entry_id=? WHERE id=?",
            (je_id, tid)
        )

    return jsonify({'success': True, 'message': 'تم الترحيل', 'data': {'journal_entry_id': je_id}})


# ============================================================
# فك ترحيل إذن الصرف (إرجاع الكميات للدفعات)
# ============================================================
@issue_bp.route('/<int:tid>/unpost', methods=['POST'])
def unpost_issue(tid):
    with db.transaction() as conn:
        txn = conn.execute(
            "SELECT * FROM stock_transactions WHERE id=? AND transaction_type='ISSUE'",
            (tid,)
        ).fetchone()
        if not txn:
            return jsonify({'success': False, 'message': 'الإذن غير موجود'}), 404
        txn = dict(txn)
        
        if txn['status'] != 'POSTED':
            return jsonify({'success': False, 'message': 'الإذن مش مرحّل'}), 400
        
        lines = [dict(r) for r in conn.execute(
            "SELECT * FROM stock_transaction_lines WHERE transaction_id=?", (tid,)
        ).fetchall()]
        
        # إرجاع الكميات للمخزون
        for line in lines:
            bal = conn.execute(
                """SELECT id, quantity, total_value FROM stock_balances
                   WHERE warehouse_id=? AND item_id=? AND batch_no=''""",
                (txn['from_warehouse_id'], line['item_id'])
            ).fetchone()
            
            if bal:
                new_qty = float(bal['quantity']) + float(line['base_quantity'] or line['quantity'])
                new_val = float(bal['total_value']) + float(line['total_cost'])
                new_avg = new_val / new_qty if new_qty > 0 else 0
                conn.execute(
                    "UPDATE stock_balances SET quantity=?, total_value=?, average_cost=? WHERE id=?",
                    (new_qty, new_val, new_avg, bal['id'])
                )
            
            # ✅ إرجاع للدفعات
            if line.get('notes'):
                try:
                    import json
                    batches_used = json.loads(line['notes'])
                    cost_engine.restore_batches_in_db(conn, batches_used)
                except Exception as e:
                    print(f"⚠️ Error restoring batches: {e}")
        
        conn.execute("""
            UPDATE stock_transactions 
            SET status='DRAFT', posted_at=NULL 
            WHERE id=?
        """, (tid,))
    
    return jsonify({'success': True, 'message': 'تم فك الترحيل'})
