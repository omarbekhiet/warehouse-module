import sqlite3

DB = 'J:/warehouse-module/database/warehouse.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ============ 1. تسويات الشيكات ============
cur.execute("""
CREATE TABLE IF NOT EXISTS cheque_settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    settlement_no TEXT UNIQUE NOT NULL,
    settlement_date TEXT NOT NULL,
    settlement_type TEXT NOT NULL,          -- RECEIVED / ISSUED
    source_type TEXT NOT NULL,              -- SUPPLIER_PAYMENT / CUSTOMER_RECEIPT
    source_id INTEGER NOT NULL,
    cheque_no TEXT,
    cheque_date TEXT,
    bank_name TEXT,
    amount REAL NOT NULL,
    status TEXT DEFAULT 'PENDING',          -- PENDING / CLEARED / BOUNCED / CANCELLED
    cleared_date TEXT,
    notes TEXT,
    journal_entry_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: cheque_settlements")

# ============ 2. تسويات البطاقات ============
cur.execute("""
CREATE TABLE IF NOT EXISTS card_settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    settlement_no TEXT UNIQUE NOT NULL,
    settlement_date TEXT NOT NULL,
    source_type TEXT NOT NULL,              -- SUPPLIER_PAYMENT / CUSTOMER_RECEIPT
    source_id INTEGER NOT NULL,
    card_type TEXT,                         -- VISA / MASTERCARD / MEEZA
    transaction_no TEXT,
    gross_amount REAL NOT NULL,
    commission_pct REAL DEFAULT 0,
    commission_amount REAL DEFAULT 0,
    net_amount REAL NOT NULL,
    bank_account TEXT,
    status TEXT DEFAULT 'PENDING',
    settled_date TEXT,
    notes TEXT,
    journal_entry_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: card_settlements")

conn.commit()

print()
print("=" * 50)
print("=== Tables ===")
for t in ['cheque_settlements', 'card_settlements']:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {cur.fetchone()[0]} rows")

conn.close()
print()
print("Done!")
