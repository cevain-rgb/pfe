# main.py
# Point d'entrée — Détection de Somnolence au Volant
# Flux : Authentification faciale (LED) → Choix du pipeline → Surveillance
#
# Pipeline principal : YOLOv8 (.tflite) — détection.py YOLO
# Pipeline de secours : MediaPipe EAR/MAR — bascule automatique (FP7)
#
# Lancement :
#   python main.py
#
# Dépendances :
#   pip install opencv-python mediapipe numpy deepface ultralytics
#   pip install RPi.GPIO        # uniquement sur Raspberry Pi

import os

import buzzer
import led
from auth import authentifier_conducteur
from config import YOLO_MODEL_PATH
import db_context 


def choisir_pipeline():
    """
    Sélectionne le pipeline de détection :
    - YOLOv8 (.tflite) si le modèle est présent → pipeline principal
    - MediaPipe EAR/MAR sinon, ou en cas d'erreur → fallback (FP7)
    """
    if os.path.exists(YOLO_MODEL_PATH):
        try:
            from detection_yolo import lancer_detection_yolo
            print(f"[MAIN] Modèle YOLO trouvé ({YOLO_MODEL_PATH}) — pipeline principal activé.")
            return lancer_detection_yolo
        except Exception as e:
            print(f"[MAIN] Erreur chargement YOLO ({e}) — bascule sur le fallback.")

    from detection import lancer_detection
    print("[MAIN] Modèle YOLO absent — pipeline de secours MediaPipe activé.")
    return lancer_detection


def main():
    print("=" * 50)
    print("  Système de Détection de Somnolence au Volant")
    print("=" * 50)

    #  Étape 1 : Authentification faciale (LED)
    conducteur = authentifier_conducteur()
    if conducteur is None:
        print("[MAIN] Accès refusé — module arrêté.")
        led.nettoyer()
        return

    # ── Étape 2 : Choix du pipeline + surveillance ───
    pipeline = choisir_pipeline()
    print(f"[MAIN] Bienvenue {conducteur} — démarrage de la surveillance.")
    try:
        pipeline(conducteur)
    finally:
        led.nettoyer()
        buzzer.nettoyer()


if __name__ == "__main__":
    main()