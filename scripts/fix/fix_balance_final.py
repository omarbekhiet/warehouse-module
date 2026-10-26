# -*- coding: utf-8 -*-
import re

# ============================================================
# 1. تعديل السيرفر: إرسال كل الحسابات (بدون فلترة)
# ============================================================
PATH_PY = "app/routes/report_routes.py"
raw_py = open(PATH_PY, "rb").read()
content_py = raw_py.decode("utf-8-sig")

pattern = re.compile(r"@report_bp\.route\('/financial-reports/balance-sheet'.*?(?=@report_bp\.route|$)", re.DOTALL)
content_py = pattern.sub("", content_py)

new_func = """
@report_bp.route('/financial-reports/balance-sheet', methods=['GET'])
def balance_sheet_report():
    as_of = request.args.get('as_of')
    
    try:
        with db.get_connection() as conn:
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level, financial_statement FROM accounts ORDER BY code").fetchall()
            
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                
                acc_dict[code] = {
                    'code': code, 'name': a['name_ar'],
                    'parent_code': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl, 'financial_statement': a['financial_statement'],
                    'balance': 0.0
                }

            if as_of:
                q = \"\"\"SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                       FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                       WHERE je.status = 'POSTED' AND je.entry_date <= ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)\"\"\"
                for r in conn.execute(q, (as_of,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict:
                        acc_dict[c]['balance'] = float(r['bal'])

            sorted_for_rollup = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_for_rollup:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict:
                    acc_dict[parent]['balance'] += node['balance']

            result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                # عكس إشارة الالتزامات (2) وحقوق الملكية (8)
                if code.startswith('2') or code.startswith('8'):
                    node['balance'] = -node['balance']
                result.append(node)

            return jsonify({'success': True, 'data': result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
"""
content_py += new_func

with open(PATH_PY, "w", encoding="utf-8", newline="\n") as f:
    f.write(content_py)
print("✅ 1. السيرفر: يرسل كل الحسابات (بدون فلترة) مع الحقل financial_statement.")


# ============================================================
# 2. تعديل الواجهة: الإجماليات من كل الحسابات الورقية (ثابتة)
# ============================================================
PATH_HTML = "app/static/balance_sheet.html"
raw_html = open(PATH_HTML, "rb").read()
content_html = raw_html.decode("utf-8-sig")

# البحث عن دالة loadTrialBalance أو load في الواجهة
js_pattern = re.compile(r'async function load\(\)\s*\{.*?(?=window\.onload)', re.DOTALL)

new_js = """
async function load() {
    const content = document.getElementById('bs-content');
    content.innerHTML = '<div class="text-center py-4"><i class="bi bi-arrow-clockwise"></i> جاري التحميل...</div>';

    try {
        const asOf = parseDateDMY(document.getElementById('f-asof').value);
        const level = document.getElementById('f-level') ? document.getElementById('f-level').value : '1';
        
        const qs = new URLSearchParams();
        if (asOf) qs.append('as_of', asOf);
        
        const res = await fetch(`${API}/financial-reports/balance-sheet?${qs.toString()}`).then(r => r.json());
        if (!res.success) throw new Error(res.message || 'خطأ');
        
        const allData = res.data;
        const fmt = (v) => (Number(v) || 0).toLocaleString('en-US', {minimumFractionDigits:2});

        // 1. حساب الإجماليات الثابتة من كل الحسابات الورقية
        const parentCodesAll = new Set();
        allData.forEach(r => {
            if (r.parent_code) parentCodesAll.add(r.parent_code);
        });
        
        let totalAssets = 0, totalLiab = 0, totalEq = 0;
        allData.forEach(r => {
            if (parentCodesAll.has(r.code)) return; // تخطي الآباء
            
            if (r.financial_statement === 'BS') totalAssets += r.balance;
            else if (r.financial_statement === 'EQ') totalEq += r.balance;
            else if (r.code.startsWith('2')) totalLiab += Math.abs(r.balance);
        });
        // تصحيح: الأصول قد تكون BS وتشمل الالتزامات، لذا نستخدم الكود
        totalAssets = 0; totalLiab = 0;
        allData.forEach(r => {
            if (parentCodesAll.has(r.code)) return;
            if (r.code.startsWith('1')) totalAssets += r.balance;
            else if (r.code.startsWith('2')) totalLiab += Math.abs(r.balance);
            else if (r.code.startsWith('8')) totalEq += r.balance;
        });

        const totalLiabPlusEq = totalLiab + totalEq;

        // 2. فلترة البيانات للعرض
        let data = allData;
        if (level !== '99') {
            const target = parseInt(level);
            data = data.filter(r => (r.level || 1) <= target);
        }

        // 3. تصنيف الأصول والالتزامات وحقوق الملكية للعرض
        const assets = data.filter(r => r.code.startsWith('1'));
        const liabilities = data.filter(r => r.code.startsWith('2'));
        const equity = data.filter(r => r.code.startsWith('8'));

        const nonCurrentAssets = assets.filter(a => a.code.startsWith('11'));
        const currentAssets = assets.filter(a => a.code.startsWith('12'));
        const nonCurrentLiab = liabilities.filter(l => l.code.startsWith('21'));
        const currentLiab = liabilities.filter(l => l.code.startsWith('22'));

        const makeRows = (arr) => {
            if (!arr.length) return '<div class="text-muted p-3 text-center">لا توجد حسابات</div>';
            return arr.map(a => {
                const lvl = a.level || 1;
                const indent = lvl > 1 ? '&nbsp;&nbsp;&nbsp;&nbsp;'.repeat(lvl - 1) + '↳ ' : '';
                return `<div class="bs-row">
                    <div class="bs-code">${a.code}</div>
                    <div class="bs-name">${indent}${a.name}</div>
                    <div class="bs-amount">${fmt(a.balance)}</div>
                </div>`;
            }).join('');
        };

        let html = '<div class="bs-grid">';

        // العمود الأيمن: الأصول
        html += '<div>';
        html += `<div class="bs-section">
            <div class="bs-section-header assets"><i class="bi bi-building"></i> الأصول غير المتداولة (${nonCurrentAssets.length} حساب)</div>
            ${makeRows(nonCurrentAssets)}
            <div class="bs-subtotal"><span>إجمالي الأصول غير المتداولة</span><span>${fmt(nonCurrentAssets.reduce((s, a) => s + (a.balance || 0), 0))}</span></div>
        </div>`;
        html += `<div class="bs-section" style="margin-top:8px;">
            <div class="bs-section-header assets"><i class="bi bi-cash-stack"></i> الأصول المتداولة (${currentAssets.length} حساب)</div>
            ${makeRows(currentAssets)}
            <div class="bs-subtotal"><span>إجمالي الأصول المتداولة</span><span>${fmt(currentAssets.reduce((s, a) => s + (a.balance || 0), 0))}</span></div>
        </div>`;
        html += `<div class="bs-total assets" style="margin-top:8px;">
            <span>إجمالي الأصول</span><span>${fmt(totalAssets)}</span>
        </div>`;
        html += '</div>';

        // العمود الأيسر: الالتزامات + حقوق الملكية
        html += '<div>';
        html += `<div class="bs-section">
            <div class="bs-section-header liabilities"><i class="bi bi-bank"></i> الالتزامات غير المتداولة (${nonCurrentLiab.length} حساب)</div>
            ${makeRows(nonCurrentLiab)}
            <div class="bs-subtotal"><span>إجمالي الالتزامات غير المتداولة</span><span>${fmt(nonCurrentLiab.reduce((s, a) => s + Math.abs(a.balance || 0), 0))}</span></div>
        </div>`;
        html += `<div class="bs-section" style="margin-top:8px;">
            <div class="bs-section-header liabilities"><i class="bi bi-truck"></i> الالتزامات المتداولة (${currentLiab.length} حساب)</div>
            ${makeRows(currentLiab)}
            <div class="bs-subtotal"><span>إجمالي الالتزامات المتداولة</span><span>${fmt(currentLiab.reduce((s, a) => s + Math.abs(a.balance || 0), 0))}</span></div>
        </div>`;
        html += `<div class="bs-total liabilities" style="margin-top:8px;">
            <span>إجمالي الالتزامات</span><span>${fmt(totalLiab)}</span>
        </div>`;
        html += `<div class="bs-section" style="margin-top:8px;">
            <div class="bs-section-header equity"><i class="bi bi-people"></i> حقوق الملكية (${equity.length} حساب)</div>
            ${makeRows(equity)}
            <div class="bs-subtotal"><span>إجمالي حقوق الملكية</span><span>${fmt(totalEq)}</span></div>
        </div>`;
        html += `<div class="bs-total liab_eq" style="margin-top:8px;">
            <span>الالتزامات + حقوق الملكية</span><span>${fmt(totalLiabPlusEq)}</span>
        </div>`;
        html += '</div>';

        html += '</div>'; // bs-grid

        // Balance check
        const isBalanced = Math.abs(totalAssets - totalLiabPlusEq) < 0.01;
        if (isBalanced) {
            html += `<div class="balance-check ok">
                <i class="bi bi-check-circle-fill"></i> الميزانية متوازنة
                <div class="diff">الأصول: ${fmt(totalAssets)} = الالتزامات + حقوق الملكية: ${fmt(totalLiabPlusEq)}</div>
            </div>`;
        } else {
            html += `<div class="balance-check bad">
                <i class="bi bi-exclamation-triangle-fill"></i> الميزانية غير متوازنة
                <div class="diff">الفرق: ${fmt(Math.abs(totalAssets - totalLiabPlusEq))}</div>
            </div>`;
        }

        content.innerHTML = html;
    } catch (e) {
        console.error(e);
        content.innerHTML = `<div class="alert alert-danger">فشل تحميل البيانات: ${e.message}</div>`;
    }
}
"""
content_html = js_pattern.sub(new_js, content_html)

with open(PATH_HTML, "w", encoding="utf-8", newline="\n") as f:
    f.write(content_html)
print("✅ 2. الواجهة: الإجماليات تُحسب من كل الحسابات الورقية (ثابتة)، والفلترة للعرض فقط.")
