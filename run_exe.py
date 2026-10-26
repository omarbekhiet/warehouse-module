"""
نقطة تشغيل للـ EXE
- يشغل Flask
- يفتح المتصفح تلقائياً
- يخلي السيرفر شغال
"""
import os
import sys
import webbrowser
import threading
import time

# المسار
if getattr(sys, 'frozen', False):
    # EXE
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
    os.chdir(BASE_DIR)
else:
    # عادي
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

# ضيف مجلد المشروع للمسار
sys.path.insert(0, BUNDLE_DIR)
sys.path.insert(0, BASE_DIR)

# استورد التطبيق
from app import create_app
from app.config import Config

# ⚠️ عدّل مسار الداتابيز
# لو الداتابيز في نفس المجلد
db_path = os.path.join(BASE_DIR, 'database', 'warehouse.db')
if not os.path.exists(db_path):
    # أنشئ المجلد
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # انسخ الداتابيز من الـ bundle (لو موجودة)
    source_db = os.path.join(BUNDLE_DIR, 'database', 'warehouse.db')
    if os.path.exists(source_db):
        import shutil
        shutil.copy(source_db, db_path)

# حدّث config
Config.DATABASE_PATH = db_path

# شغل Flask
app = create_app()

def open_browser():
    """فتح المتصفح بعد ثانيتين"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

def main():
    print("=" * 60)
    print("🏭 Warehouse Module")
    print("=" * 60)
    print()
    print(f"📁 Working Dir: {BASE_DIR}")
    print(f"📁 Bundle Dir: {BUNDLE_DIR}")
    print(f"💾 Database: {db_path}")
    print()
    print("🌐 السيرفر شغال على: http://localhost:5000")
    print("🌐 السيرفر شغال على: http://127.0.0.1:5000")
    print()
    print("⚠️ اضغط Ctrl+C للإغلاق")
    print("=" * 60)
    print()
    
    # افتح المتصفح في thread منفصل
    threading.Thread(target=open_browser, daemon=True).start()
    
    # شغل السيرفر
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ تم الإغلاق")
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        input("\nاضغط Enter للإغلاق...")