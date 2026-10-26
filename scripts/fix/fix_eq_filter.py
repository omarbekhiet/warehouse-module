# -*- coding: utf-8 -*-
import re

PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# تعديل شرط الفلترة في دالة loadTrialBalance
old_filter = """        // فلترة الحسابات حسب نوع القائمة المختار
        let data = res.data;
        if (stmt && stmt !== 'all') {
            data = data.filter(r => r.financial_statement === stmt);
        }"""

new_filter = """        // فلترة الحسابات حسب نوع القائمة المختار
        let data = res.data;
        if (stmt === 'BS') {
            // الميزانية العمومية تشمل BS و EQ
            data = data.filter(r => r.financial_statement === 'BS' || r.financial_statement === 'EQ');
        } else if (stmt === 'IS') {
            // قائمة الدخل تشمل IS فقط
            data = data.filter(r => r.financial_statement === 'IS');
        }"""

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    print("✅ تم تعديل الفلتر: الميزانية العمومية تشمل BS و EQ.")
else:
    print("⚠️ لم أجد كود الفلترة. سأجرب البحث عن نمط مشابه.")
    # محاولة بديلة
    content = content.replace(
        "data = data.filter(r => r.financial_statement === stmt);",
        "data = data.filter(r => (stmt === 'BS' && (r.financial_statement === 'BS' || r.financial_statement === 'EQ')) || (stmt === 'IS' && r.financial_statement === 'IS'));"
    )
    print("✅ تم التعديل (محاولة بديلة).")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم حفظ التعديلات.")
