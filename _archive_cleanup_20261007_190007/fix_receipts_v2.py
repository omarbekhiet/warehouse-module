"""
إضافة cash_box للتحصيل - نسخة تعتمد على السطر المميز
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'app', 'services', 'payment_service.py')

print("=" * 60)
print("📝 إضافة cash_box للتحصيل")
print("=" * 60)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# البحث عن السطر المميز فقط
marker = "            receipt_id = cur.lastrowid"
insert_after = """            receipt_id = cur.lastrowid
            
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
                    ))"""

# التحقق إن مش مضاف
if "cash_box_id = data.get('cash_box_id')" in content and content.count("cash_box_id = data.get('cash_box_id')") >= 2:
    print("  ℹ️ مضاف بالفعل")
else:
    # ابحث عن السطر
    if marker in content:
        # استبدل السطر + السطر الفاضي بعده (بأي مسافات)
        import re
        pattern = re.compile(r"(\s*receipt_id = cur\.lastrowid\s*\n)")
        match = pattern.search(content)
        
        if match:
            # بعد receipt_id، ضيف الكود الجديد
            content = content[:match.end()] + insert_after.replace("            receipt_id = cur.lastrowid\n", "") + "\n" + content[match.end():]
            print("  ✅ تم إضافة cash_box للتحصيل")
        else:
            print("  ⚠️ مفيش match")
    else:
        print("  ⚠️ السطر مش موجود")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# التحقق
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("\n📊 التحقق:")
count = content.count("cash_box_id = data.get('cash_box_id')")
print(f"  cash_box في payment_service.py: {'✅' if count >= 2 else '❌'} ({count})")