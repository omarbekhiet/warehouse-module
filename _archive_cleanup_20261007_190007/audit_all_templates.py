"""
مراجعة شاملة لكل قوالب Excel
- فحص كل قالب تصدير
- فحص كل قالب استيراد
- تحديد الأخطاء
- اقتراح إصلاحات
"""
import os
import sqlite3
import re

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'database', 'warehouse.db')
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 70)
print("🔍 مراجعة شاملة لكل قوالب Excel")
print("=" * 70)

# ============================================
# 1. اتصال الداتابيز
# ============================================
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# ============================================
# 2. جدول الأعمدة
# ============================================
tables_cols = {}
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
for r in cur.fetchall():
    t = r['name']
    cur2 = conn.execute(f"PRAGMA table_info({t})")
    tables_cols[t] = [c[1] for c in cur2.fetchall()]

print(f"\n📊 عدد الجداول: {len(tables_cols)}")

# ============================================
# 3. قراءة excel_service.py
# ============================================
with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 4. استخراج قوالب التصدير
# ============================================
print("\n" + "=" * 70)
print("📤 قوالب التصدير")
print("=" * 70)

# ابحث عن EXPORT_TEMPLATES
export_match = re.search(r"EXPORT_TEMPLATES = \{(.*?)\n    \}", content, re.DOTALL)
if not export_match:
    print("❌ ما لقيتش EXPORT_TEMPLATES")
    exit(1)

export_block = export_match.group(1)

# استخرج كل قالب
template_pattern = r"'(?P<key>\w+)':\s*\{\s*'name':\s*'(?P<name>[^']+)',\s*'sql':\s*\"\"\"(?P<sql>.*?)\"\"\""
templates = re.findall(template_pattern, export_block, re.DOTALL)

print(f"\n📊 عدد القوالب: {len(templates)}\n")

ok_templates = []
error_templates = []

for key, name, sql in templates:
    sql = sql.strip()
    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
        count = len(rows)
        
        if count > 0:
            print(f"  ✅ {key:25} — {count:5} صف — {name}")
            ok_templates.append((key, name, count))
        else:
            print(f"  ⚠️  {key:25} — 0 صف (فاضي) — {name}")
            ok_templates.append((key, name, 0))
    except Exception as e:
        err = str(e)[:80]
        print(f"  ❌ {key:25} — {err}")
        error_templates.append((key, name, err))

print(f"\n📊 النتيجة:")
print(f"  ✅ نجح: {len(ok_templates)}")
print(f"  ❌ فشل: {len(error_templates)}")

# ============================================
# 5. فحص قوالب الاستيراد
# ============================================
print("\n" + "=" * 70)
print("📥 قوالب الاستيراد")
print("=" * 70)

import_match = re.search(r"IMPORT_TEMPLATES = \{(.*?)\n    \}", content, re.DOTALL)
if not import_match:
    print("❌ ما لقيتش IMPORT_TEMPLATES")
    exit(1)

import_block = import_match.group(1)

# استخرج كل قالب استيراد
import_pattern = r"'(?P<key>\w+)':\s*\{\s*'name':\s*'(?P<name>[^']+)',\s*'table':\s*'(?P<table>[^']+)',\s*'columns':\s*\{(?P<cols>.*?)\},\s*'required':\s*\[(?P<req>[^\]]+)\]"
import_templates = re.findall(import_pattern, import_block, re.DOTALL)

print(f"\n📊 عدد القوالب: {len(import_templates)}\n")

for key, name, table, cols_str, req_str in import_templates:
    # استخرج الأعمدة
    cols = re.findall(r"'(?P<field>\w+)':\s*'(?P<label>[^']+)'", cols_str)
    fields = [c[0] for c in cols]
    
    # الجدول موجود؟
    if table not in tables_cols:
        print(f"  ❌ {key:25} — الجدول {table} مش موجود")
        continue
    
    # الأعمدة موجودة؟
    actual_cols = tables_cols[table]
    missing = [f for f in fields if f not in actual_cols and f != 'id']
    
    if missing:
        print(f"  ⚠️  {key:25} — أعمدة ناقصة: {', '.join(missing[:3])}")
    else:
        print(f"  ✅ {key:25} — {len(fields)} عمود — {name}")

# ============================================
# 6. التقرير النهائي
# ============================================
print("\n" + "=" * 70)
print("📊 التقرير النهائي")
print("=" * 70)

if error_templates:
    print(f"\n❌ قوالب التصدير الفاشلة ({len(error_templates)}):")
    for key, name, err in error_templates:
        print(f"  • {key}: {err}")

# حفظ التقرير
report_path = os.path.join(BASE, 'excel_templates_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("تقرير قوالب Excel\n")
    f.write("=" * 60 + "\n\n")
    
    f.write(f"قوالب التصدير:\n")
    f.write(f"  ✅ نجح: {len(ok_templates)}\n")
    f.write(f"  ❌ فشل: {len(error_templates)}\n\n")
    
    if error_templates:
        f.write("القوالب الفاشلة:\n")
        for key, name, err in error_templates:
            f.write(f"  • {key}: {err}\n")
    
    f.write(f"\nقوالب الاستيراد:\n")
    for key, name, table, cols_str, req_str in import_templates:
        f.write(f"  • {key} → {table}\n")

print(f"\n📄 التقرير محفوظ: {report_path}")

conn.close()