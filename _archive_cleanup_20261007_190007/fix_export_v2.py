"""
تصدير Excel حتى لو مفيش بيانات — نسخة 2
- يستخدم LIMIT 0 لجلب أسماء الأعمدة
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SERVICE_PATH = os.path.join(BASE, 'app', 'services', 'excel_service.py')

print("=" * 60)
print("🔧 تعديل export_to_excel (v2)")
print("=" * 60)

with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ابحث عن دالة export_to_excel كاملة
pattern = r"(    def export_to_excel\(self.*?)(    def import_from_excel)"

match = re.search(pattern, content, re.DOTALL)

if not match:
    print("  ❌ ما لقيتش الدالة")
    exit(1)

old_func = match.group(1)

new_func = '''    def export_to_excel(self, template_key, filters=None):
        """تصدير بيانات لـ Excel — حتى لو مفيش بيانات"""
        if template_key not in self.EXPORT_TEMPLATES:
            return None, 'قالب غير موجود'

        template = self.EXPORT_TEMPLATES[template_key]
        sql = template['sql']

        # جلب البيانات
        try:
            rows = db.query(sql)
        except Exception as e:
            return None, str(e)

        # إنشاء Excel
        wb = Workbook()
        ws = wb.active
        ws.title = template['name'][:31]  # Excel limit
        ws.sheet_view.rightToLeft = True

        # الألوان
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True, size=12)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # الحصول على أسماء الأعمدة
        if rows and len(rows) > 0:
            columns = list(rows[0].keys())
        else:
            # استخدام استعلام LIMIT 0 لجلب الأعمدة
            try:
                test_sql = f"SELECT * FROM ({sql}) LIMIT 0"
                test_rows = db.query(test_sql)
                if test_rows and len(test_rows) > 0:
                    columns = list(test_rows[0].keys())
                else:
                    columns = template.get('columns', ['لا توجد بيانات'])
            except:
                columns = template.get('columns', ['لا توجد بيانات'])

        # العناوين
        for col_idx, col_name in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

        # البيانات (لو موجودة)
        if rows and len(rows) > 0:
            for row_idx, row in enumerate(rows, 2):
                for col_idx, col_name in enumerate(columns, 1):
                    value = row.get(col_name)
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = border
                    cell.alignment = Alignment(horizontal='right', vertical='center')
        else:
            # إضافة صف يوضح إن مفيش بيانات
            cell = ws.cell(row=2, column=1, value='لا توجد بيانات')
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.font = Font(italic=True, color='808080')

        # عرض الأعمدة
        for col_idx, col_name in enumerate(columns, 1):
            max_length = len(str(col_name))
            if rows and len(rows) > 0:
                for row in rows[:100]:
                    val = str(row.get(col_name, ''))
                    if len(val) > max_length:
                        max_length = len(val)
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max(max_length + 4, 12), 50)

        # حفظ
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return output, None

'''

content = content[:match.start(1)] + new_func + content[match.start(2):]

with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

# اختبار
import py_compile
try:
    py_compile.compile(SERVICE_PATH, doraise=True)
    print("  ✅ الملف سليم")
except py_compile.PyCompileError as e:
    print(f"  ❌ {e}")