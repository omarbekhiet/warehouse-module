"""
اختبار شامل لقاعدة البيانات — نسخة محسّنة
"""
import sqlite3
import os
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'warehouse.db')

print(f"Database: {DB_PATH}\n")

if not os.path.exists(DB_PATH):
    print("❌ الداتابيز مش موجودة!")
    exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ============================================
# 1. الجداول المتوقعة (بأسماء صحيحة)
# ============================================
CORE_TABLES = {
    'البيانات الأساسية': [
        'accounts', 'users', 'settings', 'roles',
        'warehouses', 'items', 'item_groups', 'units_of_measure',
        'suppliers', 'customers',
    ],
    'المشتريات': [
        'purchase_requisitions', 'purchase_orders', 'purchase_invoices',
        'purchase_returns', 'purchase_invoice_lines',
        'supplier_payments', 'payment_allocations', 'payment_methods',
    ],
    'المبيعات': [
        'sales_invoices', 'sales_returns', 'sales_invoice_lines',
        'customer_receipts',
    ],
    'المخازن': [
        'material_requests', 'stock_transactions', 'stock_transaction_lines',
        'stock_balances', 'inventory_counts', 'inventory_count_lines',
        'cost_layers',
    ],
    'المحاسبة': [
        'journal_entries', 'journal_entry_lines',
        'inventory_account_mappings', 'account_types',
    ],
    'الخزائن (جديدة)': [
        'cash_boxes', 'banks', 'payment_cards',
        'cash_box_transactions',
    ],
    'النثريات (جديدة)': [
        'expense_categories', 'petty_cash_expenses', 'expense_details',
    ],
    'الضرائب والخصومات (جديدة)': [
        'tax_settings', 'discount_settings', 'payment_lines',
    ],
    'التسوية البنكية (جديدة)': [
        'bank_reconciliations', 'bank_reconciliation_items',
    ],
    'الفروع (جديدة)': [
        'branches',
    ],
    'التفاصيل الإضافية': [
        'purchase_order_lines', 'purchase_requisition_lines',
        'purchase_return_lines', 'sales_return_lines',
        'material_request_lines', 'payment_details',
        'cheque_settlements', 'card_settlements',
    ],
}

# ============================================
# 2. فحص الجداول
# ============================================
print("=" * 70)
print("📋 1. الجداول حسب الفئة")
print("=" * 70)

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
existing = {r['name'] for r in cur.fetchall()}

missing_total = 0
found_total = 0

for category, tables in CORE_TABLES.items():
    found = [t for t in tables if t in existing]
    missing = [t for t in tables if t not in existing]
    
    found_total += len(found)
    missing_total += len(missing)
    
    icon = '✅' if not missing else '⚠️'
    print(f"\n{icon} {category}: {len(found)}/{len(tables)}")
    
    for t in found:
        cur.execute(f"SELECT COUNT(*) as n FROM {t}")
        cnt = cur.fetchone()['n']
        print(f"    ✅ {t:35} — {cnt} صف")
    
    for t in missing:
        print(f"    ❌ {t:35} — مفقود")

# ============================================
# 3. الفهارس
# ============================================
print("\n" + "=" * 70)
print("📑 2. الفهارس")
print("=" * 70)

cur.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
idx_count = cur.fetchone()['n']
print(f"  📊 إجمالي الفهارس: {idx_count}")

# ============================================
# 4. العلاقات
# ============================================
print("\n" + "=" * 70)
print("🔗 3. العلاقات (Foreign Keys)")
print("=" * 70)

fk_count = 0
for table in sorted(existing):
    cur.execute(f"PRAGMA foreign_key_list({table})")
    fks = cur.fetchall()
    if fks:
        fk_count += len(fks)
        # نتجاهل التفاصيل عشان نختصر

print(f"  📊 إجمالي العلاقات: {fk_count}")

# ============================================
# 5. البيانات اليتيمة
# ============================================
print("\n" + "=" * 70)
print("🔍 4. البيانات اليتيمة")
print("=" * 70)

orphan_checks = [
    ('purchase_invoices', 'supplier_id', 'suppliers', 'id'),
    ('sales_invoices', 'customer_id', 'customers', 'id'),
    ('supplier_payments', 'supplier_id', 'suppliers', 'id'),
    ('customer_receipts', 'customer_id', 'customers', 'id'),
    ('journal_entry_lines', 'journal_entry_id', 'journal_entries', 'id'),
    ('cash_box_transactions', 'box_id', 'cash_boxes', 'id'),
    ('petty_cash_expenses', 'cash_box_id', 'cash_boxes', 'id'),
    ('petty_cash_expenses', 'category_id', 'expense_categories', 'id'),
    ('bank_reconciliations', 'bank_id', 'banks', 'id'),
    ('purchase_invoice_lines', 'invoice_id', 'purchase_invoices', 'id'),
    ('sales_invoice_lines', 'invoice_id', 'sales_invoices', 'id'),
]

orphan_total = 0
for child_table, child_field, parent_table, parent_field in orphan_checks:
    if child_table not in existing or parent_table not in existing:
        continue
    
    try:
        cur.execute(f"""
            SELECT COUNT(*) as n FROM {child_table} c
            WHERE c.{child_field} IS NOT NULL
              AND c.{child_field} NOT IN (SELECT {parent_field} FROM {parent_table})
        """)
        cnt = cur.fetchone()['n']
        
        if cnt > 0:
            print(f"  ⚠️ {child_table}.{child_field}: {cnt} يتيم")
            orphan_total += cnt
        else:
            print(f"  ✅ {child_table}.{child_field}")
    except:
        pass

# ============================================
# 6. القيود المحاسبية
# ============================================
print("\n" + "=" * 70)
print("📒 5. القيود المحاسبية")
print("=" * 70)

try:
    cur.execute("""
        SELECT COUNT(*) as n FROM journal_entries 
        WHERE ABS(COALESCE(total_debit, 0) - COALESCE(total_credit, 0)) > 0.01
    """)
    unbalanced = cur.fetchone()['n']
    if unbalanced > 0:
        print(f"  ❌ {unbalanced} قيد غير متوازن")
    else:
        print(f"  ✅ كل القيود متوازنة")

    cur.execute("""
        SELECT COUNT(*) as n FROM journal_entries je
        LEFT JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
        WHERE jel.id IS NULL
    """)
    no_lines = cur.fetchone()['n']
    if no_lines > 0:
        print(f"  ❌ {no_lines} قيد بدون سطور")
    else:
        print(f"  ✅ كل القيود عندها سطور")
except Exception as e:
    print(f"  ⚠️ {e}")

# ============================================
# 7. الأرصدة
# ============================================
print("\n" + "=" * 70)
print("💰 6. الأرصدة")
print("=" * 70)

for table, label, icon in [
    ('cash_boxes', 'خزائن', '💵'),
    ('banks', 'بنوك', '🏦'),
    ('payment_cards', 'بطاقات', '💳'),
]:
    if table in existing:
        try:
            cur.execute(f"SELECT COUNT(*) as n, COALESCE(SUM(current_balance), 0) as total FROM {table} WHERE is_active=1")
            r = cur.fetchone()
            print(f"  {icon} {label}: {r['n']} — الإجمالي: {r['total']:.2f}")
        except:
            pass

# ============================================
# ملخص نهائي
# ============================================
print("\n" + "=" * 70)
print("📊 ملخص نهائي")
print("=" * 70)

total_tables = len(existing)

print(f"  📋 الجداول:")
print(f"     ✅ متوقعة: {found_total}")
print(f"     ❌ مفقودة: {missing_total}")
print(f"     ➕ إجمالي في الداتابيز: {total_tables}")

print(f"\n  🔗 العلاقات: {fk_count}")
print(f"  📑 الفهارس: {idx_count}")
print(f"  ⚠️ صفوف يتيمة: {orphan_total}")

print()
issues = missing_total + orphan_total
if issues == 0:
    print("  🎉 ممتاز! قاعدة البيانات سليمة 100%")
elif issues <= 10:
    print(f"  ✅ قاعدة البيانات جيدة — {issues} مشكلة")
else:
    print(f"  ⚠️ فيه {issues} مشكلة محتاجة مراجعة")

# حفظ التقرير
report_path = os.path.join(os.path.dirname(__file__), 'database_report.txt')
try:
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("تقرير قاعدة البيانات\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"إجمالي الجداول: {total_tables}\n")
        f.write(f"جداول متوقعة: {found_total}\n")
        f.write(f"جداول مفقودة: {missing_total}\n")
        f.write(f"العلاقات: {fk_count}\n")
        f.write(f"الفهارس: {idx_count}\n")
        f.write(f"صفوف يتيمة: {orphan_total}\n")
    print(f"\n  📄 التقرير محفوظ: {report_path}")
except Exception as e:
    print(f"\n  ⚠️ خطأ في حفظ التقرير: {e}")

conn.close()
print()