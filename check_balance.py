# -*- coding: utf-8 -*-
import os
import sys
import sqlite3

# محاولة استيراد اتصال قاعدة البيانات من مشروعك
try:
    from app.database import db
except ImportError:
    print("❌ لم يتم العثور على وحدة app.database. تأكد من تشغيل السكريبت من داخل مجلد المشروع.")
    sys.exit(1)

def print_balance_sheet(as_of_date=None):
    print("=" * 80)
    print(f"📊 مراجعة الميزانية العمومية - حتى تاريخ: {as_of_date or 'كل الفترات'}")
    print("=" * 80)
    
    try:
        with db.get_connection() as conn:
            # 1. جلب الحسابات
            accounts = conn.execute("SELECT code, name_ar, parent_code, COALESCE(level, 'L1') as level FROM accounts ORDER BY code").fetchall()
            
            acc_dict = {}
            for a in accounts:
                code = str(a['code']).strip()
                lvl_str = str(a['level'] or 'L1').replace('L', '')
                try: lvl = int(lvl_str)
                except: lvl = 1
                
                acc_dict[code] = {
                    'code': code, 
                    'name': a['name_ar'],
                    'parent': str(a['parent_code']).strip() if a['parent_code'] else None,
                    'level': lvl, 
                    'balance': 0.0
                }

            # 2. جلب الأرصدة
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

            # 3. التجميع للأعلى (Roll-up)
            sorted_codes = sorted(acc_dict.keys(), key=lambda x: acc_dict[x]['level'], reverse=True)
            for code in sorted_codes:
                node = acc_dict[code]
                parent = node['parent']
                if parent and parent in acc_dict:
                    acc_dict[parent]['balance'] += node['balance']

            # 4. الطباعة الشجرية
            total_assets = 0.0
            total_liab = 0.0
            total_eq = 0.0
            other = 0.0
            parent_codes = set(n['parent'] for n in acc_dict.values() if n['parent'])

            for code in sorted(acc_dict.keys()):
                node = acc_dict[code]
                bal = node['balance']
                
                # تصنيف المجاميع
                is_leaf = code not in parent_codes
                if is_leaf:
                    if code.startswith('1'): total_assets += bal
                    elif code.startswith('2'): total_liab += abs(bal)
                    elif code.startswith('8'): total_eq += bal
                    else: other += (abs(bal) if code.startswith('4') else bal)

                if abs(bal) < 0.01: continue # تخطي الحسابات الصفرية

                # تحديد النوع
                stmt = "أصول" if code.startswith('1') else "التزام" if code.startswith('2') else "حقوق" if code.startswith('8') else "إيراد" if code.startswith('4') else "مصروف" if code.startswith('5') else "أخرى"
                
                # التنسيق الشجري
                indent = "  " * (node['level'] - 1)
                prefix = "├── " if node['level'] > 1 else ""
                if node['level'] == 1: prefix = "📁 "
                elif node['level'] == 2: prefix = "  ┣━ "
                elif node['level'] >= 3: prefix = "  " * (node['level']-1) + "  ┗━ "

                # الألوان (تنسيق ANSI)
                color = "\033[0m" # Reset
                if code.startswith('1'): color = "\033[94m" # Blue
                elif code.startswith('2'): color = "\033[91m" # Red
                elif code.startswith('8'): color = "\033[92m" # Green
                elif code.startswith('4'): color = "\033[96m" # Cyan
                elif code.startswith('5'): color = "\033[93m" # Yellow

                # طباعة السطر
                name = node['name'][:30].ljust(30)
                print(f"{color}{indent}{prefix}{code.ljust(8)} | {name} | {bal:>15,.2f} | {stmt}\033[0m")

            print("-" * 80)
            print(f"إجمالي الأصول: \033[94m{total_assets:,.2f}\033[0m")
            print(f"إجمالي الالتزامات: \033[91m{total_liab:,.2f}\033[0m")
            print(f"إجمالي حقوق الملكية (الأساسية): \033[92m{total_eq:,.2f}\033[0m")
            print(f"صافي الإيرادات/المصروفات (تسويات): \033[93m{other:,.2f}\033[0m")
            print(f"\nإجمالي الالتزامات + حقوق الملكية المعدلة: {total_liab + total_eq + other:,.2f}")
            
            diff = abs(total_assets - (total_liab + total_eq + other))
            if diff < 0.01:
                print("\n\033[92m✅ الميزانية متوازنة تماماً.\033[0m")
            else:
                print(f"\n\033[91m⚠️ الميزانية غير متوازنة. الفرق: {diff:,.2f}\033[0m")

    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

if __name__ == "__main__":
    # يمكنك تغيير التاريخ هنا أو تمريره كوسيط
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    print_balance_sheet(date_arg)
