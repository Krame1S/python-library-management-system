import os
from flask import Flask
from flask_login import LoginManager
from app.models import db, User
from dotenv import load_dotenv

load_dotenv()

login_manager = LoginManager()

def create_app():
    app = Flask(__name__, template_folder='templates', instance_relative_config=True)
    
    # Build database URI from environment variables
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'library')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    with app.app_context():
        db.create_all()
    
    from app.api.routes import register_routes
    register_routes(app)
    
    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))