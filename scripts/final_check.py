import sqlite3
conn = sqlite3.connect('database/warehouse.db')
conn.row_factory = sqlite3.Row

print('=' * 70)
print('FINAL SYSTEM CHECK')
print('=' * 70)

print()
print('--- STOCK TRANSACTIONS ---')
for r in conn.execute("SELECT id, transaction_no, transaction_type, status, total_qty FROM stock_transactions ORDER BY id"):
    print(f"  id={r['id']:3} | {r['transaction_no']:20} | {r['transaction_type']:10} | {r['status']:8} | qty={r['total_qty']}")

print()
print('--- STOCK BALANCES ---')
for r in conn.execute("""SELECT w.name_ar as wh, i.name_ar as item, sb.batch_no, 
                         sb.quantity, sb.average_cost, sb.total_value
                         FROM stock_balances sb
                         JOIN warehouses w ON sb.warehouse_id = w.id
                         JOIN items i ON sb.item_id = i.id
                         WHERE sb.quantity > 0"""):
    print(f"  {r['wh']:25} | {r['item']:15} | qty={r['quantity']:7} | avg={r['average_cost']:7} | val={r['total_value']}")

print()
print('--- JOURNAL ENTRIES ---')
for r in conn.execute("SELECT id, entry_no, reference_no, total_debit, total_credit FROM journal_entries ORDER BY id"):
    print(f"  id={r['id']} | {r['entry_no']} | {r['reference_no']:20} | D={r['total_debit']:8} | C={r['total_credit']}")

print()
print('=' * 70)
conn.close()
