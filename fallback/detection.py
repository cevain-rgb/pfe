# detection.py — Pipeline FALLBACK MediaPipe
# Écriture alerte uniquement à la TRANSITION vers un nouvel état d'alerte

import cv2
import time
import mediapipe as mp
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarker, FaceLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from mediapipe.tasks.python.core.base_options import BaseOptions

from config import (
    EAR_SEUIL, MAR_SEUIL, FRAMES_CONSEC, FRAMES_CONSEC_POSE,
    POSE_SEUIL_YAW, POSE_SEUIL_PITCH, POSE_SEUIL_ROLL,
    OEIL_GAUCHE, OEIL_DROIT, BOUCHE,
    CAM_INDEX, CAM_WIDTH, CAM_HEIGHT, CAM_FPS
)
from utils         import calculer_EAR, calculer_MAR, estimer_pose, pretraiter_frame
from logger        import init_log, ecrire_log, rapport_final
import buzzer
import led
import state
import session_manager

MODEL_PATH = "face_landmarker.task"


def creer_landmarker():
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
    for lm in landmarks:
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 1, (0, 200, 0), -1)


def lancer_detection(conducteur="Inconnu"):
    landmarker = creer_landmarker()

    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          CAM_FPS)

    if not cap.isOpened():
        print(f"[ERREUR] Impossible d'ouvrir la caméra (index {CAM_INDEX})")
        return

    time.sleep(1.0)
    for _ in range(10):
        cap.read()

    cpt_yeux      = 0
    cpt_baille    = 0
    cpt_tete_tomb = 0
    cpt_dist      = 0
    nb_alertes    = 0

    # ── Suivi de transition ──────────────────────────
    # Écriture en base + buzzer UNIQUEMENT quand on ENTRE dans un état d'alerte
    statut_precedent = "Eveille"

    liste_fps = []
    liste_ear = []
    t_debut   = time.time()

    init_log()
    print(f"[INFO] Détection démarrée pour '{conducteur}' — Q pour quitter.")

    with landmarker:
        while cap.isOpened():
            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            frame = cv2.flip(frame, 1)

            frame_traite = pretraiter_frame(frame)
            frame_rgb    = cv2.cvtColor(frame_traite, cv2.COLOR_BGR2RGB)
            mp_image     = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            res          = landmarker.detect_for_video(mp_image, int(time.time() * 1000))

            ear, mar, pitch, yaw, roll = 0.0, 0.0, 0.0, 0.0, 0.0
            statut, couleur = "Aucun visage", (128, 128, 128)

            if res.face_landmarks:
                lm = res.face_landmarks[0]

                ear   = (calculer_EAR(lm, OEIL_GAUCHE) + calculer_EAR(lm, OEIL_DROIT)) / 2
                mar   = calculer_MAR(lm, BOUCHE)
                pitch, yaw, roll = estimer_pose(lm, w, h)
                liste_ear.append(ear)

                cpt_yeux      = cpt_yeux      + 1 if ear < EAR_SEUIL else 0
                cpt_baille    = cpt_baille    + 1 if mar > MAR_SEUIL else 0
                cpt_tete_tomb = cpt_tete_tomb + 1 if (pitch < POSE_SEUIL_PITCH or abs(roll) > POSE_SEUIL_ROLL) else 0
                cpt_dist      = cpt_dist      + 1 if abs(yaw) > POSE_SEUIL_YAW else 0

                # ── Calcul du nouveau statut ─────────
                if cpt_yeux >= FRAMES_CONSEC:
                    statut, couleur = "SOMNOLENCE", (0, 0, 255)
                elif cpt_baille >= FRAMES_CONSEC_POSE or cpt_tete_tomb >= FRAMES_CONSEC_POSE:
                    sous = "BAILLEMENT" if cpt_baille >= FRAMES_CONSEC_POSE else "TETE_TOMBANTE"
                    statut, couleur = f"FATIGUE-{sous}", (0, 140, 255)
                elif cpt_dist >= FRAMES_CONSEC_POSE:
                    statut, couleur = "DISTRACTION", (255, 0, 0)
                else:
                    statut, couleur = "Eveille", (0, 255, 0)

                # ── Transition → action une seule fois ─
                if statut != statut_precedent:
                    if statut != "Eveille":
                        # Entrée dans un état d'alerte
                        nb_alertes += 1
                        ecrire_log(statut, ear, mar, yaw, pitch, roll, conducteur)
                        buzzer.declencher_alerte(
                            "SOMNOLENCE" if "SOMNOLENCE" in statut
                            else "FATIGUE"  if "FATIGUE"    in statut
                            else "DISTRACTION"
                        )
                    statut_precedent = statut

                dessiner_landmarks(frame, lm, w, h)

            # ── Mise à jour session + état partagé ───
            session_manager.mettre_a_jour_statut(statut)
            fps = 1.0 / (time.time() - t0)
            liste_fps.append(fps)
            state.mettre_a_jour(conducteur, statut, ear, mar, yaw, pitch, roll, fps, nb_alertes)

            # afficher_hud(frame, conducteur, statut, couleur, ear, mar, yaw, pitch, roll, fps, nb_alertes)
            # cv2.imshow("Detection Somnolence  (Q pour quitter)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    buzzer.arreter()
    state.reinitialiser()
    rapport_final(liste_fps, liste_ear, nb_alertes, time.time() - t_debut)


def afficher_hud(frame, conducteur, statut, couleur, ear, mar, yaw, pitch, roll, fps, nb_alertes):
    cv2.rectangle(frame, (0, 0), (330, 195), (30, 30, 30), -1)
    lignes = [
        (f"Conducteur : {conducteur}",                    (255, 200, 0)),
        (f"STATUT : {statut}",                            couleur),
        (f"EAR    : {ear:.3f}  (seuil {EAR_SEUIL})",      (255, 255, 255)),
        (f"MAR    : {mar:.3f}  (seuil {MAR_SEUIL})",      (255, 255, 255)),
        (f"Pitch / Roll : {pitch:.1f}°  /  {roll:.1f}°",  (255, 255, 255)),
        (f"Yaw : {yaw:.1f}°",                              (255, 255, 255)),
        (f"FPS : {fps:.1f}   Alertes : {nb_alertes}",      (200, 200, 200)),
    ]
    for i, (texte, col) in enumerate(lignes):
        cv2.putText(frame, texte, (8, 28 + i * 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1)
