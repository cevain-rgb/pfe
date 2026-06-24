# sync.py
# Synchronisation périodique avec le serveur Cloud (Plan Entreprise)

import json

import requests
from extensions import db
from models import Driver

CLOUD_URL = "http://votre-vps.exemple.com:8000"   # à adapter
DEVICE_ID = 1                                       # id numérique attribué par le cloud à ce Pi


def synchroniser():
    """
    Récupère les conducteurs autorisés depuis le cloud et les insère
    localement (source='sync'), sans toucher aux conducteurs 'local'.
    En cas d'échec réseau, conserve le cache local existant (cache
    horaire prévu dans l'architecture du Plan Entreprise).
    """
    try:
        resp = requests.get(
            f"{CLOUD_URL}/api/drivers",
            params={"device_id": DEVICE_ID},
            timeout=5
        )
        resp.raise_for_status()
        conducteurs_distants = resp.json()
    except requests.RequestException as e:
        print(f"[SYNC] Échec réseau ({e}) — cache local conservé.")
        return False

    Driver.query.filter_by(source="sync").delete()
    for c in conducteurs_distants:
        driver = Driver(
            name=c["name"],
            embedding=json.dumps(c["embedding"]),
            source="sync"
        )
        db.session.add(driver)
    db.session.commit()

    print(f"[SYNC] {len(conducteurs_distants)} conducteur(s) synchronisé(s) depuis le cloud.")
    return True