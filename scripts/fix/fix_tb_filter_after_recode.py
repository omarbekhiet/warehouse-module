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
    
    # التأكد من أن الفلترة تستخدم level_filter
    if "level_filter" not in func:
        func = func.replace(
            "to_date = request.args.get('to_date')",
            "to_date = request.args.get('to_date')\n    level_filter = request.args.get('level')"
        )
        print("✅ تمت إضافة قراءة level_filter.")
    
    # تعديل شرط الفلترة (إذا لم يكن موجوداً)
    if "if level_filter and level_filter != '99':" not in func:
        old_result = """result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                node['closing_balance'] = node['opening_balance'] + node['period_debit'] - node['period_credit']
                result.append(node)"""
        
        new_result = """result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                node['closing_balance'] = node['opening_balance'] + node['period_debit'] - node['period_credit']
                
                # الفلترة حسب المستوى (تراكمي)
                if level_filter and level_filter != '99':
                    try:
                        target_level = int(level_filter)
                        if node['level'] > target_level:
                            continue
                    except ValueError:
                        pass
                
                result.append(node)"""
        
        if old_result in func:
            func = func.replace(old_result, new_result)
            print("✅ تمت إضافة فلترة المستوى.")
        else:
            print("⚠️ لم أجد كود بناء النتيجة.")
    
    content = content.replace(match.group(0), func)
    print("✅ تم تحديث دالة trial_balance.")
else:
    print("⚠️ لم أجد دالة trial_balance.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تشغيل السيرفر.")
