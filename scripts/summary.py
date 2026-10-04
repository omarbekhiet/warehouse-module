import sqlite3
conn = sqlite3.connect('database/warehouse.db')
conn.row_factory = sqlite3.Row
print('=== ALL TRANSACTIONS ===')
for r in conn.execute("SELECT id, transaction_no, transaction_type, status, total_qty, total_value FROM stock_transactions ORDER BY id"):
    print(f"  id={r['id']:3} | {r['transaction_no']:20} | {r['transaction_type']:10} | {r['status']:8} | qty={r['total_qty']:6} | val={r['total_value']}")
print()
print('=== JOURNAL ENTRIES ===')
for r in conn.execute("SELECT id, entry_no, reference_no, total_debit, total_credit FROM journal_entries ORDER BY id"):
    print(f"  id={r['id']} | {r['entry_no']} | ref={r['reference_no']} | D={r['total_debit']} | C={r['total_credit']}")
conn.close()
