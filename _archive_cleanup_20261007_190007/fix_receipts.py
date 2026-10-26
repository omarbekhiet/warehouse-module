"""
إضافة cash_box للتحصيل فقط
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'services', 'payment_service.py')

print("=" * 60)
print("📝 إضافة cash_box للتحصيل")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# النمط الفعلي بالظبط
old = """            receipt_id = cur.lastrowid

            # 4. القيد (فحص auto_journal_receipts)"""

new = """            receipt_id = cur.lastrowid
            
            # ✅ تسجيل حركة الخزينة (تحصيل)
            cash_box_id = data.get('cash_box_id')
            cash_box_type = data.get('cash_box_type', 'CASH_BOX')
            
            if cash_box_id:
                table_map = {'CASH_BOX': 'cash_boxes', 'BANK': 'banks', 'CARD': 'payment_cards'}
                box_table = table_map.get(cash_box_type, 'cash_boxes')
                
                cur.execute(f"SELECT * FROM {box_table} WHERE id=?", (cash_box_id,))
                box = cur.fetchone()
                
                if box:
                    current_bal = float(box['current_balance'] or 0)
                    new_bal = current_bal + float(data['amount'])
                    
                    cur.execute(f"UPDATE {box_table} SET current_balance=? WHERE id=?", (new_bal, cash_box_id))
                    
                    cur.execute(\"\"\"
                        INSERT INTO cash_box_transactions 
                        (box_id, box_type, txn_type, txn_date, amount, balance_after,
                         reference_no, description, created_by)
                        VALUES (?, ?, 'DEPOSIT', ?, ?, ?, ?, ?, ?)
                    \"\"\", (
                        cash_box_id, cash_box_type, data['receipt_date'],
                        float(data['amount']), new_bal, receipt_no,
                        f"تحصيل من عميل - {receipt_no}", user_id
                    ))

            # 4. القيد (فحص auto_journal_receipts)"""

if old in content:
    content = content.replace(old, new)
    print("  ✅ تم إضافة cash_box للتحصيل")
elif "cash_box_id = data.get('cash_box_id')" in content:
    # ممكن يكون مضاف بالفعل
    count = content.count("cash_box_id = data.get('cash_box_id')")
    if count >= 2:
        print("  ℹ️ مضاف بالفعل (count = {})".format(count))
    else:
        print("  ⚠️ مش موجود — محتاج أشوف الكود")
else:
    print("  ⚠️ النمط مش موجود")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n📊 التحقق:")
count = content.count("cash_box_id = data.get('cash_box_id')")
print(f"  cash_box في payment_service.py: {'✅' if count >= 2 else '❌'} ({count})")