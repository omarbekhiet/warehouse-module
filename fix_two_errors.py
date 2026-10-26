from app import create_app
from app.database import db

app = create_app()
with app.app_context():
    with db.get_connection() as conn:
        # 1. تصحيح الحساب 22006 (شيكات صادرة)
        # بما أن أبوه 22، والأكواد الأخرى في المستوى الرابع تحت 22 هي 221001، 222001...
        # سنغير كوده إلى 220006 (أو 229001 إذا أردت ترتيباً منطقياً)
        # الأفضل: نغيره إلى 220006 ليكون تابعاً لـ 22 مباشرة
        conn.execute("UPDATE accounts SET code = '220006' WHERE code = '22006'")
        conn.execute("UPDATE journal_entry_lines SET account_code = '220006' WHERE account_code = '22006'")
        print("✅ تم تصحيح 22006 -> 220006")

        # 2. تصحيح 123006001 (وسيط - استلام بضاعة) ليكون L5
        conn.execute("UPDATE accounts SET level = 'L5' WHERE code = '123006001'")
        conn.execute("UPDATE accounts SET level = 'L5' WHERE code = '123006002'")
        conn.execute("UPDATE accounts SET level = 'L5' WHERE code = '123006003'")
        print("✅ تم تصحيح 123006001/2/3 إلى L5")

        conn.commit()
        print("🎉 تم الإصلاح.")
