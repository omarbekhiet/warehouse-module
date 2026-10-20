from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe
from app.services.payment_service import payment_service
from datetime import datetime

pay_bp = Blueprint('payments', __name__)


# =========================================
# Payment Methods
# =========================================

@pay_bp.route('/methods/', methods=['GET'])
def list_methods():
    rows = db.query("SELECT * FROM payment_methods WHERE is_active=1 ORDER BY id")
    return jsonify({'success': True, 'data': json_safe(rows)})


# =========================================
# Supplier Payments
# =========================================

@pay_bp.route('/payments/', methods=['GET'])
def list_payments():
    rows = db.query("""
        SELECT sp.*, s.name_ar as supplier_name
        FROM supplier_payments sp
        LEFT JOIN suppliers s ON sp.supplier_id = s.id
        ORDER BY sp.id DESC LIMIT 200
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@pay_bp.route('/payments/<int:pid>', methods=['GET'])
def get_payment(pid):
    row = db.query("""
        SELECT sp.*, s.name_ar as supplier_name, s.code as supplier_code
        FROM supplier_payments sp
        LEFT JOIN suppliers s ON sp.supplier_id = s.id
        WHERE sp.id=?
    """, (pid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    
    # التوزيعات
    allocations = db.query("""
        SELECT pa.*, pi.invoice_date
        FROM payment_allocations pa
        LEFT JOIN purchase_invoices pi ON pa.invoice_id = pi.id
        WHERE pa.payment_id=? AND pa.payment_type='SUPPLIER_PAYMENT'
    """, (pid,))
    row['allocations'] = allocations
    
    return jsonify({'success': True, 'data': json_safe(row)})


@pay_bp.route('/payments/', methods=['POST'])
def create_payment():
    d = request.get_json() or {}
    
    if not d.get('supplier_id') or not d.get('amount'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    result = payment_service.create_supplier_payment(d, user_id=1)
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@pay_bp.route('/payments/<int:pid>', methods=['DELETE'])
def delete_payment(pid):
    with db.transaction() as conn:
        cur = conn.cursor()
        
        # حذف القيد
        cur.execute("SELECT journal_entry_id FROM supplier_payments WHERE id=?", (pid,))
        row = cur.fetchone()
        if row and row['journal_entry_id']:
            cur.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id=?", (row['journal_entry_id'],))
            cur.execute("DELETE FROM journal_entries WHERE id=?", (row['journal_entry_id'],))
        
        # حذف التوزيعات
        cur.execute("DELETE FROM payment_allocations WHERE payment_id=? AND payment_type='SUPPLIER_PAYMENT'", (pid,))
        
        # حذف الدفعة
        cur.execute("DELETE FROM supplier_payments WHERE id=?", (pid,))
        
        conn.commit()
    
    return jsonify({'success': True, 'message': 'تم الحذف'})


# =========================================
# Customer Receipts
# =========================================

@pay_bp.route('/receipts/', methods=['GET'])
def list_receipts():
    rows = db.query("""
        SELECT cr.*, c.name_ar as customer_name
        FROM customer_receipts cr
        LEFT JOIN customers c ON cr.customer_id = c.id
        ORDER BY cr.id DESC LIMIT 200
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@pay_bp.route('/receipts/<int:rid>', methods=['GET'])
def get_receipt(rid):
    row = db.query("""
        SELECT cr.*, c.name_ar as customer_name, c.code as customer_code
        FROM customer_receipts cr
        LEFT JOIN customers c ON cr.customer_id = c.id
        WHERE cr.id=?
    """, (rid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    
    allocations = db.query("""
        SELECT pa.*, si.invoice_date
        FROM payment_allocations pa
        LEFT JOIN sales_invoices si ON pa.invoice_id = si.id
        WHERE pa.payment_id=? AND pa.payment_type='CUSTOMER_RECEIPT'
    """, (rid,))
    row['allocations'] = allocations
    
    return jsonify({'success': True, 'data': json_safe(row)})


@pay_bp.route('/receipts/', methods=['POST'])
def create_receipt():
    d = request.get_json() or {}
    
    if not d.get('customer_id') or not d.get('amount'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    result = payment_service.create_customer_receipt(d, user_id=1)
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@pay_bp.route('/receipts/<int:rid>', methods=['DELETE'])
def delete_receipt(rid):
    with db.transaction() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT journal_entry_id FROM customer_receipts WHERE id=?", (rid,))
        row = cur.fetchone()
        if row and row['journal_entry_id']:
            cur.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id=?", (row['journal_entry_id'],))
            cur.execute("DELETE FROM journal_entries WHERE id=?", (row['journal_entry_id'],))
        
        cur.execute("DELETE FROM payment_allocations WHERE payment_id=? AND payment_type='CUSTOMER_RECEIPT'", (rid,))
        cur.execute("DELETE FROM customer_receipts WHERE id=?", (rid,))
        
        conn.commit()
    
    return jsonify({'success': True, 'message': 'تم الحذف'})


# =========================================
# Open Invoices
# =========================================

@pay_bp.route('/open-invoices/supplier/<int:supplier_id>', methods=['GET'])
def supplier_open_invoices(supplier_id):
    invoices = payment_service.get_supplier_open_invoices(supplier_id)
    return jsonify({'success': True, 'data': invoices})


@pay_bp.route('/open-invoices/customer/<int:customer_id>', methods=['GET'])
def customer_open_invoices(customer_id):
    invoices = payment_service.get_customer_open_invoices(customer_id)
    return jsonify({'success': True, 'data': invoices})



# ============================================================
# Payment Details
# ============================================================

@pay_bp.route('/details/<string:source_type>/<int:payment_id>', methods=['GET'])
def get_payment_details(source_type, payment_id):
    """يجيب تفاصيل دفع معين"""
    row = db.query(
        "SELECT * FROM payment_details WHERE source_type=? AND payment_id=?",
        (source_type, payment_id),
        one=True
    )
    return jsonify({'success': True, 'data': json_safe(row)})


@pay_bp.route('/details', methods=['POST'])
def save_payment_details():
    """يحفظ تفاصيل دفع"""
    d = request.get_json() or {}
    
    payment_type = d.get('payment_type')
    payment_id = d.get('payment_id')
    source_type = d.get('source_type')
    
    if not payment_type or not payment_id or not source_type:
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400
    
    # امسح القديم
    db.execute(
        "DELETE FROM payment_details WHERE source_type=? AND payment_id=?",
        (source_type, payment_id)
    )
    
    # ضيف الجديد
    db.execute("""
        INSERT INTO payment_details 
        (payment_type, payment_id, source_type,
         cheque_no, cheque_bank, cheque_date, cheque_status,
         transfer_no, transfer_bank,
         card_txn_no, card_last4, card_bank,
         wallet_name, wallet_txn_no, wallet_phone,
         notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payment_type, payment_id, source_type,
        d.get('cheque_no'), d.get('cheque_bank'), d.get('cheque_date'), d.get('cheque_status'),
        d.get('transfer_no'), d.get('transfer_bank'),
        d.get('card_txn_no'), d.get('card_last4'), d.get('card_bank'),
        d.get('wallet_name'), d.get('wallet_txn_no'), d.get('wallet_phone'),
        d.get('notes')
    ))
    
    return jsonify({'success': True, 'message': 'تم الحفظ'})


@pay_bp.route('/details/<int:detail_id>', methods=['DELETE'])
def delete_payment_details(detail_id):
    """يمسح تفاصيل دفع"""
    db.execute("DELETE FROM payment_details WHERE id=?", (detail_id,))
    return jsonify({'success': True, 'message': 'تم الحذف'})