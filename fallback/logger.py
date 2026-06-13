# logger.py
# Journalisation horodatée des alertes (EF8)

import csv
from datetime import datetime
from config import LOG_FICHIER


def init_log():
    """Crée le fichier CSV avec les en-têtes."""
    with open(LOG_FICHIER, mode='w', newline='') as f:
        csv.writer(f).writerow([
            "timestamp", "type_alerte",
            "ear", "mar", "yaw", "pitch"
        ])
    print(f"[LOG] Fichier initialisé : {LOG_FICHIER}")


def ecrire_log(type_alerte, ear, mar, yaw, pitch, roll):
    """Enregistre une ligne d'alerte horodatée."""
    with open(LOG_FICHIER, mode='a', newline='') as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            type_alerte,
            round(ear,   4),
            round(mar,   4),
            round(yaw,   2),
            round(pitch, 2),
            round(roll, 2)
        ])


def rapport_final(liste_fps, liste_ear, nb_alertes, duree):
    """
    Affiche le rapport de validation en fin de test.
    Vérifie automatiquement les exigences du cahier des charges.
    """
    import numpy as np

    fps_moy = np.mean(liste_fps) if liste_fps else 0
    fps_min = np.min(liste_fps)  if liste_fps else 0
    ear_moy = np.mean(liste_ear) if liste_ear else 0
    nb_frames = len(liste_fps)

    print("\n" + "=" * 50)
    print("  RAPPORT DE VALIDATION — PoC Somnolence")
    print("=" * 50)
    print(f"  Durée du test     : {duree:.1f} s")
    print(f"  Frames traitées   : {nb_frames}")
    print(f"  FPS moyen         : {fps_moy:.1f}")
    print(f"  FPS minimum       : {fps_min:.1f}")
    print(f"  Latence estimée   : {1000/fps_moy:.1f} ms" if fps_moy > 0 else "  Latence estimée   : N/A")
    print(f"  EAR moyen         : {ear_moy:.3f}")
    print(f"  Alertes totales   : {nb_alertes}")
    print(f"  Logs sauvegardés  : {LOG_FICHIER}")
    print("-" * 50)

    checks = {
        "EF1  — FPS ≥ 15"         : fps_moy >= 15,
        "EF2  — Visage détecté"   : nb_frames > 0,
        "EF3  — EAR calculé"      : ear_moy  > 0,
        "ENF1 — Latence < 1000ms" : fps_moy  >= 1,
        "ENF5 — Durée ≥ 30s"      : duree    >= 30,
    }
    for label, ok in checks.items():
        print(f"  {'✓' if ok else '✗'}  {label}")
    print("=" * 50)