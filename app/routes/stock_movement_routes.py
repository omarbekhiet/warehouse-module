from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe

mv_bp = Blueprint('stock_movements', __name__)


@mv_bp.route('/', methods=['GET'])
def list_movements():
    rows = db.query("""
        SELECT * FROM stock_movements
        ORDER BY 
            CASE movement_type 
                WHEN 'ADD' THEN 1 
                WHEN 'SUBTRACT' THEN 2 
                WHEN 'TRANSFER' THEN 3 
                WHEN 'ADJUST' THEN 4 
                ELSE 5 
            END,
            code
    """)
    return jsonify({'success': True, 'data': json_safe(rows)})


@mv_bp.route('/<int:mid>', methods=['GET'])
def get_movement(mid):
    row = db.query("SELECT * FROM stock_movements WHERE id=?", (mid,), one=True)
    if not row:
        return jsonify({'success': False, 'message': 'الحركة غير موجودة'}), 404
    return jsonify({'success': True, 'data': json_safe(row)})


@mv_bp.route('/', methods=['POST'])
def create_movement():
    d = request.get_json() or {}
    
    if not d.get('code'):
        return jsonify({'success': False, 'message': 'الكود مطلوب'}), 400
    if not d.get('name_ar'):
        return jsonify({'success': False, 'message': 'الاسم مطلوب'}), 400
    if not d.get('movement_type'):
        return jsonify({'success': False, 'message': 'نوع العملية مطلوب'}), 400
    if not d.get('debit_side') or not d.get('credit_side'):
        return jsonify({'success': False, 'message': 'الطرفان المدين والدائن مطلوبان'}), 400
    
    # التحقق من عدم تكرار الكود
    existing = db.query("SELECT id FROM stock_movements WHERE code=?", (d['code'],), one=True)
    if existing:
        return jsonify({'success': False, 'message': f"الكود {d['code']} مستخدم بالفعل"}), 400
    
    try:
        mid = db.execute("""
            INSERT INTO stock_movements
            (code, name_ar, name_en, movement_type,
             debit_side, credit_side, tax_side, extra_side,
             affects_quantity, affects_value, requires_reference,
             notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d['code'], d['name_ar'], d.get('name_en'),
            d['movement_type'],
            d['debit_side'], d['credit_side'],
            d.get('tax_side'), d.get('extra_side'),
            1 if d.get('affects_quantity', True) else 0,
            1 if d.get('affects_value', True) else 0,
            1 if d.get('requires_reference', False) else 0,
            d.get('notes'),
            1 if d.get('is_active', True) else 0
        ))
        return jsonify({'success': True, 'data': {'id': mid}}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@mv_bp.route('/<int:mid>', methods=['PUT'])
def update_movement(mid):
    d = request.get_json() or {}
    
    fields = ['name_ar', 'name_en', 'movement_type',
              'debit_side', 'credit_side', 'tax_side', 'extra_side',
              'affects_quantity', 'affects_value', 'requires_reference',
              'notes', 'is_active']
    
    updates, values = [], []
    for k in fields:
        if k in d:
            updates.append(f"{k}=?")
            v = d[k]
            if k in ('affects_quantity', 'affects_value', 'requires_reference', 'is_active'):
                v = 1 if v else 0
            values.append(v)
    
    if not updates:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    
    values.append(mid)
    db.execute(f"UPDATE stock_movements SET {','.join(updates)} WHERE id=?", values)
    return jsonify({'success': True, 'message': 'تم التحديث'})


@mv_bp.route('/<int:mid>', methods=['DELETE'])
def delete_movement(mid):
    # تحقق إن مفيش حركات فعلية مستخدمة
    try:
        used = db.query(
            "SELECT COUNT(*) as n FROM stock_transactions WHERE movement_type_id=?",
            (mid,), one=True
        )
        if used and used['n'] > 0:
            return jsonify({'success': False, 'message': 'لا يمكن حذف نوع مستخدم في حركات فعلية'}), 400
    except:
        pass
    
    db.execute("DELETE FROM stock_movements WHERE id=?", (mid,))
    return jsonify({'success': True})

from app.services.movement_engine import movement_engine


@mv_bp.route('/preview-entry', methods=['POST'])
def preview_entry():
    """معاينة القيد المحاسبي قبل الحفظ"""
    d = request.get_json() or {}
    
    # البيانات المطلوبة
    warehouse_id = d.get('warehouse_id')
    movement_code = d.get('movement_code')
    amount = d.get('amount')
    
    if not warehouse_id:
        return jsonify({'success': False, 'message': 'المستودع مطلوب'}), 400
    if not movement_code:
        return jsonify({'success': False, 'message': 'نوع الحركة مطلوب'}), 400
    if not amount or float(amount) <= 0:
        return jsonify({'success': False, 'message': 'المبلغ مطلوب'}), 400
    
    try:
        result = movement_engine.preview(
            warehouse_id=int(warehouse_id),
            movement_code=movement_code,
            amount=float(amount),
            warehouse_to_id=d.get('warehouse_to_id'),
            warehouse_from_id=d.get('warehouse_from_id'),
            reference=d.get('reference'),
            notes=d.get('notes')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@mv_bp.route('/test-entry', methods=['POST'])
def test_entry():
    """اختبار سريع للقيد"""
    d = request.get_json() or {}
    try:
        result = movement_engine.generate_entry(
            warehouse_id=int(d.get('warehouse_id', 1)),
            movement_code=d.get('movement_code', 'RECV'),
            amount=float(d.get('amount', 1000)),
            reference=d.get('reference', 'TEST-001'),
            notes=d.get('notes', 'اختبار')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500