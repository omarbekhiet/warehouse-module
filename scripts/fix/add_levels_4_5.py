# -*- coding: utf-8 -*-
import re

PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# البحث عن قائمة المستويات وإضافة الخيارات 4 و 5
old_select = """<select id="f-level" class="form-select form-select-sm" onchange="loadTrialBalance()">
                    <option value="99">كل المستويات</option>
                    <option value="1">المستوى الأول فقط</option>
                    <option value="2">المستوى الثاني فقط</option>
                    <option value="3">المستوى الثالث فقط</option>
                </select>"""

new_select = """<select id="f-level" class="form-select form-select-sm" onchange="loadTrialBalance()">
                    <option value="99">كل المستويات</option>
                    <option value="1">المستوى الأول فقط</option>
                    <option value="2">المستوى الثاني فقط</option>
                    <option value="3">المستوى الثالث فقط</option>
                    <option value="4">المستوى الرابع فقط</option>
                    <option value="5">المستوى الخامس فقط</option>
                </select>"""

if old_select in content:
    content = content.replace(old_select, new_select)
    print("✅ تمت إضافة المستويات 4 و 5 إلى القائمة.")
else:
    # محاولة بديلة: البحث عن أي قائمة منسدلة تحتوي على f-level
    pattern = re.compile(r'<select id="f-level".*?</select>', re.DOTALL)
    match = pattern.search(content)
    if match:
        new_select_alt = """<select id="f-level" class="form-select form-select-sm" onchange="loadTrialBalance()">
                    <option value="99">كل المستويات</option>
                    <option value="1">المستوى الأول فقط</option>
                    <option value="2">المستوى الثاني فقط</option>
                    <option value="3">المستوى الثالث فقط</option>
                    <option value="4">المستوى الرابع فقط</option>
                    <option value="5">المستوى الخامس فقط</option>
                </select>"""
        content = content.replace(match.group(0), new_select_alt)
        print("✅ تمت إضافة المستويات 4 و 5 (محاولة بديلة).")
    else:
        print("⚠️ لم أجد قائمة المستويات.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم الحفظ. أعد تحميل الصفحة لتجربة المستويات 4 و 5.")
