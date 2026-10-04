from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe
from datetime import datetime

pay_bp = Blueprint('payments', __name__)


def _next_payment_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM supplier_payments")
    return f"PAY-{datetime.now().year}-{cur.fetchone()['n']:06d}"


def _next_receipt_no(conn):
    cur = conn.execute("SELECT COUNT(*)+1 as n FROM customer_receipts")
    return f"RCP-{datetime.now().year}-{cur.fetchone()['n']:06d}"


# ============ Supplier Payments ============

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
    return jsonify({'success': True, 'data': json_safe(row)})


@pay_bp.route('/payments/', methods=['POST'])
def create_payment():
    d = request.get_json() or {}
    if not d.get('supplier_id') or not d.get('amount'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        no = _next_payment_no(conn)
        cur = conn.execute("""
            INSERT INTO supplier_payments
            (payment_no, payment_date, supplier_id, payment_method,
             amount, reference, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'POSTED')
        """, (no, d.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
              d['supplier_id'], d.get('payment_method', 'CASH'),
              float(d['amount']), d.get('reference'), d.get('notes')))
        pid = cur.lastrowid

        # Journal entry: Debit AP (2211), Credit Cash/Bank
        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        cur = conn.execute("""
            INSERT INTO journal_entries
            (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
            VALUES (?, ?, 'SUPPLIER_PAYMENT', ?, ?, ?, 'POSTED')
        """, (je_no, d.get('payment_date'), pid, no, f"سداد مورد {no}"))
        je_id = cur.lastrowid

        # Debit AP
        conn.execute("""
            INSERT INTO journal_entry_lines
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 1, '2211', 'ذمم الموردين - سداد', ?, 0)
        """, (je_id, float(d['amount'])))

        # Credit Cash
        cash_acc = '1211' if d.get('payment_method') == 'CASH' else '1212'
        conn.execute("""
            INSERT INTO journal_entry_lines
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 2, ?, 'نقدية - سداد مورد', 0, ?)
        """, (je_id, cash_acc, float(d['amount'])))

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (float(d['amount']), float(d['amount']), je_id))
        conn.execute("UPDATE supplier_payments SET journal_entry_id=? WHERE id=?", (je_id, pid))

    return jsonify({'success': True, 'data': {'id': pid, 'payment_no': no}, 'message': 'تم السداد'}), 201


@pay_bp.route('/payments/<int:pid>', methods=['DELETE'])
def delete_payment(pid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT journal_entry_id FROM supplier_payments WHERE id=?", (pid,))
        row = cur.fetchone()
        if row and row['journal_entry_id']:
            conn.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id=?", (row['journal_entry_id'],))
            conn.execute("DELETE FROM journal_entries WHERE id=?", (row['journal_entry_id'],))
        conn.execute("DELETE FROM supplier_payments WHERE id=?", (pid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})


# ============ Customer Receipts ============

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
    return jsonify({'success': True, 'data': json_safe(row)})


@pay_bp.route('/receipts/', methods=['POST'])
def create_receipt():
    d = request.get_json() or {}
    if not d.get('customer_id') or not d.get('amount'):
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    with db.transaction() as conn:
        no = _next_receipt_no(conn)
        cur = conn.execute("""
            INSERT INTO customer_receipts
            (receipt_no, receipt_date, customer_id, receipt_method,
             amount, reference, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'POSTED')
        """, (no, d.get('receipt_date', datetime.now().strftime('%Y-%m-%d')),
              d['customer_id'], d.get('receipt_method', 'CASH'),
              float(d['amount']), d.get('reference'), d.get('notes')))
        rid = cur.lastrowid

        # Journal: Debit Cash, Credit AR (1221)
        je_no = f"JE-{datetime.now().year}-{str(conn.execute('SELECT COUNT(*)+1 as n FROM journal_entries').fetchone()['n']).zfill(6)}"
        cur = conn.execute("""
            INSERT INTO journal_entries
            (entry_no, entry_date, reference_type, reference_id, reference_no, description, status)
            VALUES (?, ?, 'CUSTOMER_RECEIPT', ?, ?, ?, 'POSTED')
        """, (je_no, d.get('receipt_date'), rid, no, f"تحصيل من عميل {no}"))
        je_id = cur.lastrowid

        cash_acc = '1211' if d.get('receipt_method') == 'CASH' else '1212'
        conn.execute("""
            INSERT INTO journal_entry_lines
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 1, ?, 'نقدية - تحصيل', ?, 0)
        """, (je_id, cash_acc, float(d['amount'])))

        conn.execute("""
            INSERT INTO journal_entry_lines
            (journal_entry_id, line_no, account_code, description, debit_amount, credit_amount)
            VALUES (?, 2, '1221', 'ذمم العملاء - تحصيل', 0, ?)
        """, (je_id, float(d['amount'])))

        conn.execute("UPDATE journal_entries SET total_debit=?, total_credit=? WHERE id=?",
                     (float(d['amount']), float(d['amount']), je_id))
        conn.execute("UPDATE customer_receipts SET journal_entry_id=? WHERE id=?", (je_id, rid))

    return jsonify({'success': True, 'data': {'id': rid, 'receipt_no': no}, 'message': 'تم التحصيل'}), 201


@pay_bp.route('/receipts/<int:rid>', methods=['DELETE'])
def delete_receipt(rid):
    with db.transaction() as conn:
        cur = conn.execute("SELECT journal_entry_id FROM customer_receipts WHERE id=?", (rid,))
        row = cur.fetchone()
        if row and row['journal_entry_id']:
            conn.execute("DELETE FROM journal_entry_lines WHERE journal_entry_id=?", (row['journal_entry_id'],))
            conn.execute("DELETE FROM journal_entries WHERE id=?", (row['journal_entry_id'],))
        conn.execute("DELETE FROM customer_receipts WHERE id=?", (rid,))
    return jsonify({'success': True, 'message': 'تم الحذف'})
