# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = "database/warehouse.db"

def restructure_tree():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # 1. جلب كل الحسابات
        accounts = cur.execute("SELECT code, name_ar, parent_code, level FROM accounts ORDER BY code").fetchall()
        acc_dict = {str(a['code']).strip(): dict(a) for a in accounts}

        # 2. تحديد "الورقية" (التي ليس لها أبناء) و "الآباء"
        parent_codes = set()
        for a in accounts:
            parent = str(a['parent_code']).strip() if a['parent_code'] else None
            if parent:
                parent_codes.add(parent)

        # 3. حساب العمق (المستوى) لكل حساب بناءً على الشجرة
        def get_depth(code, seen=None):
            if seen is None: seen = set()
            if code in seen: return 1
            seen.add(code)
            acc = acc_dict.get(code)
            if not acc: return 1
            parent = str(acc['parent_code']).strip() if acc['parent_code'] else None
            if not parent or parent not in acc_dict:
                return 1
            return 1 + get_depth(parent, seen)

        # 4. تحديد المستوى الجديد:
        # - الجذور (L1) تبقى L1.
        # - الحسابات التي ليس لها أبناء (الورقية) تصبح L5.
        # - الحسابات الوسيطة (الآباء) تأخذ مستويات بين L2 و L4 بناءً على عمقها.
        
        updated_count = 0
        for code, acc in acc_dict.items():
            depth = get_depth(code)
            is_leaf = code not in parent_codes  # ليس له أبناء
            is_root = not acc['parent_code'] or str(acc['parent_code']).strip() not in acc_dict

            if is_root:
                new_level = 'L1'
            elif is_leaf:
                new_level = 'L5'
            else:
                # الآباء الوسيطون: نوزعهم على L2, L3, L4
                # إذا كان العمق 2 (ابن الجذر) -> L2
                # إذا كان العمق 3 -> L3
                # إذا كان العمق 4 -> L4
                if depth <= 2:
                    new_level = 'L2'
                elif depth == 3:
                    new_level = 'L3'
                else:
                    new_level = 'L4'

            if acc['level'] != new_level:
                cur.execute("UPDATE accounts SET level = ? WHERE code = ?", (new_level, code))
                updated_count += 1

        conn.commit()
        print(f"✅ تم تحديث مستوى {updated_count} حساب.")
        
        # 5. التحقق من التوزيع الجديد
        print("\n=== توزيع المستويات بعد التعديل ===")
        for lvl in ['L1', 'L2', 'L3', 'L4', 'L5']:
            count = cur.execute("SELECT COUNT(*) as c FROM accounts WHERE level = ?", (lvl,)).fetchone()['c']
            print(f"{lvl}: {count} حساب")

        # 6. التحقق من أن جميع الحركات على L5 فقط
        print("\n=== الحسابات التي عليها حركات (يجب أن تكون كلها L5) ===")
        q = """
            SELECT CAST(jl.account_code AS TEXT) as code, a.name_ar, a.level
            FROM journal_entry_lines jl
            JOIN journal_entries je ON jl.journal_entry_id = je.id
            LEFT JOIN accounts a ON CAST(jl.account_code AS TEXT) = CAST(a.code AS TEXT)
            WHERE je.status = 'POSTED'
            GROUP BY jl.account_code
        """
        rows = cur.execute(q).fetchall()
        non_l5 = 0
        for r in rows:
            lvl = r['level'] if r['level'] else 'غير موجود'
            if lvl != 'L5':
                print(f"⚠️ كود: {r['code']} | مستوى: {lvl} | اسم: {r['name_ar']}")
                non_l5 += 1
        if non_l5 == 0:
            print("✅ جميع الحركات على L5.")
        else:
            print(f"⚠️ هناك {non_l5} حساب بها حركات وليست L5.")

    except Exception as e:
        conn.rollback()
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    restructure_tree()
