"""
ربط كل الحركات بالقيود والعكس
- إضافة journal_entry_id لكل جدول
- إضافة reference_no للحركات
- التحقق من الترابط
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'warehouse.db')
print(f"Database: {DB_PATH}\n")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ============================================
# 1. فحص الجداول الحالية
# ============================================
print("=" * 60)
print("📊 فحص الجداول الحالية")
print("=" * 60)

tables_to_check = [
    'supplier_payments',
    'customer_receipts',
    'cash_box_transactions',
    'petty_cash_expenses',
    'purchase_invoices',
    'sales_invoices',
    'purchase_returns',
    'sales_returns',
    'receipts',
    'issues',
    'transfers',
    'counts',
    'stock_adjustments',
]

# ابحث عن العمود `reference_no` كـ عمود
def has_column(table, col):
    try:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        return col in cols
    except:
        return False

# اطبع حالة كل جدول
for table in tables_to_check:
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if not cur.fetchone():
        print(f"  ⏭️ {table}: مش موجود")
        continue
    
    has_je = has_column(table, 'journal_entry_id')
    has_ref = has_column(table, 'reference_no')
    
    je_icon = '✅' if has_je else '❌'
    ref_icon = '✅' if has_ref else '❌'
    
    print(f"  {table}: journal_entry_id={je_icon} reference_no={ref_icon}")

# ============================================
# 2. إضافة journal_entry_id لو ناقص
# ============================================
print("\n" + "=" * 60)
print("🔧 إضافة journal_entry_id")
print("=" * 60)

for table in tables_to_check:
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if not cur.fetchone():
        continue
    
    if not has_column(table, 'journal_entry_id'):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN journal_entry_id INTEGER")
            print(f"  ✅ {table}: تم إضافة journal_entry_id")
        except Exception as e:
            print(f"  ⚠️ {table}: {e}")
    else:
        print(f"  ℹ️ {table}: journal_entry_id موجود بالفعل")

# ============================================
# 3. إضافة reference_no لو ناقص
# ============================================
print("\n" + "=" * 60)
print("🔧 إضافة reference_no")
print("=" * 60)

for table in tables_to_check:
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if not cur.fetchone():
        continue
    
    if not has_column(table, 'reference_no'):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN reference_no TEXT")
            print(f"  ✅ {table}: تم إضافة reference_no")
        except Exception as e:
            print(f"  ⚠️ {table}: {e}")
    else:
        print(f"  ℹ️ {table}: reference_no موجود بالفعل")

# ============================================
# 4. تحديث reference_no من الأعمدة الموجودة
# ============================================
print("\n" + "=" * 60)
print("🔗 ربط reference_no بالأعمدة الأصلية")
print("=" * 60)

# supplier_payments: reference_no من payment_no
try:
    cur.execute("""
        UPDATE supplier_payments 
        SET reference_no = payment_no 
        WHERE reference_no IS NULL AND payment_no IS NOT NULL
    """)
    print(f"  ✅ supplier_payments: {cur.rowcount} صف")
except Exception as e:
    print(f"  ⚠️ supplier_payments: {e}")

# customer_receipts: reference_no من receipt_no
try:
    cur.execute("""
        UPDATE customer_receipts 
        SET reference_no = receipt_no 
        WHERE reference_no IS NULL AND receipt_no IS NOT NULL
    """)
    print(f"  ✅ customer_receipts: {cur.rowcount} صف")
except Exception as e:
    print(f"  ⚠️ customer_receipts: {e}")

# petty_cash_expenses: reference_no من expense_no
try:
    cur.execute("""
        UPDATE petty_cash_expenses 
        SET reference_no = expense_no 
        WHERE reference_no IS NULL AND expense_no IS NOT NULL
    """)
    print(f"  ✅ petty_cash_expenses: {cur.rowcount} صف")
except Exception as e:
    print(f"  ⚠️ petty_cash_expenses: {e}")

# purchase_invoices
try:
    cur.execute("""
        UPDATE purchase_invoices 
        SET reference_no = invoice_no 
        WHERE reference_no IS NULL AND invoice_no IS NOT NULL
    """)
    print(f"  ✅ purchase_invoices: {cur.rowcount} صف")
except Exception as e:
    print(f"  ⚠️ purchase_invoices: {e}")

# sales_invoices
try:
    cur.execute("""
        UPDATE sales_invoices 
        SET reference_no = invoice_no 
        WHERE reference_no IS NULL AND invoice_no IS NOT NULL
    """)
    print(f"  ✅ sales_invoices: {cur.rowcount} صف")
except Exception as e:
    print(f"  ⚠️ sales_invoices: {e}")

# ============================================
# 5. فهارس للربط
# ============================================
print("\n" + "=" * 60)
print("📑 فهارس للربط السريع")
print("=" * 60)

indexes = [
    ("idx_je_ref", "journal_entries", "reference_type, reference_id"),
    ("idx_je_refno", "journal_entries", "reference_no"),
    ("idx_sp_je", "supplier_payments", "journal_entry_id"),
    ("idx_cr_je", "customer_receipts", "journal_entry_id"),
    ("idx_cbt_je", "cash_box_transactions", "journal_entry_id"),
    ("idx_pce_je", "petty_cash_expenses", "journal_entry_id"),
    ("idx_pi_je", "purchase_invoices", "journal_entry_id"),
    ("idx_si_je", "sales_invoices", "journal_entry_id"),
]

for idx_name, table, cols in indexes:
    try:
        cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})")
        print(f"  ✅ {idx_name}")
    except Exception as e:
        print(f"  ⚠️ {idx_name}: {e}")

# ============================================
# 6. التحقق من الترابط
# ============================================
print("\n" + "=" * 60)
print("🔍 التحقق من الترابط")
print("=" * 60)

# supplier_payments
try:
    cur.execute("SELECT COUNT(*) FROM supplier_payments")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM supplier_payments WHERE journal_entry_id IS NOT NULL")
    linked = cur.fetchone()[0]
    print(f"  💳 supplier_payments: {linked}/{total} مربوطة بقيد")
except Exception as e:
    print(f"  ⚠️ supplier_payments: {e}")

# customer_receipts
try:
    cur.execute("SELECT COUNT(*) FROM customer_receipts")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM customer_receipts WHERE journal_entry_id IS NOT NULL")
    linked = cur.fetchone()[0]
    print(f"  💰 customer_receipts: {linked}/{total} مربوطة بقيد")
except Exception as e:
    print(f"  ⚠️ customer_receipts: {e}")

# cash_box_transactions
try:
    cur.execute("SELECT COUNT(*) FROM cash_box_transactions")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cash_box_transactions WHERE journal_entry_id IS NOT NULL")
    linked = cur.fetchone()[0]
    print(f"  🔄 cash_box_transactions: {linked}/{total} مربوطة بقيد")
except Exception as e:
    print(f"  ⚠️ cash_box_transactions: {e}")

# petty_cash_expenses
try:
    cur.execute("SELECT COUNT(*) FROM petty_cash_expenses")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM petty_cash_expenses WHERE journal_entry_id IS NOT NULL")
    linked = cur.fetchone()[0]
    print(f"  🧾 petty_cash_expenses: {linked}/{total} مربوطة بقيد")
except Exception as e:
    print(f"  ⚠️ petty_cash_expenses: {e}")

# journal_entries
try:
    cur.execute("SELECT COUNT(*) FROM journal_entries")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM journal_entries WHERE reference_no IS NOT NULL")
    linked = cur.fetchone()[0]
    print(f"  📒 journal_entries: {linked}/{total} لها reference_no")
except Exception as e:
    print(f"  ⚠️ journal_entries: {e}")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ تم الربط!")
print("=" * 60)
print("\n📌 المطلوب بعد كده:")
print("  1. تحديث payment_service.py عشان يسجل journal_entry_id")
print("  2. تحديث الـ Services التانية")
print("  3. إضافة API للبحث بالرقم")