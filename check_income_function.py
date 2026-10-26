import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# البحث عن دالة income_statement (التي تحتوي على /income-statement)
pattern = re.compile(r"@report_bp\.route\('/income-statement'.*?(?=@report_bp\.route|$)", re.DOTALL)
match = pattern.search(content)

if match:
    print("=== محتوى دالة income_statement ===")
    lines = match.group(0).split('\n')
    for i, line in enumerate(lines[:25]):
        print(f"{i+1}: {line}")
else:
    print("❌ لم أجد دالة income_statement.")
