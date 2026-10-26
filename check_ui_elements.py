# -*- coding: utf-8 -*-
PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

print("=== هل عمود 'نوع القائمة' موجود؟ ===")
if 'نوع القائمة' in content:
    print("✅ نعم، العمود موجود.")
else:
    print("❌ لا، العمود غير موجود.")

print("\n=== هل فلتر 'f-stmt' موجود؟ ===")
if 'id="f-stmt"' in content:
    print("✅ نعم، الفلتر موجود.")
else:
    print("❌ لا، الفلتر غير موجود.")
