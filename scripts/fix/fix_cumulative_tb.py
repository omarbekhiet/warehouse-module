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
    
    # تعديل شرط الفلترة ليكون تراكمياً (<= بدلاً من ==)
    old_filter = """if level_filter and level_filter != '99':
                    try:
                        target_level = int(level_filter)
                        if node['level'] != target_level:
                            continue
                    except ValueError:
                        pass"""
    
    new_filter = """if level_filter and level_filter != '99':
                    try:
                        target_level = int(level_filter)
                        if node['level'] > target_level:
                            continue
                    except ValueError:
                        pass"""
    
    if old_filter in func:
        func = func.replace(old_filter, new_filter)
        print("✅ تم تعديل الفلترة لتكون تراكمية (تعرض المستوى المختار وما دونه).")
    else:
        print("⚠️ لم أجد كود الفلترة.")
    
    content = content.replace(match.group(0), func)
    print("✅ تم تحديث دالة trial_balance.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تشغيل السيرفر واختبر الفلتر التراكمي.")
