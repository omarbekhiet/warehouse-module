from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe, to_decimal, round_decimal
from app.services.accounting_service import accounting_service
from app.services.doc_number_service import doc_number_service

invoice_bp = Blueprint('purchase_invoices', __name__)


# ============================================================
# قائمة الفواتير
# ============================================================
@invoice_bp.route('/', methods=['GET'])
def list_invoices():
    status = request.args.get('status')
    sql = """
        SELECT pi.*, s.name_ar as supplier_name, w.name_ar as warehouse_name
        FROM purchase_invoices pi
        LEFT JOIN suppliers s ON pi.supplier_id = s.id
        LEFT JOIN warehouses w ON pi.warehouse_id = w.id
    """
    params = []
    if status:
        sql += " WHERE pi.status=?"
        params.append(status)
    sql += " ORDER BY pi.id DESC LIMIT 100"
    rows = db.query(sql, params)
    return jsonify({'success': True, 'data': json_safe(rows)})


# ============================================================
# أذون الاستلام غير المفوتَرة
# ============================================================
@invoice_bp.route('/available-receipts', methods=['GET'])
def available_receipts():
    """أذون الاستلام غير المفوتَرة"""
    rows = db.query("""
        SELECT
            st.id,
            st.transaction_no,
            st.transaction_date,
            st.to_warehouse_id,
            st.total_qty,
            st.reference_no,
            st.notes,
            st.supplier_id,
            w.code as warehouse_code,
            w.name_ar as warehouse_name,
            s.code as supplier_code,
            s.name_ar as supplier_name
        FROM stock_transactions st
        LEFT JOIN warehouses w ON st.to_warehouse_id = w.id
        LEFT JOIN suppliers s ON st.supplier_id = s.id
        WHERE st.transaction_type = 'RECEIPT'
          AND st.status = 'POSTED'
          AND NOT EXISTS (
              SELECT 1 FROM purchase_invoices pi WHERE pi.receipt_id = st.id
          )
        ORDER BY st.id DESC
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


# ============================================================
# عرض فاتورة واحدة
# ============================================================
@invoice_bp.route('/<int:iid>', methods=['GET'])
def get_invoice(iid):
    inv = db.query("""
        SELECT pi.*, s.name_ar as supplier_name, s.code as supplier_code,
               w.name_ar as warehouse_name
        FROM purchase_invoices pi
        LEFT JOIN suppliers s ON pi.supplier_id = s.id
        LEFT JOIN warehouses w ON pi.warehouse_id = w.id
        WHERE pi.id=?
    """, (iid,), one=True)
    if not inv:
        return jsonify({'success': False, 'message': 'الفاتورة غير موجودة'}), 404
    
    lines = db.query("""
        SELECT l.*, i.name_ar as item_name, i.code as item_code,
               u.name_ar as uom_name
        FROM purchase_invoice_lines l
        LEFT JOIN items i ON l.item_id = i.id
        LEFT JOIN units_of_measure u ON l.uom_id = u.id
        WHERE l.invoice_id=?
        ORDER BY l.line_no
    """, (iid,))
    inv['lines'] = lines
    return jsonify({'success': True, 'data': json_safe(inv)})


# ============================================================
# إنشاء فاتورة من إذن استلام
# ============================================================
@invoice_bp.route('/', methods=['POST'])
def create_invoice():
    d = request.get_json() or {}
    
    receipt_id = d.get('receipt_id')
    if not receipt_id:
        return jsonify({'success': False, 'message': 'يجب اختيار إذن استلام'}), 400
    
    if not d.get('lines'):
        return jsonify({'success': False, 'message': 'يجب إضافة بنود'}), 400
    
    supplier_id = d.get('supplier_id')
    if not supplier_id:
        return jsonify({'success': False, 'message': 'يجب اختيار المورد'}), 400
    
    try:
        with db.transaction() as conn:
            # جيب إذن الاستلام
            receipt = conn.execute(
                "SELECT * FROM stock_transactions WHERE id=? AND transaction_type='RECEIPT'",
                (receipt_id,)
            ).fetchone()
            
            if not receipt:
                return jsonify({'success': False, 'message': 'إذن الاستلام غير موجود'}), 404
            receipt = dict(receipt)
            
            # تحقق من عدم وجود فاتورة
            existing = conn.execute(
                "SELECT id FROM purchase_invoices WHERE receipt_id=?", (receipt_id,)
            ).fetchone()
            if existing:
                return jsonify({'success': False, 'message': 'يوجد فاتورة لهذا الإذن بالفعل'}), 400
            
            # رقم الفاتورة
            invoice_no = d.get('invoice_no') or doc_number_service.invoice_purchase(conn)
            
            # الحسابات
            subtotal = sum(float(l['quantity']) * float(l['unit_cost']) for l in d['lines'])
            tax_rate = float(d.get('tax_rate', 0))
            tax_amount = round(float(subtotal or 0) * float(tax_rate or 0) / 100, 4)
            total = float(subtotal) + float(tax_amount)
            
            # إدراج الفاتورة
            cur = conn.execute("""
                INSERT INTO purchase_invoices
                (invoice_no, invoice_date, supplier_id, warehouse_id,
                 receipt_id, movement_code, reference_no,
                 subtotal, tax_rate, tax_amount, total_amount,
                 status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, 'PINV', ?, ?, ?, ?, ?, 'DRAFT', ?, 1)
            """, (
                invoice_no,
                d.get('invoice_date', '2026-01-01'),
                supplier_id,
                receipt['to_warehouse_id'],
                receipt_id,
                d.get('reference_no'),
                subtotal, tax_rate, tax_amount, total,
                d.get('notes')
            ))
            invoice_id = cur.lastrowid
            
            # إدراج البنود
            for i, line in enumerate(d['lines'], start=1):
                qty = float(line['quantity'])
                price = float(line['unit_cost'])
                base_qty = qty
                line_subtotal = qty * price
                ltax_rate = float(line.get('tax_rate', 0) or 0)
                line_tax = line_subtotal * ltax_rate / 100
                line_total = line_subtotal + line_tax

                conn.execute("""
                    INSERT INTO purchase_invoice_lines
                    (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                     unit_price, discount_pct, tax_rate,
                     line_subtotal, line_tax, line_total, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id, i, line['item_id'], line.get('uom_id'),
                    qty, base_qty,
                    price, 0, ltax_rate,
                    line_subtotal, line_tax, line_total,
                    line.get('notes')
                ))
        
        return jsonify({
            'success': True,
            'data': {'id': invoice_id, 'invoice_no': invoice_no}
        }), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 400


# ============================================================
# تعديل فاتورة (مسودة فقط)
# ============================================================
@invoice_bp.route('/<int:iid>', methods=['PUT'])
def update_invoice(iid):
    d = request.get_json() or {}
    
    if not d.get('lines'):
        return jsonify({'success': False, 'message': 'يجب إضافة بنود'}), 400
    
    try:
        with db.transaction() as conn:
            inv = conn.execute(
                "SELECT * FROM purchase_invoices WHERE id=? AND status='DRAFT'", (iid,)
            ).fetchone()
            if not inv:
                return jsonify({'success': False, 'message': 'الفاتورة غير موجودة أو مرحّلة'}), 404
            
            # الحسابات
            subtotal = sum(float(l['quantity']) * float(l['unit_cost']) for l in d['lines'])
            tax_rate = float(d.get('tax_rate', 0))
            tax_amount = round(float(subtotal or 0) * float(tax_rate or 0) / 100, 4)
            total = float(subtotal) + float(tax_amount)
            
            # حدّث الفاتورة
            conn.execute("""
                UPDATE purchase_invoices
                SET invoice_date=?, supplier_id=?, reference_no=?, notes=?,
                    subtotal=?, tax_rate=?, tax_amount=?, total_amount=?
                WHERE id=?
            """, (
                d.get('invoice_date'),
                d.get('supplier_id'),
                d.get('reference_no'),
                d.get('notes'),
                subtotal, tax_rate, tax_amount, total,
                iid
            ))
            
            # امسح البنود القديمة
            conn.execute("DELETE FROM purchase_invoice_lines WHERE invoice_id=?", (iid,))
            
            # أضف البنود الجديدة
            for i, line in enumerate(d['lines'], start=1):
                qty = float(line['quantity'])
                price = float(line['unit_cost'])
                base_qty = qty
                line_subtotal = qty * price
                ltax_rate = float(line.get('tax_rate', 0) or 0)
                line_tax = line_subtotal * ltax_rate / 100
                line_total = line_subtotal + line_tax
                
                conn.execute("""
                    INSERT INTO purchase_invoice_lines
                    (invoice_id, line_no, item_id, uom_id, quantity, base_quantity,
                     unit_price, discount_pct, tax_rate,
                     line_subtotal, line_tax, line_total, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    iid, i, line['item_id'], line.get('uom_id'),
                    qty, base_qty,
                    price, 0, ltax_rate,
                    line_subtotal, line_tax, line_total,
                    line.get('notes')
                ))
        
        return jsonify({'success': True, 'message': 'تم التعديل'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 400


# ============================================================
# ترحيل الفاتورة (مع تحديث المخزون)
# ============================================================
@invoice_bp.route('/<int:iid>/post', methods=['POST'])
def post_invoice(iid):
    try:
        with db.transaction() as conn:
            inv = conn.execute(
                "SELECT * FROM purchase_invoices WHERE id=? AND status='DRAFT'", (iid,)
            ).fetchone()
            if not inv:
                return jsonify({'success': False, 'message': 'الفاتورة غير موجودة أو مرحّلة'}), 404
            inv = dict(inv)
            
            lines = [dict(r) for r in conn.execute(
                "SELECT * FROM purchase_invoice_lines WHERE invoice_id=?", (iid,)
            ).fetchall()]
            
            if not lines:
                return jsonify({'success': False, 'message': 'لا توجد بنود'}), 400
            
            # ============================================================
            # 1. تحديث stock_balances بالسعر والقيمة (المتوسط المرجح)
            # ============================================================
            for line in lines:
                item_id = line['item_id']
                qty = float(line['quantity'])
                unit_cost = float(line['unit_price'])
                total_cost = float(line['line_total'])
                
                bal = conn.execute("""
                    SELECT id, quantity, average_cost, total_value
                    FROM stock_balances
                    WHERE warehouse_id=? AND item_id=? AND batch_no=''
                """, (inv['warehouse_id'], item_id)).fetchone()
                
                if not bal:
                    conn.execute("""
                        INSERT INTO stock_balances
                        (warehouse_id, item_id, batch_no, quantity, average_cost, total_value)
                        VALUES (?, ?, '', ?, ?, ?)
                    """, (inv['warehouse_id'], item_id, qty, unit_cost, total_cost))
                else:
                    bal = dict(bal)
                    old_total_value = float(bal['total_value'] or 0)
                    old_qty = float(bal['quantity'] or 0)
                    new_total_value = old_total_value + total_cost
                    new_avg = new_total_value / old_qty if old_qty > 0 else 0
                    
                    conn.execute("""
                        UPDATE stock_balances
                        SET total_value=?, average_cost=?
                        WHERE id=?
                    """, (new_total_value, new_avg, bal['id']))
            
            # ============================================================
            # 2. توليد القيد المحاسبي المزدوج
            # ============================================================
            wh = conn.execute(
                "SELECT account_code, name_ar FROM warehouses WHERE id=?",
                (inv['warehouse_id'],)
            ).fetchone()
            
            if not wh or not wh['account_code']:
                return jsonify({
                    'success': False,
                    'message': 'المستودع غير مرتبط بحساب مخزون'
                }), 400
            
            warehouse_account = wh['account_code']
            stock_amount = float(inv['subtotal'])
            tax_amount = float(inv['tax_amount'])
            total_amount = float(inv['total_amount'])
            
            entry_no = doc_number_service.journal(conn)
            
            cur = conn.execute("""
                INSERT INTO journal_entries
                (entry_no, entry_date, reference_type, reference_id,
                 reference_no, description, status)
                VALUES (?, ?, 'PURCHASE_INVOICE', ?, ?, ?, 'POSTED')
            """, (
                entry_no,
                inv['invoice_date'],
                inv['id'],
                inv['invoice_no'],
                f"قيد فاتورة مشتريات - {inv['invoice_no']}"
            ))
            je_id = cur.lastrowid
            
            lines_to_insert = [
                {
                    'account': warehouse_account,
                    'debit': stock_amount,
                    'credit': 0,
                    'description': f"قيمة مخزون - {inv['invoice_no']}"
                },
                {
                    'account': '120201',
                    'debit': tax_amount,
                    'credit': 0,
                    'description': f"ضريبة قيمة مضافة - {inv['invoice_no']}"
                },
                {
                    'account': '220298',
                    'debit': 0,
                    'credit': stock_amount,
                    'description': f"إقفال استلامات - {inv['invoice_no']}"
                },
                {
                    'account': '220201',
                    'debit': 0,
                    'credit': total_amount,
                    'description': f"استحقاق مورد - {inv['invoice_no']}"
                }
            ]
            
            line_no = 1
            total_debit = 0
            total_credit = 0
            
            for l in lines_to_insert:
                conn.execute("""
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_no, account_code, description,
                     debit_amount, credit_amount, warehouse_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    je_id, line_no, l['account'], l['description'],
                    float(l['debit']), float(l['credit']),
                    inv['warehouse_id']
                ))
                total_debit += float(l['debit'])
                total_credit += float(l['credit'])
                line_no += 1
            
            conn.execute("""
                UPDATE journal_entries
                SET total_debit=?, total_credit=?
                WHERE id=?
            """, (total_debit, total_credit, je_id))
            
            # ============================================================
            # 3. تحديث الفاتورة
            # ============================================================
            conn.execute("""
                UPDATE purchase_invoices 
                SET status='POSTED', journal_entry_id=?, posted_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (je_id, iid))
            
            return jsonify({
                'success': True,
                'message': 'تم ترحيل الفاتورة + تحديث المخزون + توليد القيد',
                'data': {
                    'journal_entry_id': je_id,
                    'journal_entry_no': entry_no,
                    'stock_amount': stock_amount,
                    'tax_amount': tax_amount,
                    'total_amount': total_amount
                }
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# حذف فاتورة
# ============================================================
@invoice_bp.route('/<int:iid>', methods=['DELETE'])
def delete_invoice(iid):
    inv = db.query("SELECT status FROM purchase_invoices WHERE id=?", (iid,), one=True)
    if not inv:
        return jsonify({'success': False, 'message': 'غير موجودة'}), 404
    if inv['status'] == 'POSTED':
        return jsonify({'success': False, 'message': 'لا يمكن حذف فاتورة مرحّلة'}), 400
    
    db.execute("DELETE FROM purchase_invoice_lines WHERE invoice_id=?", (iid,))
    db.execute("DELETE FROM purchase_invoices WHERE id=?", (iid,))
    return jsonify({'success': True})