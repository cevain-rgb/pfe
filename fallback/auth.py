# auth.py
# Orchestration de l'authentification faciale au démarrage du module

import time

import cv2
import led
from config import CAM_HEIGHT, CAM_INDEX, CAM_WIDTH, TIMEOUT_AUTH
from recognition import identifier_conducteur


def authentifier_conducteur():
    """
    Lance la procédure d'authentification :
    - LED clignote pendant la recherche
    - Comparaison toutes les ~1s (DeepFace est coûteux en calcul)
    - LED fixe + retour du nom si succès
    - Timeout après TIMEOUT_AUTH secondes → échec

    Retourne le nom du conducteur (str) ou None si échec.
    """
    led.demarrer_clignotement()

    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    if not cap.isOpened():
        print("[AUTH] Impossible d'ouvrir la caméra.")
        led.eteindre()
        return None

    print("[AUTH] Recherche du conducteur...")
    t_debut = time.time()
    derniere_tentative = 0
    INTERVALLE_TENTATIVE = 1.0  # secondes entre 2 appels mobilefacenet

    while time.time() - t_debut < TIMEOUT_AUTH:
        ret, frame = cap.read()
        if not ret:
            continue

        maintenant = time.time()
        if maintenant - derniere_tentative >= INTERVALLE_TENTATIVE:
            derniere_tentative = maintenant
            nom, distance = identifier_conducteur(frame)

            if nom:
                print(f"[AUTH] ✅ Conducteur reconnu : {nom} (distance={distance})")
                cap.release()
                led.allumer_fixe()
                return nom
            elif distance is not None:
                print(f"[AUTH] Visage détecté, non reconnu (distance={distance})", end="\r")

    cap.release()
    led.eteindre()
    print("\n[AUTH] ❌ Échec — aucun conducteur reconnu dans le délai imparti.")
    return None