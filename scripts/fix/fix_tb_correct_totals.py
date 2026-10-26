# -*- coding: utf-8 -*-
import re

# ============================================================
# 1. تعديل السيرفر: الفلترة حسب المستوى وإرسال الحسابات المطلوبة فقط
# ============================================================
PATH_PY = "app/routes/report_routes.py"
raw_py = open(PATH_PY, "rb").read()
content_py = raw_py.decode("utf-8-sig")

pattern = re.compile(r"@report_bp\.route\('/trial-balance'.*?(?=@report_bp\.route|$)", re.DOTALL)
content_py = pattern.sub("", content_py)

new_func = """
@report_bp.route('/trial-balance', methods=['GET'])
def trial_balance():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    level_filter = request.args.get('level')
    stmt_filter = request.args.get('stmt')

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
                    'opening_balance': 0.0, 'period_debit': 0.0, 'period_credit': 0.0
                }

            if from_date:
                q_open = \"\"\"SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) as d, COALESCE(SUM(jl.credit_amount), 0) as c
                             FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                             WHERE je.status = 'POSTED' AND je.entry_date < ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)\"\"\"
                for r in conn.execute(q_open, (from_date,)).fetchall():
                    c = str(r['acc_code']).strip()
                    if c in acc_dict:
                        acc_dict[c]['opening_balance'] = float(r['d']) - float(r['c'])

            cond, vals = ["je.status = 'POSTED'", "jl.account_code IS NOT NULL"], []
            if from_date:
                cond.append("je.entry_date >= ?"); vals.append(from_date)
            if to_date:
                cond.append("je.entry_date <= ?"); vals.append(to_date)
            where = " AND ".join(cond)

            q_period = f\"\"\"SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) as d, COALESCE(SUM(jl.credit_amount), 0) as c
                            FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                            WHERE {where} GROUP BY CAST(jl.account_code AS TEXT)\"\"\"
            for r in conn.execute(q_period, tuple(vals)).fetchall():
                c = str(r['acc_code']).strip()
                if c in acc_dict:
                    acc_dict[c]['period_debit'] = float(r['d'])
                    acc_dict[c]['period_credit'] = float(r['c'])

            # التجميع (Roll-up)
            sorted_for_rollup = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_for_rollup:
                node = acc_dict[code]
                parent = node['parent_code']
                if parent and parent in acc_dict:
                    acc_dict[parent]['opening_balance'] += node['opening_balance']
                    acc_dict[parent]['period_debit'] += node['period_debit']
                    acc_dict[parent]['period_credit'] += node['period_credit']

            # بناء النتيجة مع الفلترة
            result = []
            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                node['closing_balance'] = node['opening_balance'] + node['period_debit'] - node['period_credit']
                
                # فلترة المستوى
                if level_filter and level_filter != '99':
                    try:
                        target_level = int(level_filter)
                        if node['level'] != target_level:
                            continue
                    except ValueError:
                        pass
                
                # فلترة نوع القائمة
                if stmt_filter and stmt_filter != 'all':
                    if stmt_filter == 'BS' and node['financial_statement'] not in ['BS', 'EQ']:
                        continue
                    elif stmt_filter == 'IS' and node['financial_statement'] not in ['IS']:
                        continue
                
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
print("✅ 1. السيرفر: يرسل الحسابات المفلترة فقط (حسب المستوى ونوع القائمة).")


# ============================================================
# 2. تعديل الواجهة: جمع الإجماليات من الحسابات المعروضة فقط
# ============================================================
PATH_HTML = "app/static/trial_balance.html"
raw_html = open(PATH_HTML, "rb").read()
content_html = raw_html.decode("utf-8-sig")

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
        const res = await fetch(`${API}/reports/trial-balance?${qs.toString()}`).then(r => r.json());
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
        
        // 1. جمع الإجماليات من **الحسابات المعروضة فقط** (لأن السيرفر أرسلها مفلترة)
        let sumOpD = 0, sumOpC = 0, sumPd = 0, sumPc = 0, sumClD = 0, sumClC = 0;
        res.data.forEach(r => {
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
        
        const parentCodes = new Set();
        res.data.forEach(row => {
            if (row.parent_code) parentCodes.add(row.parent_code);
        });
        
        // 2. عرض الحسابات
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
        
        // 3. تحديث سطر الإجماليات (من الحسابات المعروضة)
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
content_html = js_pattern.sub(new_js, content_html)

with open(PATH_HTML, "w", encoding="utf-8", newline="\n") as f:
    f.write(content_html)
print("✅ 2. الواجهة: تجمع الإجماليات من الحسابات المعروضة فقط (بعد الفلترة).")
