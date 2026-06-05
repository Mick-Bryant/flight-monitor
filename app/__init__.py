from flask import Flask, render_template
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from app.models import db, User
from config import Config

bcrypt        = Bcrypt()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialise extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view    = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth   import auth_bp
    from app.routes import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Enable SQLite foreign key enforcement on every connection
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    import sqlite3 as _sqlite3

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, _sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Inject app name into all templates
    app.jinja_env.globals['app_name'] = Config.APP_NAME

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    return app
