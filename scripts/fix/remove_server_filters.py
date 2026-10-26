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
    
    # إزالة فلترة المستوى من السيرفر (نترك السيرفر يرسل كل الحسابات)
    old_filter = """# فلترة المستوى
                if level_filter and level_filter != '99':
                    try:
                        target_level = int(level_filter)
                        if node['level'] != target_level:
                            continue
                    except ValueError:
                        pass"""
    
    if old_filter in func:
        func = func.replace(old_filter, "")
        print("✅ تم إزالة فلترة المستوى من السيرفر.")
    else:
        print("⚠️ لم أجد كود فلترة المستوى في السيرفر.")
    
    # إزالة فلترة نوع القائمة أيضاً (نتركها للواجهة)
    old_stmt_filter = """# فلترة نوع القائمة
                if stmt_filter and stmt_filter != 'all':
                    if stmt_filter == 'BS' and node['financial_statement'] not in ['BS', 'EQ']:
                        continue
                    elif stmt_filter == 'IS' and node['financial_statement'] not in ['IS']:
                        continue"""
    
    if old_stmt_filter in func:
        func = func.replace(old_stmt_filter, "")
        print("✅ تم إزالة فلترة نوع القائمة من السيرفر.")
    
    content = content.replace(match.group(0), func)
    print("✅ تم تحديث دالة trial_balance.")
else:
    print("⚠️ لم أجد دالة trial_balance.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تشغيل السيرفر.")
