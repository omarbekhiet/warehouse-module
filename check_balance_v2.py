# -*- coding: utf-8 -*-
import sys
try:
    from app.database import db
except ImportError:
    print("Error: app.database not found.")
    sys.exit(1)

def print_balance_sheet(as_of_date=None):
    print("=" * 80)
    print(f"Balance Sheet Check - As of: {as_of_date or 'All Periods'}")
    print("=" * 80)
    
    with db.get_connection() as conn:
        accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level FROM accounts ORDER BY code").fetchall()
        
        acc_dict = {}
        for a in accounts:
            code = str(a['code']).strip()
            lvl_str = str(a['level'] or 'L1').replace('L', '')
            try: lvl = int(lvl_str)
            except: lvl = 1
            acc_dict[code] = {'code': code, 'name': a['name_ar'], 'parent': str(a['parent_code']).strip() if a['parent_code'] else None, 'level': lvl, 'balance': 0.0}

        if as_of_date:
            q = """SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                   FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                   WHERE je.status = 'POSTED' AND je.entry_date <= ? AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)"""
            params = (as_of_date,)
        else:
            q = """SELECT CAST(jl.account_code AS TEXT) as acc_code, COALESCE(SUM(jl.debit_amount), 0) - COALESCE(SUM(jl.credit_amount), 0) as bal
                   FROM journal_entry_lines jl JOIN journal_entries je ON jl.journal_entry_id = je.id
                   WHERE je.status = 'POSTED' AND jl.account_code IS NOT NULL GROUP BY CAST(jl.account_code AS TEXT)"""
            params = ()
            
        for r in conn.execute(q, params).fetchall():
            c = str(r['acc_code']).strip()
            if c in acc_dict:
                acc_dict[c]['balance'] = float(r['bal'])

        sorted_codes = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
        for code in sorted_codes:
            node = acc_dict[code]
            parent = node['parent']
            if parent and parent in acc_dict:
                acc_dict[parent]['balance'] += node['balance']

        parent_codes = set(n['parent'] for n in acc_dict.values() if n['parent'])

        total_assets = 0.0
        total_liab = 0.0
        total_eq = 0.0
        total_rev = 0.0
        total_exp = 0.0

        for code in sorted(acc_dict.keys()):
            node = acc_dict[code]
            bal = node['balance']
            
            is_leaf = code not in parent_codes
            if is_leaf:
                if code.startswith('1'): total_assets += bal
                elif code.startswith('2'): total_liab += abs(bal)
                elif code.startswith('8'): total_eq += abs(bal)
                elif code.startswith('4'): total_rev += abs(bal)
                elif code.startswith('5') or code.startswith('3') or code.startswith('6') or code.startswith('7'): total_exp += bal

            if abs(bal) < 0.01: continue

            stmt = "Asset" if code.startswith('1') else "Liab" if code.startswith('2') else "Equity" if code.startswith('8') else "Rev" if code.startswith('4') else "Exp" if code.startswith('5') else "Cost" if code.startswith('3') else "Other"
            indent = "  " * (node['level'] - 1)
            prefix = ""
            if node['level'] == 1: prefix = "[+] "
            elif node['level'] == 2: prefix = "  |- "
            elif node['level'] >= 3: prefix = "  " * (node['level']-1) + "  |_ "
            name = node['name'][:30].ljust(30)
            print(f"{indent}{prefix}{code.ljust(8)} | {name} | {bal:>15,.2f} | {stmt}")

        net_profit = total_rev - total_exp
        adjusted_eq = total_eq + net_profit
        total_liab_eq = total_liab + adjusted_eq

        print("-" * 80)
        print(f"Total Assets: {total_assets:,.2f}")
        print(f"Total Liabilities: {total_liab:,.2f}")
        print(f"Total Equity: {total_eq:,.2f}")
        print(f"Net Profit (Rev - Exp): {net_profit:,.2f}")
        print(f"Total Liab + Equity: {total_liab_eq:,.2f}")
        
        diff = abs(total_assets - total_liab_eq)
        if diff < 0.01:
            print("\n[OK] Balance Sheet is Balanced.")
        else:
            print(f"\n[WARN] Balance Sheet is NOT Balanced. Difference: {diff:,.2f}")

if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    print_balance_sheet(date_arg)
