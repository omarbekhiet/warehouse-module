import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# ============ جدول العملاء ============
conn.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    tax_number TEXT,
    account_code TEXT DEFAULT '1221',
    credit_limit REAL DEFAULT 0,
    payment_terms INTEGER DEFAULT 30,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: customers table")

# ============ جدول فواتير البيع ============
conn.execute("""
CREATE TABLE IF NOT EXISTS sales_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT UNIQUE NOT NULL,
    invoice_date TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    tax_amount REAL DEFAULT 0,
    discount_amount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    cogs_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    stock_txn_id INTEGER,
    journal_entry_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER DEFAULT 1,
    posted_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
)
""")
print("OK: sales_invoices table")

# ============ جدول بنود فاتورة البيع ============
conn.execute("""
CREATE TABLE IF NOT EXISTS sales_invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    uom_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    base_quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    unit_cost REAL DEFAULT 0,
    discount_pct REAL DEFAULT 0,
    tax_rate REAL DEFAULT 14,
    line_subtotal REAL DEFAULT 0,
    line_tax REAL DEFAULT 0,
    line_total REAL DEFAULT 0,
    line_cost REAL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (invoice_id) REFERENCES sales_invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id)
)
""")
print("OK: sales_invoice_lines table")

conn.commit()
conn.close()
print()
print("Done!")
