import sqlite3

conn = sqlite3.connect('database/warehouse.db')

# حذف كل الحركات والقيود (نبدأ من جديد)
conn.execute("DELETE FROM journal_entry_lines")
conn.execute("DELETE FROM journal_entries")
conn.execute("DELETE FROM stock_transaction_lines")
conn.execute("DELETE FROM stock_transactions")
conn.execute("DELETE FROM stock_balances")
conn.execute("DELETE FROM cost_layers")

conn.commit()

print("=== After cleanup ===")
for table in ['stock_transactions', 'stock_balances', 'journal_entries', 'journal_entry_lines']:
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"  {table}: {cur.fetchone()[0]} rows")

conn.close()
print("\nOK: Database cleaned")
