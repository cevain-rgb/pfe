# state.py
# Partage de l'état courant entre le processus de détection (main.py)
# et le serveur Flask (app.py) via un fichier JSON.
#
# Les deux processus tournent en parallèle et ne partagent pas la mémoire —
# le fichier JSON est le seul moyen simple et fiable de les synchroniser.

import json
import os
from datetime import datetime

STATE_FILE = "current_status.json"

_ETAT_DEFAUT = {
    "conducteur"  : "Inconnu",
    "statut"      : "Inactif",
    "ear"         : 0.0,
    "mar"         : 0.0,
    "yaw"         : 0.0,
    "pitch"       : 0.0,
    "roll"        : 0.0,
    "fps"         : 0.0,
    "nb_alertes"  : 0,
    "alerte"      : False,
    "timestamp"   : None,
}


def mettre_a_jour(conducteur, statut, ear=0.0, mar=0.0,
                yaw=0.0, pitch=0.0, roll=0.0, fps=0.0, nb_alertes=0):
    """
    Écrit l'état courant dans le fichier JSON.
    Appelé à chaque frame de détection (ou à chaque changement de statut).
    """
    etat = {
        "conducteur" : conducteur,
        "statut"     : statut,
        "ear"        : round(ear,   3),
        "mar"        : round(mar,   3),
        "yaw"        : round(yaw,   2),
        "pitch"      : round(pitch, 2),
        "roll"       : round(roll,  2),
        "fps"        : round(fps,   1),
        "nb_alertes" : nb_alertes,
        "alerte"     : statut not in ("Eveille", "Aucun visage", "Inactif"),
        "timestamp"  : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(STATE_FILE, "w") as f:
        json.dump(etat, f)


def lire():
    """
    Lit l'état courant depuis le fichier JSON.
    Retourne l'état par défaut si le fichier n'existe pas encore.
    """
    if not os.path.exists(STATE_FILE):
        return _ETAT_DEFAUT.copy()
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return _ETAT_DEFAUT.copy()


def reinitialiser():
    """Remet l'état à 'Inactif' (fin de session de détection)."""
    mettre_a_jour("Inconnu", "Inactif")