"""
إصلاح export_routes.py — إزالة except مكرر
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

# 1. إصلاح try بدون except
old_pattern = '''    try:
        file_content = file.read()
        result = excel_service.import_from_excel(template_key, file_content)
        return jsonify(result)


@export_bp.route('/excel/preview/<template_key>', methods=['POST'])'''

new_pattern = '''    try:
        file_content = file.read()
        result = excel_service.import_from_excel(template_key, file_content)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/excel/preview/<template_key>', methods=['POST'])'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    print("  ✅ تم إضافة except للـ try الأول")
else:
    print("  ⚠️ النمط الأول مش موجود")


# 2. شيل except المكرر
old_dup = '''    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500'''

new_dup = '''    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500'''

if old_dup in content:
    content = content.replace(old_dup, new_dup)
    print("  ✅ تم إزالة except المكرر")
else:
    print("  ⚠️ النمط المكرر مش موجود")


with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("\n  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"\n  ❌ {e}")