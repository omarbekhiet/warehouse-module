# -*- coding: utf-8 -*-
import re

PATH = "app/static/trial_balance.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

js_pattern = re.compile(r'async function loadTrialBalance\(\)\s*\{.*?(?=window\.onload)', re.DOTALL)

new_js = """
async function loadTrialBalance() {
    const f = document.getElementById('fromDate').value;
    const t = document.getElementById('toDate').value;
    const level = document.getElementById('f-level').value;
    const stmt = document.getElementById('f-stmt').value;
    
    const qs = new URLSearchParams();
    if (f) qs.append('from_date', f);
    if (t) qs.append('to_date', t);
    if (level) qs.append('level', level);
    if (stmt) qs.append('stmt', stmt);
    
    try {
        // نطلب البيانات المفلترة للعرض
        const res = await fetch(`${API}/reports/trial-balance?${qs.toString()}`).then(r => r.json());
        
        // نطلب البيانات الكاملة (بدون فلترة) لحساب الإجماليات الحقيقية
        const qsAll = new URLSearchParams();
        if (f) qsAll.append('from_date', f);
        if (t) qsAll.append('to_date', t);
        const resAll = await fetch(`${API}/reports/trial-balance?${qsAll.toString()}`).then(r => r.json());
        
        const tbody = document.getElementById('tbBody');
        const tfoot = document.getElementById('tbFooter');
        
        if (!res.success || !res.data || res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-danger">لا توجد بيانات</td></tr>';
            tfoot.style.display = 'none';
            return;
        }
        
        const getNumLevel = (lvl) => {
            if (typeof lvl === 'number') return lvl;
            if (typeof lvl === 'string') return parseInt(lvl.replace('L', '')) || 1;
            return 1;
        };
        
        // 1. حساب الإجماليات من البيانات الكاملة (resAll)
        const parentCodesAll = new Set();
        if (resAll.success && resAll.data) {
            resAll.data.forEach(row => {
                if (row.parent_code) parentCodesAll.add(row.parent_code);
            });
        }
        
        let sumOpD = 0, sumOpC = 0, sumPd = 0, sumPc = 0, sumClD = 0, sumClC = 0;
        
        if (resAll.success && resAll.data) {
            resAll.data.forEach(r => {
                const isLeaf = !parentCodesAll.has(r.code);
                if (!isLeaf) return;
                
                const openingDebit = r.opening_balance > 0 ? r.opening_balance : 0;
                const openingCredit = r.opening_balance < 0 ? -r.opening_balance : 0;
                const closingDebit = r.closing_balance > 0 ? r.closing_balance : 0;
                const closingCredit = r.closing_balance < 0 ? -r.closing_balance : 0;
                
                sumOpD += openingDebit;
                sumOpC += openingCredit;
                sumPd += (r.period_debit || 0);
                sumPc += (r.period_credit || 0);
                sumClD += closingDebit;
                sumClC += closingCredit;
            });
        }
        
        // 2. عرض الحسابات المفلترة (res.data)
        const parentCodes = new Set();
        res.data.forEach(row => {
            if (row.parent_code) parentCodes.add(row.parent_code);
        });
        
        tbody.innerHTML = res.data.map(r => {
            const openingDebit = r.opening_balance > 0 ? r.opening_balance : 0;
            const openingCredit = r.opening_balance < 0 ? -r.opening_balance : 0;
            const closingDebit = r.closing_balance > 0 ? r.closing_balance : 0;
            const closingCredit = r.closing_balance < 0 ? -r.closing_balance : 0;
            
            const lvl = getNumLevel(r.level);
            const indent = lvl > 1 ? '&nbsp;&nbsp;&nbsp;&nbsp;'.repeat(lvl - 1) + '↳ ' : '';
            
            const isParent = parentCodes.has(r.code);
            const rowClass = isParent ? 'fw-bold' : '';
            
            const stmtLabel = r.financial_statement === 'BS' ? 'ميزانية' : (r.financial_statement === 'EQ' ? 'حقوق ملكية' : (r.financial_statement === 'IS' ? 'دخل' : '—'));
            
            return `
                <tr class="${rowClass}">
                    <td>${r.code}</td>
                    <td class="text-end">${indent}${r.name}</td>
                    <td><span class="badge bg-secondary">${stmtLabel}</span></td>
                    <td>${openingDebit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${openingCredit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${(r.period_debit || 0).toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${(r.period_credit || 0).toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${closingDebit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                    <td>${closingCredit.toLocaleString('en-US', {minimumFractionDigits:2})}</td>
                </tr>
            `;
        }).join('');
        
        // 3. تحديث سطر الإجماليات من البيانات الكاملة
        document.getElementById('ft_opD').textContent = sumOpD.toLocaleString('en-US', {minimumFractionDigits:2});
        document.getElementById('ft_opC').textContent = sumOpC.toLocaleString('en-US', {minimumFractionDigits:2});
        document.getElementById('ft_pD').textContent = sumPd.toLocaleString('en-US', {minimumFractionDigits:2});
        document.getElementById('ft_pC').textContent = sumPc.toLocaleString('en-US', {minimumFractionDigits:2});
        document.getElementById('ft_clD').textContent = sumClD.toLocaleString('en-US', {minimumFractionDigits:2});
        document.getElementById('ft_clC').textContent = sumClC.toLocaleString('en-US', {minimumFractionDigits:2});
        
        tfoot.style.display = 'table-footer-group';
        
    } catch (e) {
        alert('خطأ: ' + e.message);
    }
}
"""
content = js_pattern.sub(new_js, content)

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم تعديل الواجهة: الإجماليات تُحسب من البيانات الكاملة (بدون فلترة) وتظهر ثابتة في كل المستويات.")
