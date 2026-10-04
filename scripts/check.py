import sqlite3

conn = sqlite3.connect('database/warehouse.db')
conn.row_factory = sqlite3.Row

print('=== ALL STOCK TRANSACTIONS ===')
for r in conn.execute("SELECT id, transaction_no, transaction_type, status, total_qty, transaction_date FROM stock_transactions ORDER BY id"):
    print(f"  id={r['id']:3} | {r['transaction_no']:20} | {r['transaction_type']:10} | {r['status']:10} | qty={r['total_qty']}")

print()
print('=== STOCK BALANCES ===')
rows = list(conn.execute("SELECT * FROM stock_balances"))
if not rows:
    print('  (فارغ)')
for r in rows:
    print(f"  wh={r['warehouse_id']} | item={r['item_id']} | batch='{r['batch_no']}' | qty={r['quantity']} | value={r['total_value']}")

print()
print('=== JOURNAL ENTRIES ===')
for r in conn.execute("SELECT id, entry_no, reference_no, total_debit FROM journal_entries ORDER BY id"):
    print(f"  id={r['id']} | {r['entry_no']} | ref={r['reference_no']} | D={r['total_debit']}")

conn.close()
