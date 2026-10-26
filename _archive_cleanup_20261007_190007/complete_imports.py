"""
إكمال نظام الاستيراد:
1. إنشاء جداول opening_balances + opening_stock
2. تحسين import_from_excel (mapping + dry_run)
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'database', 'warehouse.db')

# ============================================
# 1. إنشاء الجداول
# ============================================
print("=" * 60)
print("📦 1. إنشاء جداول الأرصدة الافتتاحية")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# جدول الأرصدة الافتتاحية
cur.execute("""
    CREATE TABLE IF NOT EXISTS opening_balances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_code TEXT NOT NULL,
        party_type TEXT,
        party_code TEXT,
        amount REAL NOT NULL,
        direction TEXT NOT NULL DEFAULT 'DEBIT',
        notes TEXT,
        is_posted INTEGER DEFAULT 0,
        journal_entry_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  ✅ opening_balances")

# جدول الكميات الافتتاحية
cur.execute("""
    CREATE TABLE IF NOT EXISTS opening_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT NOT NULL,
        warehouse_code TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit_cost REAL NOT NULL,
        total_cost REAL,
        batch_no TEXT,
        notes TEXT,
        is_posted INTEGER DEFAULT 0,
        journal_entry_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  ✅ opening_stock")

# فهارس
cur.execute("CREATE INDEX IF NOT EXISTS idx_ob_account ON opening_balances(account_code)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_ob_party ON opening_balances(party_type, party_code)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_os_item ON opening_stock(item_code, warehouse_code)")

conn.commit()
conn.close()

print("\n✅ تم إنشاء الجداول")


# ============================================
# 2. تحسين import_from_excel
# ============================================
print("\n" + "=" * 60)
print("🔧 2. تحسين import_from_excel")
print("=" * 60)

service_path = os.path.join(BASE, 'app', 'services', 'excel_service.py')

with open(service_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ابحث عن دالة import_from_excel واستبدلها
import re

# نلاقي الدالة كاملة
pattern = r"(    def import_from_excel\(self.*?)(    def get_import_template)"

match = re.search(pattern, content, re.DOTALL)

if match:
    old_func = match.group(1)
    
    new_func = '''    def import_from_excel(self, template_key, file_content, dry_run=False):
        """استيراد من Excel
        
        Args:
            template_key: اسم القالب
            file_content: محتوى الملف
            dry_run: لو True، يعرض النتائج بدون حفظ
        """
        if template_key not in self.IMPORT_TEMPLATES:
            return {'success': False, 'message': 'قالب غير موجود'}
        
        template = self.IMPORT_TEMPLATES[template_key]
        
        try:
            wb = load_workbook(io.BytesIO(file_content), data_only=True)
            ws = wb.active
        except Exception as e:
            return {'success': False, 'message': f'ملف Excel غير صالح: {e}'}
        
        # قراءة العناوين
        headers = []
        for col in ws[1]:
            headers.append(str(col.value).strip() if col.value else '')
        
        # خريطة الأعمدة
        col_map = {}
        for field, label in template['columns'].items():
            if label in headers:
                col_map[field] = headers.index(label)
        
        # التحقق من الأعمدة المطلوبة
        missing = []
        for field in template['required']:
            if field not in col_map:
                missing.append(template['columns'].get(field, field))
        
        if missing:
            return {
                'success': False,
                'message': f'أعمدة مطلوبة ناقصة: {", ".join(missing)}'
            }
        
        # قراءة الصفوف
        imported = 0
        updated = 0
        skipped = 0
        errors = []
        preview = []
        valid_rows = []
        
        # جلب mapping
        mappings = template.get('mapping', {})
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not any(row):
                continue
            
            data = {}
            for field, col_idx in col_map.items():
                value = row[col_idx] if col_idx < len(row) else None
                data[field] = value
            
            # تحقق من الحقول المطلوبة
            if not all(data.get(f) for f in template['required']):
                skipped += 1
                continue
            
            # تحويل mappings
            for field, (ref_table, ref_col, target_col) in mappings.items():
                if field in data and data[field]:
                    try:
                        ref_row = db.query(
                            f"SELECT {target_col} as val FROM {ref_table} WHERE {ref_col} = ?",
                            (data[field],), one=True
                        )
                        if ref_row:
                            data[field] = ref_row['val']
                        else:
                            errors.append(f'صف {row_idx}: {field} "{data[field]}" مش موجود')
                            continue
                    except Exception as e:
                        errors.append(f'صف {row_idx}: خطأ في {field}: {str(e)[:50]}')
            
            valid_rows.append((row_idx, data))
            
            # معاينة
            if dry_run and len(preview) < 10:
                preview.append({
                    'row': row_idx,
                    'data': {k: str(v)[:30] for k, v in data.items()}
                })
        
        if dry_run:
            return {
                'success': True,
                'data': {
                    'dry_run': True,
                    'total_rows': len(valid_rows),
                    'preview': preview,
                    'errors': errors[:20]
                }
            }
        
        # الحفظ الفعلي
        table = template['table']
        
        # التحقق إن الجدول موجود
        table_exists = db.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,), one=True
        )
        
        if not table_exists:
            return {
                'success': False,
                'message': f'الجدول {table} مش موجود في الداتابيز'
            }
        
        for row_idx, data in valid_rows:
            try:
                # تحقق إن موجود
                if 'code' in data and data['code']:
                    existing = db.query(
                        f"SELECT id FROM {table} WHERE code = ?",
                        (data['code'],),
                        one=True
                    )
                else:
                    existing = None
                
                if existing:
                    # تحديث
                    fields = [f"{k} = ?" for k in data.keys() if k != 'code']
                    values = [data[k] for k in data.keys() if k != 'code']
                    
                    if 'code' in data:
                        values.append(data['code'])
                        db.execute(
                            f"UPDATE {table} SET {', '.join(fields)} WHERE code = ?",
                            values
                        )
                    else:
                        id_field = 'id'
                        db.execute(
                            f"UPDATE {table} SET {', '.join(fields)} WHERE {id_field} = ?",
                            values
                        )
                    updated += 1
                else:
                    # إدخال
                    cols = ', '.join(data.keys())
                    placeholders = ', '.join(['?' for _ in data])
                    values = list(data.values())
                    
                    db.execute(
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                        values
                    )
                    imported += 1
            except Exception as e:
                errors.append(f'صف {row_idx}: {str(e)[:80]}')
        
        return {
            'success': True,
            'data': {
                'imported': imported,
                'updated': updated,
                'skipped': skipped,
                'total': imported + updated,
                'errors': errors[:20]
            }
        }
    
'''
    
    content = content[:match.start(1)] + new_func + content[match.start(2):]
    print("  ✅ تم تحديث import_from_excel")
else:
    print("  ⚠️ ما لقيتش import_from_excel")


# ============================================
# 3. تحديث API للاستيراد (dry_run)
# ============================================
print("\n" + "=" * 60)
print("🔧 3. تحديث APIs الاستيراد")
print("=" * 60)

# نضيف endpoint للمعاينة في export_routes.py

with open(service_path, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(service_path, doraise=True)
    print("  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"  ❌ {e}")

print("\n" + "=" * 60)
print("✅ تم!")
print("=" * 60)