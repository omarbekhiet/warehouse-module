# -*- coding: utf-8 -*-
import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# البحث عن دالة trial_balance
pattern = re.compile(r"@report_bp\.route\('/trial-balance'.*?(?=@report_bp\.route|$)", re.DOTALL)
match = pattern.search(content)

if match:
    func = match.group(0)
    
    # 1. تعديل جلب الحسابات ليشمل financial_statement
    old_select = 'conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, \'L1\') as level FROM accounts ORDER BY code")'
    new_select = 'conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, \'L1\') as level, financial_statement FROM accounts ORDER BY code")'
    
    if old_select in func:
        func = func.replace(old_select, new_select)
        print("✅ تم تعديل جلب الحسابات ليشمل financial_statement.")
    else:
        print("⚠️ لم أجد كود جلب الحسابات.")
    
    # 2. إضافة financial_statement إلى acc_dict
    old_dict = """acc_dict[code] = {
                    'code': code,
                    'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl,
                    'opening_balance': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0
                }"""
    
    new_dict = """acc_dict[code] = {
                    'code': code,
                    'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl,
                    'financial_statement': a['financial_statement'],
                    'opening_balance': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0
                }"""
    
    if old_dict in func:
        func = func.replace(old_dict, new_dict)
        print("✅ تمت إضافة financial_statement إلى قاموس الحسابات.")
    else:
        print("⚠️ لم أجد كود بناء القاموس.")
    
    # 3. إضافة الفلترة حسب financial_statement (إذا تم إرسال stmt)
    old_filter = """# الفلترة: نعرض فقط الحسابات التي تنتمي للمستوى المختار
                if level_filter and level_filter != '99':"""
    
    new_filter = """# الفلترة حسب نوع القائمة (financial_statement)
                stmt_filter = request.args.get('stmt')  # BS أو IS
                if stmt_filter and stmt_filter != 'all':
                    if stmt_filter == 'BS' and node.get('financial_statement') != 'BS':
                        continue
                    elif stmt_filter == 'IS' and node.get('financial_statement') == 'BS':
                        continue
                
                # الفلترة: نعرض فقط الحسابات التي تنتمي للمستوى المختار
                if level_filter and level_filter != '99':"""
    
    if old_filter in func:
        func = func.replace(old_filter, new_filter)
        print("✅ تمت إضافة الفلترة حسب financial_statement.")
    else:
        print("⚠️ لم أجد كود الفلترة.")
    
    content = content.replace(match.group(0), func)
    print("✅ تم تحديث دالة trial_balance.")
else:
    print("⚠️ لم أجد دالة trial_balance.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تشغيل السيرفر.")
