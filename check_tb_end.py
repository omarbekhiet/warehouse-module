import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

pattern = re.compile(r"@report_bp\.route\('/trial-balance'.*?(?=@report_bp\.route|$)", re.DOTALL)
match = pattern.search(content)

if match:
    lines = match.group(0).split('\n')
    print("=== آخر 30 سطراً من دالة trial_balance ===")
    for i, line in enumerate(lines[-30:]):
        print(f"{len(lines)-30+i+1}: {line}")
else:
    print("❌ لم أجد دالة trial_balance.")
