# backend/python_app/routes/user.py

from flask import Blueprint, jsonify, session
from services.models import User

user_bp = Blueprint('user', __name__)

@user_bp.route('/list', methods=['GET'])
def get_user_list():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Instead of getting all users, filter them by their role.
        # This string must EXACTLY match the role value in your database.
        users = User.query.filter_by(role='business process owner').all()
        
        user_list = [{'user_id': u.user_id, 'name': u.name} for u in users]
        return jsonify(user_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500