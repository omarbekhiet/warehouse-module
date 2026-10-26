"""
توحيد تنسيق جدول accounts.html مع style.css
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'static', 'accounts.html')

print("=" * 60)
print("🎨 توحيد التنسيق مع style.css")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# ابحث عن بداية <style> ونهايتها
start = content.find('<style>')
end = content.find('</style>')

if start < 0 or end < 0:
    print("⚠️ <style> مش موجود")
    exit(1)

# CSS الجديد المتوافق مع style.css
new_css = '''<style>
/* ============================================
   Tree Table — متوافق مع style.css
   ============================================ */
.tree-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
    margin: 0;
}
.tree-table thead th {
    background: #f8fafc;
    color: #475569;
    font-weight: 700;
    padding: 10px 11px;
    text-align: right;
    font-size: 0.80rem;
    line-height: 1.45;
    border-bottom: 1.5px solid #e2e8f0;
    white-space: nowrap;
    position: sticky;
    top: 0;
    z-index: 10;
}
.tree-table tbody tr {
    border-bottom: 1px solid #f1f5f9;
    transition: background 0.15s;
}
.tree-table tbody tr:hover { background: #fafbfc; }

.tree-table tbody td {
    padding: 10px 11px;
    font-size: 0.86rem;
    line-height: 1.55;
    vertical-align: middle;
    word-break: normal;
    overflow-wrap: break-word;
}

/* ألوان المستويات */
.tree-table tbody tr.level-L1 { background: #f0fdf4; font-weight: 700; }
.tree-table tbody tr.level-L1:hover { background: #dcfce7; }
.tree-table tbody tr.level-L2 { background: #f8fafc; }
.tree-table tbody tr.level-L3 { background: #fefefe; }
.tree-table tbody tr.level-L4 { background: white; }

/* الأعمدة */
.col-code {
    width: 90px;
    font-family: 'Consolas', 'Monaco', monospace;
}
.col-code code {
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.78rem;
    color: #475569;
}

.col-name {
    min-width: 280px;
}

.col-nature { width: 80px; text-align: center; }
.col-stmt { width: 80px; text-align: center; }
.col-type { width: 120px; text-align: center; }
.col-level { width: 70px; text-align: center; }
.col-actions { width: 120px; text-align: center; }

/* إزاحة الشجرة */
.indent-1 { padding-right: 11px !important; }
.indent-2 { padding-right: 31px !important; }
.indent-3 { padding-right: 51px !important; }
.indent-4 { padding-right: 71px !important; }

.node-icon {
    display: inline-block;
    width: 18px;
    text-align: center;
    color: #94a3b8;
}
.node-icon.folder { color: #f59e0b; }

.node-name {
    color: #1e3c72;
    font-weight: 600;
}
.level-L1 .node-name {
    font-size: 0.92rem;
    font-weight: 800;
    color: #15803d;
}

.node-en {
    color: #94a3b8;
    font-size: 0.74rem;
    margin-right: 6px;
    line-height: 1.35;
}

/* Badges — متوافقة مع style.css */
.badge {
    font-weight: 600;
    font-size: 0.74rem;
    line-height: 1.35;
    padding: 4px 9px;
    border-radius: 12px;
    display: inline-block;
}

.badge-nature-D { background: #d4edda; color: #155724; }
.badge-nature-C { background: #f8d7da; color: #721c24; }
.badge-nature-CC { background: #fff3cd; color: #856404; }

.badge-stmt-BS { background: #e0f2fe; color: #0369a1; }
.badge-stmt-IS { background: #fef3c7; color: #92400e; }
.badge-stmt-EQ { background: #ede9fe; color: #6d28d9; }

.badge-type-LEAF { background: #d1fae5; color: #065f46; }
.badge-type-GROUP { background: #f1f5f9; color: #64748b; }

.badge-level {
    background: #1e293b;
    color: white;
    padding: 3px 8px;
    border-radius: 10px;
    font-size: 0.70rem;
    font-weight: 700;
}

/* Action buttons */
.btn-action {
    padding: 4px 8px;
    font-size: 0.74rem;
    border-radius: 6px;
    margin: 0 1px;
    border: 1px solid;
    background: white;
    transition: all 0.15s;
    cursor: pointer;
    line-height: 1.2;
}
.btn-action:hover { transform: translateY(-1px); }
.btn-action.view { color: #06b6d4; border-color: #06b6d4; }
.btn-action.view:hover { background: #06b6d4; color: white; }
.btn-action.edit { color: #f59e0b; border-color: #f59e0b; }
.btn-action.edit:hover { background: #f59e0b; color: white; }
.btn-action.del { color: #ef4444; border-color: #ef4444; }
.btn-action.del:hover { background: #ef4444; color: white; }

/* Tree container */
.tree-container {
    max-height: calc(100vh - 340px);
    overflow-y: auto;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: white;
}
.tree-container::-webkit-scrollbar { width: 8px; }
.tree-container::-webkit-scrollbar-track { background: #f1f5f9; }
.tree-container::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
.tree-container::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* Legend (لو موجود) */
.tree-legend {
    background: #f8fafc;
    border-radius: 8px;
    padding: 10px 15px;
    margin-bottom: 12px;
    font-size: 0.78rem;
    line-height: 1.5;
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    align-items: center;
}
.tree-legend .legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    color: #64748b;
}
.tree-legend .legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    display: inline-block;
}

/* ============================================
   تحسينات عامة على الصفحة
   ============================================ */
.page-head h2 {
    font-size: 1.25rem;
    line-height: 1.45;
}

.row.g-1 > [class*="col-"] {
    padding-right: 4px;
    padding-left: 4px;
}

/* Stats صغيرة */
.stat-card.card.p-1 {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: all 0.15s;
}
.stat-card.card.p-1:hover {
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(0,0,0,0.08);
}

/* Responsive */
@media (max-width: 768px) {
    .col-code { width: 70px; }
    .col-name { min-width: 200px; }
    .col-nature, .col-stmt, .col-level { width: 60px; }
    .col-type { width: 100px; }
    .col-actions { width: 100px; }
    
    .tree-table tbody td {
        padding: 8px;
        font-size: 0.80rem;
    }
    
    .badge { font-size: 0.70rem; padding: 3px 7px; }
}

/* Print */
@media print {
    .col-actions, .btn-action { display: none; }
    .tree-table { font-size: 9px; }
    .tree-table thead th { font-size: 8.5px; padding: 5px; }
    .tree-table tbody td { padding: 4px 5px; font-size: 9px; }
}
</style>'''

content = content[:start] + new_css + content[end + len('</style>'):]

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ تم تحديث CSS")
print("=" * 60)
print("📋 الخصائص الجديدة:")
print("  ✅ ارتفاع الصفوف: 10px padding (متوافق مع style.css)")
print("  ✅ خط الجدول: 0.86rem")
print("  ✅ خط الـ header: 0.80rem")
print("  ✅ الأعمدة محسّنة")
print("  ✅ Badges متوافقة")
print("  ✅ Responsive + Print")