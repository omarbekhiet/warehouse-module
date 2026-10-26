"""
تصدير Excel حتى لو مفيش بيانات
- ينزّل ملف بالعناوين فقط
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 60)
print("🔧 تعديل export_to_excel")
print("=" * 60)

with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 1. شيل شرط "لا توجد بيانات"
# ============================================
old_check = """        if not rows:
            return None, 'لا توجد بيانات'

        # إنشاء Excel"""

new_check = """        # إنشاء Excel (حتى لو فاضي)"""

if old_check in content:
    content = content.replace(old_check, new_check)
    print("  ✅ تم شيل شرط 'لا توجد بيانات'")
else:
    print("  ⚠️ ما لقيتش الشرط")

# ============================================
# 2. عدّل استخراج الأعمدة
# ============================================
# المشكلة: لو rows فاضية، rows[0] هيرمي IndexError
# الحل: نستخرج الأعمدة من template['columns'] أو من SQL

old_columns = """        # العناوين
        columns = list(rows[0].keys())"""

new_columns = """        # العناوين
        if rows and len(rows) > 0:
            columns = list(rows[0].keys())
        else:
            # لو مفيش بيانات، نستخرج الأعمدة من template
            columns = template.get('columns', [])
            
            # لو template['columns'] فاضي، نستخدم أسماء من SQL
            if not columns:
                # نستخرج أسماء الأعمدة من الاستعلام
                # أو نستخدم أسماء عامة
                columns = ['لا توجد بيانات']"""

if old_columns in content:
    content = content.replace(old_columns, new_columns)
    print("  ✅ تم تعديل استخراج الأعمدة")
else:
    print("  ⚠️ ما لقيتش سطر الأعمدة")

with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(SERVICE_PATH, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")