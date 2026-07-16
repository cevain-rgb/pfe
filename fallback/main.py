# main.py
# Point d'entrée — DriveSafe
#
# Flux :
#   1. Contexte Flask/SQLAlchemy
#   2. Migration automatique (db.create_all)
#   3. Sync Cloud→Pi immédiate au démarrage
#   4. Sync périodique bidirectionnelle en arrière-plan (thread daemon)
#   5. Authentification faciale (LED clignote → fixe)
#   6. Ouverture session (LigneUtilisation)
#   7. Pipeline détection (YOLO ou fallback MediaPipe)
#   8. Fermeture session + nettoyage
#
# Lancement :
#   python main.py
#
# Serveur API (terminal séparé) :
#   python app.py

import db_context   # ⚠️ EN PREMIER — active le contexte Flask/SQLAlchemy

import os
from auth            import authentifier_conducteur
from config          import YOLO_MODEL_PATH
from session_manager import ouvrir_session, fermer_session
import led
import buzzer


# ── Étape 1 : Migration auto ──────────────────────────

def migration_auto():
    """Crée les tables manquantes sans écraser les données existantes."""
    from extensions import db
    from models import Driver, LigneUtilisation, Alert   # noqa: F401
    db.create_all()
    print("[DB] ✅ Tables vérifiées.")


# ── Étape 2 : Synchronisation cloud ──────────────────

def sync_demarrage():
    """
    Synchronisation immédiate au démarrage :
    - Cloud→Pi : conducteurs autorisés
    - Pi→Cloud : alertes en attente (offline depuis la dernière session)
    Silencieuse si le cloud est inaccessible.
    """
    try:
        from sync import synchroniser
        synchroniser()
    except Exception as e:
        print(f"[SYNC] Ignoré au démarrage : {e}")


def sync_periodique():
    """
    Lance la sync bidirectionnelle toutes les heures en arrière-plan.
    Gère automatiquement la reconnexion et les alertes en attente.
    """
    try:
        from sync import demarrer_sync_periodique
        demarrer_sync_periodique(intervalle_secondes=3600)
    except Exception as e:
        print(f"[SYNC] Sync périodique non démarrée : {e}")


# ── Étape 3 : Choix du pipeline ───────────────────────

def choisir_pipeline():
    """
    YOLOv8n (.tflite) si le modèle est présent → pipeline principal.
    MediaPipe EAR/MAR sinon → fallback (FP7).
    """
    if os.path.exists(YOLO_MODEL_PATH):
        try:
            from detection_yolo import lancer_detection_yolo
            print(f"[MAIN] YOLO ({YOLO_MODEL_PATH}) — pipeline principal.")
            return lancer_detection_yolo
        except Exception as e:
            print(f"[MAIN] YOLO indisponible ({e}) — bascule fallback.")

    from detection import lancer_detection
    print("[MAIN] Pipeline de secours MediaPipe activé.")
    return lancer_detection


# ── Point d'entrée ────────────────────────────────────

def main():
    print("=" * 52)
    print("DriveSafe — Détection de Somnolence au Volant")
    print("=" * 52)

    migration_auto()
    sync_demarrage()
    sync_periodique()

    conducteur = authentifier_conducteur()
    if conducteur is None:
        print("[MAIN] ❌ Accès refusé — module arrêté.")
        led.nettoyer()
        return

    print(f"[MAIN] ✅ Bienvenue {conducteur}")

    pipeline = choisir_pipeline()
    try:
        ouvrir_session(conducteur)
        pipeline(conducteur)
    finally:
        fermer_session()
        led.nettoyer()
        buzzer.nettoyer()
        # Sync finale : envoie les alertes de cette session avant de quitter
        try:
            from sync import sync_alertes
            sync_alertes()
        except Exception:
            pass
        print("[MAIN] Session terminée.")


if __name__ == "__main__":
    main()