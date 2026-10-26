import re

PATH = "app/routes/report_routes.py"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

pattern = re.compile(r"@report_bp\.route\('/income-statement'.*?(?=@report_bp\.route|$)", re.DOTALL)
match = pattern.search(content)

if match:
    func = match.group(0)
    # البحث عن ترتيب العمليات
    has_rollup = "sorted_for_rollup" in func
    has_filter = "level_filter" in func
    
    # تحديد مكان التجميع والفلترة
    rollup_pos = func.find("sorted_for_rollup")
    filter_pos = func.find("if level_filter")
    
    print(f"هل يوجد تجميع (Roll-up)؟ {has_rollup}")
    print(f"هل يوجد فلترة (Filter)؟ {has_filter}")
    print(f"موضع التجميع: {rollup_pos}")
    print(f"موضع الفلترة: {filter_pos}")
    
    if rollup_pos < filter_pos:
        print("✅ التجميع يحدث قبل الفلترة (وهذا صحيح).")
    else:
        print("❌ الفلترة تحدث قبل التجميع (وهذا خطأ).")
else:
    print("❌ لم أجد دالة income_statement.")
