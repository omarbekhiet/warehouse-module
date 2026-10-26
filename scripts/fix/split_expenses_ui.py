# -*- coding: utf-8 -*-
import re

PATH = "app/static/income_statement.html"
raw = open(PATH, "rb").read()
content = raw.decode("utf-8-sig")

# تعديل الجزء الذي يعرض المصروفات في قسم التشغيل
old_html_gen = """        let revHtml = '', costHtml = '', opexHtml = '';
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
        html += `<div class="cf-subtotal"><span>${resultLabel(grossProfit, 'مجمل الربح')}</span><span>${fmt(grossProfit)}</span></div>`;
        html += opexHtml;
        html += `<div class="cf-subtotal"><span>${resultLabel(operatingProfit, 'ربح التشغيل')}</span><span>${fmt(operatingProfit)}</span></div>`;"""

new_html_gen = """        let revHtml = '', costHtml = '', sellingHtml = '', adminHtml = '';
        sections.operating.items.forEach(item => {
            const row = `
                <div class="cf-row">
                    <div>${item.code} - ${item.name}</div>
                    <div class="cf-amount ${item.closing_balance < 0 ? 'text-danger' : 'text-success'}">${fmt(item.closing_balance)}</div>
                </div>
            `;
            if (item.code.startsWith('4')) revHtml += row;
            else if (item.code.startsWith('3')) costHtml += row;
            else if (item.code.startsWith('54')) sellingHtml += row; // مصروفات بيعية
            else if (item.code.startsWith('5')) adminHtml += row; // مصروفات عمومية وإدارية
        });
        
        html += revHtml;
        html += costHtml;
        html += `<div class="cf-subtotal"><span>${resultLabel(grossProfit, 'مجمل الربح')}</span><span>${fmt(grossProfit)}</span></div>`;
        
        // عرض المصروفات البيعية (إذا وجدت)
        if (sellingHtml) {
            html += `<div class="text-muted mt-2 mb-1" style="font-weight:bold; font-size:12px;">مصروفات بيعية وتسويقية:</div>`;
            html += sellingHtml;
        }
        
        // عرض المصروفات العمومية والإدارية (إذا وجدت)
        if (adminHtml) {
            html += `<div class="text-muted mt-2 mb-1" style="font-weight:bold; font-size:12px;">مصروفات عمومية وإدارية:</div>`;
            html += adminHtml;
        }
        
        html += `<div class="cf-subtotal"><span>${resultLabel(operatingProfit, 'ربح التشغيل')}</span><span>${fmt(operatingProfit)}</span></div>`;"""

if old_html_gen in content:
    content = content.replace(old_html_gen, new_html_gen)
    print("✅ تم تعديل الواجهة: تقسيم المصروفات إلى بيعية وعمومية وإدارية.")
else:
    print("⚠️ لم أجد الكود القديم. قد يكون تم تعديله.")

with open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

print("✅ تم الحفظ.")
