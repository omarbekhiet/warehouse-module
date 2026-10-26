import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# البحث عن دالة trial_balance
pattern = re.compile(r"@report_bp\.route\('/trial-balance'.*?(?=@report_bp\.route|$)", re.DOTALL)
match = pattern.search(content)

if match:
    print("=== محتوى دالة trial_balance (أول 30 سطراً) ===")
    lines = match.group(0).split('\n')
    for i, line in enumerate(lines[:30]):
        print(f"{i+1}: {line}")
    
    print("\n=== هل يحتوي على level_filter؟ ===")
    if "level_filter" in match.group(0):
        print("✅ نعم، level_filter موجود.")
    else:
        print("❌ لا، level_filter غير موجود!")
else:
    print("❌ لم أجد دالة trial_balance.")
