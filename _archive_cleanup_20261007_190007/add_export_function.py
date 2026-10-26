"""
إضافة دالة exportToExcel لكل الشاشات اللي فيها زر تصدير
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'app', 'static')

# ============================================
# دالة JavaScript
# ============================================
EXPORT_FUNCTION = '''
<script>
// دالة تصدير Excel
function exportToExcel(templateKey) {
    if (!templateKey) {
        alert('مفيش قالب تصدير');
        return;
    }
    window.location.href = '/api/v1/export/excel/export/' + templateKey;
}
</script>
'''

# ============================================
# التنفيذ
# ============================================
print("=" * 60)
print("🔧 إضافة دالة exportToExcel")
print("=" * 60)

total = 0
skipped = 0
no_button = 0
errors = []

for filename in os.listdir(STATIC):
    if not filename.endswith('.html'):
        continue
    
    path = os.path.join(STATIC, filename)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # تحقق إن فيه زر تصدير
        if 'exportToExcel(' not in content:
            no_button += 1
            continue
        
        # تحقق إن الدالة معرّفة
        if 'function exportToExcel' in content:
            skipped += 1
            continue
        
        # ضيف الدالة قبل </body>
        if '</body>' in content:
            content = content.replace('</body>', EXPORT_FUNCTION + '\n</body>', 1)
        else:
            content += EXPORT_FUNCTION
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ {filename}")
        total += 1
    except Exception as e:
        errors.append(filename)
        print(f"  ❌ {filename}: {e}")

print()
print("=" * 60)
print("📊 الملخص")
print("=" * 60)
print(f"  ✅ تم إضافة الدالة: {total}")
print(f"  ℹ️ موجودة مسبقاً: {skipped}")
print(f"  ⏭️ مفيش زر: {no_button}")
print(f"  ❌ فشل: {len(errors)}")