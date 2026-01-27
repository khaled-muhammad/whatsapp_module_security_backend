"""
Data Routes
Handles contacts and message logs APIs
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

import auth
import models

data_bp = Blueprint('data', __name__, url_prefix='/api')


# ============================================
# Contacts API
# ============================================

@data_bp.route('/contacts', methods=['GET'])
@jwt_required()
def list_contacts():
    """List all contacts with pagination and search."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    search = request.args.get('search', '')
    
    # Cap limit to prevent abuse
    limit = min(limit, 500)
    
    contacts = models.list_contacts(limit=limit, offset=offset, search=search if search else None)
    total = models.count_contacts()
    
    return jsonify({
        "contacts": contacts,
        "total": total,
        "limit": limit,
        "offset": offset
    })


@data_bp.route('/contacts/sync', methods=['POST'])
@jwt_required()
def sync_contacts():
    """Sync contacts from scraped data."""
    data = request.get_json() or {}
    contacts = data.get('contacts', [])
    source_group = data.get('source_group', 'Unknown')
    
    if not contacts:
        return jsonify({"error": "No contacts provided"}), 400
    
    user_id = auth.get_current_user_id()
    count = models.bulk_add_contacts(contacts, source_group, user_id)
    
    return jsonify({
        "message": f"Synced {count} contacts",
        "synced": count
    })


@data_bp.route('/contacts/stats', methods=['GET'])
@jwt_required()
def contacts_stats():
    """Get contact statistics."""
    total = models.count_contacts()
    return jsonify({
        "total_contacts": total
    })


# ============================================
# Messages API
# ============================================

@data_bp.route('/messages', methods=['GET'])
@jwt_required()
def list_messages():
    """List message logs with pagination."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    sender_id = request.args.get('sender_id', type=int)
    
    # Cap limit
    limit = min(limit, 500)
    
    # Workers can only see their own messages
    current_role = auth.get_current_role()
    current_id = auth.get_current_user_id()
    
    if current_role == 'worker':
        sender_id = current_id
    
    messages = models.list_messages(limit=limit, offset=offset, sender_id=sender_id)
    total = models.count_messages(sender_id=sender_id if current_role == 'worker' else None)
    
    return jsonify({
        "messages": messages,
        "total": total,
        "limit": limit,
        "offset": offset
    })


@data_bp.route('/messages/log', methods=['POST'])
@jwt_required()
def log_message():
    """Log a sent message."""
    data = request.get_json() or {}
    recipient_phone = data.get('recipient_phone', '').strip()
    message_content = data.get('message_content', '')
    attachment_path = data.get('attachment_path')
    template_used = data.get('template_used')
    status = data.get('status', 'sent')
    
    if not recipient_phone:
        return jsonify({"error": "Recipient phone required"}), 400
    
    sender_id = auth.get_current_user_id()
    log_id = models.log_message(
        sender_id=sender_id,
        recipient_phone=recipient_phone,
        message_content=message_content,
        attachment_path=attachment_path,
        template_used=template_used,
        status=status
    )
    
    return jsonify({
        "message": "Message logged",
        "log_id": log_id
    }), 201


@data_bp.route('/messages/bulk-log', methods=['POST'])
@jwt_required()
def bulk_log_messages():
    """Log multiple messages at once."""
    data = request.get_json() or {}
    messages = data.get('messages', [])
    
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
    
    sender_id = auth.get_current_user_id()
    count = 0
    
    for msg in messages:
        if msg.get('recipient_phone'):
            models.log_message(
                sender_id=sender_id,
                recipient_phone=msg.get('recipient_phone', ''),
                message_content=msg.get('message_content', ''),
                attachment_path=msg.get('attachment_path'),
                template_used=msg.get('template_used'),
                status=msg.get('status', 'sent')
            )
            count += 1
    
    return jsonify({
        "message": f"Logged {count} messages",
        "logged": count
    }), 201


@data_bp.route('/messages/stats', methods=['GET'])
@jwt_required()
def messages_stats():
    """Get message statistics."""
    current_role = auth.get_current_role()
    current_id = auth.get_current_user_id()
    
    if current_role == 'worker':
        total = models.count_messages(sender_id=current_id)
    else:
        total = models.count_messages()
    
    return jsonify({
        "total_messages": total
    })
