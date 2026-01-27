"""
User Management Routes
Handles CRUD operations for users with role-based access
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

import auth
import models

users_bp = Blueprint('users', __name__, url_prefix='/api/users')


@users_bp.route('', methods=['GET'])
@jwt_required()
@auth.require_role('manager', 'admin')
def list_users():
    """List users. Managers see only their created users, admins see all."""
    role = auth.get_current_role()
    user_id = auth.get_current_user_id()
    
    if role == 'admin':
        users = models.list_users()
    else:
        users = models.list_users(created_by=user_id)
    
    return jsonify({"users": users, "total": len(users)})


@users_bp.route('/<int:target_id>', methods=['GET'])
@jwt_required()
@auth.require_role('manager', 'admin')
def get_user(target_id):
    """Get a specific user."""
    user_id = auth.get_current_user_id()
    
    # Check permission
    if auth.get_current_role() != 'admin' and not models.can_manage_user(user_id, target_id):
        return jsonify({"error": "Cannot access this user"}), 403
    
    user = models.get_user_by_id(target_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user['id'],
        "username": user['username'],
        "role": user['role'],
        "created_by": user['created_by'],
        "created_at": user['created_at'],
        "is_active": user['is_active']
    })


@users_bp.route('', methods=['POST'])
@jwt_required()
@auth.require_role('manager', 'admin')
def create_user():
    """Create a new user."""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'worker').lower()
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    # Validate role
    current_role = auth.get_current_role()
    allowed_roles = ['worker']
    if current_role == 'admin':
        allowed_roles = ['worker', 'manager']
    
    if role not in allowed_roles:
        return jsonify({"error": f"Cannot create user with role '{role}'"}), 403
    
    # Check if username exists
    if models.get_user_by_username(username):
        return jsonify({"error": "Username already exists"}), 409
    
    creator_id = auth.get_current_user_id()
    user_id = models.create_user(username, password, role, created_by=creator_id)
    
    return jsonify({
        "message": "User created successfully",
        "user": {
            "id": user_id,
            "username": username,
            "role": role,
            "created_by": creator_id
        }
    }), 201


@users_bp.route('/<int:target_id>', methods=['PUT'])
@jwt_required()
@auth.require_role('manager', 'admin')
def update_user(target_id):
    """Update a user."""
    user_id = auth.get_current_user_id()
    
    # Check permission
    if not models.can_manage_user(user_id, target_id):
        return jsonify({"error": "Cannot modify this user"}), 403
    
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    is_active = data.get('is_active')
    
    if username is not None:
        username = username.strip()
        existing = models.get_user_by_username(username)
        if existing and existing['id'] != target_id:
            return jsonify({"error": "Username already taken"}), 409
    
    success = models.update_user(target_id, username=username, password=password, is_active=is_active)
    
    if success:
        return jsonify({"message": "User updated successfully"})
    return jsonify({"error": "No changes made or user not found"}), 400


@users_bp.route('/<int:target_id>', methods=['DELETE'])
@jwt_required()
@auth.require_role('manager', 'admin')
def delete_user(target_id):
    """Terminate (soft delete) a user."""
    user_id = auth.get_current_user_id()
    
    # Cannot delete yourself
    if user_id == target_id:
        return jsonify({"error": "Cannot delete your own account"}), 400
    
    # Check permission
    if not models.can_manage_user(user_id, target_id):
        return jsonify({"error": "Cannot delete this user"}), 403
    
    success = models.delete_user(target_id)
    
    if success:
        return jsonify({"message": "User terminated successfully"})
    return jsonify({"error": "User not found"}), 404
