from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

clearing_bp = Blueprint('clearing', __name__)


@clearing_bp.route('/summary', methods=['GET'])
def clearing_summary():
    """ملخص الحسابات الوسيطة."""
    rows = db.query(
        """SELECT 
             jel.account_code,
             jel.description,
             SUM(jel.debit_amount) as total_debit,
             SUM(jel.credit_amount) as total_credit,
             SUM(jel.debit_amount) - SUM(jel.credit_amount) as balance
           FROM journal_entry_lines jel
           WHERE jel.account_code LIKE '1236%'
           GROUP BY jel.account_code
           ORDER BY jel.account_code"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@clearing_bp.route('/grni', methods=['GET'])
def grni_report():
    """تقرير البضاعة المستلمة بدون فاتورة (GRNI)."""
    rows = db.query(
        """SELECT 
             t.id as txn_id,
             t.transaction_no,
             t.transaction_date,
             w.name_ar as warehouse_name,
             i.code as item_code,
             i.name_ar as item_name,
             l.base_quantity,
             l.unit_cost,
             l.total_cost,
             i.clearing_account
           FROM stock_transactions t
           JOIN stock_transaction_lines l ON t.id = l.transaction_id
           JOIN items i ON l.item_id = i.id
           JOIN warehouses w ON t.to_warehouse_id = w.id
           WHERE t.transaction_type='RECEIPT'
             AND t.status='POSTED'
             AND (t.invoice_id IS NULL OR t.invoice_id = 0)
           ORDER BY t.transaction_date DESC, t.id DESC"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@clearing_bp.route('/invoices', methods=['GET'])
def invoices_with_clearing():
    """الفواتير وتأثيرها على الحسابات الوسيطة."""
    rows = db.query(
        """SELECT 
             pi.id,
             pi.invoice_no,
             pi.invoice_date,
             pi.total_amount,
             pi.status,
             s.name_ar as supplier_name,
             w.name_ar as warehouse_name,
             pi.stock_txn_id,
             st.transaction_no as stock_txn_no
           FROM purchase_invoices pi
           LEFT JOIN suppliers s ON pi.supplier_id = s.id
           LEFT JOIN warehouses w ON pi.warehouse_id = w.id
           LEFT JOIN stock_transactions st ON pi.stock_txn_id = st.id
           ORDER BY pi.id DESC"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@clearing_bp.route('/statement/<account_code>', methods=['GET'])
def clearing_statement(account_code):
    """كشف حساب لحساب وسيط محدد."""
    rows = db.query(
        """SELECT 
             je.entry_no,
             je.entry_date,
             je.reference_no,
             je.description,
             jel.debit_amount,
             jel.credit_amount,
             (SELECT SUM(jel2.debit_amount) - SUM(jel2.credit_amount)
              FROM journal_entry_lines jel2
              JOIN journal_entries je2 ON jel2.journal_entry_id = je2.id
              WHERE jel2.account_code = jel.account_code
                AND je2.id <= je.id) as running_balance
           FROM journal_entry_lines jel
           JOIN journal_entries je ON jel.journal_entry_id = je.id
           WHERE jel.account_code = ?
           ORDER BY je.entry_date, je.id""",
        (account_code,)
    )
    return jsonify({'success': True, 'data': json_safe(rows)})


@clearing_bp.route('/unmatched', methods=['GET'])
def unmatched_receipts():
    """الاستلامات غير المرتبطة بفواتير."""
    rows = db.query(
        """SELECT 
             t.id,
             t.transaction_no,
             t.transaction_date,
             t.total_value,
             w.name_ar as warehouse_name,
             CAST(julianday('now') - julianday(t.transaction_date) AS INTEGER) as age_days
           FROM stock_transactions t
           JOIN warehouses w ON t.to_warehouse_id = w.id
           WHERE t.transaction_type='RECEIPT'
             AND t.status='POSTED'
             AND (t.invoice_id IS NULL OR t.invoice_id = 0)
           ORDER BY t.transaction_date"""
    )
    return jsonify({'success': True, 'data': json_safe(rows)})
