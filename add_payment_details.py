import sqlite3

db_path = r'J:\warehouse-module\database\warehouse.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# ============================================================
# إنشاء جدول payment_details
# ============================================================
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment_details'")
exists = cur.fetchone()

if exists:
    print("الجدول موجود بالفعل")
else:
    cur.execute("""
        CREATE TABLE payment_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_type TEXT NOT NULL,
            payment_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            
            -- بيانات الشيك
            cheque_no TEXT,
            cheque_bank TEXT,
            cheque_date DATE,
            cheque_status TEXT DEFAULT 'PENDING',
            
            -- بيانات التحويل
            transfer_no TEXT,
            transfer_bank TEXT,
            
            -- بيانات البطاقة
            card_txn_no TEXT,
            card_last4 TEXT,
            card_bank TEXT,
            
            -- بيانات المحفظة
            wallet_name TEXT,
            wallet_txn_no TEXT,
            wallet_phone TEXT,
            
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("OK: تم إنشاء جدول payment_details")

conn.commit()
conn.close()