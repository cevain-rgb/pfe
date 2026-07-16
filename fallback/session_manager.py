# session_manager.py
# Gère le cycle de vie d'une LigneUtilisation (session de conduite).
#
# Flux :
#   auth.py → ouvrir_session(conducteur)
#   detection.py → mettre_a_jour_statut(statut) à chaque changement
#   main.py (finally) → fermer_session()

from datetime import datetime
from models import LigneUtilisation, Driver
from extensions import db

_session_courante: LigneUtilisation | None = None


def ouvrir_session(conducteur: str) -> LigneUtilisation:
    """
    Crée une nouvelle LigneUtilisation au démarrage de la détection.
    Appelé juste après l'authentification réussie.
    """
    global _session_courante

    driver = Driver.query.filter_by(nom=conducteur).first()
    session = LigneUtilisation(
        driver_id=driver.id if driver else None,
        statut="Eveille",
        date_debut=datetime.utcnow(),
    )
    db.session.add(session)
    db.session.commit()
    _session_courante = session
    print(f"[SESSION] Session #{session.id} ouverte pour '{conducteur}'.")
    return session


def mettre_a_jour_statut(statut: str):
    """
    Met à jour le statut courant de la session (= état du conducteur).
    Appelé à chaque changement de statut dans detection.py.
    Évite les écritures inutiles si le statut n'a pas changé.
    """
    global _session_courante
    if _session_courante is None:
        return
    if _session_courante.statut == statut:
        return

    _session_courante.statut = statut
    db.session.commit()


def fermer_session():
    """
    Clôture la session en cours (date_fin + statut final).
    Appelé dans le bloc finally de main.py.
    """
    global _session_courante
    if _session_courante is None:
        return

    _session_courante.date_fin = datetime.utcnow()
    _session_courante.statut   = "termine"
    db.session.commit()
    print(f"[SESSION] Session #{_session_courante.id} fermée.")
    _session_courante = None


def get_session_id() -> int | None:
    """Retourne l'ID de la session courante (pour lier les alertes)."""
    return _session_courante.id if _session_courante else None