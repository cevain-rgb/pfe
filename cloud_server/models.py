# cloud_server/models.py
# Modèles SQLAlchemy — Serveur Cloud (Plan Entreprise)
# Alignés sur le diagramme de classes validé

from datetime import datetime
import enum
from extensions import db



# ─────────────────────────────────────────────────────
# Admin — gestionnaire de la flotte
# ─────────────────────────────────────────────────────

class Admin(db.Model):
    __tablename__ = "admins"

    id            = db.Column(db.Integer, primary_key=True)
    nom           = db.Column(db.String(100), nullable=False)
    prenom        = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    groupes = db.relationship("Group",  backref="admin", lazy=True)
    modules = db.relationship("Module", backref="admin", lazy=True)

    def to_dict(self):
        return {
            "id":     self.id,
            "nom":    self.nom,
            "prenom": self.prenom,
            "email":  self.email,
        }


# ─────────────────────────────────────────────────────
# Group — sous-groupe de véhicules/conducteurs
# ─────────────────────────────────────────────────────

class Group(db.Model):
    __tablename__ = "groups"

    id         = db.Column(db.Integer, primary_key=True)
    nom        = db.Column(db.String(100), nullable=False)
    admin_id   = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    modules = db.relationship("Module", backref="groupe", lazy=True)
    drivers = db.relationship("Driver", backref="groupe", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "nom":        self.nom,
            "nb_modules": len(self.modules),
            "nb_drivers": len(self.drivers),
        }


# ─────────────────────────────────────────────────────
# Module — module embarqué (Raspberry Pi)
# Anciennement "Device" — renommé conformément au diagramme
# ─────────────────────────────────────────────────────

class Module(db.Model):
    __tablename__ = "modules"

    id         = db.Column(db.Integer, primary_key=True)
    num_module = db.Column(db.Integer, unique=True, nullable=False)
    nom        = db.Column(db.String(100))
    statut     = db.Column(db.Enum("actif", "inactif", name="statut_module"), default="inactif")
    admin_id   = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=False)
    group_id   = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    last_sync  = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "num_module": self.num_module,
            "nom":        self.nom,
            "statut":     self.statut,
            "group_id":   self.group_id,
            "last_sync":  self.last_sync.isoformat() if self.last_sync else None,
        }


# ─────────────────────────────────────────────────────
# Driver — conducteur autorisé
# ─────────────────────────────────────────────────────

class Driver(db.Model):
    __tablename__ = "drivers"

    id         = db.Column(db.Integer, primary_key=True)
    nom        = db.Column(db.String(100), nullable=False)
    prenom     = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), nullable=True)           # ajout diagramme v2
    embedding  = db.Column(db.Text, nullable=False)
   # source     = db.Column(db.Enum(SourceEnum), default=SourceEnum.local)
    group_id   = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship("LigneUtilisation", backref="driver", lazy=True)

    def to_dict(self):
        return {
            "id":       self.id,
            "nom":      self.nom,
            "prenom":   self.prenom,
            "email":    self.email,
            # "source":   self.source.value,
            "group_id": self.group_id,
        }

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"


# ─────────────────────────────────────────────────────
# LigneUtilisation — session de conduite
# Regroupe toutes les alertes d'un trajet
# ─────────────────────────────────────────────────────

class LigneUtilisation(db.Model):
    __tablename__ = "lignes_utilisation"

    id         = db.Column(db.Integer, primary_key=True)
    driver_id  = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
    date_debut = db.Column(db.DateTime, default=datetime.utcnow)
    date_fin   = db.Column(db.DateTime, nullable=True)  
    statut     = db.Column(db.String(20), default="en_cours")  # 'en_cours' | 'termine'

    alertes = db.relationship("Alerte", backref="session", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "driver_id":  self.driver_id,
            "timestamp":  self.timestamp.isoformat(),
            "statut":     self.statut,
            "nb_alertes": len(self.alertes),
        }


# ─────────────────────────────────────────────────────
# Alerte — événement de somnolence/fatigue/distraction
# Liée à une LigneUtilisation (session de conduite)
# ─────────────────────────────────────────────────────

class Alerte(db.Model):
    __tablename__ = "alertes"

    id          = db.Column(db.Integer, primary_key=True)
    session_id  = db.Column(db.Integer, db.ForeignKey("lignes_utilisation.id"), nullable=True)
    type_alerte = db.Column(db.String(40), nullable=False)
    ear         = db.Column(db.Float, default=0.0)
    mar         = db.Column(db.Float, default=0.0)
    yaw         = db.Column(db.Float, default=0.0)
    pitch       = db.Column(db.Float, default=0.0)
    roll        = db.Column(db.Float, default=0.0)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "session_id":  self.session_id,
            "type_alerte": self.type_alerte,
            "ear":         self.ear,
            "mar":         self.mar,
            "yaw":         self.yaw,
            "pitch":       self.pitch,
            "roll":        self.roll,
            "timestamp":   self.timestamp.isoformat(),
        }
