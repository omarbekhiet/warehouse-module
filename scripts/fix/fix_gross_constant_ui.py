# -*- coding: utf-8 -*-
import re

PATH = "app/static/income_statement.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

js_pattern = re.compile(r'async function loadReport\(\)\s*\{.*?(?=window\.onload)', re.DOTALL)

new_js = """
async function loadReport() {
    const from = document.getElementById('fromDate').value;
    const to = document.getElementById('toDate').value;
    const level = document.getElementById('f-level').value;
    
    const qs = new URLSearchParams();
    if (from) qs.append('from_date', from);
    if (to) qs.append('to_date', to);
    
    const content = document.getElementById('report-content');
    content.innerHTML = '<div class="text-center p-5">جاري التحميل...</div>';

    try {
        const res = await fetch(`${API}/reports/income-statement?${qs.toString()}`).then(r => r.json());
        if (!res.success) { content.innerHTML = `<div class="alert alert-danger">${res.message}</div>`; return; }
        
        const allData = res.data; // البيانات الكاملة (قبل الفلترة)
        const fmt = (v) => (Number(v) || 0).toLocaleString('en-US', {minimumFractionDigits:2});

        // 1. حساب المجاميع الثابتة من البيانات الكاملة (قبل الفلترة)
        let totalRevenue = 0, totalCost = 0, totalOpex = 0;
        allData.forEach(item => {
            if (item.code.startsWith('4')) totalRevenue += item.closing_balance;
            else if (item.code.startsWith('3')) totalCost += item.closing_balance;
            else if (item.code.startsWith('5')) totalOpex += item.closing_balance;
        });
        
        const grossProfit = totalRevenue + totalCost;
        const operatingProfit = grossProfit + totalOpex;

        // 2. فلترة البيانات للعرض (تراكمية)
        let filteredData = allData;
        if (level !== '99') {
            const target = parseInt(level);
            filteredData = allData.filter(r => (r.level || 1) <= target);
        }

        // 3. تصنيف الحسابات المفلترة للعرض
        const sections = {
            'operating': { name: 'قسم التشغيل (Operating)', items: [], total: 0 },
            'investing': { name: 'قسم الاستثمار (Investing)', items: [], total: 0 },
            'financing': { name: 'قسم التمويل (Financing)', items: [], total: 0 },
            'taxes': { name: 'قسم الضرائب (Income Taxes)', items: [], total: 0 },
            'discontinued': { name: 'قسم العمليات المتوقفة', items: [], total: 0 }
        };
        
        filteredData.forEach(r => {
            const group = r.pl_group || '';
            let section = 'operating';
            if (group === 'TAX' || r.code.startsWith('7')) section = 'taxes';
            else if (group === 'FIN' || r.code.startsWith('6')) section = 'financing';
            else if (group === 'INV' || r.code.startsWith('42')) section = 'investing';
            else if (group === 'DISC') section = 'discontinued';
            
            sections[section].items.push(r);
            sections[section].total += r.closing_balance;
        });

        // 4. حساب المجاميع الفرعية من البيانات المعروضة (للعرض فقط)
        const investingProfit = sections.investing.total;
        const profitBeforeFinancingAndTax = operatingProfit + investingProfit;
        const financingCost = sections.financing.total;
        const profitBeforeTax = profitBeforeFinancingAndTax + financingCost;
        const taxExpense = sections.taxes.total;
        const netProfit = profitBeforeTax + taxExpense;

        const resultLabel = (val, base) => {
            return val >= 0 ? `${base} (ربح)` : `${base} (خسارة)`;
        };

        const getOrder = (code) => {
            if (code.startsWith('4')) return 1;
            if (code.startsWith('3')) return 2;
            if (code.startsWith('5')) return 3;
            return 4;
        };
        sections.operating.items.sort((a, b) => getOrder(a.code) - getOrder(b.code));

        let html = '';
        
        // ============ 1. قسم التشغيل ============
        html += `<div class="section-title">${sections.operating.name}</div>`;
        let revHtml = '', costHtml = '', opexHtml = '';
        sections.operating.items.forEach(item => {
            const row = `
                <div class="cf-row">
                    <div>${item.code} - ${item.name}</div>
                    <div class="cf-amount ${item.closing_balance < 0 ? 'text-danger' : 'text-success'}">${fmt(item.closing_balance)}</div>
                </div>
            `;
            if (item.code.startsWith('4')) revHtml += row;
            else if (item.code.startsWith('3')) costHtml += row;
            else if (item.code.startsWith('5')) opexHtml += row;
        });
        html += revHtml;
        html += costHtml;
        // استخدام القيمة الثابتة (من كل الحسابات) لمجمل الربح
        html += `<div class="cf-subtotal"><span>${resultLabel(grossProfit, 'مجمل الربح')}</span><span>${fmt(grossProfit)}</span></div>`;
        html += opexHtml;
        html += `<div class="cf-subtotal"><span>${resultLabel(operatingProfit, 'ربح التشغيل')}</span><span>${fmt(operatingProfit)}</span></div>`;
        
        // ============ 2. قسم الاستثمار ============
        html += `<div class="section-title">${sections.investing.name}</div>`;
        if (sections.investing.items.length === 0) {
            html += '<div class="text-muted p-2 text-center">لا توجد بنود استثمارية</div>';
        } else {
            html += sections.investing.items.map(item => `
                <div class="cf-row">
                    <div>${item.code} - ${item.name}</div>
                    <div class="cf-amount ${item.closing_balance < 0 ? 'text-danger' : 'text-success'}">${fmt(item.closing_balance)}</div>
                </div>
            `).join('');
        }
        html += `<div class="cf-subtotal"><span>${resultLabel(investingProfit, 'صافي ربح الاستثمار')}</span><span>${fmt(investingProfit)}</span></div>`;
        
        // ============ الربح قبل التمويل والضرائب ============
        html += `<div class="cf-grand-total"><span>${resultLabel(profitBeforeFinancingAndTax, 'الربح قبل التمويل والضرائب')}</span><span>${fmt(profitBeforeFinancingAndTax)}</span></div>`;
        
        // ============ 3. قسم التمويل ============
        html += `<div class="section-title">${sections.financing.name}</div>`;
        if (sections.financing.items.length === 0) {
            html += '<div class="text-muted p-2 text-center">لا توجد بنود تمويلية</div>';
        } else {
            html += sections.financing.items.map(item => `
                <div class="cf-row">
                    <div>${item.code} - ${item.name}</div>
                    <div class="cf-amount ${item.closing_balance < 0 ? 'text-danger' : 'text-success'}">${fmt(item.closing_balance)}</div>
                </div>
            `).join('');
        }
        html += `<div class="cf-subtotal"><span>صافي تكاليف التمويل</span><span>${fmt(financingCost)}</span></div>`;
        
        // ============ الربح قبل الضرائب ============
        html += `<div class="cf-grand-total"><span>${resultLabel(profitBeforeTax, 'الربح قبل ضريبة الدخل')}</span><span>${fmt(profitBeforeTax)}</span></div>`;
        
        // ============ 4. قسم الضرائب ============
        html += `<div class="section-title">${sections.taxes.name}</div>`;
        if (sections.taxes.items.length === 0) {
            html += '<div class="text-muted p-2 text-center">لا توجد ضرائب مسجلة</div>';
        } else {
            html += sections.taxes.items.map(item => `
                <div class="cf-row">
                    <div>${item.code} - ${item.name}</div>
                    <div class="cf-amount ${item.closing_balance < 0 ? 'text-danger' : 'text-success'}">${fmt(item.closing_balance)}</div>
                </div>
            `).join('');
        }
        html += `<div class="cf-subtotal"><span>صافي الضرائب</span><span>${fmt(taxExpense)}</span></div>`;
        
        // ============ 5. قسم العمليات المتوقفة ============
        if (sections.discontinued.items.length > 0) {
            html += `<div class="section-title">${sections.discontinued.name}</div>`;
            html += sections.discontinued.items.map(item => `
                <div class="cf-row">
                    <div>${item.code} - ${item.name}</div>
                    <div class="cf-amount ${item.closing_balance < 0 ? 'text-danger' : 'text-success'}">${fmt(item.closing_balance)}</div>
                </div>
            `).join('');
            html += `<div class="cf-subtotal"><span>صافي العمليات المتوقفة</span><span>${fmt(sections.discontinued.total)}</span></div>`;
        }
        
        // ============ صافي الربح النهائي ============
        const finalLabel = netProfit >= 0 ? 'صافي الربح (Profit)' : 'صافي الخسارة (Loss)';
        const finalClass = netProfit >= 0 ? 'cf-final-total' : 'cf-final-total loss';
        html += `<div class="${finalClass}"><span>${finalLabel}</span><span>${fmt(netProfit)}</span></div>`;
        
        content.innerHTML = html;
    } catch (e) {
        content.innerHTML = `<div class="alert alert-danger">حدث خطأ: ${e.message}</div>`;
    }
}
"""
content = js_pattern.sub(new_js, content)

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم تعديل الواجهة: 'مجمل الربح' و 'ربح التشغيل' يُحسبان من كل الحسابات (ثابتان في كل المستويات).")
