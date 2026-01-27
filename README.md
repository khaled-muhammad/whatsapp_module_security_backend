# Security Backend for Nexus WhatsApp

A separate Flask backend that provides authentication, role-based access control, and centralized data management for the WhatsApp automation application.

## Quick Start

### 1. Install Dependencies

```bash
cd security_backend
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

Set these environment variables if you want to customize the defaults:

```bash
export JWT_SECRET_KEY="your-secure-secret-key"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="admin123"
export SECURITY_PORT=5501
```

### 3. Run the Security Backend

```bash
python app.py
```

The server will start at `http://127.0.0.1:5501`

### 4. Access Admin Panel

Navigate to `http://127.0.0.1:5501` and login with:
- **Username**: admin
- **Password**: admin123 (change this in production!)

## Running the Main App with Security

Set `SECURITY_MODE=true` (default) when running the main app:

```bash
cd ..
SECURITY_MODE=true python web_app.py
```

This will require users to login before accessing the main WhatsApp app.

## API Endpoints

### Authentication
- `POST /auth/login` - Login and get JWT tokens
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info
- `POST /auth/validate` - Validate token (for main app)

### User Management (Managers/Admins only)
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `PUT /api/users/<id>` - Update user
- `DELETE /api/users/<id>` - Terminate user

### Data (Authenticated)
- `GET /api/contacts` - List contacts with pagination/search
- `POST /api/contacts/sync` - Sync contacts from main app
- `GET /api/messages` - List message logs
- `POST /api/messages/log` - Log a sent message

## Account Roles

| Role | Permissions |
|------|-------------|
| **Worker** | Login, send messages, view own message history |
| **Manager** | Worker permissions + create/manage accounts they created |
| **Admin** | Full access to all features and users |

## Security Notes

> **Important**: Change the default admin password before deploying to production!

> **JWT Secret**: Set `JWT_SECRET_KEY` environment variable to a strong random string in production.

## File Structure

```
security_backend/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── models.py           # Database models (SQLite)
├── auth.py             # Authentication helpers
├── requirements.txt    # Python dependencies
├── routes/
│   ├── auth_routes.py  # Login/logout endpoints
│   ├── users.py        # User management API
│   └── data.py         # Contacts & messages API
└── templates/
    ├── base.html       # Base template
    ├── login.html      # Login page
    └── admin/
        ├── dashboard.html
        ├── users.html
        ├── contacts.html
        └── messages.html
```
