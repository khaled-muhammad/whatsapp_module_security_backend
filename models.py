"""
Database Models for Security Backend
Handles user accounts, contacts, and message logging
"""
import sqlite3
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
import bcrypt
import config

_lock = threading.Lock()


def _get_conn():
    """Get database connection with row factory."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    with _get_conn() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('worker', 'manager', 'admin')),
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Contacts table (centralized)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                name TEXT,
                source_group TEXT,
                scraped_by INTEGER REFERENCES users(id),
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(phone)
            )
        """)
        
        # Message logs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER REFERENCES users(id),
                recipient_phone TEXT NOT NULL,
                message_content TEXT,
                attachment_path TEXT,
                template_used TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent'
            )
        """)
        
        conn.commit()


# ============================================
# User Management Functions
# ============================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_user(username: str, password: str, role: str, created_by: Optional[int] = None) -> int:
    """Create a new user."""
    with _lock:
        with _get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO users (username, password_hash, role, created_by, created_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (username, hash_password(password), role, created_by, datetime.now().isoformat())
            )
            conn.commit()
            return cur.lastrowid


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_users(created_by: Optional[int] = None) -> List[Dict[str, Any]]:
    """List all users, optionally filtering by creator."""
    with _get_conn() as conn:
        if created_by is not None:
            rows = conn.execute(
                "SELECT id, username, role, created_by, created_at, is_active FROM users WHERE created_by = ? ORDER BY id DESC",
                (created_by,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, username, role, created_by, created_at, is_active FROM users ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_user(user_id: int, username: Optional[str] = None, password: Optional[str] = None, 
                is_active: Optional[bool] = None) -> bool:
    """Update user details."""
    with _lock:
        user = get_user_by_id(user_id)
        if not user:
            return False
        
        updates = []
        params = []
        
        if username is not None:
            updates.append("username = ?")
            params.append(username)
        if password is not None:
            updates.append("password_hash = ?")
            params.append(hash_password(password))
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if not updates:
            return False
        
        params.append(user_id)
        with _get_conn() as conn:
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        return True


def delete_user(user_id: int) -> bool:
    """Soft delete a user (set inactive)."""
    return update_user(user_id, is_active=False)


def can_manage_user(manager_id: int, target_user_id: int) -> bool:
    """Check if a manager can manage a target user."""
    manager = get_user_by_id(manager_id)
    target = get_user_by_id(target_user_id)
    
    if not manager or not target:
        return False
    
    # Admins can manage anyone
    if manager['role'] == 'admin':
        return True
    
    # Managers can only manage users they created
    if manager['role'] == 'manager':
        return target['created_by'] == manager_id
    
    return False


# ============================================
# Contact Functions
# ============================================

def add_contact(phone: str, name: Optional[str] = None, source_group: Optional[str] = None,
                scraped_by: Optional[int] = None) -> int:
    """Add or update a contact."""
    with _lock:
        with _get_conn() as conn:
            # Use INSERT OR REPLACE for upsert behavior
            cur = conn.execute(
                """INSERT OR REPLACE INTO contacts (phone, name, source_group, scraped_by, scraped_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (phone, name, source_group, scraped_by, datetime.now().isoformat())
            )
            conn.commit()
            return cur.lastrowid


def bulk_add_contacts(contacts: List[Dict], source_group: str, scraped_by: int) -> int:
    """Add multiple contacts at once."""
    count = 0
    with _lock:
        with _get_conn() as conn:
            for c in contacts:
                phone = c.get('phone') or c.get('number')
                name = c.get('name')
                if phone:
                    conn.execute(
                        """INSERT OR REPLACE INTO contacts (phone, name, source_group, scraped_by, scraped_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (phone, name, source_group, scraped_by, datetime.now().isoformat())
                    )
                    count += 1
            conn.commit()
    return count


def list_contacts(limit: int = 100, offset: int = 0, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """List contacts with pagination and search."""
    with _get_conn() as conn:
        if search:
            rows = conn.execute(
                """SELECT * FROM contacts WHERE phone LIKE ? OR name LIKE ? 
                   ORDER BY scraped_at DESC LIMIT ? OFFSET ?""",
                (f"%{search}%", f"%{search}%", limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contacts ORDER BY scraped_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [dict(r) for r in rows]


def count_contacts() -> int:
    """Get total contact count."""
    with _get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]


# ============================================
# Message Log Functions
# ============================================

def log_message(sender_id: int, recipient_phone: str, message_content: str,
                attachment_path: Optional[str] = None, template_used: Optional[str] = None,
                status: str = 'sent') -> int:
    """Log a sent message."""
    with _lock:
        with _get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO message_logs (sender_id, recipient_phone, message_content, 
                   attachment_path, template_used, sent_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sender_id, recipient_phone, message_content, attachment_path, 
                 template_used, datetime.now().isoformat(), status)
            )
            conn.commit()
            return cur.lastrowid


def list_messages(limit: int = 100, offset: int = 0, sender_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """List message logs with pagination."""
    with _get_conn() as conn:
        if sender_id is not None:
            rows = conn.execute(
                """SELECT m.*, u.username as sender_username FROM message_logs m
                   LEFT JOIN users u ON m.sender_id = u.id
                   WHERE m.sender_id = ?
                   ORDER BY m.sent_at DESC LIMIT ? OFFSET ?""",
                (sender_id, limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT m.*, u.username as sender_username FROM message_logs m
                   LEFT JOIN users u ON m.sender_id = u.id
                   ORDER BY m.sent_at DESC LIMIT ? OFFSET ?""",
                (limit, offset)
            ).fetchall()
        return [dict(r) for r in rows]


def count_messages(sender_id: Optional[int] = None) -> int:
    """Get total message count."""
    with _get_conn() as conn:
        if sender_id:
            return conn.execute("SELECT COUNT(*) FROM message_logs WHERE sender_id = ?", (sender_id,)).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM message_logs").fetchone()[0]


# ============================================
# Admin Seeding
# ============================================

def seed_admin():
    """Create initial admin user if not exists."""
    existing = get_user_by_username(config.ADMIN_USERNAME)
    if not existing:
        create_user(config.ADMIN_USERNAME, config.ADMIN_PASSWORD, 'admin')
        print(f"[Security Backend] Created admin user: {config.ADMIN_USERNAME}")
    else:
        print(f"[Security Backend] Admin user already exists: {config.ADMIN_USERNAME}")
