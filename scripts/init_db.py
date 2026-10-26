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
    reference_id INTEGER,
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
    expiry_date TEXT,
    notes TEXT,
    FOREIGN KEY (transaction_id) REFERENCES stock_transactions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    batch_no TEXT DEFAULT '',
    expiry_date TEXT,
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
    expiry_date TEXT,
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


CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    value_type TEXT DEFAULT 'string',
    label_ar TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, key)
);
CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

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


-- Settings Defaults
INSERT OR IGNORE INTO settings (category, key, value, value_type, label_ar) VALUES
('company', 'name_ar', 'اسم الشركة', 'string', 'اسم الشركة عربي'),
('company', 'name_en', '', 'string', 'اسم الشركة انجليزي'),
('company', 'address', '', 'string', 'العنوان'),
('company', 'city', '', 'string', 'المدينة'),
('company', 'country', 'مصر', 'string', 'الدولة'),
('company', 'phone', '', 'string', 'التليفون'),
('company', 'email', '', 'string', 'البريد'),
('company', 'tax_number', '', 'string', 'الرقم الضريبي'),
('company', 'currency', 'EGP', 'string', 'العملة'),
('company', 'currency_symbol', 'ج.م', 'string', 'رمز العملة'),
('company', 'currency_name', 'جنيه مصري', 'string', 'اسم العملة'),
('accounting', 'cost_method', 'WEIGHTED_AVERAGE', 'string', 'طريقة التكلفة'),
('accounting', 'default_vat_rate', '14', 'float', 'نسبة VAT'),
('accounting', 'ar_account', '1221', 'string', 'ذمم العملاء'),
('accounting', 'ap_account', '2211', 'string', 'ذمم الموردين'),
('inventory', 'allow_negative_stock', '0', 'bool', 'السماح بالكمية السالبة'),
('inventory', 'multi_warehouse', '1', 'bool', 'متعدد المستودعات'),
('inventory', 'barcode_enabled', '1', 'bool', 'تفعيل الباركود'),
('customers', 'default_payment_terms', '30', 'int', 'مدة السماح'),
('suppliers', 'default_payment_terms', '30', 'int', 'مدة السماح'),
('cash', 'method_cash', '1', 'bool', 'نقدي'),
('print', 'paper_size', 'A4', 'string', 'حجم الورق'),
('backup', 'auto_backup_enabled', '0', 'bool', 'النسخ التلقائي'),

('company', 'phone2', '', 'string', 'تليفون اضافي'),
('company', 'mobile', '', 'string', 'الموبايل'),
('company', 'fax', '', 'string', 'الفاكس'),
('company', 'website', '', 'string', 'الموقع'),
('company', 'commercial_register', '', 'string', 'السجل التجاري'),
('company', 'tax_card', '', 'string', 'البطاقة الضريبية'),
('company', 'fiscal_year_start', '01', 'string', 'بداية السنة المالية'),
('company', 'fiscal_year_end', '12', 'string', 'نهاية السنة المالية'),
('company', 'logo_url', '', 'string', 'شعار الشركة'),
('company', 'stamp_url', '', 'string', 'الختم'),
('company', 'signature_url', '', 'string', 'التوقيع'),
('company', 'footer_note', '', 'string', 'تذييل'),
('company', 'show_logo_in_reports', '1', 'bool', 'إظهار الشعار'),
('company', 'show_tax_in_invoices', '1', 'bool', 'إظهار الرقم الضريبي'),
('company', 'show_stamp', '0', 'bool', 'إظهار الختم'),
('accounting', 'allow_negative_inventory', '0', 'bool', 'السماح بالمخزون السالب'),
('accounting', 'monthly_revaluation', '0', 'bool', 'إعادة التقييم الشهري'),
('accounting', 'auto_journal_invoices', '1', 'bool', 'قيد تلقائي فواتير'),
('accounting', 'auto_journal_receipts', '1', 'bool', 'قيد تلقائي تحصيل'),
('accounting', 'auto_journal_issues', '1', 'bool', 'قيد تلقائي صرف'),
('accounting', 'auto_journal_transfers', '0', 'bool', 'قيد تلقائي تحويلات'),
('accounting', 'default_inventory_account', '1231', 'string', 'حساب المخزون'),
('accounting', 'default_sales_account', '4111', 'string', 'حساب المبيعات'),
('accounting', 'default_cogs_account', '3000', 'string', 'حساب COGS'),
('accounting', 'vat_input_account', '1251', 'string', 'VAT مدخلات'),
('accounting', 'vat_output_account', '2231', 'string', 'VAT مخرجات'),
('accounting', 'cash_account', '1111', 'string', 'الصندوق'),
('accounting', 'bank_account', '1211', 'string', 'البنك'),
('accounting', 'shortage_account', '5563', 'string', 'حساب العجز'),
('accounting', 'surplus_account', '4231', 'string', 'حساب الزيادة'),
('accounting', 'fiscal_period_start', '', 'string', 'بداية الفترة'),
('accounting', 'fiscal_period_end', '', 'string', 'نهاية الفترة'),
('accounting', 'auto_close_period', '0', 'bool', 'إغلاق الفترة تلقائيا'),
('accounting', 'allow_backdated_entries', '1', 'bool', 'القيود الرجعية'),
('inventory', 'multi_branch', '0', 'bool', 'متعدد الفروع'),
('inventory', 'batch_tracking', '0', 'bool', 'تتبع الدفعات'),
('inventory', 'expiry_tracking', '0', 'bool', 'تتبع الصلاحية'),
('inventory', 'auto_transfer', '0', 'bool', 'التحويل التلقائي'),
('inventory', 'default_reorder_level', '10', 'int', 'الحد الأدنى'),
('inventory', 'default_cost_method', 'WEIGHTED_AVERAGE', 'string', 'طريقة التكلفة'),
('inventory', 'default_warehouse_id', '', 'string', 'المستودع الافتراضي'),
('inventory', 'low_stock_alerts', '1', 'bool', 'تنبيهات المخزون'),
('inventory', 'allow_direct_adjustments', '1', 'bool', 'السماح بالتسويات'),
('inventory', 'require_adjustment_reason', '1', 'bool', 'إلزامية السبب'),
('customers', 'default_credit_limit', '0', 'float', 'حد الائتمان'),
('customers', 'block_overdue_customers', '0', 'bool', 'منع البيع للمتأخرين'),
('customers', 'require_credit_limit', '0', 'bool', 'إلزامية حد الائتمان'),
('customers', 'allow_prepayment', '1', 'bool', 'الدفع المقدم'),
('customers', 'overdue_alerts', '1', 'bool', 'تنبيهات التأخر'),
('customers', 'monthly_statement', '0', 'bool', 'كشف حساب شهري'),
('customers', 'default_discount', '0', 'float', 'نسبة الخصم'),
('suppliers', 'default_discount', '0', 'float', 'نسبة الخصم'),
('suppliers', 'require_po_before_invoice', '0', 'bool', 'إلزامية أمر الشراء'),
('suppliers', 'allow_receipt_without_invoice', '1', 'bool', 'الاستلام بدون فاتورة'),
('suppliers', 'pending_po_alerts', '1', 'bool', 'إشعارات أوامر الشراء'),
('suppliers', 'upcoming_payment_alerts', '1', 'bool', 'إشعارات الفواتير'),
('suppliers', 'price_comparison', '0', 'bool', 'مقارنة الأسعار'),
('suppliers', 'supplier_rating', '0', 'bool', 'تصنيف الموردين'),
('suppliers', 'supplier_performance', '0', 'bool', 'تقييم الأداء'),
('cash', 'method_cheque', '1', 'bool', 'شيك'),
('cash', 'method_card', '1', 'bool', 'بطاقة'),
('cash', 'method_transfer', '1', 'bool', 'تحويل بنكي'),
('cash', 'method_wallet', '0', 'bool', 'محفظة الكترونية'),
('cash', 'method_credit', '1', 'bool', 'آجل'),
('cash', 'allow_negative_cash', '0', 'bool', 'الرصيد السالب'),
('cash', 'print_receipt', '1', 'bool', 'طباعة ايصال'),
('cash', 'auto_numbering', '1', 'bool', 'ترقيم تلقائي'),
('cash', 'merge_cash_accounts', '0', 'bool', 'دمج الخزائن'),
('cash', 'max_cash_payment', '0', 'float', 'الحد الاقصى للدفعة'),
('cash', 'min_cash_balance', '0', 'float', 'الحد الادنى للتحذير'),
('print', 'page_orientation', 'portrait', 'string', 'اتجاه الصفحة'),
('print', 'font_size', 'medium', 'string', 'حجم الخط'),
('print', 'invoice_template', 'classic', 'string', 'تصميم الفاتورة'),
('print', 'print_copies', '1', 'int', 'عدد النسخ'),
('print', 'print_logo', '1', 'bool', 'إظهار الشعار'),
('print', 'print_tax_number', '1', 'bool', 'إظهار الرقم الضريبي'),
('print', 'print_qr', '0', 'bool', 'إظهار QR'),
('print', 'print_stamp', '0', 'bool', 'إظهار الختم'),
('print', 'print_signature', '0', 'bool', 'إظهار التوقيع'),
('print', 'print_tafqeet', '1', 'bool', 'إظهار التفقيط'),
('print', 'print_barcode', '0', 'bool', 'إظهار الباركود'),
('print', 'invoice_footer', 'شكرا لتعاملكم معنا', 'string', 'تذييل الفاتورة'),
('print', 'invoice_terms', '', 'string', 'الشروط'),
('backup', 'backup_frequency', 'daily', 'string', 'التكرار'),
('backup', 'backup_time', '23:00', 'string', 'الوقت'),
('backup', 'backup_keep_count', '7', 'int', 'عدد النسخ'),
('backup', 'backup_path', '', 'string', 'المسار');

"""




def run_extension_scripts():
    """تشغيل ملفات الإضافة (add_*.py) بالتسلسل"""
    import subprocess
    from pathlib import Path

    scripts_dir = Path(__file__).parent

    extensions = [
        'add_accounting.py',
        'add_suppliers_groups.py',
        'add_sales_tables.py',
        'add_users.py',
        'add_invoices.py',
        'add_purchase_orders.py',
        'add_payments.py',
        'add_payment_system.py',
        'add_returns.py',
        'add_settlements.py',
        'add_requisitions.py',
        'add_material_requests.py',
        'add_base_qty.py',
        'add_operating_type.py',
        'add_payment_method_to_invoices.py',
        'add_tiers.py',
    ]

    print('[DB] Running extension scripts...')
    success = 0
    failed = 0
    skipped = 0

    for ext in extensions:
        script_path = scripts_dir / ext
        if not script_path.exists():
            print(f'[DB]   - SKIP: {ext}')
            skipped += 1
            continue

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(scripts_dir.parent)
            )
            if result.returncode == 0:
                print(f'[DB]   OK: {ext}')
                success += 1
            else:
                print(f'[DB]   FAIL: {ext}')
                if result.stderr:
                    err = result.stderr.strip().split('\n')[-1]
                    print(f'[DB]     {err[:120]}')
                failed += 1
        except subprocess.TimeoutExpired:
            print(f'[DB]   TIMEOUT: {ext}')
            failed += 1
        except Exception as e:
            print(f'[DB]   ERROR: {ext} - {str(e)[:80]}')
            failed += 1

    print(f'[DB] Extensions: {success} OK | {failed} FAIL | {skipped} SKIP')
    return success, failed


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
        print('[DB] Base tables done!')

        # Summary
        for t in ['warehouses', 'units_of_measure', 'item_categories',
                  'items', 'inventory_account_mappings']:
            try:
                cur = conn.execute(f'SELECT COUNT(*) FROM {t}')
                print(f'   {t}: {cur.fetchone()[0]} rows')
            except Exception as e:
                print(f'   {t}: (error - {e})')
    finally:
        conn.close()

    # Run extension scripts
    run_extension_scripts()

    print('[DB] All done!')

    # Final report
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        )
        total_tables = cur.fetchone()[0]
        print(f'[DB] Total tables: {total_tables}')

        critical = ['settings', 'customers', 'suppliers', 'sales_invoices',
                    'purchase_invoices', 'users', 'payment_methods']
        print('[DB] Critical tables:')
        for t in critical:
            cur.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (t,)
            )
            exists = cur.fetchone()[0] > 0
            status = 'OK' if exists else 'MISSING'
            print(f'   {status}: {t}')
    finally:
        conn.close()
if __name__ == '__main__':
    main()
