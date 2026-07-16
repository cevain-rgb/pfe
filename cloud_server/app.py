# Serveur Flask Cloud — Plan Entreprise (déployé sur VPS)

import os
from flask import Flask
from extensions import db, migrate, jwt
from routes_cloud import api_bp


def create_app():
    app = Flask(__name__)
    # SQLite par défaut (dev). En production, utiliser PostgreSQL via la
    # variable d'environnement DATABASE_URL (meilleure gestion de la
    # concurrence multi-device qu'un fichier SQLite).
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///cloud.db" 
        # "postgresql://user:pass@host/db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "DMS_SOMNOLENCE3.0")
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "DMS_SOMNOLENCE3.0_JWT") # Préférable

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000)