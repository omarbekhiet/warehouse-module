"""
إضافة روابط الشاشات الجديدة في index.html
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'index.html')

print("=" * 60)
print("🔧 إضافة الروابط في index.html")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ابحث عن آخر رابط في قسم المحاسبة (financial_reports.html)
old = '''<a href="financial_reports.html" class="feature-card" style="--feature-color: #10b981; --feature-bg: #ecfdf5;">
                            <div class="feature-icon"><i class="bi bi-graph-up"></i></div>
                            <div class="feature-content">
                                <div class="feature-name">التقارير المالية</div>
                                <div class="feature-desc">Financial</div>
                            </div>
                            <i class="bi bi-arrow-left feature-arrow"></i>
                        </a>'''

new_links = old + '''

                        <!-- ✅ الشاشات الجديدة -->
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

# التحقق
if 'cash_boxes.html' in content:
    print("  ℹ️ cash_boxes.html موجود بالفعل")
else:
    if old in content:
        content = content.replace(old, new_links, 1)
        print("  ✅ تم إضافة 7 روابط جديدة")
    else:
        print("  ⚠️ النمط مش موجود")
        print()
        print("  ابحث يدوياً عن:")
        print("  '<a href=\"financial_reports.html\" ...>'")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n📊 التحقق:")
for link in ['cash_boxes.html', 'cash_box_transactions.html', 'expenses.html', 
             'expense_categories.html', 'bank_reconciliation.html', 
             'cash_box_reports.html', 'branches.html']:
    print(f"  {link}: {'✅' if link in content else '❌'}")