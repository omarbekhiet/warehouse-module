import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# ============ أوامر الشراء ============
conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_no TEXT UNIQUE NOT NULL,
    po_date TEXT NOT NULL,
    supplier_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    expected_date TEXT,
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    tax_amount REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    notes TEXT,
    created_by INTEGER DEFAULT 1,
    approved_at TIMESTAMP,
    approved_by INTEGER,
    stock_txn_id INTEGER,
    invoice_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: purchase_orders")

conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id INTEGER NOT NULL,
    line_no INTEGER,
    item_id INTEGER NOT NULL,
    uom_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    base_quantity REAL NOT NULL,
    received_qty REAL DEFAULT 0,
    unit_price REAL NOT NULL,
    discount_pct REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    line_subtotal REAL DEFAULT 0,
    line_tax REAL DEFAULT 0,
    line_total REAL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE
)
""")
print("OK: purchase_order_lines")

conn.commit()
conn.close()
print()
print("Done!")
