from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        print("=== فحص financial_statement لحسابات حقوق الملكية (8) ===")
        rows = conn.execute("SELECT code, name_ar, financial_statement FROM accounts WHERE code LIKE '8%' LIMIT 10").fetchall()
        for r in rows:
            print(f"كود: {r['code']} | اسم: {r['name_ar']} | financial_statement: {r['financial_statement']}")
