# local_api/models.py
# Modèles SQLAlchemy — Serveur local (Plan Particulier, sur le Pi)
# Définis en premier pour permettre les migrations (Flask-Migrate / Alembic)

from datetime import datetime

from extensions import db


class Driver(db.Model):
    __tablename__ = "drivers"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    embedding  = db.Column(db.Text, nullable=False)         # JSON: 512 floats (FaceNet512)
    source     = db.Column(db.String(20), default="local")  # 'local' ou 'sync' (Plan Entreprise)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    alerts = db.relationship("Alert", backref="driver", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }


class Alert(db.Model):
    __tablename__ = "alerts"
    
    id          = db.Column(db.Integer, primary_key=True)
    driver_id   = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
    driver_name = db.Column(db.String(100), default="Inconnu")  # dénormalisé (robuste si driver supprimé)
    type_alerte = db.Column(db.String(40), nullable=False)
    ear         = db.Column(db.Float, default=0.0)
    mar         = db.Column(db.Float, default=0.0)
    yaw         = db.Column(db.Float, default=0.0)
    pitch       = db.Column(db.Float, default=0.0)
    roll        = db.Column(db.Float, default=0.0)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "conducteur": self.driver_name,
            "type_alerte": self.type_alerte,
            "ear": self.ear, "mar": self.mar,
            "yaw": self.yaw, "pitch": self.pitch, "roll": self.roll,
            "timestamp": self.timestamp.isoformat(),
        }