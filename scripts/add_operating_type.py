import sqlite3

DB = 'J:/warehouse-module/database/warehouse.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# === 1. حقل operating_type ===
cur.execute("PRAGMA table_info(items)")
cols = [r[1] for r in cur.fetchall()]

if 'operating_type' not in cols:
    cur.execute("ALTER TABLE items ADD COLUMN operating_type TEXT DEFAULT 'OPERATING'")
    print("OK: Added operating_type to items")
else:
    print("- operating_type already exists")

# === 2. حساب 1270 ===
cur.execute("SELECT COUNT(*) FROM accounts WHERE code='1270'")
if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO accounts 
        (code, name_ar, name_en, level, parent_code, nature,
         financial_statement, bs_group, is_group, is_leaf, is_active)
        VALUES 
        ('1270', 'مخزون غير تشغيلي', 'Non-Operating Inventory',
         'L4', '1230', 'D', 'BS', 'CA', 0, 1, 1)
    """)
    print("OK: Added account 1270 (Non-Operating Inventory)")
else:
    print("- account 1270 already exists")

# === 3. حساب 1271 ===
cur.execute("SELECT COUNT(*) FROM accounts WHERE code='1271'")
if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO accounts 
        (code, name_ar, name_en, level, parent_code, nature,
         financial_statement, bs_group, is_group, is_leaf, is_active)
        VALUES 
        ('1271', 'قطع غيار رأسمالية', 'Capital Spare Parts',
         'L4', '1230', 'D', 'BS', 'CA', 0, 1, 1)
    """)
    print("OK: Added account 1271 (Capital Spare Parts)")
else:
    print("- account 1271 already exists")

conn.commit()

# === عرض النتائج ===
print()
print("=" * 50)
print("=== ITEMS TABLE ===")
for r in cur.execute("PRAGMA table_info(items)"):
    print(f"  {r[1]} ({r[2]})")

print()
print("=== NEW ACCOUNTS ===")
for r in cur.execute("SELECT code, name_ar, name_en, nature FROM accounts WHERE code IN ('1270','1271')"):
    print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")

print()
print("=== ITEMS operating_type distribution ===")
for r in cur.execute("SELECT operating_type, COUNT(*) as n FROM items GROUP BY operating_type"):
    print(f"  {r[0] or '(null)'}: {r[1]}")

conn.close()
print()
print("=" * 50)
print("Done!")
