import sqlite3
conn = sqlite3.connect('database/warehouse.db')

# ============ طلبات الصرف ============
conn.execute("""
CREATE TABLE IF NOT EXISTS material_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_no TEXT UNIQUE NOT NULL,
    request_date TEXT NOT NULL,
    requester_name TEXT,
    department TEXT,
    warehouse_id INTEGER NOT NULL,
    purpose TEXT,
    priority TEXT DEFAULT 'NORMAL',
    status TEXT DEFAULT 'DRAFT',
    approved_at TIMESTAMP,
    approved_by INTEGER,
    notes TEXT,
    stock_txn_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: material_requests")

conn.execute("""
CREATE TABLE IF NOT EXISTS material_request_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    line_no INTEGER,
    item_id INTEGER NOT NULL,
    uom_id INTEGER NOT NULL,
    requested_qty REAL NOT NULL,
    base_requested_qty REAL NOT NULL,
    issued_qty REAL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (request_id) REFERENCES material_requests(id) ON DELETE CASCADE
)
""")
print("OK: material_request_lines")

conn.commit()
conn.close()
print()
print("Done!")
