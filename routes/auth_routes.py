"""
Authentication Routes
Handles login, logout, token refresh
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

import auth
import models

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens."""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    user = auth.authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    
    tokens = auth.generate_tokens(user['id'], user['username'], user['role'])
    
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "role": user['role']
        },
        **tokens
    })


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token."""
    user_id = int(get_jwt_identity())
    user = models.get_user_by_id(user_id)
    
    if not user or not user.get('is_active'):
        return jsonify({"error": "User not found or inactive"}), 401
    
    tokens = auth.generate_tokens(user['id'], user['username'], user['role'])
    return jsonify(tokens)


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Get current user info."""
    user = auth.get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user['id'],
        "username": user['username'],
        "role": user['role'],
        "created_at": user['created_at']
    })


@auth_bp.route('/validate', methods=['POST'])
@jwt_required()
def validate():
    """Validate token and return user info - for main app integration."""
    user = auth.get_current_user()
    if not user or not user.get('is_active'):
        return jsonify({"valid": False}), 401
    
    return jsonify({
        "valid": True,
        "user_id": user['id'],
        "username": user['username'],
        "role": user['role']
    })
