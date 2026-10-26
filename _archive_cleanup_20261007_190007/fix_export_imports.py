"""
إصلاح imports في export_routes.py
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'routes', 'export_routes.py')

print("=" * 60)
print("🔧 إصلاح imports")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# شوف أول 5 سطور
lines = content.split('\n')
print("\n📋 أول 5 سطور:")
for i, line in enumerate(lines[:5]):
    print(f"  {i+1}: {line}")

# ابحث عن السطر اللي فيه from flask import
found = False
for i, line in enumerate(lines[:20]):
    if 'from flask import' in line:
        # ضيف jsonify لو مش موجود
        if 'jsonify' not in line:
            new_line = line.rstrip().rstrip(',') + ', jsonify'
            lines[i] = new_line
            found = True
            print(f"\n  ✅ تم تحديث السطر {i+1}:")
            print(f"     من: {line}")
            print(f"     إلى: {new_line}")
        else:
            print(f"\n  ℹ️ jsonify موجود بالفعل في السطر {i+1}")
            found = True
        break

if not found:
    # ضيف import جديد
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            continue
        # ضيف في أول سطر بعد الـ imports
        lines.insert(i, 'from flask import jsonify')
        print(f"\n  ✅ تم إضافة: from flask import jsonify (السطر {i+1})")
        break

content = '\n'.join(lines)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# تحقق
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("\n  ✅ الملف سليم — مفيش أخطاء")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ فيه خطأ: {e}")