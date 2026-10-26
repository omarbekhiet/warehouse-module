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
    
    # تعديل شرط الفلترة (إذا كان موجوداً)
    old_condition = """if stmt_filter == 'BS' and node.get('financial_statement') != 'BS':
                        continue
                    elif stmt_filter == 'IS' and node.get('financial_statement') == 'BS':
                        continue"""
    
    new_condition = """if stmt_filter == 'BS' and node.get('financial_statement') not in ['BS', 'EQ']:
                        continue
                    elif stmt_filter == 'IS' and node.get('financial_statement') not in ['IS', 'PL']:
                        continue"""
    
    if old_condition in func:
        func = func.replace(old_condition, new_condition)
        print("✅ تم تعديل شرط الفلترة في السيرفر ليشمل EQ ضمن BS.")
    else:
        print("⚠️ لم أجد شرط الفلترة في السيرفر. قد يكون تم تعديله سابقاً.")
    
    content = content.replace(match.group(0), func)
    print("✅ تم تحديث دالة trial_balance.")
else:
    print("⚠️ لم أجد دالة trial_balance.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تشغيل السيرفر.")
