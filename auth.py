"""
Authentication Logic for Security Backend
Handles JWT tokens and role-based access control
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    get_jwt_identity, verify_jwt_in_request, get_jwt
)
import models


def authenticate_user(username: str, password: str):
    """Authenticate user and return user dict if valid."""
    user = models.get_user_by_username(username)
    if user and user.get('is_active') and models.verify_password(password, user['password_hash']):
        return user
    return None


def generate_tokens(user_id: int, username: str, role: str):
    """Generate access and refresh tokens."""
    identity = str(user_id)
    additional_claims = {"username": username, "role": role}
    
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


def require_role(*allowed_roles):
    """Decorator to require specific roles for a route."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role', '')
            
            if user_role not in allowed_roles:
                return jsonify({"error": "Insufficient permissions", "required_roles": list(allowed_roles)}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user():
    """Get the current authenticated user from JWT."""
    try:
        user_id = int(get_jwt_identity())
        return models.get_user_by_id(user_id)
    except (ValueError, TypeError):
        return None


def get_current_user_id():
    """Get the current user ID from JWT."""
    try:
        return int(get_jwt_identity())
    except (ValueError, TypeError):
        return None


def get_current_role():
    """Get the current user's role from JWT."""
    claims = get_jwt()
    return claims.get('role', '')
