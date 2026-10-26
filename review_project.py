"""
مراجعة شاملة للمشروع
- هيكل الملفات
- حجم الكود
- جودة الكود
- الأداء
- الأمان
- التنظيم
"""
import os
import re
import sqlite3
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'database', 'warehouse.db')

# ============================================
# 1. هيكل المشروع
# ============================================
print("=" * 70)
print("📁 1. هيكل المشروع")
print("=" * 70)

def count_files(directory, extensions=None):
    """عد الملفات وحجمها"""
    total = 0
    size = 0
    for root, dirs, files in os.walk(directory):
        # تجاهل المجلدات
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '_archive', 'chroma_db']]
        
        for f in files:
            if extensions is None or any(f.endswith(ext) for ext in extensions):
                total += 1
                size += os.path.getsize(os.path.join(root, f))
    return total, size

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

# إحصائيات عامة
for folder in ['app', 'app/routes', 'app/services', 'app/static', 'app/ai', 'scripts', 'database']:
    path = os.path.join(BASE, folder)
    if os.path.exists(path):
        # Python
        py_count, py_size = count_files(path, ['.py'])
        # HTML
        html_count, html_size = count_files(path, ['.html'])
        # JS
        js_count, js_size = count_files(path, ['.js'])
        # CSS
        css_count, css_size = count_files(path, ['.css'])
        
        print(f"\n📂 {folder}/")
        if py_count > 0:
            print(f"  🐍 Python: {py_count} ملف ({format_size(py_size)})")
        if html_count > 0:
            print(f"  🌐 HTML: {html_count} ملف ({format_size(html_size)})")
        if js_count > 0:
            print(f"  📜 JS: {js_count} ملف ({format_size(js_size)})")
        if css_count > 0:
            print(f"  🎨 CSS: {css_count} ملف ({format_size(css_size)})")

# ============================================
# 2. حجم الكود
# ============================================
print("\n" + "=" * 70)
print("📊 2. حجم الكود")
print("=" * 70)

total_lines = 0
file_stats = []

for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '_archive', 'chroma_db']]
    
    for f in files:
        if f.endswith(('.py', '.html', '.js', '.css')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                    lines = sum(1 for _ in file)
                total_lines += lines
                file_stats.append((path, lines, f))
            except:
                pass

file_stats.sort(key=lambda x: -x[1])

print(f"  📈 إجمالي الأسطر: {total_lines:,}")

# أكبر 10 ملفات
print(f"\n  📄 أكبر 10 ملفات:")
for path, lines, name in file_stats[:10]:
    rel = os.path.relpath(path, BASE)
    print(f"     {lines:6,} سطر — {rel}")

# ============================================
# 3. جودة الكود (Python)
# ============================================
print("\n" + "=" * 70)
print("🐍 3. جودة كود Python")
print("=" * 70)

issues = {
    'print': 0,
    'import *': 0,
    'except_pass': 0,
    'hardcoded_url': 0,
    'todo': 0,
    'fixme': 0,
    'long_lines': 0,
}

py_files = []
for root, dirs, files in os.walk(os.path.join(BASE, 'app')):
    dirs[:] = [d for d in dirs if d not in ['__pycache__']]
    for f in files:
        if f.endswith('.py'):
            py_files.append(os.path.join(root, f))

for path in py_files:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            lines = content.split('\n')
            
            for line in lines:
                if re.search(r'^\s*print\s*\(', line) and 'app/routes' not in path and 'app/services' not in path:
                    issues['print'] += 1
                if re.search(r'from\s+\S+\s+import\s+\*', line):
                    issues['import *'] += 1
                if re.search(r'except\s*:\s*pass', line):
                    issues['except_pass'] += 1
                if re.search(r'localhost:\d+', line) and 'test' not in path.lower():
                    issues['hardcoded_url'] += 1
                if 'TODO' in line:
                    issues['todo'] += 1
                if 'FIXME' in line:
                    issues['fixme'] += 1
                if len(line) > 120:
                    issues['long_lines'] += 1
    except:
        pass

print(f"  📊 ملفات Python: {len(py_files)}")
print()
for issue, count in issues.items():
    icon = '✅' if count == 0 else '⚠️'
    label = {
        'print': 'print statements (تُنقل لـ logging)',
        'import *': 'import * (ممارسة سيئة)',
        'except_pass': 'except: pass (تخفي الأخطاء)',
        'hardcoded_url': 'URLs ثابتة',
        'todo': 'TODO (مهام معلقة)',
        'fixme': 'FIXME (مشاكل معروفة)',
        'long_lines': 'أسطر طويلة (> 120 حرف)',
    }[issue]
    print(f"  {icon} {label}: {count}")

# ============================================
# 4. الملفات الثابتة (JS/HTML)
# ============================================
print("\n" + "=" * 70)
print("🌐 4. الملفات الثابتة (Frontend)")
print("=" * 70)

static_dir = os.path.join(BASE, 'app', 'static')

# عد الـ HTML
html_files = [f for f in os.listdir(static_dir) if f.endswith('.html')]
print(f"  📄 HTML: {len(html_files)} ملف")

# تحقق من استخدام style.css و permissions.js
uses_style = 0
uses_permissions = 0
uses_bootstrap = 0
uses_fontawesome = 0

for f in html_files:
    path = os.path.join(static_dir, f)
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            if 'style.css' in content:
                uses_style += 1
            if 'permissions.js' in content:
                uses_permissions += 1
            if 'bootstrap' in content.lower():
                uses_bootstrap += 1
            if 'font-awesome' in content.lower() or 'fontawesome' in content.lower():
                uses_fontawesome += 1
    except:
        pass

print(f"\n  📊 تحليل الملفات:")
print(f"     ✅ تستخدم style.css: {uses_style}/{len(html_files)}")
print(f"     ✅ تستخدم permissions.js: {uses_permissions}/{len(html_files)}")
print(f"     ✅ تستخدم Bootstrap: {uses_bootstrap}/{len(html_files)}")

# ============================================
# 5. قاعدة البيانات
# ============================================
print("\n" + "=" * 70)
print("🗄️ 5. قاعدة البيانات")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]

print(f"  📊 الجداول: {len(tables)}")

# حجم الداتابيز
db_size = os.path.getsize(DB_PATH)
print(f"  💾 حجم الداتابيز: {format_size(db_size)}")

# أكبر الجداول
table_sizes = []
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        table_sizes.append((t, cnt))
    except:
        pass

table_sizes.sort(key=lambda x: -x[1])
print(f"\n  📋 أكبر 10 جداول:")
for t, cnt in table_sizes[:10]:
    print(f"     {cnt:6,} صف — {t}")

conn.close()

# ============================================
# 6. الأمان
# ============================================
print("\n" + "=" * 70)
print("🔒 6. الأمان")
print("=" * 70)

security_issues = []

# كلمات مرور مشفرة؟
try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users LIMIT 5")
    passwords = [r[0] for r in cur.fetchall()]
    if all(p and len(p) > 20 for p in passwords if p):
        print(f"  ✅ كلمات المرور مشفرة (طول > 20)")
    else:
        print(f"  ⚠️ كلمات المرور مش مشفرة!")
        security_issues.append('كلمات مرور ضعيفة')
    conn.close()
except:
    pass

# تحقق من .env
env_path = os.path.join(BASE, '.env')
if os.path.exists(env_path):
    print(f"  ✅ ملف .env موجود")
    try:
        with open(env_path, 'r') as f:
            content = f.read()
            if 'SECRET' in content or 'KEY' in content:
                print(f"  ✅ يحتوي على مفاتيح سرية")
    except:
        pass
else:
    print(f"  ⚠️ ملف .env مش موجود")

# تحقق من .gitignore
gitignore = os.path.join(BASE, '.gitignore')
if os.path.exists(gitignore):
    print(f"  ✅ ملف .gitignore موجود")
    with open(gitignore, 'r') as f:
        content = f.read()
        checks = ['.env', '__pycache__', '*.db']
        for check in checks:
            if check in content:
                print(f"     ✅ يحتوي على: {check}")
else:
    print(f"  ⚠️ ملف .gitignore مش موجود")

# ============================================
# 7. الأداء
# ============================================
print("\n" + "=" * 70)
print("⚡ 7. الأداء")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# حجم البيانات
cur.execute("SELECT COUNT(*) FROM stock_transactions")
print(f"  📊 حركات المخزون: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM journal_entries")
print(f"  📊 القيود: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM journal_entry_lines")
print(f"  📊 سطور القيود: {cur.fetchone()[0]}")

# اختبار سرعة استعلام
import time
start = time.time()
cur.execute("""
    SELECT je.id, COUNT(jel.id) 
    FROM journal_entries je
    LEFT JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
    GROUP BY je.id
    LIMIT 100
""")
cur.fetchall()
elapsed = (time.time() - start) * 1000
print(f"\n  ⏱️ استعلام JOIN: {elapsed:.2f} ms")

conn.close()

# ============================================
# 8. الملفات المؤقتة
# ============================================
print("\n" + "=" * 70)
print("📁 8. ملفات المشروع")
print("=" * 70)

# ملفات في root
root_files = [f for f in os.listdir(BASE) if os.path.isfile(os.path.join(BASE, f))]

# تصنيف
categories = {
    'إعدادات': ['.env', '.gitignore', 'requirements.txt', 'requirements-production.txt', 
                'runtime.txt', 'Procfile', 'render-start.sh'],
    'تشغيل': ['run.py', 'run.bat', 'start.bat'],
    'توثيق': ['README.md'],
    'سكريبتات إعداد': ['add_*.py'],
    'سكريبتات اختبار': ['test_*.py'],
    'سكريبتات تعديل': ['fix_*.py', 'setup_*.py'],
}

print(f"\n  📊 ملفات root: {len(root_files)}")
print()

for cat, patterns in categories.items():
    matched = []
    for f in root_files:
        for p in patterns:
            if p.startswith('*'):
                if f.endswith(p[1:]):
                    matched.append(f)
                    break
            elif f == p:
                matched.append(f)
                break
    
    if matched:
        print(f"  📁 {cat}: {len(matched)}")
        for m in matched[:3]:
            print(f"     • {m}")
        if len(matched) > 3:
            print(f"     ... و {len(matched)-3} آخرين")

# ============================================
# ملخص
# ============================================
print("\n" + "=" * 70)
print("📊 ملخص المراجعة")
print("=" * 70)

print(f"""
  📁 هيكل المشروع:
     • مجلدات: app, database, scripts
     • ملفات Python: {len(py_files)}
     • ملفات HTML: {len(html_files)}
     • إجمالي الأسطر: {total_lines:,}

  🗄️ قاعدة البيانات:
     • الجداول: {len(tables)}
     • الحجم: {format_size(db_size)}

  🔒 الأمان:
     • كلمات المرور: {'✅ مشفرة' if not security_issues else '⚠️ فيها مشاكل'}
     • .env: {'✅' if os.path.exists(env_path) else '❌'}

  ⚠️ مشاكل محتملة:
     • TODO: {issues['todo']}
     • FIXME: {issues['fixme']}
     • except:pass: {issues['except_pass']}
     • أسطر طويلة: {issues['long_lines']}
""")

# النتيجة
total_issues = sum(issues.values())
if total_issues == 0:
    print("  🎉 المشروع نظيف تماماً!")
elif total_issues < 10:
    print(f"  ✅ المشروع جيد — {total_issues} ملاحظة بسيطة")
elif total_issues < 50:
    print(f"  ⚠️ المشروع متوسط — {total_issues} ملاحظة")
else:
    print(f"  ❌ المشروع فيه {total_issues} ملاحظة محتاجة مراجعة")

print()