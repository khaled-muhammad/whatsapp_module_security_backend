"""
Security Backend - Main Application
Flask app with JWT authentication and admin panel
"""
from flask import Flask, render_template, redirect, url_for, request, jsonify, make_response
from flask_jwt_extended import JWTManager, jwt_required, get_jwt, verify_jwt_in_request
from flask_cors import CORS
from functools import wraps

import config
import models
import auth as auth_module

# Import route blueprints
from routes.auth_routes import auth_bp
from routes.users import users_bp
from routes.data import data_bp


app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config.JWT_ACCESS_TOKEN_EXPIRES
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = config.JWT_REFRESH_TOKEN_EXPIRES
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
app.config['JWT_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Enable in production

# Initialize extensions
jwt = JWTManager(app)
CORS(app, origins=[config.MAIN_APP_URL], supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(data_bp)

# Initialize database and seed admin
models.init_db()
models.seed_admin()


# ============================================
# Admin Panel Routes (Web UI)
# ============================================

def admin_required(fn):
    """Decorator for admin panel pages - checks cookie token."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get('access_token')
        if not token:
            return redirect(url_for('login_page'))
        
        try:
            # Manually verify the token
            from flask_jwt_extended import decode_token
            decoded = decode_token(token)
            user_id = int(decoded['sub'])
            user = models.get_user_by_id(user_id)
            
            if not user or not user.get('is_active'):
                return redirect(url_for('login_page'))
            
            if user['role'] not in ['manager', 'admin']:
                return redirect(url_for('login_page'))
            
            # Add user to request context
            request.current_user = user
            return fn(*args, **kwargs)
        except Exception as e:
            print(f"Token verification failed: {e}")
            return redirect(url_for('login_page'))
    
    return wrapper


@app.route('/')
def index():
    """Redirect to dashboard or login."""
    token = request.cookies.get('access_token')
    if token:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))


@app.route('/login')
def login_page():
    """Render login page."""
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_submit():
    """Handle login form submission."""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    user = auth_module.authenticate_user(username, password)
    if not user:
        return render_template('login.html', error="Invalid credentials")
    
    if user['role'] not in ['manager', 'admin']:
        return render_template('login.html', error="Admin access required")
    
    tokens = auth_module.generate_tokens(user['id'], user['username'], user['role'])
    
    response = make_response(redirect(url_for('dashboard')))
    # access_token needs to be readable by JavaScript for API calls
    response.set_cookie('access_token', tokens['access_token'], httponly=False, samesite='Lax')
    response.set_cookie('refresh_token', tokens['refresh_token'], httponly=True, samesite='Lax')
    
    return response


@app.route('/logout')
def logout():
    """Clear cookies and redirect to login."""
    response = make_response(redirect(url_for('login_page')))
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response


@app.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard."""
    user = request.current_user
    
    stats = {
        'total_users': len(models.list_users()),
        'total_contacts': models.count_contacts(),
        'total_messages': models.count_messages(),
        'my_users': len(models.list_users(created_by=user['id'])) if user['role'] == 'manager' else None
    }
    
    return render_template('admin/dashboard.html', user=user, stats=stats)


@app.route('/users')
@admin_required
def users_page():
    """User management page."""
    user = request.current_user
    
    if user['role'] == 'admin':
        users = models.list_users()
    else:
        users = models.list_users(created_by=user['id'])
    
    return render_template('admin/users.html', user=user, users=users)


@app.route('/contacts')
@admin_required
def contacts_page():
    """Contacts listing page."""
    user = request.current_user
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    limit = 50
    offset = (page - 1) * limit
    
    contacts = models.list_contacts(limit=limit, offset=offset, search=search if search else None)
    total = models.count_contacts()
    pages = (total + limit - 1) // limit
    
    return render_template('admin/contacts.html', user=user, contacts=contacts, 
                         page=page, pages=pages, total=total, search=search)


@app.route('/messages')
@admin_required
def messages_page():
    """Message logs page."""
    user = request.current_user
    
    page = request.args.get('page', 1, type=int)
    limit = 50
    offset = (page - 1) * limit
    
    messages = models.list_messages(limit=limit, offset=offset)
    total = models.count_messages()
    pages = (total + limit - 1) // limit
    
    return render_template('admin/messages.html', user=user, messages=messages,
                         page=page, pages=pages, total=total)


# ============================================
# Health Check
# ============================================

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "security-backend"})


# ============================================
# Run Application
# ============================================

if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"Security Backend starting on http://{config.HOST}:{config.PORT}")
    print(f"Admin login: {config.ADMIN_USERNAME}")
    print(f"{'='*50}\n")
    
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
