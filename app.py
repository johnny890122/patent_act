from flask import Flask
import os
import secrets
from datetime import timedelta
from db.models import Database
from routes.admin import admin_bp
from routes.quiz import quiz_bp
from routes.laws import laws_bp, questions_bp
from routes.frontend import frontend_bp
from routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    
    # Configure secret key for session management
    # Use environment variable or generate a random key for development
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Configure session settings
    app.config['SESSION_COOKIE_NAME'] = 'patent_act_session'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session expires after 7 days
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    
    # Initialize DB indexes
    db = Database()
    db.init_db()

    # Register Blueprints
    # Authentication routes (must be first to handle login before other routes)
    app.register_blueprint(auth_bp)
    
    # Frontend routes (HTML pages)
    app.register_blueprint(frontend_bp)
    
    # API routes (blueprints already have their url_prefix defined)
    app.register_blueprint(admin_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(laws_bp)
    app.register_blueprint(questions_bp)

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
