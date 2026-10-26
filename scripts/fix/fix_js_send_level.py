# -*- coding: utf-8 -*-
import re

PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# البحث عن دالة loadTrialBalance في الواجهة
js_pattern = re.compile(r'async function loadTrialBalance\(\)\s*\{.*?(?=window\.onload)', re.DOTALL)

new_js = """
async function loadTrialBalance() {
    const f = document.getElementById('fromDate').value;
    const t = document.getElementById('toDate').value;
    const level = document.getElementById('f-level').value; // قراءة المستوى المختار
    const qs = new URLSearchParams();
    if (f) qs.append('from_date', f);
    if (t) qs.append('to_date', t);
    if (level) qs.append('level', level); // إرسال المستوى إلى السيرفر
    
    try {
        const res = await fetch(`${API}/reports/trial-balance?${qs.toString()}`).then(r => r.json());
        const tbody = document.getElementById('tbBody');
        
        if (!res.success || !res.data || res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">لا توجد بيانات</td></tr>';
            return;
        }
        
        const getNumLevel = (lvl) => {
            if (typeof lvl === 'number') return lvl;
            if (typeof lvl === 'string') return parseInt(lvl.replace('L', '')) || 1;
            return 1;
        };
        
        // عرض البيانات (السيرفر قام بالفلترة بالفعل)
        const data = res.data;
        
        // بناء خريطة للأباء لمعرفة من له أبناء (لتمييز الحسابات الوسيطة)
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
            
            return `
                <tr class="${rowClass}">
                    <td>${r.code}</td>
                    <td class="text-end">${indent}${r.name}</td>
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

# التأكد من وجود خيارات المستويات 4 و 5
if 'value="4"' not in content:
    content = content.replace(
        '<option value="3">المستوى الثالث فقط</option>',
        '<option value="3">المستوى الثالث فقط</option>\n<option value="4">المستوى الرابع فقط</option>\n<option value="5">المستوى الخامس فقط</option>'
    )

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم تعديل الواجهة: ترسل level إلى السيرفر، وتعرض البيانات المفلترة.")
