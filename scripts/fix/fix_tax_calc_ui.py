# -*- coding: utf-8 -*-
import re

PATH = "app/static/income_statement.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# تعديل حساب صافي الربح النهائي ليكون (الربح قبل الضريبة - الضريبة)
old_calc = "const netProfit = profitBeforeTax + taxExpense;"
new_calc = "const netProfit = profitBeforeTax - Math.abs(taxExpense);"

if old_calc in content:
    content = content.replace(old_calc, new_calc)
    print("✅ تم تعديل معادلة صافي الربح (خصم الضريبة).")
else:
    print("⚠️ لم أجد معادلة صافي الربح.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم الحفظ.")
