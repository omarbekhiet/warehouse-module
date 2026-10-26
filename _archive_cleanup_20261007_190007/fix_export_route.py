"""
إصلاح export_routes.py — إزالة try بدون except + except مكرر
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'routes', 'export_routes.py')

print("=" * 60)
print("🔧 إصلاح export_routes.py")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# اطبع السطور 195-215
lines = content.split('\n')
print("\n📋 السطور 195-215 قبل الإصلاح:")
for i in range(194, min(215, len(lines))):
    print(f"  {i+1}: {lines[i]}")

# الإصلاح 1: إضافة except للـ try الأول
old1 = """    try:
        file_content = file.read()
        result = excel_service.import_from_excel(template_key, file_content)
        return jsonify(result)


@export_bp.route('/excel/preview/<template_key>', methods=['POST'])"""

new1 = """    try:
        file_content = file.read()
        result = excel_service.import_from_excel(template_key, file_content)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/excel/preview/<template_key>', methods=['POST'])"""

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("\n  ✅ تم إضافة except للـ try الأول")
else:
    print("\n  ⚠️ النمط 1 مش موجود — نجرب نمط تاني")

# الإصلاح 2: شيل except المكرر
old2 = """    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500"""

new2 = """    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500"""

if old2 in content:
    content = content.replace(old2, new2)
    print("  ✅ تم إزالة except المكرر")
else:
    print("  ⚠️ النمط 2 مش موجود")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("\n  ✅ الملف سليم — مفيش أخطاء")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ لسه فيه خطأ:")
    print(f"     {e}")
    
    # اطبع السياق
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    
    # استخرج رقم السطر
    match = re.search(r'line (\d+)', str(e))
    if match:
        line_no = int(match.group(1))
        print(f"\n  📍 السياق حول السطر {line_no}:")
        for i in range(max(0, line_no-5), min(line_no+5, len(lines))):
            marker = " ← ← ←" if i+1 == line_no else ""
            print(f"  {i+1}: {lines[i]}{marker}")