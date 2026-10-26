"""
إنشاء جداول السطور المتعددة للدفعات والتحصيلات
+ إعدادات الضرائب والخصومات
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'warehouse.db')
print(f"Database: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("\n📦 إنشاء الجداول...")

# ============================================
# 1. payment_lines (سطور الدفعات والتحصيلات)
# ============================================
cur.execute("""
    CREATE TABLE IF NOT EXISTS payment_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_type TEXT NOT NULL,
        parent_id INTEGER NOT NULL,
        line_no INTEGER NOT NULL,
        
        -- نوع السطر
        line_type TEXT NOT NULL DEFAULT 'MAIN',
        
        -- الحساب
        account_code TEXT NOT NULL,
        account_name TEXT,
        
        -- المبلغ
        amount REAL NOT NULL,
        direction TEXT NOT NULL DEFAULT 'DEBIT',
        
        -- الضرائب
        tax_rate REAL DEFAULT 0,
        tax_base REAL DEFAULT 0,
        
        -- الخصومات
        discount_type TEXT,
        discount_rate REAL DEFAULT 0,
        
        -- تفاصيل
        description TEXT,
        reference TEXT,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_pl_parent ON payment_lines(parent_type, parent_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_pl_account ON payment_lines(account_code)")
print("  ✅ payment_lines")

# ============================================
# 2. tax_settings (إعدادات الضرائب)
# ============================================
cur.execute("""
    CREATE TABLE IF NOT EXISTS tax_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name_ar TEXT NOT NULL,
        name_en TEXT,
        tax_type TEXT NOT NULL DEFAULT 'VAT',
        rate REAL DEFAULT 0,
        account_code TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        applies_to TEXT DEFAULT 'BOTH',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  ✅ tax_settings")

# ============================================
# 3. discount_settings (إعدادات الخصومات)
# ============================================
cur.execute("""
    CREATE TABLE IF NOT EXISTS discount_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name_ar TEXT NOT NULL,
        name_en TEXT,
        discount_type TEXT NOT NULL DEFAULT 'TRADE',
        default_rate REAL DEFAULT 0,
        account_code TEXT NOT NULL,
        applies_to TEXT DEFAULT 'BOTH',
        is_active INTEGER DEFAULT 1,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  ✅ discount_settings")

# ============================================
# 4. إضافة بيانات افتراضية
# ============================================
print("\n📝 إضافة بيانات افتراضية...")

# ضريبة القيمة المضافة 14%
cur.execute("SELECT COUNT(*) FROM tax_settings WHERE code='VAT'")
if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO tax_settings 
        (code, name_ar, name_en, tax_type, rate, account_code, is_default, applies_to)
        VALUES ('VAT', 'ضريبة قيمة مضافة', 'VAT', 'VAT', 14, '1410', 1, 'BOTH')
    """)
    print("  ✅ ضريبة القيمة المضافة (14%)")

# ضريبة الخصم والإضافة 1%
cur.execute("SELECT COUNT(*) FROM tax_settings WHERE code='WHT'")
if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO tax_settings 
        (code, name_ar, name_en, tax_type, rate, account_code, is_default, applies_to)
        VALUES ('WHT', 'ضريبة خصم وإضافة', 'Withholding Tax', 'WHT', 1, '1420', 0, 'BOTH')
    """)
    print("  ✅ ضريبة خصم وإضافة (1%)")

# خصم تجاري 5%
cur.execute("SELECT COUNT(*) FROM discount_settings WHERE code='TRADE_5'")
if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO discount_settings 
        (code, name_ar, name_en, discount_type, default_rate, account_code, applies_to)
        VALUES ('TRADE_5', 'خصم تجاري 5%', 'Trade Discount 5%', 'TRADE', 5, '5201', 'BOTH')
    """)
    print("  ✅ خصم تجاري 5%")

# خصم نقدي 2%
cur.execute("SELECT COUNT(*) FROM discount_settings WHERE code='CASH_2'")
if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO discount_settings 
        (code, name_ar, name_en, discount_type, default_rate, account_code, applies_to)
        VALUES ('CASH_2', 'خصم نقدي 2%', 'Cash Discount 2%', 'CASH', 2, '5202', 'BOTH')
    """)
    print("  ✅ خصم نقدي 2%")

# ============================================
# 5. تحديث supplier_payments و customer_receipts
# ============================================
print("\n📝 تحديث الجداول الموجودة...")

# إضافة أعمدة جديدة لـ supplier_payments
for col in [
    ("gross_amount", "REAL DEFAULT 0"),
    ("discount_amount", "REAL DEFAULT 0"),
    ("tax_amount", "REAL DEFAULT 0"),
    ("net_amount", "REAL DEFAULT 0"),
]:
    try:
        cur.execute(f"ALTER TABLE supplier_payments ADD COLUMN {col[0]} {col[1]}")
        print(f"  ✅ supplier_payments: {col[0]}")
    except sqlite3.OperationalError:
        pass  # موجود بالفعل

# إضافة أعمدة جديدة لـ customer_receipts
for col in [
    ("gross_amount", "REAL DEFAULT 0"),
    ("discount_amount", "REAL DEFAULT 0"),
    ("tax_amount", "REAL DEFAULT 0"),
    ("net_amount", "REAL DEFAULT 0"),
]:
    try:
        cur.execute(f"ALTER TABLE customer_receipts ADD COLUMN {col[0]} {col[1]}")
        print(f"  ✅ customer_receipts: {col[0]}")
    except sqlite3.OperationalError:
        pass

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✅ تم إنشاء كل الجداول بنجاح!")
print("=" * 60)