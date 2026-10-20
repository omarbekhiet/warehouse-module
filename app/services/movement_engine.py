"""
محرك القيود التلقائي لحركات المخازن
يولّد القيود المحاسبية من (المستودع + نوع الحركة + القيمة)
"""
from app.database import db


class MovementEngine:
    """محرك توليد القيود المحاسبية"""

    # ============================================================
    # الدوال الأساسية
    # ============================================================

    def get_warehouse(self, warehouse_id):
        """جيب بيانات المستودع"""
        return db.query(
            "SELECT id, code, name_ar, account_code FROM warehouses WHERE id=?",
            (warehouse_id,), one=True
        )

    def get_movement(self, movement_code):
        """جيب نوع الحركة بالكود"""
        return db.query(
            "SELECT * FROM stock_movements WHERE code=? AND is_active=1",
            (movement_code,), one=True
        )

    def get_account_name(self, account_code):
        """جيب اسم الحساب"""
        r = db.query(
            "SELECT name_ar FROM accounts WHERE code=?",
            (account_code,), one=True
        )
        return r['name_ar'] if r else account_code

    # ============================================================
    # استبدال الحسابات المتغيرة
    # ============================================================

    def resolve_side(self, side, warehouse, warehouse_to=None, warehouse_from=None):
        """
        استبدال الحسابات المتغيرة بالحسابات الفعلية
        
        Args:
            side: قيمة الحقل (WAREHOUSE، WAREHOUSE_TO، WAREHOUSE_FROM، أو كود حساب)
            warehouse: المستودع الأساسي
            warehouse_to: المستودع المستلم (في التحويل)
            warehouse_from: المستودع المُسلِّم (في التحويل)
        
        Returns:
            كود الحساب الفعلي أو None
        """
        if not side:
            return None

        # WAREHOUSE → حساب المستودع الأساسي
        if side == 'WAREHOUSE':
            return warehouse['account_code'] if warehouse else None

        # WAREHOUSE_TO → حساب المستودع المستلم
        if side == 'WAREHOUSE_TO':
            return warehouse_to['account_code'] if warehouse_to else None

        # WAREHOUSE_FROM → حساب المستودع المُسلِّم
        if side == 'WAREHOUSE_FROM':
            return warehouse_from['account_code'] if warehouse_from else None

        # كود حساب عادي
        return side

    # ============================================================
    # توليد القيد
    # ============================================================

    def generate_entry(self, warehouse_id, movement_code, amount,
                       warehouse_to_id=None, warehouse_from_id=None,
                       reference=None, notes=None):
        """
        توليد القيد المحاسبي
        
        Args:
            warehouse_id: معرف المستودع
            movement_code: كود نوع الحركة
            amount: المبلغ الإجمالي
            warehouse_to_id: معرف المستودع المستلم (للتحويل)
            warehouse_from_id: معرف المستودع المُسلِّم (للتحويل)
            reference: رقم المرجع
            notes: ملاحظات
        
        Returns:
            dict: القيد كامل
        """
        # 1. جيب المستودع
        wh = self.get_warehouse(warehouse_id)
        if not wh:
            return {'success': False, 'message': 'المستودع غير موجود'}

        # 2. جيب نوع الحركة
        mv = self.get_movement(movement_code)
        if not mv:
            return {'success': False, 'message': f'نوع الحركة {movement_code} غير موجود'}

        # 3. جيب المستودعات الإضافية (للتحويل)
        wh_to = self.get_warehouse(warehouse_to_id) if warehouse_to_id else None
        wh_from = self.get_warehouse(warehouse_from_id) if warehouse_from_id else None

        # 4. استبدل الحسابات
        debit_acc = self.resolve_side(mv['debit_side'], wh, wh_to, wh_from)
        credit_acc = self.resolve_side(mv['credit_side'], wh, wh_to, wh_from)
        tax_acc = self.resolve_side(mv['tax_side'], wh, wh_to, wh_from) if mv['tax_side'] else None
        extra_acc = self.resolve_side(mv['extra_side'], wh, wh_to, wh_from) if mv['extra_side'] else None

        # 5. تحقق من الحسابات
        if not debit_acc or not credit_acc:
            return {'success': False, 'message': 'لا يمكن تحديد الحسابات'}

        # 6. ابنِ القيد
        lines = []

        # الطرف المدين
        lines.append({
            'account': debit_acc,
            'account_name': self.get_account_name(debit_acc),
            'debit': round(amount, 2),
            'credit': 0,
            'description': f"{mv['name_ar']} - {wh['name_ar']}"
        })

        # الطرف الدائن
        lines.append({
            'account': credit_acc,
            'account_name': self.get_account_name(credit_acc),
            'debit': 0,
            'credit': round(amount, 2),
            'description': f"{mv['name_ar']} - {wh['name_ar']}"
        })

        # حساب الضريبة (اختياري) — بس حالياً بنضيفها كسطر منفصل لو موجودة
        if tax_acc:
            lines.append({
                'account': tax_acc,
                'account_name': self.get_account_name(tax_acc),
                'debit': 0,
                'credit': 0,
                'description': f"ضريبة - {mv['name_ar']}",
                'note': 'حساب اختياري — يُستخدم عند الحاجة'
            })

        # حساب إضافي
        if extra_acc:
            lines.append({
                'account': extra_acc,
                'account_name': self.get_account_name(extra_acc),
                'debit': 0,
                'credit': 0,
                'description': f"حساب إضافي - {mv['name_ar']}",
                'note': 'حساب اختياري'
            })

        # 7. الإجماليات
        total_debit = sum(l['debit'] for l in lines)
        total_credit = sum(l['credit'] for l in lines)

        # 8. تحقق من التوازن
        if abs(total_debit - total_credit) > 0.01:
            return {
                'success': False,
                'message': f'القيد غير متوازن: مدين={total_debit}, دائن={total_credit}'
            }

        return {
            'success': True,
            'lines': lines,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'movement': dict(mv),
            'warehouse': dict(wh),
            'reference': reference,
            'notes': notes
        }

    # ============================================================
    # معاينة القيد (بدون حفظ)
    # ============================================================

    def preview(self, **kwargs):
        """معاينة القيد — نفس دالة generate_entry"""
        return self.generate_entry(**kwargs)


# نسخة جاهزة للاستيراد
movement_engine = MovementEngine()