from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
login_manager = LoginManager()
scheduler = BackgroundScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.stocks import stocks_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(stocks_bp)

    # Context Processor for Global User
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app