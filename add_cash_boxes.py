"""
سكريبت إنشاء جداول الخزائن والبنوك والبطاقات
"""
import sqlite3
from app.config import Config


def create_tables():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("📦 إنشاء جداول الخزائن والبنوك والبطاقات...")
    
    # 1. جدول الخزائن
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash_boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT,
            parent_id INTEGER,
            box_type TEXT NOT NULL DEFAULT 'MAIN',
            account_code TEXT NOT NULL,
            opening_balance REAL DEFAULT 0,
            opening_date TEXT,
            current_balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'EGP',
            is_active INTEGER DEFAULT 1,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES cash_boxes(id) ON DELETE SET NULL
        )
    """)
    print("  ✅ cash_boxes")
    
    # 2. جدول البنوك
    cur.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT,
            account_code TEXT NOT NULL DEFAULT '1212',
            account_number TEXT,
            iban TEXT,
            swift_code TEXT,
            branch_name TEXT,
            branch_address TEXT,
            contact_person TEXT,
            phone TEXT,
            opening_balance REAL DEFAULT 0,
            opening_date TEXT,
            current_balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'EGP',
            is_active INTEGER DEFAULT 1,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ banks")
    
    # 3. جدول البطاقات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT,
            card_type TEXT NOT NULL DEFAULT 'DEBIT',
            bank_id INTEGER,
            account_code TEXT NOT NULL DEFAULT '1213',
            card_last4 TEXT,
            card_holder TEXT,
            expiry_date TEXT,
            credit_limit REAL DEFAULT 0,
            opening_balance REAL DEFAULT 0,
            current_balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'EGP',
            is_active INTEGER DEFAULT 1,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bank_id) REFERENCES banks(id) ON DELETE SET NULL
        )
    """)
    print("  ✅ payment_cards")
    
    # 4. جدول الحركات (للمستقبل)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash_box_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            box_type TEXT NOT NULL,
            txn_type TEXT NOT NULL,
            txn_date TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_after REAL,
            reference_no TEXT,
            description TEXT,
            related_txn_id INTEGER,
            journal_entry_id INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ cash_box_transactions")
    
    # فهارس
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cash_boxes_parent ON cash_boxes(parent_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cash_boxes_account ON cash_boxes(account_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_banks_account ON banks(account_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_bank ON payment_cards(bank_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txns_box ON cash_box_transactions(box_id, box_type)")
    print("  ✅ فهارس")
    
    conn.commit()
    conn.close()
    
    print("\n✅ تم إنشاء كل الجداول بنجاح!")


if __name__ == '__main__':
    create_tables()