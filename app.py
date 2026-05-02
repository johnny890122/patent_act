from flask import Flask
import os
from db.models import Database
from routes.admin import admin_bp
from routes.quiz import quiz_bp
from routes.laws import laws_bp, questions_bp
from routes.frontend import frontend_bp

def create_app():
    app = Flask(__name__)
    
    # Initialize DB indexes
    db = Database()
    db.init_db()

    # Register Blueprints
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
