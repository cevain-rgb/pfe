# detection.py

import cv2
import time
import os
import urllib.request
import mediapipe as mp
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarker, FaceLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from mediapipe.tasks.python.core.base_options import BaseOptions

from config import (
    EAR_SEUIL, MAR_SEUIL, FRAMES_CONSEC,
    POSE_SEUIL_YAW, POSE_SEUIL_PITCH, POSE_SEUIL_ROLL,
    OEIL_GAUCHE, OEIL_DROIT, BOUCHE,
    CAM_INDEX, CAM_WIDTH, CAM_HEIGHT, CAM_FPS
)
from utils  import calculer_EAR, calculer_MAR, estimer_pose, pretraiter_frame
from logger import init_log, ecrire_log, rapport_final

MODEL_PATH = "face_landmarker.task"
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


# def telecharger_modele():
#     """Télécharge le modèle MediaPipe si absent."""
#     if not os.path.exists(MODEL_PATH):
#         print("[INFO] Téléchargement du modèle MediaPipe (~30 Mo)...")
#         urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
#         print("[OK]  Modèle prêt.")
#     else:
#         print("[OK]  Modèle déjà présent.")


def creer_landmarker():
    """Crée le détecteur de landmarks (mode VIDEO pour flux continu)."""
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionTaskRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.7,
        min_face_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    return FaceLandmarker.create_from_options(options)


def dessiner_landmarks(frame, landmarks, w, h):
    """Dessine les landmarks sur la frame via OpenCV."""
    for lm in landmarks:
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (x, y), 1, (0, 200, 0), -1)


def lancer_detection():
    """Lance la boucle de détection temps réel."""

    # telecharger_modele()
    landmarker = creer_landmarker()

    #  Initialisation caméra 
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAM_FPS)

    #  Compteurs d'état 
    cpt_yeux   = 0
    cpt_baille = 0
    cpt_tete_tomb = 0
    cpt_dist   = 0
    nb_alertes = 0

    #  Métriques de validation 
    liste_fps  = []
    liste_ear  = []
    t_debut    = time.time()

    init_log()
    print("[INFO] Détection démarrée - appuyez sur Q pour quitter.")

    with landmarker:
        while cap.isOpened():
            t0 = time.time()

            ret, frame = cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            frame = cv2.flip(frame, 1)

            #  Prétraitement 
            frame_traite = pretraiter_frame(frame)
            frame_rgb = cv2.cvtColor(frame_traite, cv2.COLOR_BGR2RGB)

            #  Détection landmarks (nouvelle API) 
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp_ms = int(time.time() * 1000)
            res = landmarker.detect_for_video(mp_image, timestamp_ms)

            ear, mar, pitch, yaw, roll = 0.0, 0.0, 0.0, 0.0, 0.0
            statut  = "Aucun visage"
            couleur = (128, 128, 128)

            if res.face_landmarks:
                lm = res.face_landmarks[0]  # liste de NormalizedLandmark

                # Calculs
                ear = (calculer_EAR(lm, OEIL_GAUCHE) + calculer_EAR(lm, OEIL_DROIT)) / 2
                mar = calculer_MAR(lm, BOUCHE)
                pitch, yaw, roll = estimer_pose(lm, w, h)
                liste_ear.append(ear)

                # Compteurs
                cpt_yeux = cpt_yeux + 1 if ear < EAR_SEUIL else 0
                # cpt_baille = cpt_baille + 1 if mar > MAR_SEUIL else max(0, cpt_baille - 1)
                cpt_baille = cpt_baille + 1 if mar > MAR_SEUIL else 0
                cpt_tete_tomb = cpt_tete_tomb + 1 if (pitch < POSE_SEUIL_PITCH or abs(roll) > POSE_SEUIL_ROLL) else 0
                cpt_dist = cpt_dist + 1 if abs(yaw) > POSE_SEUIL_YAW else 0

                # Décision
                if cpt_yeux >= FRAMES_CONSEC:
                    # Lancement de la sonnerie du buzzer(alerte rouge)
                    statut, couleur = "SOMNOLENCE", (0, 0, 255)
                    nb_alertes += 1
                    ecrire_log(statut, ear, mar, yaw, pitch, roll)
                elif cpt_baille >= 15 or cpt_tete_tomb >= 15 :
                    # Lancement de la sonnerie du buzzer(alerte orange)
                    statut, couleur = "FATIGUE", (0, 140, 255)
                    nb_alertes += 1
                    statut_fils = "BAILLEMENT" if cpt_baille >= 15 else "TETE_TOMBANTE"
                    ecrire_log(f"{statut}-{statut_fils}", ear, mar, yaw, pitch, roll)
                elif cpt_dist >= 15 :
                    # Lancement de la sonnerie du buzzer(alerte bleu)
                    statut, couleur = "DISTRACTION", (0, 0, 255)
                    nb_alertes += 1
                    ecrire_log(statut, ear, mar, yaw, pitch, roll)

                else:
                    statut, couleur = "Eveille", (0, 255, 0)

                dessiner_landmarks(frame, lm, w, h)

            #  FPS 
            fps = 1.0 / (time.time() - t0)
            liste_fps.append(fps)

            #  HUD 
            afficher_hud(frame, statut, couleur, ear, mar, yaw, pitch, roll, fps, nb_alertes)

            cv2.imshow("Detection Somnolence  (Q pour quitter)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    rapport_final(liste_fps, liste_ear, nb_alertes, time.time() - t_debut)


def afficher_hud(frame, statut, couleur, ear, mar, yaw, pitch, roll, fps, nb_alertes):
    """Affiche les métriques en temps réel sur la frame."""
    cv2.rectangle(frame, (0, 0), (310, 170), (30, 30, 30), -1)
    lignes = [
        (f"STATUT : {statut}", couleur),
        (f"EAR    : {ear:.3f}  (seuil {EAR_SEUIL})",  (255, 255, 255)),
        (f"MAR    : {mar:.3f}  (seuil {MAR_SEUIL})",  (255, 255, 255)),
        (f"Pitch / Roll : {pitch:.1f}°  /  {roll:.1f}°",(255, 255, 255)),
        (f"Yaw : {yaw:.1f}°",(255, 255, 255)),
        (f"FPS : {fps:.1f}   Alertes : {nb_alertes}",  (200, 200, 200)),
    ]
    for i, (texte, col) in enumerate(lignes):
        cv2.putText(frame, texte, (8, 28 + i * 26),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1)