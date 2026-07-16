# logger.py
# Journalisation horodatée des alertes (EF8)
# Écrit en CSV (sauvegarde locale) ET en base SQLAlchemy (table Alert)

import csv
from datetime import datetime
from config import LOG_FICHIER


def init_log():
    """Crée le fichier CSV avec les en-têtes."""
    with open(LOG_FICHIER, mode='w', newline='') as f:
        csv.writer(f).writerow([
            "timestamp", "conducteur", "type_alerte",
            "ear", "mar", "yaw", "pitch", "roll"
        ])
    print(f"[LOG] Fichier CSV initialisé : {LOG_FICHIER}")


def ecrire_log(type_alerte, ear, mar, yaw, pitch, roll, conducteur="Inconnu"):
    """
    Enregistre une alerte :
    - CSV  → sauvegarde locale simple (EF8)
    - Base → table Alert, consommée par /api/status et /api/alertes
    """
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 1. Écriture CSV ───────────────────────────────
    with open(LOG_FICHIER, mode='a', newline='') as f:
        csv.writer(f).writerow([
            horodatage, conducteur, type_alerte,
            round(ear,   4), round(mar,   4),
            round(yaw,   2), round(pitch, 2), round(roll, 2)
        ])

    # ── 2. Écriture en base SQLAlchemy ────────────────
    # Le contexte Flask est poussé par db_context.py via main.py.
    # Le try/except protège si ce fichier est utilisé hors contexte.
    try:
        from models import Alert, Driver
        from extensions import db
        from session_manager import get_session_id

        driver = Driver.query.filter_by(nom=conducteur).first()
        alert = Alert(
            session_id=get_session_id(),          # lie l'alerte à la session courante
            driver_id=driver.id if driver else None,
            driver_name=conducteur,
            type_alerte=type_alerte,
            ear=round(ear, 4), mar=round(mar, 4),
            yaw=round(yaw, 2), pitch=round(pitch, 2), roll=round(roll, 2),
        )
        db.session.add(alert)
        db.session.commit()
    except Exception as e:
        print(f"[LOG] ⚠️ Écriture en base échouée : {e} — CSV conservé.")


def rapport_final(liste_fps, liste_ear, nb_alertes, duree):
    """
    Rapport de validation en fin de session.
    Vérifie les exigences du cahier des charges.
    """
    import numpy as np

    fps_moy   = np.mean(liste_fps) if liste_fps else 0
    fps_min   = np.min(liste_fps)  if liste_fps else 0
    ear_moy   = np.mean(liste_ear) if liste_ear else 0
    nb_frames = len(liste_fps)

    print("\n" + "=" * 50)
    print("  RAPPORT DE VALIDATION — Session de détection")
    print("=" * 50)
    print(f"  Durée             : {duree:.1f} s")
    print(f"  Frames traitées   : {nb_frames}")
    print(f"  FPS moyen         : {fps_moy:.1f}")
    print(f"  FPS minimum       : {fps_min:.1f}")
    if fps_moy > 0:
        print(f"  Latence estimée   : {1000/fps_moy:.1f} ms")
    print(f"  EAR moyen         : {ear_moy:.3f}")
    print(f"  Alertes totales   : {nb_alertes}")
    print(f"  CSV               : {LOG_FICHIER}")
    print("-" * 50)

    checks = {
        "EF1  — FPS ≥ 15"         : fps_moy  >= 15,
        "EF2  — Visage détecté"   : nb_frames > 0,
        "EF3  — EAR calculé"      : ear_moy   > 0,
        "ENF1 — Latence < 1000ms" : fps_moy   >= 1,
        "ENF5 — Durée ≥ 30s"      : duree     >= 30,
    }
    for label, ok in checks.items():
        print(f"  {'✓' if ok else '✗'}  {label}")
    print("=" * 50)