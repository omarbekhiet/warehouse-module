import sqlite3

conn = sqlite3.connect('database/warehouse.db')
conn.execute("DELETE FROM stock_transaction_lines WHERE transaction_id IN (5, 6)")
conn.execute("DELETE FROM stock_transactions WHERE id IN (5, 6)")
conn.commit()

print("Deleted duplicate drafts")
for r in conn.execute("SELECT id, transaction_no, status FROM stock_transactions ORDER BY id"):
    print(f"  id={r[0]} | {r[1]} | {r[2]}")

conn.close()
