from flask import Blueprint, request, jsonify
from app.ai.agent_simple import ask, rebuild

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/ask', methods=['POST'])
def ai_ask():
    """يسأل الـ AI"""
    d = request.get_json() or {}
    question = d.get('question', '').strip()

    if not question:
        return jsonify({'success': False, 'message': 'السؤال مطلوب'}), 400

    try:
        answer = ask(question)
        return jsonify({'success': True, 'data': {'answer': answer}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@ai_bp.route('/rebuild', methods=['POST'])
def ai_rebuild():
    """يعيد بناء Vector Store"""
    try:
        msg = rebuild()
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500