import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# ============ جدول فواتير الشراء ============
conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT UNIQUE NOT NULL,
    invoice_date TEXT NOT NULL,
    supplier_id INTEGER NOT NULL,
    supplier_invoice_no TEXT,
    warehouse_id INTEGER NOT NULL,
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    tax_amount REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    stock_txn_id INTEGER,
    journal_entry_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER DEFAULT 1,
    posted_at TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
)
""")
print("OK: purchase_invoices table")

# ============ جدول بنود فاتورة الشراء ============
conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    uom_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    base_quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    discount_pct REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    line_subtotal REAL DEFAULT 0,
    line_tax REAL DEFAULT 0,
    line_total REAL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (invoice_id) REFERENCES purchase_invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id)
)
""")
print("OK: purchase_invoice_lines table")

# ============ إضافة حقول لربط الحركات بالفواتير ============
cur = conn.execute("PRAGMA table_info(stock_transactions)")
cols = [r[1] for r in cur.fetchall()]

if 'invoice_id' not in cols:
    conn.execute("ALTER TABLE stock_transactions ADD COLUMN invoice_id INTEGER")
    print("OK: Added invoice_id to stock_transactions")

if 'invoice_type' not in cols:
    conn.execute("ALTER TABLE stock_transactions ADD COLUMN invoice_type TEXT")
    print("OK: Added invoice_type to stock_transactions")

conn.commit()
conn.close()
print()
print("Done!")
