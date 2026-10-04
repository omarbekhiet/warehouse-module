import sqlite3
conn = sqlite3.connect('database/warehouse.db')
cur = conn.execute("PRAGMA table_info(stock_transaction_lines)")
cols = [r[1] for r in cur.fetchall()]
if 'base_quantity' not in cols:
    conn.execute("ALTER TABLE stock_transaction_lines ADD COLUMN base_quantity REAL")
    print("OK: Added base_quantity")
else:
    print("- base_quantity already exists")
conn.commit()
conn.close()
print("Done")
