"""
إصلاح دالة report_by_branch
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'routes', 'cash_box_routes.py')

print("=" * 60)
print("🔧 إصلاح دالة report_by_branch")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ابحث عن المشكلة
target = "'total': float(total_all['total'])"
idx = content.find(target)

if idx < 0:
    print("⚠️ السطر مش موجود")
    exit(1)

# اطبع 300 حرف حوالين المكان
print("\n📍 السياق الحالي:")
print(repr(content[idx-100:idx+150]))

# النمط الخاطئ
old = """    return jsonify({
        'success': True,
        'data': {
            'branches': result,
            'total': float(total_all['total'])
        }

    }"""

new = """    return jsonify({
        'success': True,
        'data': {
            'branches': result,
            'total': float(total_all['total'])
        }
    })"""

if old in content:
    content = content.replace(old, new, 1)
    print("\n✅ تم الإصلاح (النمط 1)")
else:
    # جرّب نمط تاني — بس `})` بعد `}`
    # ابحث عن أول `}` بعد `'total': float(...)`
    idx2 = content.find("}", idx + len(target))
    if idx2 > 0:
        # نشيل أي `}` أو `})` موجودة بعد السطر ونحط `})`
        # هنشوف السطور بعد الـ idx2
        after = content[idx2:idx2+100]
        print(f"\n📍 بعد السطر: {repr(after)}")
        
        # استبدل
        old_block = content[idx:idx2+3]
        new_block = """'total': float(total_all['total'])
        }
    })"""
        content = content[:idx] + new_block + content[idx2+3:]
        print("\n✅ تم الإصلاح (النمط 2)")
    else:
        print("\n⚠️ مش قادر ألاقي النهاية")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# تحقق
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("\n✅ الملف سليم — مفيش أخطاء")
except py_compile.PyCompileError as e:
    print(f"\n❌ فيه خطأ:")
    print(e)