# local_api/models.py
# Modèles SQLAlchemy — Serveur local (Pi, Plan Particulier)

from datetime import datetime
from extensions import db


class Driver(db.Model):
    __tablename__ = "drivers"

    id         = db.Column(db.Integer, primary_key=True)
    nom        = db.Column(db.String(100), nullable=False)
    prenom     = db.Column(db.String(100))
    embedding  = db.Column(db.Text, nullable=False)
    source     = db.Column(db.String(20), default="local")   # 'local' | 'sync'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship("LigneUtilisation", backref="driver", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "source":     self.source,
            "created_at": self.created_at.isoformat(),
        }
    @property
    def nom_complet(self):
        return f"{self.prenom if self.prenom else ''} {self.nom}"

class LigneUtilisation(db.Model):
    """
    Session de conduite — créée à l'authentification du conducteur,
    fermée quand le module s'arrête.
    statut = état courant du conducteur (Eveille, SOMNOLENCE,
            FATIGUE-BAILLEMENT, FATIGUE-TETE_TOMBANTE, DISTRACTION).
    """
    __tablename__ = "lignes_utilisation"

    id         = db.Column(db.Integer, primary_key=True)
    driver_id  = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
    date_debut = db.Column(db.DateTime, default=datetime.utcnow)
    date_fin   = db.Column(db.DateTime, nullable=True)           # null tant que session en cours
    statut     = db.Column(db.String(40), default="Eveille")     # mis à jour à chaque frame

    alertes = db.relationship("Alert", backref="session", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "driver_id":  self.driver_id,
            "date_debut": self.date_debut.isoformat(),
            "date_fin":   self.date_fin.isoformat() if self.date_fin else None,
            "statut":     self.statut,
            "nb_alertes": len(self.alertes),
        }


class Alert(db.Model):
    __tablename__ = "alerts"

    id          = db.Column(db.Integer, primary_key=True)
    session_id  = db.Column(db.Integer, db.ForeignKey("lignes_utilisation.id"), nullable=True)
    driver_id   = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
    driver_name = db.Column(db.String(100), default="Inconnu")
    type_alerte = db.Column(db.String(40), nullable=False)
    ear         = db.Column(db.Float, default=0.0)
    mar         = db.Column(db.Float, default=0.0)
    yaw         = db.Column(db.Float, default=0.0)
    pitch       = db.Column(db.Float, default=0.0)
    roll        = db.Column(db.Float, default=0.0)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    synced      = db.Column(db.Boolean, default=False)  # True une fois envoyée au cloud

    def to_dict(self):
        return {
            "id":          self.id,
            "conducteur":  self.driver_name,
            "type_alerte": self.type_alerte,
            "ear":         self.ear,
            "mar":         self.mar,
            "yaw":         self.yaw,
            "pitch":       self.pitch,
            "roll":        self.roll,
            "timestamp":   self.timestamp.isoformat(),
        }
