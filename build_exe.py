"""
بناء ملف EXE لـ Warehouse Module
"""
import os
import sys
import shutil
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 70)
print("🏗️ بناء ملف EXE")
print("=" * 70)

# ============================================
# 1. تأكد إن PyInstaller متثبت
# ============================================
try:
    import PyInstaller
    print("✅ PyInstaller مثبت")
except ImportError:
    print("❌ PyInstaller مش مثبت")
    print("📦 ثبته بـ: pip install pyinstaller")
    sys.exit(1)

# ============================================
# 2. تجهيز الأمر
# ============================================
print("\n📦 تجهيز الأمر...")

# المسارات
static_dir = os.path.join(BASE, 'app', 'static')
db_dir = os.path.join(BASE, 'database')

# ⚠️ المسار مهم — `static` كـ data
add_data = [
    f"{static_dir};app/static",       # HTML/JS/CSS
    f"{db_dir};database",             # الداتابيز
]

# ملفات إضافية
for extra in ['requirements.txt', 'README.md', '.env']:
    path = os.path.join(BASE, extra)
    if os.path.exists(path):
        add_data.append(f"{path};.")

# بني الأمر
cmd = [
    'pyinstaller',
    '--noconfirm',
    '--clean',
    '--name=WarehouseModule',
    '--onefile',  # ملف واحد
    '--console',  # نافذة console (للعرض)
    '--icon=NONE',
]

# ضيف data
for item in add_data:
    cmd.extend(['--add-data', item])

# hidden imports
hidden = [
    'flask',
    'flask_cors',
    'openpyxl',
    'sqlite3',
    'app',
    'app.routes',
    'app.services',
    'app.ai',
]
for h in hidden:
    cmd.extend(['--hidden-import', h])

# main file
cmd.append('run_exe.py')

print(f"\n📋 الأمر:")
print(' '.join(cmd))

# ============================================
# 3. تنفيذ
# ============================================
print("\n🚀 بدء البناء...")
print("⚠️ ده ممكن ياخد 2-5 دقايق")
print()

result = subprocess.run(cmd, cwd=BASE)

if result.returncode == 0:
    print("\n" + "=" * 70)
    print("✅ تم البناء بنجاح!")
    print("=" * 70)
    
    exe_path = os.path.join(BASE, 'dist', 'WarehouseModule.exe')
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n📦 الملف: {exe_path}")
        print(f"📏 الحجم: {size:.1f} MB")
        print(f"\n🚀 التشغيل:")
        print(f'   "{exe_path}"')
    else:
        print(f"\n⚠️ الملف مش موجود: {exe_path}")
else:
    print("\n" + "=" * 70)
    print("❌ فشل البناء")
    print("=" * 70)
    print(f"Exit code: {result.returncode}")