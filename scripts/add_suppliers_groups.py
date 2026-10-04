import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# ============ جدول الموردين ============
conn.execute("""
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    tax_number TEXT,
    account_code TEXT,
    payment_terms INTEGER DEFAULT 30,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: suppliers table")

# ============ جدول مجموعات الأصناف ============
conn.execute("""
CREATE TABLE IF NOT EXISTS item_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    parent_id INTEGER,
    level INTEGER DEFAULT 1,
    
    -- الحسابات المحاسبية
    inventory_account TEXT,
    cost_account TEXT,
    revenue_account TEXT,
    clearing_account TEXT,
    
    -- إعدادات افتراضية
    default_cost_method TEXT DEFAULT 'WEIGHTED_AVERAGE',
    default_uom_id INTEGER,
    
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES item_groups(id)
)
""")
print("OK: item_groups table")

# ============ إضافة حقل المجموعة للأصناف ============
cur = conn.execute("PRAGMA table_info(items)")
cols = [r[1] for r in cur.fetchall()]

if 'group_id' not in cols:
    conn.execute("ALTER TABLE items ADD COLUMN group_id INTEGER")
    print("OK: Added group_id to items")
else:
    print("- group_id already exists")

if 'clearing_account' not in cols:
    conn.execute("ALTER TABLE items ADD COLUMN clearing_account TEXT")
    print("OK: Added clearing_account to items")
else:
    print("- clearing_account already exists")

conn.commit()
print()
print("=== suppliers columns ===")
for r in conn.execute("PRAGMA table_info(suppliers)"):
    print(f"  {r[1]} ({r[2]})")

print()
print("=== item_groups columns ===")
for r in conn.execute("PRAGMA table_info(item_groups)"):
    print(f"  {r[1]} ({r[2]})")

conn.close()
print()
print("Done!")
