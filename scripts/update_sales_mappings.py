import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# حذف الربط القديم للبيع إن وجد
conn.execute("DELETE FROM inventory_account_mappings WHERE transaction_type='ISSUE'")

mappings = [
    # ===== الصرف (تكلفة) =====
    ('ISSUE', 'RAW_MATERIAL',   '3111', '1231', 'صرف مواد خام للإنتاج'),
    ('ISSUE', 'RAW_MATERIAL',   '3112', '1231', 'صرف مواد تعبئة'),
    ('ISSUE', 'MERCHANDISE',    '3000', '1234', 'تكلفة بضاعة مباعة'),
    ('ISSUE', 'FINISHED_GOODS', '3000', '1233', 'تكلفة منتجات مباعة'),
    ('ISSUE', 'SUPPLIES',       '3300', '1235', 'صرف مستلزمات'),
    
    # ===== البيع عبر الوسيط =====
    ('INVOICE_SALES', 'MERCHANDISE',    '1221', '1236-02', 'فاتورة بيع بضاعة - إيراد'),
    ('INVOICE_SALES', 'FINISHED_GOODS', '1221', '1236-02', 'فاتورة بيع منتجات - إيراد'),
    ('INVOICE_SALES', 'RAW_MATERIAL',   '1221', '1236-02', 'فاتورة بيع مواد'),
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
print("=== Current ISSUE/SALES mappings ===")
for r in conn.execute("""SELECT transaction_type, item_type, debit_account, credit_account 
                         FROM inventory_account_mappings 
                         WHERE transaction_type IN ('ISSUE','INVOICE_SALES')
                         ORDER BY transaction_type, item_type"""):
    print(f"  {r[0]:20} | {str(r[1]):15} | {r[2]:8} -> {r[3]}")
conn.close()
