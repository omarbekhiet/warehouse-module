import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# تحديث account_mappings: استلام → وسيط
conn.execute("DELETE FROM inventory_account_mappings WHERE transaction_type='RECEIPT'")

mappings = [
    ('RECEIPT', 'RAW_MATERIAL',   '1231', '1236-01', 'استلام مواد خام من مورد - وسيط'),
    ('RECEIPT', 'FINISHED_GOODS', '1233', '1232',    'استلام إنتاج داخلي'),
    ('RECEIPT', 'MERCHANDISE',    '1234', '1236-01', 'استلام بضاعة من مورد - وسيط'),
    ('RECEIPT', 'SUPPLIES',       '1235', '1236-01', 'استلام مستلزمات - وسيط'),
    ('INVOICE_PURCHASE', 'RAW_MATERIAL',   '1236-01', '2211', 'فاتورة شراء مواد خام'),
    ('INVOICE_PURCHASE', 'MERCHANDISE',    '1236-01', '2211', 'فاتورة شراء بضاعة'),
    ('INVOICE_PURCHASE', 'SUPPLIES',       '1236-01', '2211', 'فاتورة شراء مستلزمات'),
    ('INVOICE_PURCHASE', 'FINISHED_GOODS', '1236-01', '2211', 'فاتورة شراء منتجات'),
]

for m in mappings:
    conn.execute("""
        INSERT INTO inventory_account_mappings 
        (transaction_type, item_type, debit_account, credit_account, description_ar, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    """, m)

conn.commit()
print(f"OK: Updated {len(mappings)} mappings")
print()
print("=== Current mappings ===")
for r in conn.execute("SELECT transaction_type, item_type, debit_account, credit_account FROM inventory_account_mappings ORDER BY transaction_type, item_type"):
    print(f"  {r[0]:20} | {str(r[1]):15} | {r[2]:8} -> {r[3]}")
conn.close()
