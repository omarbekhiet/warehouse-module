from flask import Blueprint, request, send_file, jsonify
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




# =========================================
# EXCEL IMPORT/EXPORT
# =========================================

from app.services.excel_service import excel_service
from flask import send_file, make_response


@export_bp.route('/excel/templates', methods=['GET'])
def list_excel_templates():
    """قائمة قوالب Excel"""
    return jsonify({
        'success': True,
        'data': excel_service.list_templates()
    })


@export_bp.route('/excel/export/<template_key>', methods=['GET'])
def export_excel(template_key):
    """تصدير البيانات لـ Excel"""
    output, error = excel_service.export_to_excel(template_key)
    
    if error:
        return jsonify({'success': False, 'message': error}), 400
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{template_key}_{timestamp}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@export_bp.route('/excel/import-template/<template_key>', methods=['GET'])
def download_import_template(template_key):
    """تحميل قالب فارغ للاستيراد"""
    output = excel_service.get_import_template(template_key)
    
    if not output:
        return jsonify({'success': False, 'message': 'قالب غير موجود'}), 404
    
    filename = f"import_{template_key}_template.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@export_bp.route('/excel/import/<template_key>', methods=['POST'])
def import_excel(template_key):
    """استيراد من Excel"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'مافيش ملف'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': 'مافيش ملف'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'message': 'الملف يجب أن يكون Excel'}), 400
    
    try:
        file_content = file.read()
        result = excel_service.import_from_excel(template_key, file_content)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/excel/preview/<template_key>', methods=['POST'])
def preview_excel_import(template_key):
    """معاينة الاستيراد بدون حفظ (dry run)"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'مافيش ملف'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': 'مافيش ملف'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'message': 'الملف يجب أن يكون Excel'}), 400
    
    try:
        file_content = file.read()
        result = excel_service.import_from_excel(template_key, file_content, dry_run=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500