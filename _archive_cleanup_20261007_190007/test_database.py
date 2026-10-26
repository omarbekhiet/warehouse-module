"""
اختبار شامل لقاعدة البيانات
- الجداول
- العلاقات
- البيانات اليتيمة
- الفهارس
- الأعمدة
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
# 1. الجداول المتوقعة
# ============================================
EXPECTED_TABLES = [
    # أساسية
    'accounts', 'users', 'settings',
    'warehouses', 'items', 'item_groups', 'uom',
    'suppliers', 'customers',
    
    # مشتريات
    'requisitions', 'purchase_orders', 'purchase_invoices',
    'purchase_returns', 'receipts',
    'supplier_payments', 'payment_allocations',
    'payment_methods',
    
    # مبيعات
    'sales_invoices', 'sales_returns', 'issues',
    'customer_receipts',
    
    # مخازن
    'material_requests', 'transfers', 'counts',
    'stock_adjustments', 'stock_transactions',
    
    # محاسبة
    'journal_entries', 'journal_entry_lines',
    
    # خزائن (جديدة)
    'cash_boxes', 'banks', 'payment_cards',
    'cash_box_transactions',
    
    # نثريات (جديدة)
    'expense_categories', 'petty_cash_expenses', 'expense_details',
    
    # ضرائب وخصومات (جديدة)
    'tax_settings', 'discount_settings',
    'payment_lines',
    
    # تسوية بنكية (جديدة)
    'bank_reconciliations', 'bank_reconciliation_items',
    
    # فروع (جديدة)
    'branches',
]

print("=" * 70)
print("📋 1. الجداول")
print("=" * 70)

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
existing = {r['name'] for r in cur.fetchall()}

missing = []
for t in EXPECTED_TABLES:
    if t in existing:
        cur.execute(f"SELECT COUNT(*) as n FROM {t}")
        cnt = cur.fetchone()['n']
        print(f"  ✅ {t:35} — {cnt} صف")
    else:
        print(f"  ❌ {t:35} — مفقود")
        missing.append(t)

extra = existing - set(EXPECTED_TABLES)
if extra:
    print(f"\n  📌 جداول إضافية ({len(extra)}):")
    for t in sorted(extra):
        cur.execute(f"SELECT COUNT(*) as n FROM {t}")
        cnt = cur.fetchone()['n']
        print(f"     • {t} ({cnt} صف)")

# ============================================
# 2. الفهارس
# ============================================
print("\n" + "=" * 70)
print("📑 2. الفهارس (Indexes)")
print("=" * 70)

cur.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY tbl_name")
indexes = cur.fetchall()

by_table = defaultdict(list)
for idx in indexes:
    by_table[idx['tbl_name']].append(idx['name'])

total_idx = len(indexes)
print(f"  📊 إجمالي الفهارس: {total_idx}\n")

for table in sorted(by_table.keys()):
    idx_list = by_table[table]
    print(f"  {table}: {len(idx_list)} فهرس")
    for idx_name in idx_list[:3]:
        print(f"     • {idx_name}")
    if len(idx_list) > 3:
        print(f"     ... و {len(idx_list) - 3} آخرين")

# ============================================
# 3. العلاقات (Foreign Keys)
# ============================================
print("\n" + "=" * 70)
print("🔗 3. العلاقات (Foreign Keys)")
print("=" * 70)

fk_count = 0
for table in sorted(existing):
    cur.execute(f"PRAGMA foreign_key_list({table})")
    fks = cur.fetchall()
    if fks:
        print(f"\n  {table}:")
        for fk in fks:
            fk_count += 1
            print(f"    → {fk['from']} = {fk['table']}.{fk['to']}")

print(f"\n  📊 إجمالي العلاقات: {fk_count}")

# ============================================
# 4. البيانات اليتيمة (Orphan Records)
# ============================================
print("\n" + "=" * 70)
print("🔍 4. البيانات اليتيمة (Orphan Records)")
print("=" * 70)

orphan_checks = [
    # (الجدول, الحقل, الجدول الأب, حقل الأب)
    ('purchase_invoices', 'supplier_id', 'suppliers', 'id'),
    ('sales_invoices', 'customer_id', 'customers', 'id'),
    ('supplier_payments', 'supplier_id', 'suppliers', 'id'),
    ('customer_receipts', 'customer_id', 'customers', 'id'),
    ('journal_entry_lines', 'journal_entry_id', 'journal_entries', 'id'),
    ('cash_box_transactions', 'box_id', 'cash_boxes', 'id'),
    ('petty_cash_expenses', 'cash_box_id', 'cash_boxes', 'id'),
    ('petty_cash_expenses', 'category_id', 'expense_categories', 'id'),
    ('payment_lines', 'parent_id', 'supplier_payments', 'id'),
    ('bank_reconciliations', 'bank_id', 'banks', 'id'),
]

orphan_count = 0
for child_table, child_field, parent_table, parent_field in orphan_checks:
    # تحقق إن الجدول موجود
    if child_table not in existing or parent_table not in existing:
        continue
    
    # تحقق إن الحقل موجود
    cur.execute(f"PRAGMA table_info({child_table})")
    child_cols = [c['name'] for c in cur.fetchall()]
    if child_field not in child_cols:
        continue
    
    cur.execute(f"PRAGMA table_info({parent_table})")
    parent_cols = [c['name'] for c in cur.fetchall()]
    if parent_field not in parent_cols:
        continue
    
    # ابحث عن orphans
    try:
        cur.execute(f"""
            SELECT COUNT(*) as n FROM {child_table} c
            WHERE c.{child_field} IS NOT NULL
              AND c.{child_field} NOT IN (SELECT {parent_field} FROM {parent_table})
        """)
        cnt = cur.fetchone()['n']
        
        if cnt > 0:
            print(f"  ⚠️ {child_table}.{child_field} → {parent_table}: {cnt} صف يتيم")
            orphan_count += cnt
        else:
            print(f"  ✅ {child_table}.{child_field} → {parent_table}: نظيف")
    except Exception as e:
        print(f"  ⚠️ {child_table}.{child_field}: {e}")

# ============================================
# 5. الأعمدة المهمة
# ============================================
print("\n" + "=" * 70)
print("📋 5. الأعمدة المهمة")
print("=" * 70)

important_columns = [
    # (الجدول, الأعمدة المطلوبة)
    ('supplier_payments', ['id', 'payment_no', 'payment_date', 'supplier_id', 'amount', 'journal_entry_id', 'reference_no']),
    ('customer_receipts', ['id', 'receipt_no', 'receipt_date', 'customer_id', 'amount', 'journal_entry_id', 'reference_no']),
    ('cash_box_transactions', ['id', 'box_id', 'box_type', 'txn_type', 'txn_date', 'amount', 'journal_entry_id', 'reference_no']),
    ('petty_cash_expenses', ['id', 'expense_no', 'expense_date', 'category_id', 'cash_box_id', 'amount', 'journal_entry_id', 'reference_no']),
    ('journal_entries', ['id', 'entry_no', 'entry_date', 'reference_type', 'reference_id', 'reference_no', 'total_debit', 'total_credit', 'status']),
    ('journal_entry_lines', ['id', 'journal_entry_id', 'line_no', 'account_code', 'debit_amount', 'credit_amount']),
    ('cash_boxes', ['id', 'code', 'name_ar', 'account_code', 'opening_balance', 'current_balance', 'is_active']),
    ('banks', ['id', 'code', 'name_ar', 'account_code', 'current_balance']),
    ('payment_cards', ['id', 'code', 'name_ar', 'account_code', 'current_balance']),
    ('payment_lines', ['id', 'parent_type', 'parent_id', 'line_no', 'account_code', 'amount', 'direction']),
    ('tax_settings', ['id', 'code', 'name_ar', 'rate', 'account_code']),
    ('discount_settings', ['id', 'code', 'name_ar', 'default_rate', 'account_code']),
    ('branches', ['id', 'code', 'name_ar', 'is_active']),
]

missing_cols_total = 0
for table, expected_cols in important_columns:
    if table not in existing:
        print(f"  ❌ {table}: الجدول مفقود")
        continue
    
    cur.execute(f"PRAGMA table_info({table})")
    actual_cols = {c['name'] for c in cur.fetchall()}
    
    missing_cols = [c for c in expected_cols if c not in actual_cols]
    
    if missing_cols:
        print(f"  ⚠️ {table}: ناقص — {', '.join(missing_cols)}")
        missing_cols_total += len(missing_cols)
    else:
        print(f"  ✅ {table}: كل الأعمدة موجودة")

# ============================================
# 6. التحقق من القيود
# ============================================
print("\n" + "=" * 70)
print("📒 6. التحقق من القيود المحاسبية")
print("=" * 70)

# قيود غير متوازنة
try:
    cur.execute("""
        SELECT id, entry_no, total_debit, total_credit 
        FROM journal_entries 
        WHERE ABS(COALESCE(total_debit, 0) - COALESCE(total_credit, 0)) > 0.01
    """)
    unbalanced = cur.fetchall()
    if unbalanced:
        print(f"  ❌ {len(unbalanced)} قيد غير متوازن:")
        for je in unbalanced[:5]:
            print(f"     • {je['entry_no']}: مدين={je['total_debit']}, دائن={je['total_credit']}")
    else:
        print(f"  ✅ كل القيود متوازنة")
except Exception as e:
    print(f"  ⚠️ {e}")

# قيود بدون سطور
try:
    cur.execute("""
        SELECT je.id, je.entry_no 
        FROM journal_entries je
        LEFT JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
        WHERE jel.id IS NULL
    """)
    no_lines = cur.fetchall()
    if no_lines:
        print(f"  ❌ {len(no_lines)} قيد بدون سطور:")
        for je in no_lines[:5]:
            print(f"     • {je['entry_no']}")
    else:
        print(f"  ✅ كل القيود عندها سطور")
except Exception as e:
    print(f"  ⚠️ {e}")

# ============================================
# 7. الأرصدة
# ============================================
print("\n" + "=" * 70)
print("💰 7. الأرصدة")
print("=" * 70)

# الخزائن
try:
    cur.execute("SELECT COUNT(*) as n, COALESCE(SUM(current_balance), 0) as total FROM cash_boxes WHERE is_active=1")
    r = cur.fetchone()
    print(f"  💵 خزائن: {r['n']} — الإجمالي: {r['total']:.2f}")
except Exception as e:
    print(f"  ⚠️ الخزائن: {e}")

# البنوك
try:
    cur.execute("SELECT COUNT(*) as n, COALESCE(SUM(current_balance), 0) as total FROM banks WHERE is_active=1")
    r = cur.fetchone()
    print(f"  🏦 بنوك: {r['n']} — الإجمالي: {r['total']:.2f}")
except Exception as e:
    print(f"  ⚠️ البنوك: {e}")

# البطاقات
try:
    cur.execute("SELECT COUNT(*) as n, COALESCE(SUM(current_balance), 0) as total FROM payment_cards WHERE is_active=1")
    r = cur.fetchone()
    print(f"  💳 بطاقات: {r['n']} — الإجمالي: {r['total']:.2f}")
except Exception as e:
    print(f"  ⚠️ البطاقات: {e}")

# ============================================
# ملخص نهائي
# ============================================
print("\n" + "=" * 70)
print("📊 ملخص نهائي")
print("=" * 70)

total_tables = len(existing)
missing_tables = len(missing)
extra_tables = len(extra)
total_orphans = orphan_count
total_missing_cols = missing_cols_total

print(f"  📋 الجداول:")
print(f"     ✅ موجودة: {total_tables}")
print(f"     ❌ مفقودة: {missing_tables}")
print(f"     ➕ إضافية: {extra_tables}")

print(f"\n  🔗 العلاقات: {fk_count}")
print(f"  📑 الفهارس: {total_idx}")
print(f"  ⚠️ صفوف يتيمة: {total_orphans}")
print(f"  📋 أعمدة ناقصة: {total_missing_cols}")

# النتيجة النهائية
issues = missing_tables + total_orphans + total_missing_cols

print()
if issues == 0:
    print("  🎉 ممتاز! قاعدة البيانات سليمة 100%")
elif issues <= 5:
    print(f"  ✅ قاعدة البيانات جيدة — {issues} مشكلة بسيطة")
elif issues <= 20:
    print(f"  ⚠️ قاعدة البيانات متوسطة — {issues} مشكلة")
else:
    print(f"  ❌ قاعدة البيانات فيها {issues} مشكلة محتاجة مراجعة")

# حفظ التقرير
report_path = os.path.join(os.path.dirname(__file__), 'database_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"تقرير قاعدة البيانات\n")
    f.write(f"={'=' * 60}\n\n")
    f.write(f"الجداول: {total_tables}\n")
    f.write(f"مفقودة: {missing_tables}\n")
    f.write(f"إضافية: {extra_tables}\n")
    f.write(f"العلاقات: {fk_count}\n")
    f.write(f"الفهارس: {total_idx}\n")
    f.write(f"صفوف يتيمة: {total_orphans}\n")
    f.write(f"أعمدة ناقصة: {total_missing_cols}\n")

if missing:
    f.write(f"\nجداول مفقودة:\n")
    for t in missing:
        f.write(f"  - {t}\n")

print(f"\n  📄 التقرير محفوظ: {report_path}")

conn.close()