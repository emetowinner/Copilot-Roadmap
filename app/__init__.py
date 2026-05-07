from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from app.routes.dashboard import dashboard_bp
    from app.routes.features import features_bp
    from app.routes.export_routes import export_bp
    from app.routes.sync import sync_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(features_bp, url_prefix="/features")
    app.register_blueprint(export_bp, url_prefix="/export")
    app.register_blueprint(sync_bp, url_prefix="/sync")

    with app.app_context():
        db.create_all()

    return app
