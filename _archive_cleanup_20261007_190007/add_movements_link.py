"""
إضافة رابط movements_journal.html في index.html
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'index.html')

print("=" * 60)
print("🔧 إضافة movements_journal.html في index.html")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# التحقق
if 'movements_journal.html' in content:
    print("  ℹ️ موجود بالفعل")
else:
    # ابحث عن رابط branches.html
    pattern = r'(<a href="branches\.html"[^>]*>.*?</a>)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("  ❌ ما لقيتش branches.html")
        exit(1)
    
    old_link = match.group(1)
    
    # الرابط الجديد
    new_link = old_link + '''

                        <a href="movements_journal.html" class="feature-card" style="--feature-color: #8b5cf6; --feature-bg: #f5f3ff;">
                            <div class="feature-icon"><i class="bi bi-link-45deg"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">ربط الحركات بالقيود</div>
                                <div class="feature-desc">البحث والربط</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>'''
    
    content = content.replace(old_link, new_link, 1)
    print("  ✅ تم إضافة الرابط")
    
    # غيّر العدد
    # ابحث عن section-head-count في قسم المحاسبة
    # محدداً: "الشاشات</span>" ثم عدد
    old_count_pattern = r'(<span class="section-head-text">الشاشات</span>\s*<span class="section-head-count">)4(</span>)'
    
    # نبحث في قسم المحاسبة تحديداً
    # بس ممكن يتكرر — نأخد آخر واحد (اللي في المحاسبة)
    matches = list(re.finditer(old_count_pattern, content))
    
    if matches:
        # آخر match (الأقرب لقسم المحاسبة)
        last_match = matches[-1]
        content = content[:last_match.start()] + last_match.group(1) + '12' + last_match.group(2) + content[last_match.end():]
        print("  ✅ تم تحديث العدد: 4 → 12")
    else:
        print("  ⚠️ ما لقيتش العدد")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n📊 التحقق:")
print(f"  movements_journal.html في index.html: {'✅' if 'movements_journal.html' in content else '❌'}")
print(f"  عدد الشاشات في قسم المحاسبة: ", end='')
match = re.search(r'<div class="app-content" data-content="accounting".*?<span class="section-head-count">(\d+)</span>', content, re.DOTALL)
if match:
    print(match.group(1))
else:
    print("مش موجود")