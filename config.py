"""
Configuration for Security Backend
"""
import os
from datetime import timedelta

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, ".data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Database
DATABASE_PATH = os.path.join(DATA_DIR, "security.db")

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "super-secret-change-in-production")
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# Server Configuration
HOST = os.environ.get("SECURITY_HOST", "0.0.0.0")
PORT = int(os.environ.get("SECURITY_PORT", 5501))
DEBUG = os.environ.get("SECURITY_DEBUG", "false").lower() == "true"

# Main App URL (for CORS)
MAIN_APP_URL = os.environ.get("MAIN_APP_URL", "http://127.0.0.1:5500")

# Initial Admin Configuration
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # Change in production!
