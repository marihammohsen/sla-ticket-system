import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from config import get_config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config())

    db.init_app(app)

    # Database Schema Patching logic
    with app.app_context():
        # List of columns to check and their SQL types
        required_columns = [
            ("assigned_by_id", "INTEGER"),
            ("escalation_level", "VARCHAR(50)"),
            ("is_escalated", "BOOLEAN DEFAULT 0"),
            ("escalation_note", "TEXT")
        ]

        for col_name, col_type in required_columns:
            try:
                # Check if column exists
                db.session.execute(text(f"SELECT {col_name} FROM tickets LIMIT 1"))
            except Exception:
                db.session.rollback()  # Reset session after failed select
                try:
                    print(f"Schema patch: Adding missing column {col_name}")
                    db.session.execute(text(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}"))
                    db.session.commit()
                except Exception as e:
                    print(f"Could not add {col_name}: {e}")
                    db.session.rollback()

    # Configure logging
    if not os.path.exists("logs"):
        os.mkdir("logs")

    file_handler = RotatingFileHandler("logs/manager_actions.log", maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(user)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    file_handler.setLevel(logging.INFO)

    logger = logging.getLogger("app.manager")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    app.logger_manager = logger

    # Register blueprints
    from .blueprints.tickets import tickets_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.auth import auth_bp
    from .blueprints.admin import admin_bp

    app.register_blueprint(tickets_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_current_user():
        from .services.auth import get_current_user
        return {"current_user": get_current_user()}

    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("tickets.ticket_dashboard"))

    return app