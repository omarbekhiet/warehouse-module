# -*- coding: utf-8 -*-
import re

PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# البحث عن الجزء الذي يقوم بفلترة المستوى في الواجهة
old_js = """        // الفلترة (السيرفر يرسل كل الحسابات، والواجهة تفلتر حسب المستوى)
        let data = res.data;
        if (level !== '99') {
            const targetLevel = parseInt(level);
            data = data.filter(row => getNumLevel(row.level) <= targetLevel);
        }"""

new_js = """        // السيرفر يقوم بالفلترة بالفعل، لذا نعرض البيانات كما هي
        let data = res.data;"""

if old_js in content:
    content = content.replace(old_js, new_js)
    print("✅ تم إزالة الفلترة الزائدة من الواجهة.")
else:
    # محاولة بديلة: البحث عن أي سطر يحتوي على data = data.filter
    pattern = re.compile(r'let data = res\.data;.*?data = data\.filter\(.*?\);', re.DOTALL)
    content = pattern.sub('let data = res.data;', content)
    print("✅ تم إزالة الفلترة الزائدة (محاولة بديلة).")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم حفظ التعديلات. أعد تحميل الصفحة.")
