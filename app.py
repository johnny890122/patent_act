from flask import Flask
import os
from db.models import Database
from routes.admin import admin_bp

def create_app():
    app = Flask(__name__)
    
    # Initialize DB indexes
    db = Database()
    db.init_db()

    # Register Blueprints
    app.register_blueprint(admin_bp)

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
