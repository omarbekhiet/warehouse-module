# -*- coding: utf-8 -*-
import re

PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# ============================================================
# 1. إضافة عمود "نوع القائمة" في رأس الجدول
# ============================================================
# نبحث عن أي سطر يحتوي على <th>اسم الحساب</th> ونضيف العمود بعده
old_th = r'<th[^>]*>اسم الحساب</th>'
new_th = r'\g<0>\n                        <th>نوع القائمة</th>'
content = re.sub(old_th, new_th, content, count=1)
print("✅ تمت إضافة عمود 'نوع القائمة' إلى رأس الجدول.")

# ============================================================
# 2. إضافة فلتر "نوع القائمة" في شريط الفلاتر
# ============================================================
# نبحث عن حقل "مستوى العرض" ونضيف الفلتر الجديد بعده
old_level_div = r'(<div class="col-md-2">\s*<label[^>]*>مستوى العرض</label>\s*<select[^>]*id="f-level"[^>]*>.*?</select>\s*</div>)'
new_level_div = r'''\1
            <div class="col-md-3">
                <label class="form-label">نوع القائمة</label>
                <select id="f-stmt" class="form-select form-select-sm" onchange="loadTrialBalance()">
                    <option value="all">كل القوائم</option>
                    <option value="BS">الميزانية العمومية</option>
                    <option value="IS">قائمة الدخل</option>
                </select>
            </div>'''
content = re.sub(old_level_div, new_level_div, content, count=1, flags=re.DOTALL)
print("✅ تمت إضافة فلتر 'نوع القائمة'.")

# ============================================================
# 3. تعديل دالة loadTrialBalance لتطبيق الفلترة وعرض العمود
# ============================================================
js_pattern = re.compile(r'async function loadTrialBalance\(\)\s*\{.*?(?=window\.onload)', re.DOTALL)

new_js = """
async function loadTrialBalance() {
    const f = document.getElementById('fromDate').value;
    const t = document.getElementById('toDate').value;
    const level = document.getElementById('f-level').value;
    const stmtEl = document.getElementById('f-stmt');
    const stmt = stmtEl ? stmtEl.value : 'all';
    
    const qs = new URLSearchParams();
    if (f) qs.append('from_date', f);
    if (t) qs.append('to_date', t);
    if (level) qs.append('level', level);
    if (stmt && stmt !== 'all') qs.append('stmt', stmt);
    
    try {
        const res = await fetch(`${API}/reports/trial-balance?${qs.toString()}`).then(r => r.json());
        const tbody = document.getElementById('tbBody');
        
        if (!res.success || !res.data || res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-danger">لا توجد بيانات</td></tr>';
            return;
        }
        
        const getNumLevel = (lvl) => {
            if (typeof lvl === 'number') return lvl;
            if (typeof lvl === 'string') return parseInt(lvl.replace('L', '')) || 1;
            return 1;
        };
        
        const data = res.data;
        
        const parentCodes = new Set();
        data.forEach(row => {
            if (row.parent_code) parentCodes.add(row.parent_code);
        });
        
        tbody.innerHTML = data.map(r => {
            const openingDebit = r.opening_balance > 0 ? r.opening_balance : 0;
            const openingCredit = r.opening_balance < 0 ? -r.opening_balance : 0;
            const closingDebit = r.closing_balance > 0 ? r.closing_balance : 0;
            const closingCredit = r.closing_balance < 0 ? -r.closing_balance : 0;
            
            const lvl = getNumLevel(r.level);
            const indent = lvl > 1 ? '&nbsp;&nbsp;&nbsp;&nbsp;'.repeat(lvl - 1) + '↳ ' : '';
            
            const isParent = parentCodes.has(r.code);
            const rowClass = isParent ? 'fw-bold' : '';
            
            const stmtLabel = r.financial_statement === 'BS' ? 'ميزانية' : (r.financial_statement === 'IS' ? 'دخل' : '—');
            
            return `
                <tr class="${rowClass}">
                    <td>${r.code}</td>
                    <td class="text-end">${indent}${r.name}</td>
                    <td><span class="badge bg-secondary">${stmtLabel}</span></td>
                    <td>${openingDebit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${openingCredit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${r.period_debit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${r.period_credit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${closingDebit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${closingCredit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                </tr>
            `;
        }).join('');
        
    } catch (e) {
        alert('خطأ: ' + e.message);
    }
}
"""
content = js_pattern.sub(new_js, content)
print("✅ تم تعديل دالة loadTrialBalance.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("🎉 تم حفظ التعديلات. أعد تحميل الصفحة.")
