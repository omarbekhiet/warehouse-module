"""
إضافة APIs للربط بين الحركات والقيود
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'routes', 'cash_box_routes.py')

print("=" * 60)
print("🔧 إضافة APIs للربط")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_apis = '''


# =========================================
# LINKING: MOVEMENTS <-> JOURNAL ENTRIES
# =========================================

@cb_bp.route('/link/search-by-reference', methods=['GET'])
def search_by_reference():
    """البحث عن حركة برقمها — ويرجع القيد المرتبط"""
    ref_no = request.args.get('ref_no', '').strip()
    if not ref_no:
        return jsonify({'success': False, 'message': 'رقم الحركة مطلوب'}), 400
    
    results = []
    
    # 1. supplier_payments
    sp = db.query("""
        SELECT 'SUPPLIER_PAYMENT' as source_type, id, payment_no as ref_no,
               payment_date as date, amount, 'دفعة مورد' as description,
               journal_entry_id
        FROM supplier_payments
        WHERE payment_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in sp:
        results.append(dict(r))
    
    # 2. customer_receipts
    cr = db.query("""
        SELECT 'CUSTOMER_RECEIPT' as source_type, id, receipt_no as ref_no,
               receipt_date as date, amount, 'تحصيل عميل' as description,
               journal_entry_id
        FROM customer_receipts
        WHERE receipt_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in cr:
        results.append(dict(r))
    
    # 3. cash_box_transactions
    cbt = db.query("""
        SELECT 'CASH_BOX_TXN' as source_type, id, reference_no as ref_no,
               txn_date as date, amount, description,
               journal_entry_id
        FROM cash_box_transactions
        WHERE reference_no = ?
    """, (ref_no,))
    for r in cbt:
        results.append(dict(r))
    
    # 4. petty_cash_expenses
    pce = db.query("""
        SELECT 'PETTY_CASH_EXPENSE' as source_type, id, expense_no as ref_no,
               expense_date as date, amount, description,
               journal_entry_id
        FROM petty_cash_expenses
        WHERE expense_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in pce:
        results.append(dict(r))
    
    # 5. purchase_invoices
    pi = db.query("""
        SELECT 'PURCHASE_INVOICE' as source_type, id, invoice_no as ref_no,
               invoice_date as date, total_amount as amount, 
               'فاتورة شراء' as description,
               journal_entry_id
        FROM purchase_invoices
        WHERE invoice_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in pi:
        results.append(dict(r))
    
    # 6. sales_invoices
    si = db.query("""
        SELECT 'SALES_INVOICE' as source_type, id, invoice_no as ref_no,
               invoice_date as date, total_amount as amount,
               'فاتورة بيع' as description,
               journal_entry_id
        FROM sales_invoices
        WHERE invoice_no = ? OR reference_no = ?
    """, (ref_no, ref_no))
    for r in si:
        results.append(dict(r))
    
    # جلب القيود المرتبطة
    for r in results:
        if r.get('journal_entry_id'):
            je = db.query("""
                SELECT id, entry_no, entry_date, description, 
                       total_debit, total_credit, status
                FROM journal_entries WHERE id = ?
            """, (r['journal_entry_id'],), one=True)
            r['journal'] = dict(je) if je else None
            
            if je:
                lines = db.query("""
                    SELECT line_no, account_code, description,
                           debit_amount, credit_amount
                    FROM journal_entry_lines
                    WHERE journal_entry_id = ?
                    ORDER BY line_no
                """, (je['id'],))
                r['journal']['lines'] = [dict(l) for l in lines]
        else:
            r['journal'] = None
    
    return jsonify({
        'success': True,
        'data': json_safe(results),
        'count': len(results)
    })


@cb_bp.route('/link/search-by-journal/<int:je_id>', methods=['GET'])
def search_by_journal(je_id):
    """البحث عن حركة برقم القيد"""
    je = db.query("""
        SELECT * FROM journal_entries WHERE id = ?
    """, (je_id,), one=True)
    
    if not je:
        return jsonify({'success': False, 'message': 'القيد غير موجود'}), 404
    
    # جلب السطور
    lines = db.query("""
        SELECT * FROM journal_entry_lines
        WHERE journal_entry_id = ?
        ORDER BY line_no
    """, (je_id,))
    
    # جلب الحركة المرتبطة
    source = None
    ref_type = je['reference_type']
    ref_id = je['reference_id']
    
    tables_map = {
        'SUPPLIER_PAYMENT': ('supplier_payments', 'payment_no', 'payment_date', 'amount'),
        'CUSTOMER_RECEIPT': ('customer_receipts', 'receipt_no', 'receipt_date', 'amount'),
        'PETTY_CASH_EXPENSE': ('petty_cash_expenses', 'expense_no', 'expense_date', 'amount'),
        'PURCHASE_INVOICE': ('purchase_invoices', 'invoice_no', 'invoice_date', 'total_amount'),
        'SALES_INVOICE': ('sales_invoices', 'invoice_no', 'invoice_date', 'total_amount'),
        'PURCHASE_RETURN': ('purchase_returns', 'return_no', 'return_date', 'total_amount'),
        'SALES_RETURN': ('sales_returns', 'return_no', 'return_date', 'total_amount'),
        'CASH_BOX_TXN': ('cash_box_transactions', 'reference_no', 'txn_date', 'amount'),
        'CASH_BOX_TRANSFER': ('cash_box_transactions', 'reference_no', 'txn_date', 'amount'),
    }
    
    if ref_type in tables_map and ref_id:
        table, ref_field, date_field, amount_field = tables_map[ref_type]
        row = db.query(f"""
            SELECT *, {ref_field} as ref_no, {date_field} as date, 
                   {amount_field} as amount
            FROM {table} WHERE id = ?
        """, (ref_id,), one=True)
        if row:
            source = dict(row)
            source['source_type'] = ref_type
    
    return jsonify({
        'success': True,
        'data': {
            'journal': {
                'id': je['id'],
                'entry_no': je['entry_no'],
                'entry_date': je['entry_date'],
                'reference_type': ref_type,
                'reference_id': ref_id,
                'reference_no': je['reference_no'],
                'description': je['description'],
                'total_debit': je['total_debit'],
                'total_credit': je['total_credit'],
                'status': je['status'],
                'lines': [dict(l) for l in lines]
            },
            'source': source
        }
    })


@cb_bp.route('/link/movements-with-journals', methods=['GET'])
def movements_with_journals():
    """كل الحركات مع القيود في فترة"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    source_type = request.args.get('source_type')
    limit = request.args.get('limit', 200, type=int)
    
    params_base = []
    where_parts = []
    if date_from:
        where_parts.append("date >= ?")
    if date_to:
        where_parts.append("date <= ?")
    
    date_clause = " AND " + " AND ".join(where_parts) if where_parts else ""
    
    # نجمع الحركات من كل الجداول
    queries = {
        'SUPPLIER_PAYMENT': f"""
            SELECT 'SUPPLIER_PAYMENT' as source_type, id, payment_no as ref_no,
                   payment_date as date, amount, 'دفعة مورد' as description,
                   journal_entry_id
            FROM supplier_payments
            WHERE 1=1 {date_clause}
        """,
        'CUSTOMER_RECEIPT': f"""
            SELECT 'CUSTOMER_RECEIPT' as source_type, id, receipt_no as ref_no,
                   receipt_date as date, amount, 'تحصيل عميل' as description,
                   journal_entry_id
            FROM customer_receipts
            WHERE 1=1 {date_clause}
        """,
        'CASH_BOX_TXN': f"""
            SELECT 'CASH_BOX_TXN' as source_type, id, reference_no as ref_no,
                   txn_date as date, amount, description,
                   journal_entry_id
            FROM cash_box_transactions
            WHERE 1=1 {date_clause}
        """,
        'PETTY_CASH_EXPENSE': f"""
            SELECT 'PETTY_CASH_EXPENSE' as source_type, id, expense_no as ref_no,
                   expense_date as date, amount, description,
                   journal_entry_id
            FROM petty_cash_expenses
            WHERE 1=1 {date_clause}
        """,
    }
    
    results = []
    for stype, sql in queries.items():
        if source_type and source_type != stype:
            continue
        
        params = []
        if date_from:
            params.append(date_from)
        if date_to:
            params.append(date_to)
        
        rows = db.query(sql, params)
        for r in rows:
            row = dict(r)
            # جلب القيد
            if row.get('journal_entry_id'):
                je = db.query("""
                    SELECT entry_no, entry_date, total_debit, status
                    FROM journal_entries WHERE id = ?
                """, (row['journal_entry_id'],), one=True)
                row['journal_no'] = je['entry_no'] if je else None
                row['journal_status'] = je['status'] if je else None
            else:
                row['journal_no'] = None
                row['journal_status'] = None
            results.append(row)
    
    # رتب بالتاريخ
    results.sort(key=lambda x: x.get('date') or '', reverse=True)
    results = results[:limit]
    
    return jsonify({
        'success': True,
        'data': json_safe(results),
        'count': len(results)
    })


@cb_bp.route('/link/stats', methods=['GET'])
def linking_stats():
    """إحصائيات الترابط"""
    stats = {}
    
    # الحركات
    for stype, table, id_field in [
        ('supplier_payments', 'supplier_payments', 'payment_no'),
        ('customer_receipts', 'customer_receipts', 'receipt_no'),
        ('cash_box_transactions', 'cash_box_transactions', 'reference_no'),
        ('petty_cash_expenses', 'petty_cash_expenses', 'expense_no'),
        ('purchase_invoices', 'purchase_invoices', 'invoice_no'),
        ('sales_invoices', 'sales_invoices', 'invoice_no'),
    ]:
        try:
            total = db.query(f"SELECT COUNT(*) as n FROM {table}", one=True)
            linked = db.query(f"SELECT COUNT(*) as n FROM {table} WHERE journal_entry_id IS NOT NULL", one=True)
            stats[table] = {
                'total': total['n'],
                'linked': linked['n'],
                'unlinked': total['n'] - linked['n']
            }
        except:
            stats[table] = {'total': 0, 'linked': 0, 'unlinked': 0}
    
    # القيود
    try:
        je_total = db.query("SELECT COUNT(*) as n FROM journal_entries", one=True)
        je_with_ref = db.query("SELECT COUNT(*) as n FROM journal_entries WHERE reference_no IS NOT NULL", one=True)
        stats['journal_entries'] = {
            'total': je_total['n'],
            'with_reference': je_with_ref['n'],
            'without_reference': je_total['n'] - je_with_ref['n']
        }
    except:
        stats['journal_entries'] = {'total': 0, 'with_reference': 0, 'without_reference': 0}
    
    return jsonify({'success': True, 'data': stats})
'''

# أضف APIs في نهاية الملف
content = content.rstrip() + new_apis

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ تم إضافة APIs")

# تحقق من الصيغة
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ الملف سليم — مفيش أخطاء")
except py_compile.PyCompileError as e:
    print(f"❌ فيه خطأ:")
    print(e)