# -*- coding: utf-8 -*-
import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# حذف الدالة الأولى (التي تحتوي على /reports/income-statement)
pattern = re.compile(r"@report_bp\.route\('/reports/income-statement'.*?(?=@report_bp\.route|$)", re.DOTALL)
content = pattern.sub("", content)

# التحقق من عدم وجود دالة أخرى بنفس الاسم
matches = re.findall(r"def income_statement\(\)", content)
if len(matches) > 1:
    print(f"⚠️ لا يزال هناك {len(matches)} دالة income_statement. قد تحتاج لحذف المزيد.")
else:
    print(f"✅ تم حذف الدالة المكررة. متبقي {len(matches)} دالة income_statement.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم حفظ الملف. أعد تشغيل السيرفر.")
