# -*- coding: utf-8 -*-
import re

PATH = "app/static/income_statement.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# 1. تعديل أنماط CSS لتقليل المسافات
old_css = """
        .cf-row { display: flex; justify-content: space-between; padding: 6px 10px; border-bottom: 1px solid #f1f5f9; }
        .cf-row:hover { background: #f8fafc; }
        .cf-amount { font-family: monospace; font-weight: bold; }
        .cf-total { background: #e2e8f0; font-weight: 900; padding: 10px; border-top: 2px solid #cbd5e1; display: flex; justify-content: space-between; }
        .cf-subtotal { background: #f1f5f9; font-weight: 800; padding: 8px 10px; border-top: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; display: flex; justify-content: space-between; margin-top: 5px; }
        .cf-grand-total { background: #dbeafe; color: #1e3c72; font-weight: 900; padding: 15px; border-radius: 6px; display: flex; justify-content: space-between; margin-top: 20px; font-size: 15px; }
        .cf-final-total { background: linear-gradient(135deg, #10b981, #059669); color: white; font-weight: 900; padding: 18px; border-radius: 6px; display: flex; justify-content: space-between; margin-top: 20px; font-size: 16px; }
        .cf-final-total.loss { background: linear-gradient(135deg, #ef4444, #dc2626); }
"""

new_css = """
        .cf-row { display: flex; justify-content: space-between; padding: 2px 8px; border-bottom: 1px solid #f1f5f9; font-size: 12px; line-height: 1.2; }
        .cf-row:hover { background: #f8fafc; }
        .cf-amount { font-family: monospace; font-weight: bold; }
        .cf-total { background: #e2e8f0; font-weight: 900; padding: 4px 8px; border-top: 1px solid #cbd5e1; display: flex; justify-content: space-between; font-size: 12px; }
        .cf-subtotal { background: #f1f5f9; font-weight: 800; padding: 3px 8px; border-top: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; display: flex; justify-content: space-between; margin-top: 2px; font-size: 12px; }
        .cf-grand-total { background: #dbeafe; color: #1e3c72; font-weight: 900; padding: 6px 10px; border-radius: 4px; display: flex; justify-content: space-between; margin-top: 10px; font-size: 13px; }
        .cf-final-total { background: linear-gradient(135deg, #10b981, #059669); color: white; font-weight: 900; padding: 8px 10px; border-radius: 4px; display: flex; justify-content: space-between; margin-top: 10px; font-size: 14px; }
        .cf-final-total.loss { background: linear-gradient(135deg, #ef4444, #dc2626); }
"""

if old_css in content:
    content = content.replace(old_css, new_css)
    print("✅ تم تقليل المسافات في قائمة الدخل.")
else:
    print("⚠️ لم أجد كود CSS القديم. قد يكون تم تعديله.")

# 2. إضافة تقليل المسافة بين الأقسام (margin-top للـ section-title)
content = content.replace(
    '.section-title { background: #1e3c72; color: white; padding: 8px 12px; border-radius: 6px; font-weight: bold; margin-top: 20px; margin-bottom: 10px; }',
    '.section-title { background: #1e3c72; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; margin-top: 8px; margin-bottom: 4px; font-size: 12px; }'
)

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم حفظ التعديلات. أعد تحميل الصفحة.")
