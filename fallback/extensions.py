# local_api/extensions.py
# Instances partagées SQLAlchemy / Migrate

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()