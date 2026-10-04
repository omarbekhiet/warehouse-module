import sqlite3
import hashlib
import os

conn = sqlite3.connect('database/warehouse.db')

conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT DEFAULT 'USER',
    is_active INTEGER DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("OK: users table")

# إضافة مستخدم افتراضي: admin / admin123
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

users = [
    ('admin',   hash_password('admin123'),   'مدير النظام',   'admin@system.com',   'ADMIN'),
    ('manager', hash_password('manager123'), 'مدير مخازن',    'manager@system.com', 'MANAGER'),
    ('user',    hash_password('user123'),    'مستخدم عادي',   'user@system.com',    'USER'),
]

for u in users:
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
            u
        )
        print(f"OK: user '{u[0]}' created")
    except sqlite3.IntegrityError:
        print(f"- user '{u[0]}' already exists")

conn.commit()
conn.close()
print()
print("Done!")
print()
print("=== Default Users ===")
print("admin   / admin123")
print("manager / manager123")
print("user    / user123")
