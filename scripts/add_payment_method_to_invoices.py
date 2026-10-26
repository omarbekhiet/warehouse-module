import sqlite3

DB = 'J:/warehouse-module/database/warehouse.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# إضافة حقل payment_method_code للفواتير
for table in ['purchase_invoices', 'sales_invoices']:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    
    if 'payment_method_code' not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN payment_method_code TEXT")
        print(f"OK: Added payment_method_code to {table}")
    else:
        print(f"- payment_method_code already exists in {table}")

conn.commit()
conn.close()
print()
print("Done!")
