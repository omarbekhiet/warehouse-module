"""
شيل رابط company_config.html من index.html
+ تنظيف
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'index.html')

print("=" * 60)
print("🧹 شيل company_config.html")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'company_config.html' not in content:
    print("  ℹ️ company_config.html مش موجود")
else:
    # ابحث عن الرابط كامل
    pattern = r'\s*<a href="company_config\.html"[^>]*>.*?</a>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    print(f"  📊 لقيت {len(matches)} رابط")
    
    for i, m in enumerate(matches):
        content = content.replace(m, '', 1)
        print(f"  ✅ تم شيل الرابط {i+1}")
    
    # شيل سطر فاضي زيادة لو حصل
    content = re.sub(r'\n\s*\n\s*\n\s*<a', '\n\n<a', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# تحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'company_config.html' in content:
    print(f"\n⚠️ لسه موجود: {content.count('company_config.html')} مرة")
else:
    print(f"\n✅ اتمسح تماماً")

# شوف settings_company.html موجود
settings_path = os.path.join(BASE, 'app', 'static', 'settings_company.html')
if os.path.exists(settings_path):
    print(f"✅ settings_company.html موجود — الوظيفة متاحة")
else:
    print(f"⚠️ settings_company.html مش موجود")