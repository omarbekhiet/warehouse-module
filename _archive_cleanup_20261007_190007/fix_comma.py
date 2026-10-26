"""
إصلاح الفاصلة المكررة في excel_service.py
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 60)
print("🔧 إصلاح الفاصلة المكررة")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# عد المرات
count_before = content.count('""",,')
print(f"  📊 عدد الفواصل المكررة: {count_before}")

# استبدل
content = content.replace('""",,', '""",')

count_after = content.count('""",,')
print(f"  📊 بعد الإصلاح: {count_after}")

# ابحث عن أي فواصل مكررة تانية
content = re.sub(r',,', ',', content)
content = re.sub(r'",,', '",', content)
content = re.sub(r'",\)', '")', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")
    
    # اطبع السياق
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    
    match = re.search(r'line (\d+)', str(e))
    if match:
        line_no = int(match.group(1))
        print(f"\n  📍 السياق حول السطر {line_no}:")
        for i in range(max(0, line_no-3), min(line_no+3, len(lines))):
            marker = " ← ← ←" if i+1 == line_no else ""
            print(f"  {i+1}: {lines[i]}{marker}")