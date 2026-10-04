"""Create SQLite database, tables, and seed data."""
import os
import sys
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join('database', 'warehouse.db')

SCHEMA = """
-- Master tables
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    warehouse_type TEXT NOT NULL,
    location TEXT,
    account_code TEXT NOT NULL,
    allow_negative INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS units_of_measure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS item_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    parent_id INTEGER,
    default_inventory_account TEXT,
    default_cost_account TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name_ar TEXT NOT NULL,
    name_en TEXT,
    category_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    base_uom_id INTEGER NOT NULL,
    cost_method TEXT DEFAULT 'WEIGHTED_AVERAGE',
    inventory_account TEXT NOT NULL,
    cost_account TEXT NOT NULL,
    revenue_account TEXT,
    reorder_level REAL DEFAULT 0,
    barcode TEXT,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transaction tables
CREATE TABLE IF NOT EXISTS stock_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_no TEXT UNIQUE NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    from_warehouse_id INTEGER,
    to_warehouse_id INTEGER,
    reference_type TEXT,
    reference_no TEXT,
    status TEXT DEFAULT 'DRAFT',
    total_qty REAL DEFAULT 0,
    total_value REAL DEFAULT 0,
    journal_entry_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER DEFAULT 1,
    posted_at TIMESTAMP,
    posted_by INTEGER
);

CREATE TABLE IF NOT EXISTS stock_transaction_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    uom_id INTEGER,
    quantity REAL NOT NULL,
    unit_cost REAL DEFAULT 0,
    total_cost REAL DEFAULT 0,
    batch_no TEXT,
    notes TEXT,
    FOREIGN KEY (transaction_id) REFERENCES stock_transactions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    batch_no TEXT DEFAULT '',
    quantity REAL DEFAULT 0,
    average_cost REAL DEFAULT 0,
    total_value REAL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (warehouse_id, item_id, batch_no)
);

CREATE TABLE IF NOT EXISTS cost_layers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    batch_no TEXT DEFAULT '',
    receipt_date TEXT NOT NULL,
    original_qty REAL NOT NULL,
    remaining_qty REAL NOT NULL,
    unit_cost REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Accounting tables
CREATE TABLE IF NOT EXISTS inventory_account_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_type TEXT NOT NULL,
    item_type TEXT,
    debit_account TEXT NOT NULL,
    credit_account TEXT NOT NULL,
    description_ar TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_no TEXT UNIQUE NOT NULL,
    entry_date TEXT NOT NULL,
    reference_type TEXT,
    reference_id INTEGER,
    reference_no TEXT,
    description TEXT,
    total_debit REAL DEFAULT 0,
    total_credit REAL DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL,
    account_code TEXT NOT NULL,
    description TEXT,
    debit_amount REAL DEFAULT 0,
    credit_amount REAL DEFAULT 0,
    warehouse_id INTEGER,
    item_id INTEGER,
    FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inventory_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    count_no TEXT UNIQUE NOT NULL,
    warehouse_id INTEGER NOT NULL,
    count_date TEXT NOT NULL,
    count_type TEXT NOT NULL,
    status TEXT DEFAULT 'DRAFT',
    journal_entry_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_count_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    count_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    system_qty REAL NOT NULL,
    counted_qty REAL NOT NULL,
    unit_cost REAL DEFAULT 0,
    variance_value REAL DEFAULT 0,
    FOREIGN KEY (count_id) REFERENCES inventory_counts(id) ON DELETE CASCADE
);
"""

SEED = """
-- Warehouses
INSERT OR IGNORE INTO warehouses (code, name_ar, name_en, warehouse_type, location, account_code) VALUES
('WH-001', 'المستودع الرئيسي', 'Main Warehouse', 'MAIN', 'المقر الرئيسي', '1230'),
('WH-002', 'مستودع المواد الخام', 'Raw Materials WH', 'RAW_MATERIAL', 'المصنع', '1231'),
('WH-003', 'مستودع المنتجات التامة', 'Finished Goods WH', 'FINISHED_GOODS', 'المصنع', '1233'),
('WH-004', 'مستودع البضاعة التجارية', 'Merchandise WH', 'MERCHANDISE', 'المخزن التجاري', '1234'),
('WH-005', 'مستودع المستلزمات', 'Supplies WH', 'CUSTODY', 'المقر الرئيسي', '1235');

-- Units
INSERT OR IGNORE INTO units_of_measure (code, name_ar, name_en) VALUES
('PCS', 'قطعة', 'Piece'),
('BOX', 'علبة', 'Box'),
('CTN', 'كرتونة', 'Carton'),
('KG', 'كيلوجرام', 'Kilogram'),
('LTR', 'لتر', 'Liter'),
('MTR', 'متر', 'Meter');

-- Categories
INSERT OR IGNORE INTO item_categories (code, name_ar, name_en, default_inventory_account, default_cost_account) VALUES
('CAT-RM', 'المواد الخام', 'Raw Materials', '1231', '3111'),
('CAT-PKG', 'مواد التعبئة', 'Packaging', '1231', '3112'),
('CAT-FG', 'المنتجات التامة', 'Finished Goods', '1233', '3000'),
('CAT-MER', 'البضاعة التجارية', 'Merchandise', '1234', '3121'),
('CAT-SUP', 'المستلزمات', 'Supplies', '1235', '3122');

-- Items
INSERT OR IGNORE INTO items (code, name_ar, name_en, category_id, item_type, base_uom_id, cost_method, inventory_account, cost_account, reorder_level) VALUES
('ITM-0001', 'حديد خام', 'Raw Iron', 1, 'RAW_MATERIAL', 4, 'WEIGHTED_AVERAGE', '1231', '3111', 1000),
('ITM-0002', 'بلاستيك خام', 'Raw Plastic', 1, 'RAW_MATERIAL', 4, 'WEIGHTED_AVERAGE', '1231', '3111', 500),
('ITM-0100', 'منتج نهائي A', 'Finished Product A', 3, 'FINISHED_GOODS', 1, 'WEIGHTED_AVERAGE', '1233', '3000', 100),
('ITM-0200', 'بضاعة تجارية X', 'Merchandise X', 4, 'MERCHANDISE', 1, 'WEIGHTED_AVERAGE', '1234', '3121', 50),
('ITM-0300', 'قطع غيار', 'Spare Parts', 5, 'SUPPLIES', 1, 'FIFO', '1235', '3122', 20);

-- Account Mappings
INSERT OR IGNORE INTO inventory_account_mappings (transaction_type, item_type, debit_account, credit_account, description_ar) VALUES
('PURCHASE', 'RAW_MATERIAL', '1231', '2211', 'شراء مواد خام بالأجل'),
('PURCHASE', 'RAW_MATERIAL', '1231', '1212', 'شراء مواد خام نقداً'),
('PURCHASE', 'MERCHANDISE', '1234', '2211', 'شراء بضاعة بالأجل'),
('PURCHASE', 'FINISHED_GOODS', '1233', '2211', 'شراء منتجات تامة'),
('ISSUE', 'RAW_MATERIAL', '3111', '1231', 'صرف مواد خام للإنتاج'),
('ISSUE', 'MERCHANDISE', '3000', '1234', 'تكلفة بضاعة مباعة'),
('ISSUE', 'FINISHED_GOODS', '3000', '1233', 'تكلفة منتجات مباعة'),
('ISSUE', 'SUPPLIES', '3300', '1235', 'صرف مستلزمات'),
('RECEIPT', 'FINISHED_GOODS', '1233', '1232', 'استلام إنتاج تام'),
('COUNT_ADJUST', 'RAW_MATERIAL', '1231', '4231', 'زيادة جرد مواد خام'),
('COUNT_ADJUST', 'RAW_MATERIAL', '5563', '1231', 'عجز جرد مواد خام'),
('COUNT_ADJUST', 'MERCHANDISE', '1234', '4231', 'زيادة جرد بضاعة'),
('COUNT_ADJUST', 'MERCHANDISE', '5563', '1234', 'عجز جرد بضاعة');
"""


def main():
    # Ensure database dir exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    print(f'[DB] Path: {os.path.abspath(DB_PATH)}')
    conn = sqlite3.connect(DB_PATH)
    try:
        print('[DB] Creating tables...')
        conn.executescript(SCHEMA)
        print('[DB] Inserting seed data...')
        conn.executescript(SEED)
        conn.commit()
        print('[DB] Done!')

        # Summary
        for t in ['warehouses', 'units_of_measure', 'item_categories',
                  'items', 'inventory_account_mappings']:
            cur = conn.execute(f'SELECT COUNT(*) FROM {t}')
            print(f'   {t}: {cur.fetchone()[0]} rows')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
