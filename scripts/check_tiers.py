import sqlite3
conn = sqlite3.connect('database/warehouse.db')
print("=== items columns ===")
for r in conn.execute("PRAGMA table_info(items)"):
    print(f"  {r[1]} | {r[2]}")
conn.close()
