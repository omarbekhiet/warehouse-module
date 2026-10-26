"""
تنسيق أزرار الجدول في accounts.html
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'accounts.html')

print("=" * 60)
print("🎨 تنسيق أزرار الجدول")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# CSS جديد للأزرار
new_css = '''
/* ============================================
   تنسيق أزرار الإجراءات
   ============================================ */
.col-actions {
    text-align: center !important;
    white-space: nowrap;
    padding: 6px 4px !important;
}

.btn-action {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    padding: 0 !important;
    font-size: 0.72rem !important;
    border-radius: 6px;
    margin: 0 2px !important;
    border: 1.5px solid;
    background: white;
    transition: all 0.15s;
    cursor: pointer;
    vertical-align: middle;
    line-height: 1;
}

.btn-action i {
    font-size: 0.75rem;
    line-height: 1;
}

.btn-action:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.btn-action.view { color: #06b6d4; border-color: #06b6d4; }
.btn-action.view:hover { background: #06b6d4; color: white; }

.btn-action.edit { color: #f59e0b; border-color: #f59e0b; }
.btn-action.edit:hover { background: #f59e0b; color: white; }

.btn-action.del { color: #ef4444; border-color: #ef4444; }
.btn-action.del:hover { background: #ef4444; color: white; }

/* الأزرار داخل تنسيق موحّد */
.col-actions .btn-group {
    display: inline-flex;
    gap: 4px;
}

/* Responsive */
@media (max-width: 768px) {
    .btn-action {
        width: 24px;
        height: 24px;
        font-size: 0.65rem !important;
        margin: 0 1px !important;
    }
    .btn-action i {
        font-size: 0.68rem;
    }
}
'''

# ابحث عن نهاية <style> وأضف CSS الجديد قبلها
idx = content.rfind('</style>')
if idx > 0:
    # تحقق إن مش مضاف قبل كده
    if 'تنسيق أزرار الإجراءات' not in content:
        content = content[:idx] + new_css + '\n' + content[idx:]
        print("  ✅ تم إضافة CSS للأزرار")
    else:
        print("  ℹ️ CSS موجود بالفعل")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ تم!")