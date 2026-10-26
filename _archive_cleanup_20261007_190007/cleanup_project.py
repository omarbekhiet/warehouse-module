"""
تنظيف الملفات غير المرتبطة بالمشروع
- نقلهم لـ _archive_cleanup
- بدون حذف مباشر
"""
import os
import shutil
import glob
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(BASE, f'_archive_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')

print("=" * 70)
print("🧹 تنظيف الملفات غير المرتبطة")
print("=" * 70)

# إنشاء مجلد الأرشيف
os.makedirs(ARCHIVE, exist_ok=True)
print(f"\n📁 الأرشيف: {ARCHIVE}")

# ============================================
# الملفات المستثناة (مهمة)
# ============================================
KEEP = {
    'run.py',
    'add_cash_boxes.py',
    'add_cash_box_transactions.py',
    'add_payment_details.py',
    'requirements.txt',
    'requirements-production.txt',
    'runtime.txt',
    'Procfile',
    'render-start.sh',
    'run.bat',
    'start.bat',
    'README.md',
    '.env',
    '.gitignore',
    'test_all_screens.py',  # نحتفظ به
    'test_database_v2.py',
}

# ============================================
# الأنماط
# ============================================
PATTERNS = [
    # سكريبتات
    'fix_*.py',
    'check_*.py',
    'test_*.py',
    'add_*.py',
    'setup_*.py',
    'audit_*.py',
    'link_*.py',
    'cleanup_*.py',
    'upgrade_*.py',
    'remove_*.py',
    'enable_*.py',
    'complete_*.py',
    'simple_*.py',
    'move_*.py',
    'debug_*.py',
    'show_*.py',
    
    # تقارير
    '*_report.txt',
    '*_report.md',
    '*_report.json',
    '*_audit.txt',
    'database_report.txt',
    'import_report.txt',
    'linking_report.txt',
    'excel_templates_report.txt',
    
    # ملفات مؤقتة
    '*.bak',
    'loader.html',
    'loader.vbs',
    'launcher.vbs',
    'Unify-HomeIcon.ps1',
    '_extracted_schema.sql',
    'inventory_movements_audit.txt',
    'missing_home_button_report.txt',
    'missing_house_icon_report.txt',
    'FINAL_PROJECT_REPORT.md',
    'SETTINGS_FINAL_REPORT.md',
    'company_config.js',
]

# ============================================
# نقل الملفات
# ============================================
moved = 0
skipped = 0
errors = []

print("\n📤 نقل الملفات...")
print()

for pattern in PATTERNS:
    files = glob.glob(os.path.join(BASE, pattern))
    
    for f in files:
        filename = os.path.basename(f)
        
        # استثناء
        if filename in KEEP:
            print(f"  ⏭️ {filename} (مهم)")
            skipped += 1
            continue
        
        # نقل
        try:
            dst = os.path.join(ARCHIVE, filename)
            shutil.move(f, dst)
            print(f"  ✅ {filename}")
            moved += 1
        except Exception as e:
            errors.append(f"{filename}: {e}")
            print(f"  ❌ {filename}: {e}")

# ============================================
# نقل المجلدات
# ============================================
DIRS_TO_MOVE = [
    '_archive',
    '__pycache__',
    'chroma_db',
]

print("\n📁 نقل المجلدات...")
for d in DIRS_TO_MOVE:
    path = os.path.join(BASE, d)
    if os.path.exists(path) and os.path.isdir(path):
        try:
            dst = os.path.join(ARCHIVE, d)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(path, dst)
            print(f"  ✅ {d}/")
            moved += 1
        except Exception as e:
            print(f"  ❌ {d}: {e}")

# ============================================
# نقل backup folders
# ============================================
backup_dirs = glob.glob(os.path.join(BASE, '_backup_*'))
for d in backup_dirs:
    if d == ARCHIVE:
        continue
    if os.path.isdir(d):
        try:
            dst = os.path.join(ARCHIVE, os.path.basename(d))
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(d, dst)
            print(f"  ✅ {os.path.basename(d)}/")
            moved += 1
        except Exception as e:
            print(f"  ❌ {os.path.basename(d)}: {e}")

# ============================================
# تنظيف __pycache__
# ============================================
print("\n🧹 تنظيف __pycache__...")
pycache_count = 0
for root, dirs, files in os.walk(BASE):
    if '_archive' in root:
        continue
    for d in dirs[:]:
        if d == '__pycache__':
            path = os.path.join(root, d)
            try:
                shutil.rmtree(path)
                pycache_count += 1
            except:
                pass
if pycache_count:
    print(f"  ✅ تم حذف {pycache_count} مجلد __pycache__")

# ============================================
# الملخص
# ============================================
print("\n" + "=" * 70)
print("📊 الملخص")
print("=" * 70)

print(f"  ✅ تم نقل: {moved} ملف/مجلد")
print(f"  ⏭️ تم تخطي: {skipped}")
print(f"  ❌ أخطاء: {len(errors)}")

if errors:
    print(f"\n  ⚠️ الأخطاء:")
    for e in errors[:10]:
        print(f"     • {e}")

# عرض الملفات المتبقية
print("\n" + "=" * 70)
print("📋 الملفات المتبقية في المشروع")
print("=" * 70)

remaining_root = []
for item in sorted(os.listdir(BASE)):
    if item.startswith('_archive_cleanup'):
        continue
    if item.startswith('.'):
        continue
    path = os.path.join(BASE, item)
    if os.path.isfile(path):
        remaining_root.append(f"📄 {item}")
    elif os.path.isdir(path):
        remaining_root.append(f"📁 {item}/")

for r in remaining_root:
    print(f"  {r}")

print()
print("=" * 70)
print("✅ تم التنظيف!")
print("=" * 70)
print(f"\n📌 الأرشيف: {ARCHIVE}")
print(f"\n⚠️ بعد التأكد، امسح الأرشيف:")
print(f'  Remove-Item "{ARCHIVE}" -Recurse -Force')