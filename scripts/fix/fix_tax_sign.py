# -*- coding: utf-8 -*-
import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# البحث عن دالة income_statement
pattern = re.compile(r"@report_bp\.route\('/income-statement'.*?(?=@report_bp\.route|$)", re.DOTALL)
match = pattern.search(content)

if match:
    func = match.group(0)
    
    # تعديل: عكس إشارة الضرائب (7) لتصبح سالبة
    old_code = """# عكس إشارة التكلفة والمصروفات لتصبح سالبة
                elif code.startswith('3') or code.startswith('5'):
                    node['closing_balance'] = -abs(node['closing_balance'])"""
    
    new_code = """# عكس إشارة التكلفة والمصروفات لتصبح سالبة
                elif code.startswith('3') or code.startswith('5') or code.startswith('7'):
                    node['closing_balance'] = -abs(node['closing_balance'])"""
    
    if old_code in func:
        func = func.replace(old_code, new_code)
        print("✅ تم تعديل إشارة الضرائب لتصبح سالبة.")
    else:
        print("⚠️ لم أجد كود عكس الإشارة.")
    
    content = content.replace(match.group(0), func)
    print("✅ تم تحديث دالة income_statement.")
else:
    print("⚠️ لم أجد دالة income_statement.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تشغيل السيرفر.")
