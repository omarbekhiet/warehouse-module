from flask import Blueprint, request, jsonify
from app.database import db
from app.utils import json_safe
from app.services.settlement_service import settlement_service

settle_bp = Blueprint('settlements', __name__)


# ============ Cheque Settlements ============

@settle_bp.route('/cheques/', methods=['GET'])
def list_cheques():
    status = request.args.get('status')
    rows = settlement_service.list_cheque_settlements(status)
    return jsonify({'success': True, 'data': json_safe(rows)})


@settle_bp.route('/cheques/pending/', methods=['GET'])
def pending_cheques():
    direction = request.args.get('direction')
    rows = settlement_service.list_pending_cheques(direction)
    return jsonify({'success': True, 'data': json_safe(rows)})


@settle_bp.route('/cheques/', methods=['POST'])
def create_cheque():
    d = request.get_json() or {}
    required = ['settlement_date', 'settlement_type', 'source_type', 'source_id', 'amount']
    for f in required:
        if not d.get(f):
            return jsonify({'success': False, 'message': f'{f} مطلوب'}), 400
    
    result = settlement_service.create_cheque_settlement(d)
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@settle_bp.route('/cheques/<int:cid>/clear', methods=['POST'])
def clear_cheque(cid):
    d = request.get_json() or {}
    result = settlement_service.clear_cheque(
        cid, d.get('cleared_date'), d.get('notes')
    )
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@settle_bp.route('/cheques/<int:cid>/bounce', methods=['POST'])
def bounce_cheque(cid):
    d = request.get_json() or {}
    result = settlement_service.bounce_cheque(
        cid, d.get('bounce_date'), d.get('reason')
    )
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


# ============ Card Settlements ============

@settle_bp.route('/cards/', methods=['GET'])
def list_cards():
    rows = settlement_service.list_card_settlements()
    return jsonify({'success': True, 'data': json_safe(rows)})


@settle_bp.route('/cards/pending/', methods=['GET'])
def pending_cards():
    rows = settlement_service.list_pending_cards()
    return jsonify({'success': True, 'data': json_safe(rows)})


@settle_bp.route('/cards/', methods=['POST'])
def create_card():
    d = request.get_json() or {}
    required = ['settlement_date', 'source_type', 'source_id', 'gross_amount']
    for f in required:
        if not d.get(f):
            return jsonify({'success': False, 'message': f'{f} مطلوب'}), 400
    
    result = settlement_service.create_card_settlement(d)
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400