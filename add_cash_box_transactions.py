"""
سكريبت إنشاء جدول حركات الخزائن + جدول النثريات
"""
import sqlite3
from app.config import Config


def create_tables():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("📦 إنشاء جداول الحركات والنثريات...")
    
    # 1. جدول حركات الخزائن (موجود بس هنضيف أعمدة)
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
    
    # 2. جدول أنواع المصروفات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expense_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT,
            account_code TEXT NOT NULL,
            parent_id INTEGER,
            is_active INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES expense_categories(id)
        )
    """)
    print("  ✅ expense_categories")
    
    # 3. جدول المصروفات (النثريات)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS petty_cash_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_no TEXT UNIQUE NOT NULL,
            expense_date TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            cash_box_id INTEGER NOT NULL,
            beneficiary TEXT,
            description TEXT,
            reference TEXT,
            notes TEXT,
            status TEXT DEFAULT 'POSTED',
            journal_entry_id INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES expense_categories(id),
            FOREIGN KEY (cash_box_id) REFERENCES cash_boxes(id)
        )
    """)
    print("  ✅ petty_cash_expenses")
    
    # 4. جدول تفاصيل المصروفات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expense_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            payment_type TEXT,
            cheque_no TEXT,
            cheque_bank TEXT,
            cheque_date TEXT,
            transfer_no TEXT,
            transfer_bank TEXT,
            card_txn_no TEXT,
            card_last4 TEXT,
            card_bank TEXT,
            wallet_name TEXT,
            wallet_txn_no TEXT,
            wallet_phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (expense_id) REFERENCES petty_cash_expenses(id) ON DELETE CASCADE
        )
    """)
    print("  ✅ expense_details")
    
    # فهارس
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txns_box ON cash_box_transactions(box_id, box_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txns_date ON cash_box_transactions(txn_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_date ON petty_cash_expenses(expense_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_box ON petty_cash_expenses(cash_box_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_cat ON petty_cash_expenses(category_id)")
    print("  ✅ فهارس")
    
    conn.commit()
    conn.close()
    
    print("\n✅ تم إنشاء كل الجداول بنجاح!")


if __name__ == '__main__':
    create_tables()