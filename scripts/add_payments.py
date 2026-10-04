import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# ============ مدفوعات الموردين ============
conn.execute("""
CREATE TABLE IF NOT EXISTS supplier_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_no TEXT UNIQUE NOT NULL,
    payment_date TEXT NOT NULL,
    supplier_id INTEGER NOT NULL,
    payment_method TEXT DEFAULT 'CASH',
    bank_account_id INTEGER,
    amount REAL NOT NULL,
    reference TEXT,
    notes TEXT,
    status TEXT DEFAULT 'POSTED',
    journal_entry_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: supplier_payments")

# ============ تحصيلات العملاء ============
conn.execute("""
CREATE TABLE IF NOT EXISTS customer_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no TEXT UNIQUE NOT NULL,
    receipt_date TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    receipt_method TEXT DEFAULT 'CASH',
    bank_account_id INTEGER,
    amount REAL NOT NULL,
    reference TEXT,
    notes TEXT,
    status TEXT DEFAULT 'POSTED',
    journal_entry_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: customer_receipts")

conn.commit()
conn.close()
print()
print("Done!")
