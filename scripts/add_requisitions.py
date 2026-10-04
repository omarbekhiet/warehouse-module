import sqlite3
conn = sqlite3.connect('database/warehouse.db')

conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_requisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_no TEXT UNIQUE NOT NULL,
    req_date TEXT NOT NULL,
    requester_name TEXT,
    department TEXT,
    warehouse_id INTEGER,
    priority TEXT DEFAULT 'NORMAL',
    needed_by TEXT,
    reason TEXT,
    status TEXT DEFAULT 'DRAFT',
    approved_at TIMESTAMP,
    approved_by INTEGER,
    purchase_order_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: purchase_requisitions")

conn.execute("""
CREATE TABLE IF NOT EXISTS purchase_requisition_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id INTEGER NOT NULL,
    line_no INTEGER,
    item_id INTEGER,
    item_description TEXT,
    uom_id INTEGER,
    quantity REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY (req_id) REFERENCES purchase_requisitions(id) ON DELETE CASCADE
)
""")
print("OK: purchase_requisition_lines")

conn.commit()
conn.close()
print()
print("Done!")
