# -*- coding: utf-8 -*-
import sqlite3
import os
import shutil

DB_PATH = "database/warehouse.db"

def recode():
    if not os.path.exists(DB_PATH):
        print(f"❌ الملف {DB_PATH} غير موجود!")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # 1. جلب كل الحسابات
        rows = cur.execute("SELECT code, name_ar, parent_code, level FROM accounts ORDER BY code").fetchall()
        accounts = [dict(r) for r in rows]
        print(f"📊 عدد الحسابات: {len(accounts)}")

        # 2. ترتيب حسب المستوى
        levels_order = {'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4, 'L5': 5}
        accounts.sort(key=lambda x: levels_order.get(x['level'], 9))

        # 3. خريطة الكود القديم -> الكود الجديد
        mapping = {}
        parent_counters = {}

        # 4. المرور على الحسابات
        for acc in accounts:
            old_code = str(acc['code']).strip()
            parent_old = str(acc['parent_code']).strip() if acc['parent_code'] else None
            level = acc['level']
            
            parent_new = mapping.get(parent_old) if parent_old else None

            if level == 'L1':
                # الجذور: 1, 2, 3, ...
                new_code = old_code[0] if len(old_code) > 0 else old_code
                mapping[old_code] = new_code
                parent_counters[new_code] = 0
            elif level == 'L2':
                # المستوى الثاني: 11, 12, 13...
                if parent_new:
                    if parent_new not in parent_counters:
                        parent_counters[parent_new] = 0
                    parent_counters[parent_new] += 1
                    # نضيف رقم واحد فقط (1, 2, 3...)
                    new_code = f"{parent_new}{parent_counters[parent_new]}"
                else:
                    new_code = old_code
                mapping[old_code] = new_code
            elif level == 'L3':
                # المستوى الثالث: 111, 112, 121...
                if parent_new:
                    if parent_new not in parent_counters:
                        parent_counters[parent_new] = 0
                    parent_counters[parent_new] += 1
                    # نضيف رقم واحد فقط (1, 2, 3...)
                    new_code = f"{parent_new}{parent_counters[parent_new]}"
                else:
                    new_code = old_code
                mapping[old_code] = new_code
            elif level == 'L4':
                # المستوى الرابع: 111001, 111002...
                if parent_new:
                    if parent_new not in parent_counters:
                        parent_counters[parent_new] = 0
                    parent_counters[parent_new] += 1
                    # نضيف 3 أرقام (001, 002...)
                    new_code = f"{parent_new}{parent_counters[parent_new]:03d}"
                else:
                    new_code = old_code
                mapping[old_code] = new_code
            else:
                # مستويات أعمق (L5+)
                if parent_new:
                    if parent_new not in parent_counters:
                        parent_counters[parent_new] = 0
                    parent_counters[parent_new] += 1
                    new_code = f"{parent_new}{parent_counters[parent_new]:03d}"
                else:
                    new_code = old_code
                mapping[old_code] = new_code

        # 5. عرض بعض الأمثلة
        print("\n=== أمثلة على الأكواد الجديدة ===")
        for old in ['1000', '1100', '1110', '1111', '1130', '2000', '2200', '4000', '8000']:
            if old in mapping:
                print(f"  {old} -> {mapping[old]}")

        # 6. تحديث جدول الحسابات
        print("\n=== تحديث جدول الحسابات ===")
        for old_code, new_code in mapping.items():
            parent_old = None
            for acc in accounts:
                if str(acc['code']).strip() == old_code:
                    parent_old = str(acc['parent_code']).strip() if acc['parent_code'] else None
                    break
            parent_new = mapping.get(parent_old) if parent_old else None

            cur.execute("UPDATE accounts SET code = ?, parent_code = ? WHERE code = ?", (new_code, parent_new, old_code))
        print(f"✅ تم تحديث {len(mapping)} حساب.")

        # 7. تحديث جدول القيود
        print("\n=== تحديث جدول القيود ===")
        updated_lines = 0
        for old_code, new_code in mapping.items():
            cur.execute("UPDATE journal_entry_lines SET account_code = ? WHERE account_code = ?", (new_code, old_code))
            updated_lines += cur.rowcount
        print(f"✅ تم تحديث {updated_lines} سطر قيد.")

        # 8. تحديث الجداول الأخرى
        account_columns = [
            ('item_groups', 'inventory_account'), ('item_groups', 'cost_account'),
            ('item_groups', 'revenue_account'), ('item_groups', 'clearing_account'),
            ('item_groups', 'purchase_account'), ('item_groups', 'adjustment_account'),
            ('item_groups', 'waste_account'), ('item_groups', 'revenue_return_account'),
            ('item_groups', 'discount_account'),
            ('items', 'inventory_account'), ('items', 'cost_account'),
            ('items', 'revenue_account'), ('items', 'clearing_account'),
        ]
        
        print("\n=== تحديث الجداول الأخرى ===")
        for table, column in account_columns:
            try:
                cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table})").fetchall()]
                if column in cols:
                    for old_code, new_code in mapping.items():
                        cur.execute(f"UPDATE {table} SET {column} = ? WHERE {column} = ?", (new_code, old_code))
                    print(f"  ✅ تم تحديث {table}.{column}")
            except Exception:
                pass

        conn.commit()
        print("\n🎉 تم الانتهاء بنجاح!")

        res = cur.execute("SELECT SUM(debit_amount) as d, SUM(credit_amount) as c FROM journal_entry_lines").fetchone()
        print(f"\n📊 التحقق من التوازن:")
        print(f"  إجمالي المدين: {res['d']}")
        print(f"  إجمالي الدائن: {res['c']}")
        print(f"  الفرق: {(res['d'] or 0) - (res['c'] or 0)}")

    except Exception as e:
        conn.rollback()
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    recode()
