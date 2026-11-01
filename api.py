# api.py
from flask import Blueprint, jsonify, request

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/user', methods=['GET', 'POST'])  # Added 'POST' here
def get_mock_user():
    if request.method == 'POST':
        data = request.get_json()
        return jsonify({"message": "Received POST data successfully!", "data": data}), 200

    # Default GET response
    mock_user = {
        "id": 1,
        "username": "test_user",
        "email": "testuser@example.com",
        "role": "administrator",
        "is_active": True
    }
    return jsonify(mock_user), 200