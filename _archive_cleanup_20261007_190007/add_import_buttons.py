"""
إضافة زر استيراد Excel لكل الشاشات
+ نافذة منبثقة للاستيراد
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, 'app', 'static')

# ============================================
# خريطة الشاشة → قالب الاستيراد
# ============================================
SCREENS_IMPORT = {
    'accounts.html': 'accounts',
    'customers.html': 'customers',
    'suppliers.html': 'suppliers',
    'items.html': 'items',
    'warehouses.html': 'warehouses',
    'item_groups.html': 'item_groups',
    'uom.html': 'uom',
    'branches.html': 'branches',
    'expense_categories.html': 'expense_categories',
    'cash_boxes.html': 'cash_boxes',
}

# ============================================
# زر الاستيراد (HTML)
# ============================================
def get_import_button(template_key):
    return f'''<button class="btn btn-sm btn-outline-primary" onclick="openImportModal('{template_key}')" title="استيراد Excel">
                <i class="bi bi-file-earmark-arrow-up"></i> استيراد
            </button>'''

# ============================================
# نافذة الاستيراد (HTML)
# ============================================
IMPORT_MODAL = '''
<!-- Import Modal -->
<div class="modal fade" id="importExcelModal" tabindex="-1">
<div class="modal-dialog modal-lg">
<div class="modal-content">
<div class="modal-header bg-primary text-white">
    <h5 class="modal-title"><i class="bi bi-file-earmark-arrow-up"></i> استيراد من Excel</h5>
    <button class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
</div>
<div class="modal-body">
    <!-- Step 1: Instructions -->
    <div id="import-step-1">
        <div class="alert alert-info">
            <i class="bi bi-info-circle"></i>
            <strong>الخطوات:</strong>
            <ol class="mb-0 mt-2" style="padding-right: 20px;">
                <li>حمّل القالب الفارغ</li>
                <li>املأ البيانات</li>
                <li>ارفع الملف</li>
                <li>اضغط "معاينة" للتأكد</li>
                <li>اضغط "استيراد" للحفظ</li>
            </ol>
        </div>
        
        <button class="btn btn-outline-primary w-100 mb-3" onclick="downloadImportTemplate()">
            <i class="bi bi-download"></i> تحميل القالب الفارغ
        </button>
        
        <div class="upload-area" id="import-upload-area" onclick="document.getElementById('import-file-input').click()">
            <i class="bi bi-cloud-upload"></i>
            <div class="title">اسحب الملف هنا أو اضغط للاختيار</div>
            <div class="sub">ملفات Excel فقط (.xlsx, .xls)</div>
        </div>
        <input type="file" id="import-file-input" accept=".xlsx,.xls" style="display:none" onchange="handleImportFile(this.files[0])">
        
        <div id="import-file-info" style="display:none;" class="mt-3">
            <div class="alert alert-success py-2 mb-0">
                <i class="bi bi-file-earmark-excel"></i>
                <span id="import-file-name"></span>
                <button class="btn btn-sm btn-outline-danger float-end" onclick="clearImportFile()">
                    <i class="bi bi-x"></i>
                </button>
            </div>
            <div class="d-flex gap-2 mt-2">
                <button class="btn btn-outline-info flex-fill" onclick="previewImport()">
                    <i class="bi bi-eye"></i> معاينة
                </button>
                <button class="btn btn-primary flex-fill" onclick="confirmImport()">
                    <i class="bi bi-upload"></i> استيراد
                </button>
            </div>
        </div>
    </div>
    
    <!-- Result -->
    <div id="import-step-2" style="display:none;"></div>
</div>
<div class="modal-footer">
    <button class="btn btn-secondary" data-bs-dismiss="modal">إغلاق</button>
</div>
</div>
</div>
</div>
'''

# ============================================
# CSS للنافذة
# ============================================
IMPORT_CSS = '''
<style>
.upload-area {
    border: 2px dashed #cbd5e1;
    border-radius: 12px;
    padding: 30px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    background: #f8fafc;
}
.upload-area:hover {
    border-color: #3b82f6;
    background: #eff6ff;
}
.upload-area.dragover {
    border-color: #10b981;
    background: #ecfdf5;
    transform: scale(1.02);
}
.upload-area i {
    font-size: 2.5rem;
    color: #94a3b8;
    margin-bottom: 8px;
}
.upload-area .title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #475569;
    margin-bottom: 4px;
}
.upload-area .sub {
    font-size: 0.78rem;
    color: #94a3b8;
}
.import-stats {
    display: flex;
    gap: 10px;
    margin: 10px 0;
}
.import-stats .item {
    flex: 1;
    background: #f8fafc;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    border: 1px solid #e2e8f0;
}
.import-stats .num {
    font-size: 1.4rem;
    font-weight: 800;
}
.import-stats .lbl {
    font-size: 0.72rem;
    color: #64748b;
}
.preview-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
    margin-top: 8px;
}
.preview-table th {
    background: #f1f5f9;
    padding: 6px 8px;
    text-align: right;
    font-weight: 700;
    color: #475569;
    border-bottom: 1px solid #cbd5e1;
}
.preview-table td {
    padding: 5px 8px;
    border-bottom: 1px solid #f1f5f9;
}
</style>
'''

# ============================================
# JavaScript
# ============================================
IMPORT_JS = '''
<script>
// متغيرات
let currentImportFile = null;
let currentImportTemplate = null;

// فتح نافذة الاستيراد
function openImportModal(templateKey) {
    currentImportTemplate = templateKey;
    currentImportFile = null;
    
    document.getElementById('import-step-1').style.display = 'block';
    document.getElementById('import-step-2').style.display = 'none';
    document.getElementById('import-file-info').style.display = 'none';
    document.getElementById('import-file-input').value = '';
    
    const modal = new bootstrap.Modal(document.getElementById('importExcelModal'));
    modal.show();
}

// تحميل القالب
function downloadImportTemplate() {
    if (!currentImportTemplate) return;
    window.location.href = '/api/v1/export/excel/import-template/' + currentImportTemplate;
}

// معالجة الملف
function handleImportFile(file) {
    if (!file) return;
    if (!file.name.match(/\\.(xlsx|xls)$/i)) {
        alert('الملف يجب أن يكون Excel');
        return;
    }
    currentImportFile = file;
    document.getElementById('import-file-name').textContent = 
        file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
    document.getElementById('import-file-info').style.display = 'block';
}

// مسح الملف
function clearImportFile() {
    currentImportFile = null;
    document.getElementById('import-file-input').value = '';
    document.getElementById('import-file-info').style.display = 'none';
}

// معاينة
async function previewImport() {
    if (!currentImportFile) { alert('اختر ملف'); return; }
    
    const formData = new FormData();
    formData.append('file', currentImportFile);
    
    const resultEl = document.getElementById('import-step-2');
    resultEl.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> جاري المعاينة...</div>';
    resultEl.style.display = 'block';
    document.getElementById('import-step-1').style.display = 'none';
    
    try {
        const r = await fetch('/api/v1/export/excel/preview/' + currentImportTemplate, {
            method: 'POST',
            body: formData
        }).then(x => x.json());
        
        if (r.success) {
            const d = r.data;
            let html = '<h6><i class="bi bi-eye text-info"></i> معاينة</h6>';
            html += '<div class="import-stats">';
            html += '<div class="item"><div class="num text-info">' + d.total_rows + '</div><div class="lbl">صفوف صحيحة</div></div>';
            html += '<div class="item"><div class="num text-danger">' + ((d.errors || []).length) + '</div><div class="lbl">أخطاء</div></div>';
            html += '</div>';
            
            if (d.preview && d.preview.length) {
                html += '<div class="mt-3"><strong>عينة من البيانات:</strong>';
                html += '<table class="preview-table"><thead><tr>';
                Object.keys(d.preview[0].data).forEach(k => html += '<th>' + k + '</th>');
                html += '</tr></thead><tbody>';
                d.preview.forEach(row => {
                    html += '<tr>';
                    Object.values(row.data).forEach(v => html += '<td>' + (v || '-') + '</td>');
                    html += '</tr>';
                });
                html += '</tbody></table></div>';
            }
            
            if (d.errors && d.errors.length) {
                html += '<div class="alert alert-warning mt-3 py-2 mb-0" style="font-size:0.82rem;">';
                html += '<strong>أخطاء:</strong><ul class="mb-0">';
                d.errors.forEach(e => html += '<li>' + e + '</li>');
                html += '</ul></div>';
            }
            
            html += '<div class="d-flex gap-2 mt-3">';
            html += '<button class="btn btn-secondary flex-fill" onclick="backToImport()"><i class="bi bi-arrow-right"></i> رجوع</button>';
            html += '<button class="btn btn-primary flex-fill" onclick="confirmImport()"><i class="bi bi-upload"></i> تأكيد الاستيراد</button>';
            html += '</div>';
            
            resultEl.innerHTML = html;
        } else {
            resultEl.innerHTML = '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> ' + r.message + '</div>' +
                '<button class="btn btn-secondary" onclick="backToImport()"><i class="bi bi-arrow-right"></i> رجوع</button>';
        }
    } catch (e) {
        resultEl.innerHTML = '<div class="alert alert-danger">خطأ في الاتصال</div>' +
            '<button class="btn btn-secondary" onclick="backToImport()"><i class="bi bi-arrow-right"></i> رجوع</button>';
    }
}

// رجوع
function backToImport() {
    document.getElementById('import-step-1').style.display = 'block';
    document.getElementById('import-step-2').style.display = 'none';
}

// استيراد
async function confirmImport() {
    if (!currentImportFile) { alert('اختر ملف'); return; }
    
    const formData = new FormData();
    formData.append('file', currentImportFile);
    
    const resultEl = document.getElementById('import-step-2');
    resultEl.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split"></i> جاري الاستيراد...</div>';
    resultEl.style.display = 'block';
    document.getElementById('import-step-1').style.display = 'none';
    
    try {
        const r = await fetch('/api/v1/export/excel/import/' + currentImportTemplate, {
            method: 'POST',
            body: formData
        }).then(x => x.json());
        
        if (r.success) {
            const d = r.data;
            let html = '<div class="alert alert-success"><h5><i class="bi bi-check-circle-fill"></i> تم الاستيراد بنجاح</h5></div>';
            html += '<div class="import-stats">';
            html += '<div class="item"><div class="num text-success">' + (d.imported || 0) + '</div><div class="lbl">جديد</div></div>';
            html += '<div class="item"><div class="num text-primary">' + (d.updated || 0) + '</div><div class="lbl">محدث</div></div>';
            html += '<div class="item"><div class="num">' + (d.total || 0) + '</div><div class="lbl">الإجمالي</div></div>';
            html += '</div>';
            
            if (d.errors && d.errors.length) {
                html += '<div class="alert alert-warning py-2 mt-3 mb-0" style="font-size:0.82rem;">';
                html += '<strong>أخطاء (' + d.errors.length + '):</strong><ul class="mb-0">';
                d.errors.forEach(e => html += '<li>' + e + '</li>');
                html += '</ul></div>';
            }
            
            html += '<div class="d-flex gap-2 mt-3">';
            html += '<button class="btn btn-success flex-fill" onclick="location.reload()"><i class="bi bi-arrow-clockwise"></i> تحديث الصفحة</button>';
            html += '</div>';
            
            resultEl.innerHTML = html;
        } else {
            resultEl.innerHTML = '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> ' + r.message + '</div>' +
                '<button class="btn btn-secondary" onclick="backToImport()"><i class="bi bi-arrow-right"></i> رجوع</button>';
        }
    } catch (e) {
        resultEl.innerHTML = '<div class="alert alert-danger">خطأ في الاتصال</div>' +
            '<button class="btn btn-secondary" onclick="backToImport()"><i class="bi bi-arrow-right"></i> رجوع</button>';
    }
}

// Drag & Drop
document.addEventListener('DOMContentLoaded', function() {
    const area = document.getElementById('import-upload-area');
    if (!area) return;
    
    area.addEventListener('dragover', e => { e.preventDefault(); area.classList.add('dragover'); });
    area.addEventListener('dragleave', () => area.classList.remove('dragover'));
    area.addEventListener('drop', e => {
        e.preventDefault();
        area.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleImportFile(e.dataTransfer.files[0]);
    });
});
</script>
'''

# ============================================
# التنفيذ
# ============================================
print("=" * 60)
print("🔧 إضافة زر استيراد Excel")
print("=" * 60)

total = 0
skipped = 0
errors = []

for screen, template in SCREENS_IMPORT.items():
    path = os.path.join(STATIC, screen)
    
    if not os.path.exists(path):
        print(f"  ⏭️ {screen}: مش موجود")
        skipped += 1
        continue
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'openImportModal' in content:
            print(f"  ℹ️ {screen}: الزر موجود")
            skipped += 1
            continue
        
        # 1. ضيف زر "استيراد" جنب زر "Excel" (التصدير)
        # ابحث عن زر التصدير
        export_btn_pattern = r'(<button class="btn btn-sm btn-outline-success" onclick="exportToExcel\([^)]+\)"[^>]*>\s*<i class="bi bi-file-earmark-excel"></i>[^<]*</button>)'
        match = re.search(export_btn_pattern, content)
        
        if match:
            # ضيف زر الاستيراد بعد زر التصدير
            export_btn = match.group(1)
            import_btn = get_import_button(template)
            content = content.replace(export_btn, export_btn + '\n            ' + import_btn, 1)
        else:
            # ابحث عن زر الرئيسية
            home_pattern = r'(<a href="index\.html"[^>]*>.*?الرئيسية.*?</a>)'
            match2 = re.search(home_pattern, content, re.DOTALL)
            if match2:
                insert_pos = match2.start()
                content = content[:insert_pos] + get_import_button(template) + '\n            ' + content[insert_pos:]
            else:
                print(f"  ⚠️ {screen}: مفيش مكان للزر")
                continue
        
        # 2. ضيف CSS قبل </head>
        if 'upload-area {' not in content:
            content = content.replace('</head>', IMPORT_CSS + '\n</head>', 1)
        
        # 3. ضيف Modal + JS قبل </body>
        if 'importExcelModal' not in content:
            content = content.replace('</body>', IMPORT_MODAL + '\n' + IMPORT_JS + '\n</body>', 1)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ {screen}: تم إضافة الزر")
        total += 1
    except Exception as e:
        errors.append(screen)
        print(f"  ❌ {screen}: {e}")

print(f"\n  📊 النتيجة: {total} نجح، {skipped} تخطي، {len(errors)} فشل")