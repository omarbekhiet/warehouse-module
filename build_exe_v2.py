"""
بناء EXE — نسخة 2
تستخدم `python -m PyInstaller` بدل `pyinstaller`
"""
import os
import sys
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 70)
print("🏗️ بناء ملف EXE (v2)")
print("=" * 70)

# ============================================
# 1. تأكد إن PyInstaller متثبت
# ============================================
print("\n🔍 فحص PyInstaller...")
try:
    import PyInstaller
    print(f"  ✅ PyInstaller: {PyInstaller.__version__}")
except ImportError as e:
    print(f"  ❌ مش مثبت: {e}")
    sys.exit(1)

# ============================================
# 2. تأكد من الملفات
# ============================================
print("\n🔍 فحص الملفات...")

required_files = {
    'run_exe.py': os.path.join(BASE, 'run_exe.py'),
    'app/static': os.path.join(BASE, 'app', 'static'),
    'app/__init__.py': os.path.join(BASE, 'app', '__init__.py'),
    'database': os.path.join(BASE, 'database'),
}

for name, path in required_files.items():
    if os.path.exists(path):
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}: مش موجود")
        sys.exit(1)

# ============================================
# 3. بناء الأمر
# ============================================
print("\n📦 بناء الأمر...")

# المسارات
static_dir = os.path.join(BASE, 'app', 'static')
db_dir = os.path.join(BASE, 'database')

# البيانات المرفقة
# ⚠️ على Windows، الفاصل `;`
add_data = [
    f'{static_dir};app/static',
    f'{db_dir};database',
]

# ملفات إضافية
for extra in ['requirements.txt', 'README.md']:
    path = os.path.join(BASE, extra)
    if os.path.exists(path):
        add_data.append(f'{path};.')

# الأمر
cmd = [
    sys.executable,           # ← ← ← python الحالي
    '-m', 'PyInstaller',      # ← ← ← وحدة PyInstaller
    '--noconfirm',
    '--clean',
    '--name=WarehouseModule',
    '--onefile',
    '--console',
]

# Add data
for item in add_data:
    cmd.extend(['--add-data', item])

# Hidden imports
hidden_imports = [
    'flask',
    'flask_cors',
    'openpyxl',
    'sqlite3',
    'app',
    'app.routes',
    'app.services',
    'app.ai',
    'app.database',
    'app.config',
    'app.utils',
]

for h in hidden_imports:
    cmd.extend(['--hidden-import', h])

# Main file
cmd.append('run_exe.py')

print(f"\n📋 الأمر:")
print(' '.join(cmd))
print()

# ============================================
# 4. التنفيذ
# ============================================
print("🚀 بدء البناء...")
print("⚠️ ده ممكن ياخد 2-5 دقايق")
print("=" * 70)
print()

result = subprocess.run(cmd, cwd=BASE)

print()
print("=" * 70)

if result.returncode == 0:
    print("✅ تم البناء بنجاح!")
    print("=" * 70)
    
    exe_path = os.path.join(BASE, 'dist', 'WarehouseModule.exe')
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n📦 الملف: {exe_path}")
        print(f"📏 الحجم: {size:.1f} MB")
        print(f"\n🚀 للتشغيل:")
        print(f'   "{exe_path}"')
    else:
        print(f"\n⚠️ الملف مش موجود: {exe_path}")
else:
    print(f"❌ فشل البناء (Exit code: {result.returncode})")
    print("=" * 70)
    print("\n💡 الأخطاء الشائعة:")
    print("  1. تأكد إن الملفات كلها موجودة")
    print("  2. جرب تشغل من CMD بدل PowerShell")
    print("  3. شوف آخر 30 سطر من الـ log")