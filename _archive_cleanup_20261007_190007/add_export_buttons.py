"""
إضافة زر تصدير Excel لكل شاشة
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'app', 'static')

# ============================================
# خريطة: الشاشة → قالب التصدير
# ============================================
SCREEN_TEMPLATES = {
    'accounts.html': 'accounts',
    'customers.html': 'customers',
    'suppliers.html': 'suppliers',
    'items.html': 'items',
    'cash_boxes.html': 'cash_boxes',
    'banks.html': 'banks',
    'journal.html': 'journal_entries',
    'payments.html': 'supplier_payments',
    'customer_receipts.html': 'customer_receipts',
    'cash_box_transactions.html': 'cash_box_transactions',
    'expenses.html': 'expenses',
}

# ============================================
# أزرار التصدير (HTML)
# ============================================
def get_export_button(template_key):
    """يرجع زر تصدير Excel"""
    return f'''<button class="btn btn-sm btn-outline-success" onclick="exportToExcel('{template_key}')" title="تصدير Excel">
                <i class="bi bi-file-earmark-excel"></i> Excel
            </button>'''

# ============================================
# دالة التصدير (JS)
# ============================================
def get_export_js():
    return '''
<script>
// دالة تصدير Excel
function exportToExcel(templateKey) {
    if (!templateKey) {
        alert('مفيش قالب تصدير للشاشة دي');
        return;
    }
    window.location.href = `/api/v1/export/excel/export/${templateKey}`;
}
</script>
'''

# ============================================
# معالجة كل شاشة
# ============================================
print("=" * 60)
print("🔧 إضافة أزرار التصدير")
print("=" * 60)

total = 0
skipped = 0
errors = []

for screen, template in SCREEN_TEMPLATES.items():
    path = os.path.join(STATIC, screen)
    
    if not os.path.exists(path):
        print(f"  ⏭️ {screen}: مش موجود")
        skipped += 1
        continue
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # تحقق إن الزر مضاف بالفعل
        if 'exportToExcel' in content:
            print(f"  ℹ️ {screen}: الزر موجود بالفعل")
            skipped += 1
            continue
        
        # ابحث عن page-head
        page_head_patterns = [
            r'(<div class="page-head">.*?<div class="d-flex[^>]*>)',
            r'(<div class="d-flex justify-content-between[^>]*>.*?<div>)',
        ]
        
        button_added = False
        
        for pattern in page_head_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                # ضيف الزر بعد فتح الـ div الأزرار
                insert_pos = match.end()
                button_html = '\n            ' + get_export_button(template)
                content = content[:insert_pos] + button_html + content[insert_pos:]
                button_added = True
                break
        
        if not button_added:
            # طريقة بديلة: ابحث عن زر "الرئيسية" وضيف قبله
            patterns_alt = [
                r'(<a href="index\.html" class="btn[^"]*"[^>]*>\s*<i class="bi bi-house[^>]*></i>\s*الرئيسية\s*</a>)',
                r'(<a href="index\.html"[^>]*>.*?الرئيسية.*?</a>)',
            ]
            
            for pattern in patterns_alt:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    insert_pos = match.start()
                    button_html = get_export_button(template) + '\n            '
                    content = content[:insert_pos] + button_html + content[insert_pos:]
                    button_added = True
                    break
        
        if not button_added:
            errors.append(screen)
            print(f"  ⚠️ {screen}: مفيش مكان للزر")
            continue
        
        # ضيف JavaScript قبل </body>
        if 'exportToExcel' not in content:
            content = content.replace('</body>', get_export_js() + '\n</body>', 1)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ {screen}: تم إضافة الزر")
        total += 1
    
    except Exception as e:
        errors.append(screen)
        print(f"  ❌ {screen}: {e}")

# ============================================
# الملخص
# ============================================
print("\n" + "=" * 60)
print("📊 الملخص")
print("=" * 60)
print(f"  ✅ نجح: {total}")
print(f"  ℹ️ تم تخطي: {skipped}")
print(f"  ❌ فشل: {len(errors)}")

if errors:
    print(f"\n  ❌ الشاشات اللي فشلت:")
    for e in errors:
        print(f"     • {e}")