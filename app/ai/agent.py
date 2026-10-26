# ============================================================
# AI Agent - مساعد المخازن
# ============================================================

import os
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from app.database import db

# ============================================================
# الإعدادات
# ============================================================
CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'chroma_db'
)

# ============================================================
# تحميل بيانات المشروع
# ============================================================
def load_project_data():
    """يجمع بيانات المشروع من الداتابيز"""
    data = []

    try:
        # الأصناف
        items = db.query("SELECT code, name_ar, name_en FROM items LIMIT 500")
        for i in items:
            data.append(f"الصنف: {i['code']} - {i['name_ar']}")

        # الموردين
        suppliers = db.query("SELECT code, name_ar, phone FROM suppliers LIMIT 500")
        for s in suppliers:
            data.append(f"المورد: {s['code']} - {s['name_ar']} - {s['phone'] or ''}")

        # العملاء
        customers = db.query("SELECT code, name_ar, phone FROM customers LIMIT 500")
        for c in customers:
            data.append(f"العميل: {c['code']} - {c['name_ar']} - {c['phone'] or ''}")

        # المستودعات
        warehouses = db.query("SELECT code, name_ar FROM warehouses LIMIT 100")
        for w in warehouses:
            data.append(f"المستودع: {w['code']} - {w['name_ar']}")

        # فواتير الشراء
        pinv = db.query("SELECT invoice_no, invoice_date, total_amount FROM purchase_invoices LIMIT 500")
        for inv in pinv:
            data.append(f"فاتورة شراء: {inv['invoice_no']} - التاريخ: {inv['invoice_date']} - الإجمالي: {inv['total_amount']}")

        # فواتير البيع
        sinv = db.query("SELECT invoice_no, invoice_date, total_amount FROM sales_invoices LIMIT 500")
        for inv in sinv:
            data.append(f"فاتورة بيع: {inv['invoice_no']} - التاريخ: {inv['invoice_date']} - الإجمالي: {inv['total_amount']}")

        # القيود
        journal = db.query("SELECT entry_no, entry_date, description, total_debit FROM journal_entries LIMIT 500")
        for j in journal:
            data.append(f"قيد: {j['entry_no']} - {j['entry_date']} - {j['description']} - {j['total_debit']}")

        # الجرد
        counts = db.query("SELECT count_no, count_date, status FROM inventory_counts LIMIT 500")
        for c in counts:
            data.append(f"جرد: {c['count_no']} - {c['count_date']} - {c['status']}")

    except Exception as e:
        print(f"Error loading data: {e}")

    return data


# ============================================================
# إنشاء Vector Store
# ============================================================
def create_vector_store():
    """ينشئ Vector Store من بيانات المشروع"""
    print("Loading project data...")
    data = load_project_data()
    print(f"Loaded {len(data)} records")

    if not data:
        return None

    # قسّم النصوص
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
    )
    docs = text_splitter.create_documents(data)

    # Embeddings
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Vector Store
    print("Creating vector store...")
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    print("Vector store created!")
    return vectorstore


# ============================================================
# تحميل Vector Store موجود
# ============================================================
def load_vector_store():
    """يحمل Vector Store موجود أو ينشئ واحد جديد"""
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        print("Loading existing vector store...")
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings
        )
    else:
        print("Creating new vector store...")
        vectorstore = create_vector_store()

    return vectorstore


# ============================================================
# إنشاء Chain
# ============================================================
def create_qa_chain():
    """ينشئ QA Chain"""
    vectorstore = load_vector_store()

    if not vectorstore:
        return None

    llm = OllamaLLM(model="llama3.2:3b")

    # Prompt مخصص
        # Prompt مخصص
    prompt_template = """أنت مساعد ذكي لمشروع مخازن.
مهمتك: تجاوب على أسئلة المستخدم بالعربي بناءً على البيانات اللي تحت.

قواعد مهمة:
1. استخدم البيانات اللي تحت بس.
2. لو البيانات فيها الإجابة، اكتبها مباشرة.
3. متقولش "مفيش بيانات كافية" إلا لو البيانات فعلاً فاضية.
4. لو السؤال عن حاجة مش موجودة، قول "معلش، مفيش بيانات عن [الحاجة]".
5. اكتب الإجابة بشكل واضح ومفصل.

البيانات المتاحة:
{context}

السؤال: {question}

الإجابة المباشرة:"""


    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 15}
        ),
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=False
    )

    return qa


# ============================================================
# دالة السؤال
# ============================================================
_qa_chain = None

def ask(question):
    """يسأل الـ AI ويرجع الإجابة"""
    global _qa_chain

    try:
        if _qa_chain is None:
            print("Initializing QA chain...")
            _qa_chain = create_qa_chain()

        if _qa_chain is None:
            return "معلش، الـ AI مش جاهز. حاول تاني."

        result = _qa_chain.invoke({"query": question})
        answer = result.get("result", "مفيش إجابة")

        return answer

    except Exception as e:
        print(f"AI Error: {e}")
        return f"حدث خطأ: {str(e)}"


# ============================================================
# إعادة بناء Vector Store
# ============================================================
def rebuild():
    """يعيد بناء Vector Store من البيانات الحديثة"""
    global _qa_chain

    # امسح القديم
    if os.path.exists(CHROMA_DIR):
        import shutil
        shutil.rmtree(CHROMA_DIR)

    # أنشئ جديد
    create_vector_store()
    _qa_chain = None

    return "تم إعادة البناء"