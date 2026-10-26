import sqlite3

DB = 'J:/warehouse-module/database/warehouse.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ============ 1. حقل payment_type في الفواتير ============
for table in ['purchase_invoices', 'sales_invoices']:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if 'payment_type' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN payment_type TEXT DEFAULT 'CREDIT'")
        print(f"OK: Added payment_type to {table}")
    else:
        print(f"- payment_type already exists in {table}")

# ============ 2. جدول طرق السداد ============
cur.execute("""
CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    account_code TEXT,           -- الحساب الذي يُدين/يُدائن
    requires_clearing INTEGER DEFAULT 0,  -- 1 للشيك والبطاقة
    is_active INTEGER DEFAULT 1
)
""")
print("OK: payment_methods table")

# ============ 3. جدول توزيع الدفعات على الفواتير ============
cur.execute("""
CREATE TABLE IF NOT EXISTS payment_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL,        -- ID من supplier_payments أو customer_receipts
    payment_type TEXT NOT NULL,         -- SUPPLIER_PAYMENT / CUSTOMER_RECEIPT
    invoice_id INTEGER NOT NULL,
    invoice_type TEXT NOT NULL,         -- PURCHASE / SALES
    invoice_no TEXT,
    amount REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: payment_allocations table")

# ============ 4. حسابات جديدة في الدليل ============
new_accounts = [
    ('1225', 'شيكات تحت التحصيل', 'Cheques Under Collection', 'L4', '1250', 'D', 'BS', 'CA'),
    ('1213', 'بطاقات وسيطة', 'Card Clearing', 'L4', '1210', 'D', 'BS', 'CA'),
    ('1214', 'محافظ إلكترونية', 'E-Wallets', 'L4', '1210', 'D', 'BS', 'CA'),
    ('2245', 'شيكات صادرة', 'Cheques Issued', 'L4', '2200', 'C', 'BS', 'CL'),
]

for acc in new_accounts:
    cur.execute("SELECT COUNT(*) FROM accounts WHERE code=?", (acc[0],))
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO accounts 
            (code, name_ar, name_en, level, parent_code, nature,
             financial_statement, bs_group, is_group, is_leaf, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 1)
        """, acc)
        print(f"OK: Added account {acc[0]} - {acc[1]}")
    else:
        print(f"- account {acc[0]} already exists")

# ============ 5. طرق السداد ============
methods = [
    ('CASH',           'نقدي',              'Cash',              '1211', 0),
    ('BANK_TRANSFER',  'تحويل بنكي',        'Bank Transfer',     '1212', 0),
    ('CHEQUE',         'شيك',               'Cheque',            '1225', 1),
    ('CARD',           'بطاقة فيزا',        'Card',              '1213', 1),
    ('WALLET',         'محفظة إلكترونية',   'E-Wallet',          '1214', 1),
]

for m in methods:
    cur.execute("SELECT COUNT(*) FROM payment_methods WHERE code=?", (m[0],))
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO payment_methods (code, name_ar, name_en, account_code, requires_clearing)
            VALUES (?, ?, ?, ?, ?)
        """, m)
        print(f"OK: Added payment method {m[0]}")
    else:
        print(f"- payment method {m[0]} already exists")

conn.commit()

# ============ عرض النتائج ============
print()
print("=" * 60)
print("=== payment_methods ===")
for r in cur.execute("SELECT code, name_ar, account_code, requires_clearing FROM payment_methods"):
    print(f"  {r[0]:15} | {r[1]:20} | حساب: {r[2]} | {'وسيط' if r[3] else 'مباشر'}")

print()
print("=== الحسابات الجديدة ===")
for r in cur.execute("SELECT code, name_ar FROM accounts WHERE code IN ('1225','1213','1214','2245')"):
    print(f"  {r[0]} | {r[1]}")

conn.close()
print()
print("Done!")
