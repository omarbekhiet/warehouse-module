# -*- coding: utf-8 -*-
import re

PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# 1. تعيين القيمة الافتراضية للمستوى إلى 2 (المستوى الثاني)
old_select = '<select id="f-level" class="form-select form-select-sm" onchange="loadTrialBalance()">'
new_select = '<select id="f-level" class="form-select form-select-sm" onchange="loadTrialBalance()">'
content = content.replace(
    '<option value="99">كل المستويات</option>\n                    <option value="1">المستوى الأول فقط</option>',
    '<option value="99">كل المستويات</option>\n                    <option value="1">المستوى الأول فقط</option>'
)

# إضافة selected للخيار 2 (المستوى الثاني)
content = content.replace(
    '<option value="2">المستوى الثاني فقط</option>',
    '<option value="2" selected>المستوى الثاني فقط</option>'
)
print("✅ تم تعيين المستوى الافتراضي إلى الثاني.")

# 2. التأكد من أن دالة الفلترة في الواجهة لا تستبعد EQ
old_filter = """        let data = res.data;
        if (stmt === 'BS') {
            // الميزانية العمومية تشمل BS و EQ
            data = data.filter(r => r.financial_statement === 'BS' || r.financial_statement === 'EQ');
        } else if (stmt === 'IS') {
            // قائمة الدخل تشمل IS فقط
            data = data.filter(r => r.financial_statement === 'IS');
        }"""
        
new_filter = """        let data = res.data;
        // السيرفر قام بالفلترة بالفعل، لذا نعرض البيانات كما هي
        // (إذا أردت التأكد، يمكنك إضافة فلترة احتياطية هنا)"""

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    print("✅ تم إزالة الفلترة الزائدة من الواجهة.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم الحفظ.")
