"""
إضافة الجرد (INVENTORY_COUNT) لـ link APIs
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'routes', 'cash_box_routes.py')

print("=" * 60)
print("🔧 إضافة الجرد للـ link")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 1. إضافة الجرد لـ link/stats
# ============================================
old_stats = """    for stype, table, id_field in [
        ('supplier_payments', 'supplier_payments', 'payment_no'),
        ('customer_receipts', 'customer_receipts', 'receipt_no'),
        ('cash_box_transactions', 'cash_box_transactions', 'reference_no'),
        ('petty_cash_expenses', 'petty_cash_expenses', 'expense_no'),
        ('purchase_invoices', 'purchase_invoices', 'invoice_no'),
        ('sales_invoices', 'sales_invoices', 'invoice_no'),
    ]:"""

new_stats = """    for stype, table, id_field in [
        ('supplier_payments', 'supplier_payments', 'payment_no'),
        ('customer_receipts', 'customer_receipts', 'receipt_no'),
        ('cash_box_transactions', 'cash_box_transactions', 'reference_no'),
        ('petty_cash_expenses', 'petty_cash_expenses', 'expense_no'),
        ('purchase_invoices', 'purchase_invoices', 'invoice_no'),
        ('sales_invoices', 'sales_invoices', 'invoice_no'),
        ('inventory_counts', 'inventory_counts', 'count_no'),      # ← جديد
        ('stock_transactions', 'stock_transactions', 'transaction_no'),  # ← جديد
    ]:"""

if old_stats in content:
    content = content.replace(old_stats, new_stats, 1)
    print("  ✅ تم إضافة الجرد لـ link/stats")
else:
    print("  ⚠️ نمط link/stats مش موجود")


# ============================================
# 2. إضافة الجرد لـ movements-with-journals
# ============================================
old_movements = """    # نجمع الحركات من كل الجداول
    queries = {
        'SUPPLIER_PAYMENT': f\"\"\"
            SELECT 'SUPPLIER_PAYMENT' as source_type, id, payment_no as ref_no,
                   payment_date as date, amount, 'دفعة مورد' as description,
                   journal_entry_id
            FROM supplier_payments
            WHERE 1=1 {date_clause}
        \"\"\",
        'CUSTOMER_RECEIPT': f\"\"\"
            SELECT 'CUSTOMER_RECEIPT' as source_type, id, receipt_no as ref_no,
                   receipt_date as date, amount, 'تحصيل عميل' as description,
                   journal_entry_id
            FROM customer_receipts
            WHERE 1=1 {date_clause}
        \"\"\",
        'CASH_BOX_TXN': f\"\"\"
            SELECT 'CASH_BOX_TXN' as source_type, id, reference_no as ref_no,
                   txn_date as date, amount, description,
                   journal_entry_id
            FROM cash_box_transactions
            WHERE 1=1 {date_clause}
        \"\"\",
        'PETTY_CASH_EXPENSE': f\"\"\"
            SELECT 'PETTY_CASH_EXPENSE' as source_type, id, expense_no as ref_no,
                   expense_date as date, amount, description,
                   journal_entry_id
            FROM petty_cash_expenses
            WHERE 1=1 {date_clause}
        \"\"\",
    }"""

new_movements = """    # نجمع الحركات من كل الجداول
    queries = {
        'SUPPLIER_PAYMENT': f\"\"\"
            SELECT 'SUPPLIER_PAYMENT' as source_type, id, payment_no as ref_no,
                   payment_date as date, amount, 'دفعة مورد' as description,
                   journal_entry_id
            FROM supplier_payments
            WHERE 1=1 {date_clause}
        \"\"\",
        'CUSTOMER_RECEIPT': f\"\"\"
            SELECT 'CUSTOMER_RECEIPT' as source_type, id, receipt_no as ref_no,
                   receipt_date as date, amount, 'تحصيل عميل' as description,
                   journal_entry_id
            FROM customer_receipts
            WHERE 1=1 {date_clause}
        \"\"\",
        'CASH_BOX_TXN': f\"\"\"
            SELECT 'CASH_BOX_TXN' as source_type, id, reference_no as ref_no,
                   txn_date as date, amount, description,
                   journal_entry_id
            FROM cash_box_transactions
            WHERE 1=1 {date_clause}
        \"\"\",
        'PETTY_CASH_EXPENSE': f\"\"\"
            SELECT 'PETTY_CASH_EXPENSE' as source_type, id, expense_no as ref_no,
                   expense_date as date, amount, description,
                   journal_entry_id
            FROM petty_cash_expenses
            WHERE 1=1 {date_clause}
        \"\"\",
        'INVENTORY_COUNT': f\"\"\"
            SELECT 'INVENTORY_COUNT' as source_type, id, count_no as ref_no,
                   count_date as date, 0 as amount, 'جرد مخزني' as description,
                   journal_entry_id
            FROM inventory_counts
            WHERE status = 'POSTED' {date_clause}
        \"\"\",
    }"""

if old_movements in content:
    content = content.replace(old_movements, new_movements, 1)
    print("  ✅ تم إضافة الجرد لـ movements")
else:
    print("  ⚠️ نمط movements مش موجود")


# ============================================
# 3. إضافة الجرد لـ search-by-reference
# ============================================
old_search = """    # 6. sales_invoices
    si = db.query(\"\"\"
        SELECT 'SALES_INVOICE' as source_type, id, invoice_no as ref_no,
               invoice_date as date, total_amount as amount,
               'فاتورة بيع' as description,
               journal_entry_id
        FROM sales_invoices
        WHERE invoice_no = ? OR reference_no = ?
    \"\"\", (ref_no, ref_no))
    for r in si:
        results.append(dict(r))"""

new_search = """    # 6. sales_invoices
    si = db.query(\"\"\"
        SELECT 'SALES_INVOICE' as source_type, id, invoice_no as ref_no,
               invoice_date as date, total_amount as amount,
               'فاتورة بيع' as description,
               journal_entry_id
        FROM sales_invoices
        WHERE invoice_no = ? OR reference_no = ?
    \"\"\", (ref_no, ref_no))
    for r in si:
        results.append(dict(r))
    
    # 7. inventory_counts (جديد)
    ic = db.query(\"\"\"
        SELECT 'INVENTORY_COUNT' as source_type, id, count_no as ref_no,
               count_date as date, 0 as amount, 'جرد مخزني' as description,
               journal_entry_id
        FROM inventory_counts
        WHERE count_no = ?
    \"\"\", (ref_no,))
    for r in ic:
        results.append(dict(r))
    
    # 8. stock_transactions (جديد)
    st = db.query(\"\"\"
        SELECT 'STOCK_TRANSACTION' as source_type, id, transaction_no as ref_no,
               transaction_date as date, total_value as amount, 
               notes as description,
               journal_entry_id
        FROM stock_transactions
        WHERE transaction_no = ? AND journal_entry_id IS NOT NULL
    \"\"\", (ref_no,))
    for r in st:
        results.append(dict(r))"""

if old_search in content:
    content = content.replace(old_search, new_search, 1)
    print("  ✅ تم إضافة الجرد لـ search")
else:
    print("  ⚠️ نمط search مش موجود")


with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")