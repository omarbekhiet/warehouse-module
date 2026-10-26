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
    
    # تعديل: عكس إشارة الإيرادات (الحسابات التي تبدأ بـ 4) لتصبح موجبة
    old_item = "item = {'code': code, 'name': node['name'], 'amount': balance}"
    new_item = """# عكس إشارة الإيرادات لتصبح موجبة
                if code.startswith('4'):
                    balance = -balance
                
                item = {'code': code, 'name': node['name'], 'amount': balance}"""
    
    if old_item in func:
        func = func.replace(old_item, new_item)
        print("✅ تم تعديل إشارة الإيرادات لتصبح موجبة.")
    else:
        print("⚠️ لم أجد كود بناء البند.")
    
    content = content.replace(match.group(0), func)
    print("✅ تم تحديث دالة income_statement.")
else:
    print("⚠️ لم أجد دالة income_statement.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تشغيل السيرفر.")
