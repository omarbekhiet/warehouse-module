import sqlite3
conn = sqlite3.connect('database/warehouse.db')
conn.execute("DELETE FROM stock_transaction_lines WHERE transaction_id=7")
conn.execute("DELETE FROM stock_transactions WHERE id=7")
conn.commit()
print("Deleted pending transfer #7")
conn.close()
