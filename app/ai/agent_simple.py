import os
import ollama
from app.database import db

def load_project_data():
    """يجمع بيانات المشروع"""
    data = []

    try:
        # الأصناف
        items = db.query("SELECT code, name_ar FROM items LIMIT 100")
        for i in items:
            data.append(f"الصنف: {i['code']} - {i['name_ar']}")

        # الموردين
        suppliers = db.query("SELECT code, name_ar FROM suppliers LIMIT 100")
        for s in suppliers:
            data.append(f"المورد: {s['code']} - {s['name_ar']}")

        # العملاء
        customers = db.query("SELECT code, name_ar FROM customers LIMIT 100")
        for c in customers:
            data.append(f"العميل: {c['code']} - {c['name_ar']}")

        # المستودعات
        warehouses = db.query("SELECT code, name_ar FROM warehouses LIMIT 100")
        for w in warehouses:
            data.append(f"المستودع: {w['code']} - {w['name_ar']}")

        # الفواتير
        pinv = db.query("SELECT invoice_no, total_amount FROM purchase_invoices LIMIT 100")
        for inv in pinv:
            data.append(f"فاتورة شراء: {inv['invoice_no']} - {inv['total_amount']}")

        sinv = db.query("SELECT invoice_no, total_amount FROM sales_invoices LIMIT 100")
        for inv in sinv:
            data.append(f"فاتورة بيع: {inv['invoice_no']} - {inv['total_amount']}")

    except Exception as e:
        print(f"Error: {e}")

    return data


def ask(question):
    """يسأل الـ AI"""
    try:
        # اجمع البيانات
        data = load_project_data()
        context = "\n".join(data)

        # الـ Prompt
        prompt = f"""أنت مساعد مخازن. جاوب بالعربي بس.

البيانات:
{context}

السؤال: {question}

الإجابة:"""

        # اسأل Ollama
        response = ollama.chat(
            model='qwen2.5:1.5b',
            messages=[
                {'role': 'user', 'content': prompt}
            ],
            options={
                'temperature': 0.3,
                'num_predict': 200,
            }
        )

        return response['message']['content']

    except Exception as e:
        return f"حدث خطأ: {str(e)}"


def rebuild():
    return "تم"