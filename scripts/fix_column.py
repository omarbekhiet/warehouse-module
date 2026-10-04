import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# Check current columns
cur = conn.execute("PRAGMA table_info(stock_transactions)")
cols = [r[1] for r in cur.fetchall()]
print("Current columns:", cols)

# Add reference_id if not exists
if 'reference_id' not in cols:
    conn.execute("ALTER TABLE stock_transactions ADD COLUMN reference_id INTEGER")
    print("Added reference_id column")
else:
    print("reference_id already exists")

conn.commit()
conn.close()
