from flask import Blueprint, Response, request
from app.database import db
import csv
import io
from datetime import datetime

export_bp = Blueprint('export', __name__)


def _to_csv(headers, rows):
    output = io.StringIO()
    # BOM for Excel to recognize UTF-8
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(headers)
    for r in rows:
        writer.writerow(r)
    return output.getvalue()


def _csv_response(content, filename):
    return Response(
        content,
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'text/csv; charset=utf-8'
        }
    )


@export_bp.route('/items', methods=['GET'])
def export_items():
    rows = db.query("SELECT code, name_ar, name_en, item_type, inventory_account, cost_account FROM items ORDER BY code")
    content = _to_csv(
        ['الكود', 'الاسم عربي', 'الاسم إنجليزي', 'النوع', 'حساب المخزون', 'حساب التكلفة'],
        [[r['code'], r['name_ar'], r['name_en'], r['item_type'], r['inventory_account'], r['cost_account']] for r in rows]
    )
    return _csv_response(content, f'items_{datetime.now().strftime("%Y%m%d")}.csv')


@export_bp.route('/accounts', methods=['GET'])
def export_accounts():
    rows = db.query("SELECT code, name_ar, name_en, level, nature, financial_statement FROM accounts ORDER BY code")
    content = _to_csv(
        ['الكود', 'الاسم عربي', 'الاسم إنجليزي', 'المستوى', 'الطبيعة', 'القائمة'],
        [[r['code'], r['name_ar'], r['name_en'], r['level'], r['nature'], r['financial_statement']] for r in rows]
    )
    return _csv_response(content, f'accounts_{datetime.now().strftime("%Y%m%d")}.csv')


@export_bp.route('/suppliers', methods=['GET'])
def export_suppliers():
    rows = db.query("SELECT code, name_ar, phone, email, tax_number FROM suppliers ORDER BY code")
    content = _to_csv(
        ['الكود', 'الاسم', 'الهاتف', 'البريد', 'الرقم الضريبي'],
        [[r['code'], r['name_ar'], r['phone'], r['email'], r['tax_number']] for r in rows]
    )
    return _csv_response(content, f'suppliers_{datetime.now().strftime("%Y%m%d")}.csv')


@export_bp.route('/customers', methods=['GET'])
def export_customers():
    rows = db.query("SELECT code, name_ar, phone, email, tax_number FROM customers ORDER BY code")
    content = _to_csv(
        ['الكود', 'الاسم', 'الهاتف', 'البريد', 'الرقم الضريبي'],
        [[r['code'], r['name_ar'], r['phone'], r['email'], r['tax_number']] for r in rows]
    )
    return _csv_response(content, f'customers_{datetime.now().strftime("%Y%m%d")}.csv')


@export_bp.route('/stock-balance', methods=['GET'])
def export_stock():
    rows = db.query("""
        SELECT w.name_ar as wh, i.code as item_code, i.name_ar as item_name,
               sb.quantity, sb.average_cost, sb.total_value
        FROM stock_balances sb
        JOIN warehouses w ON sb.warehouse_id = w.id
        JOIN items i ON sb.item_id = i.id
        WHERE sb.quantity != 0
        ORDER BY w.code, i.code
    """)
    content = _to_csv(
        ['المستودع', 'كود الصنف', 'اسم الصنف', 'الكمية', 'متوسط التكلفة', 'القيمة'],
        [[r['wh'], r['item_code'], r['item_name'], r['quantity'], r['average_cost'], r['total_value']] for r in rows]
    )
    return _csv_response(content, f'stock_balance_{datetime.now().strftime("%Y%m%d")}.csv')


@export_bp.route('/journal', methods=['GET'])
def export_journal():
    rows = db.query("""
        SELECT je.entry_no, je.entry_date, je.reference_no,
               jel.account_code, a.name_ar as account_name,
               jel.debit_amount, jel.credit_amount
        FROM journal_entries je
        JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
        LEFT JOIN accounts a ON jel.account_code = a.code
        ORDER BY je.id DESC
    """)
    content = _to_csv(
        ['رقم القيد', 'التاريخ', 'المرجع', 'الكود', 'اسم الحساب', 'مدين', 'دائن'],
        [[r['entry_no'], r['entry_date'], r['reference_no'], r['account_code'],
          r['account_name'], r['debit_amount'], r['credit_amount']] for r in rows]
    )
    return _csv_response(content, f'journal_{datetime.now().strftime("%Y%m%d")}.csv')


@export_bp.route('/trial-balance', methods=['GET'])
def export_trial_balance():
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT a.code, a.name_ar,
                   COALESCE(SUM(jel.debit_amount), 0) as td,
                   COALESCE(SUM(jel.credit_amount), 0) as tc
            FROM accounts a
            LEFT JOIN journal_entry_lines jel ON jel.account_code = a.code
            GROUP BY a.code
            ORDER BY a.code
        """).fetchall()
    content = _to_csv(
        ['الكود', 'الاسم', 'مدين', 'دائن'],
        [[r['code'], r['name_ar'], r['td'], r['tc']] for r in rows]
    )
    return _csv_response(content, f'trial_balance_{datetime.now().strftime("%Y%m%d")}.csv')
