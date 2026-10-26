"""
نقل روابط الخزائن من الإعدادات لقسم المحاسبة
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'index.html')

print("=" * 60)
print("🔧 نقل روابط الخزائن لقسم المحاسبة")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================
# 1. شيل الروابط من قسم الإعدادات
# ============================================
print("\n📝 1. شيل من الإعدادات...")

# ابحث عن cash_boxes.html في الإعدادات
pattern1 = r'\s*<a href="cash_boxes\.html"[^>]*>.*?</a>'
pattern2 = r'\s*<a href="expenses\.html"[^>]*>.*?</a>'
pattern3 = r'\s*<!-- ✅ الجديد -->'

# احذفهم من مكانهم
removed = 0
for pattern in [pattern1, pattern2, pattern3]:
    matches = re.findall(pattern, content, re.DOTALL)
    if matches:
        content = re.sub(pattern, '', content, count=1, flags=re.DOTALL)
        removed += 1

print(f"  ✅ تم حذف {removed} عناصر من الإعدادات")

# صلّح section-head-count في الإعدادات (4 → 4-2 = 2)
old_count = '''<span class="section-head-text">الإعدادات المحاسبية والمالية</span>
                        <span class="section-head-count">4</span>'''
new_count = '''<span class="section-head-text">الإعدادات المحاسبية والمالية</span>
                        <span class="section-head-count">2</span>'''

if old_count in content:
    content = content.replace(old_count, new_count)
    print("  ✅ تم تعديل العدد: 4 → 2")
else:
    # جرّب النمط بالعربي المشوّه
    print("  ⚠️ نمط العدد مش موجود")

# ============================================
# 2. ضيفهم في قسم المحاسبة
# ============================================
print("\n📝 2. ضيف في قسم المحاسبة...")

# ابحث عن آخر رابط في قسم المحاسبة
# النمط: آخر <a> في data-content="accounting"
# هنجرب نضيف بعد financial_reports.html

old_financial = '''<a href="financial_reports.html" class="feature-card" style="--feature-color: #10b981; --feature-bg: #ecfdf5;">
                            <div class="feature-icon"><i class="bi bi-graph-up"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">التقارير المالية</div>
                                <div class="feature-desc">Financial</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>'''

new_links = old_financial + '''

                        <a href="cash_boxes.html" class="feature-card" style="--feature-color: #f59e0b; --feature-bg: #fffbeb;">
                            <div class="feature-icon"><i class="bi bi-safe2-fill"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">الخزائن والبنوك</div>
                                <div class="feature-desc">إدارة الخزائن والبطاقات</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>

                        <a href="cash_box_transactions.html" class="feature-card" style="--feature-color: #6366f1; --feature-bg: #eef2ff;">
                            <div class="feature-icon"><i class="bi bi-arrow-left-right"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">حركات الخزائن</div>
                                <div class="feature-desc">إيداع وسحب وتحويل</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>

                        <a href="expenses.html" class="feature-card" style="--feature-color: #ef4444; --feature-bg: #fef2f2;">
                            <div class="feature-icon"><i class="bi bi-receipt-cutoff"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">صرف النثريات</div>
                                <div class="feature-desc">المصروفات النقدية</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>

                        <a href="expense_categories.html" class="feature-card" style="--feature-color: #f59e0b; --feature-bg: #fffbeb;">
                            <div class="feature-icon"><i class="bi bi-tags"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">تصنيفات المصروفات</div>
                                <div class="feature-desc">أنواع المصروفات</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>

                        <a href="bank_reconciliation.html" class="feature-card" style="--feature-color: #06b6d4; --feature-bg: #ecfeff;">
                            <div class="feature-icon"><i class="bi bi-clipboard-check"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">التسوية البنكية</div>
                                <div class="feature-desc">مطابقة كشوف البنك</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>

                        <a href="cash_box_reports.html" class="feature-card" style="--feature-color: #a18cd1; --feature-bg: #f5f3ff;">
                            <div class="feature-icon"><i class="bi bi-bar-chart-line"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">تقارير الخزائن</div>
                                <div class="feature-desc">الأرصدة والحركات</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>

                        <a href="branches.html" class="feature-card" style="--feature-color: #0ea5e9; --feature-bg: #f0f9ff;">
                            <div class="feature-icon"><i class="bi bi-building"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">الفروع</div>
                                <div class="feature-desc">إدارة الفروع</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>'''

if old_financial in content:
    content = content.replace(old_financial, new_links, 1)
    print("  ✅ تم إضافة 7 روابط في قسم المحاسبة")
else:
    print("  ⚠️ نمط financial_reports مش موجود")
    # جرب نجيب آخر 500 حرف قبل إغلاق feature-grid في accounting
    idx = content.find('data-content="accounting"')
    if idx > 0:
        end_idx = content.find('</div>', idx + 2000)
        print(f"  المحاسبة في السطر: {content[:idx].count(chr(10)) + 1}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n📊 التحقق:")
for link in ['cash_boxes.html', 'cash_box_transactions.html', 'expenses.html', 
             'expense_categories.html', 'bank_reconciliation.html', 
             'cash_box_reports.html', 'branches.html']:
    count = content.count(link)
    print(f"  {link}: {count} مرة")