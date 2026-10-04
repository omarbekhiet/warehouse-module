import sqlite3
conn = sqlite3.connect('database/warehouse.db')

cur = conn.execute("PRAGMA table_info(items)")
cols = [r[1] for r in cur.fetchall()]

new_cols = [
    ('major_uom_id', 'INTEGER'),
    ('major_to_medium_factor', 'REAL'),
    ('medium_uom_id', 'INTEGER'),
    ('medium_to_minor_factor', 'REAL'),
]
for name, typ in new_cols:
    if name not in cols:
        conn.execute(f"ALTER TABLE items ADD COLUMN {name} {typ}")
        print(f"OK Added: {name}")
    else:
        print(f"- Already exists: {name}")

conn.commit()
print()
print("=== Items table columns ===")
for r in conn.execute("PRAGMA table_info(items)"):
    print(f"  {r[1]} ({r[2]})")

conn.close()
print()
print("Done!")
