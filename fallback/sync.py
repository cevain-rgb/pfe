# sync.py
# Synchronisation bidirectionnelle Pi ↔ Cloud (Plan Entreprise)
#
# sync Cloud→Pi : récupère les conducteurs autorisés depuis le cloud
# sync Pi→Cloud : envoie les alertes locales non encore synchronisées
#
# Gestion de la reconnexion : file d'attente locale (pending_sync.json)
# Les données en attente sont renvoyées dès que le cloud est joignable.

import json
import os
from datetime import datetime

import requests

from config import CLOUD_URL, NUM_MODULE
from extensions import db
from models import Alert, Driver

PENDING_FILE = "pending_sync.json"   # file d'attente offline


# ── Helpers file d'attente ────────────────────────────

def _charger_pending() -> list:
    if not os.path.exists(PENDING_FILE):
        return []
    try:
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _sauvegarder_pending(alertes: list):
    with open(PENDING_FILE, "w") as f:
        json.dump(alertes, f)


def _ajouter_pending(alerte_dict: dict):
    """Ajoute une alerte à la file d'attente offline."""
    pending = _charger_pending()
    pending.append(alerte_dict)
    _sauvegarder_pending(pending)


# ── Sync Cloud → Pi ───────────────────────────────────

def sync_conducteurs() -> bool:
    """
    Récupère les conducteurs autorisés depuis le cloud pour ce module.
    Remplace uniquement les conducteurs source='sync' en base locale.
    En cas d'échec réseau, conserve le cache existant.
    """
    try:
        resp = requests.get(
            f"{CLOUD_URL}/api/drivers",
            params={"num_module": NUM_MODULE},
            timeout=5
        )
        resp.raise_for_status()
        conducteurs_distants = resp.json()

    except requests.RequestException as e:
        print(f"[SYNC ↓] ❌ Échec réseau ({e}) — cache local conservé.")
        return False

    Driver.query.filter_by(source="sync").delete()
    for c in conducteurs_distants:
        driver = Driver(
            nom=c["name"],
            embedding=json.dumps(c["embedding"]),
            source="sync"
        )
        db.session.add(driver)
    db.session.commit()
    print(f"[SYNC ↓] ✅ {len(conducteurs_distants)} conducteur(s) reçu(s).")
    return True


# ── Sync Pi → Cloud ───────────────────────────────────

def _alertes_a_envoyer() -> list:
    """
    Retourne les alertes locales non encore synchronisées
    + celles en attente dans le fichier offline.
    """
    pending = _charger_pending()

    # Alertes en base depuis la dernière sync
    non_sync = Alert.query.filter_by(synced=False).all()  # voir modèle ci-dessous
    for a in non_sync:
        pending.append(a.to_dict())

    return pending, non_sync


def sync_alertes() -> bool:
    """
    Envoie les alertes locales vers le cloud.
    En cas d'échec, les sauvegarde dans pending_sync.json
    pour un renvoi ultérieur.
    """
    pending = _charger_pending()

    # Récupère aussi les nouvelles alertes non synchro en base
    non_sync = Alert.query.filter_by(synced=False).all()
    nouvelles = [a.to_dict() for a in non_sync]
    a_envoyer = pending + nouvelles

    if not a_envoyer:
        return True   # rien à envoyer

    try:
        resp = requests.post(
            f"{CLOUD_URL}/api/sync/alertes",
            json={"num_module": NUM_MODULE, "alertes": a_envoyer},
            timeout=10
        )
        resp.raise_for_status()

        # Marquer comme synchronisées
        for a in non_sync:
            a.synced = True
        db.session.commit()

        # Vider la file d'attente
        _sauvegarder_pending([])
        print(f"[SYNC ↑] ✅ {len(a_envoyer)} alerte(s) envoyée(s).")
        return True

    except requests.RequestException as e:
        # Sauvegarder pour renvoi ultérieur
        _sauvegarder_pending(a_envoyer)
        print(f"[SYNC ↑] ❌ Échec ({e}) — {len(a_envoyer)} alerte(s) en attente.")
        return False


# ── Synchronisation complète ──────────────────────────

def synchroniser() -> dict:
    """
    Lance la synchronisation bidirectionnelle complète.
    Retourne un résumé {conducteurs_ok, alertes_ok}.
    """
    print("[SYNC] Démarrage synchronisation bidirectionnelle...")
    conducteurs_ok = sync_conducteurs()
    alertes_ok     = sync_alertes()
    print(f"[SYNC] Terminé — conducteurs: {'✅' if conducteurs_ok else '❌'}  alertes: {'✅' if alertes_ok else '❌'}")
    return {"conducteurs_ok": conducteurs_ok, "alertes_ok": alertes_ok}


# ── Sync périodique (à lancer dans un thread séparé) ──

def demarrer_sync_periodique(intervalle_secondes: int = 3600):
    """
    Lance la synchronisation en arrière-plan toutes les N secondes.
    Appeler dans main.py via threading.Thread(daemon=True).
    """
    import threading
    import time

    def boucle():
        while True:
            time.sleep(intervalle_secondes)
            try:
                synchroniser()
            except Exception as e:
                print(f"[SYNC] Erreur inattendue : {e}")

    t = threading.Thread(target=boucle, daemon=True)
    t.start()
    print(f"[SYNC] Sync périodique activée (toutes les {intervalle_secondes}s).")