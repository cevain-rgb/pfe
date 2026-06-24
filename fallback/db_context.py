# dms/db_context.py
# Active le contexte Flask/SQLAlchemy pour les scripts standalone
# (main.py, enroll.py) qui ne tournent PAS comme serveur web.
#
# ⚠️ À importer EN PREMIER dans main.py et enroll.py

import sys
import os

from app import create_app

_app = create_app()
_app.app_context().push()

print("[DB_CONTEXT] Contexte Flask/SQLAlchemy actif.")