import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# ============ مرتجعات الشراء ============
conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_no TEXT UNIQUE NOT NULL,
    return_date TEXT NOT NULL,
    original_invoice_id INTEGER,
    supplier_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    tax_amount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    stock_txn_id INTEGER,
    journal_entry_id INTEGER,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP
)
""")
print("OK: purchase_returns")

conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_return_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    line_no INTEGER,
    item_id INTEGER NOT NULL,
    uom_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    base_quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    tax_rate REAL DEFAULT 14,
    line_subtotal REAL DEFAULT 0,
    line_tax REAL DEFAULT 0,
    line_total REAL DEFAULT 0,
    line_cost REAL DEFAULT 0,
    FOREIGN KEY (return_id) REFERENCES purchase_returns(id) ON DELETE CASCADE
)
""")
print("OK: purchase_return_lines")

# ============ مرتجعات البيع ============
conn.execute("""
CREATE TABLE IF NOT EXISTS sales_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_no TEXT UNIQUE NOT NULL,
    return_date TEXT NOT NULL,
    original_invoice_id INTEGER,
    customer_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    tax_amount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    cogs_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    stock_txn_id INTEGER,
    journal_entry_id INTEGER,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP
)
""")
print("OK: sales_returns")

conn.execute("""
CREATE TABLE IF NOT EXISTS sales_return_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    line_no INTEGER,
    item_id INTEGER NOT NULL,
    uom_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    base_quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    unit_cost REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    line_subtotal REAL DEFAULT 0,
    line_tax REAL DEFAULT 0,
    line_total REAL DEFAULT 0,
    line_cost REAL DEFAULT 0,
    FOREIGN KEY (return_id) REFERENCES sales_returns(id) ON DELETE CASCADE
)
""")
print("OK: sales_return_lines")

conn.commit()
conn.close()
print()
print("Done!")
