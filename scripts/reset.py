import sqlite3
conn = sqlite3.connect('database/warehouse.db')
conn.execute("DELETE FROM journal_entry_lines")
conn.execute("DELETE FROM journal_entries")
conn.execute("DELETE FROM stock_transaction_lines")
conn.execute("DELETE FROM stock_transactions")
conn.execute("DELETE FROM stock_balances")
conn.execute("DELETE FROM cost_layers")
conn.commit()
print("Database cleaned")
for t in ['stock_transactions', 'stock_balances', 'journal_entries']:
    cur = conn.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {cur.fetchone()[0]}")
conn.close()
