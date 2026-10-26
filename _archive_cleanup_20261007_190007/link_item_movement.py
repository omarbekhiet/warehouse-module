"""
ربط item_movement.html في index.html
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE, 'app', 'static', 'index.html')

print("=" * 60)
print("🔗 ربط item_movement.html")
print("=" * 60)

with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# تحقق إن مضاف
if 'item_movement.html' in content:
    print("  ℹ️ موجود بالفعل")
else:
    # ابحث عن آخر رابط في قسم التقارير
    # أو أضفه جنب reports.html
    
    patterns = [
        # نمط 1: جنب reports.html
        (r'(<a href="reports\.html"[^>]*>.*?</a>)', 
         'after'),
        # نمط 2: جنب supplier_rating.html
        (r'(<a href="supplier_rating\.html"[^>]*>.*?</a>)',
         'after'),
        # نمط 3: جنب price_comparison.html
        (r'(<a href="price_comparison\.html"[^>]*>.*?</a>)',
         'after'),
    ]
    
    added = False
    import re
    
    for pattern, position in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            old_link = match.group(1)
            new_link = old_link + '''

                        <a href="item_movement.html" class="feature-card" style="--feature-color: #8b5cf6; --feature-bg: #f5f3ff;">
                            <div class="feature-icon"><i class="bi bi-arrow-left-right"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">حركة الأصناف</div>
                                <div class="feature-desc">تتبع حركات الأصناف</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>'''
            
            content = content.replace(old_link, new_link, 1)
            added = True
            print(f"  ✅ تم إضافة الرابط (بعد {old_link[:60]}...)")
            break
    
    if not added:
        print("  ⚠️ ما لقيتش مكان للرابط")
        print("  💡 افتح index.html يدوياً وأضف الرابط في قسم التقارير")
    else:
        with open(INDEX_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ تم حفظ index.html")

# التحقق النهائي
with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"\n📊 التحقق:")
print(f"  item_movement.html في index.html: {'✅' if 'item_movement.html' in content else '❌'}")