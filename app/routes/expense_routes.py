"""
مسارات صرف النثريات
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe
from app.services.expense_service import expense_service

exp_bp = Blueprint('expenses', __name__)


# =========================================
# Categories
# =========================================

@exp_bp.route('/categories/', methods=['GET'])
def list_categories():
    rows = expense_service.list_categories()
    return jsonify({'success': True, 'data': json_safe(rows)})


@exp_bp.route('/categories/', methods=['POST'])
def create_category():
    d = request.get_json() or {}
    result = expense_service.create_category(d)
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@exp_bp.route('/categories/<int:cid>', methods=['PUT'])
def update_category(cid):
    d = request.get_json() or {}
    fields, values = [], []
    for k in ['name_ar', 'name_en', 'account_code', 'parent_id', 'is_active', 'notes']:
        if k in d:
            fields.append(f"{k} = ?")
            values.append(d[k])
    if not fields:
        return jsonify({'success': False, 'message': 'لا توجد بيانات'}), 400
    values.append(cid)
    db.execute(f"UPDATE expense_categories SET {', '.join(fields)} WHERE id = ?", values)
    return jsonify({'success': True})


@exp_bp.route('/categories/<int:cid>', methods=['DELETE'])
def delete_category(cid):
    used = db.query("SELECT COUNT(*) as n FROM petty_cash_expenses WHERE category_id=?", (cid,), one=True)
    if used and used['n'] > 0:
        return jsonify({'success': False, 'message': 'التصنيف مستخدم في مصروفات'}), 400
    db.execute("DELETE FROM expense_categories WHERE id=?", (cid,))
    return jsonify({'success': True})


# =========================================
# Expenses
# =========================================

@exp_bp.route('/expenses/', methods=['GET'])
def list_expenses():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    category_id = request.args.get('category_id', type=int)
    cash_box_id = request.args.get('cash_box_id', type=int)
    limit = request.args.get('limit', 200, type=int)
    
    rows = expense_service.list_expenses(date_from, date_to, category_id, cash_box_id, limit)
    return jsonify({'success': True, 'data': json_safe(rows)})


@exp_bp.route('/expenses/', methods=['POST'])
def create_expense():
    d = request.get_json() or {}
    result = expense_service.create_expense(d, user_id=1)
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@exp_bp.route('/expenses/<int:eid>', methods=['GET'])
def get_expense(eid):
    exp = expense_service.get_expense(eid)
    if not exp:
        return jsonify({'success': False, 'message': 'غير موجود'}), 404
    return jsonify({'success': True, 'data': json_safe(exp)})


@exp_bp.route('/expenses/<int:eid>', methods=['DELETE'])
def delete_expense(eid):
    result = expense_service.delete_expense(eid)
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@exp_bp.route('/stats', methods=['GET'])
def get_stats():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    stats = expense_service.get_stats(date_from, date_to)
    return jsonify({'success': True, 'data': stats})