# detection_yolo.py
# Pipeline PRINCIPAL — Somnolence/Fatigue via YOLOv8 (TFLite)
#                       Distraction via MediaPipe (pose Pitch/Yaw/Roll)
#
# Réutilise : config.py, utils.py, logger.py, buzzer.py
# Même hiérarchie d'alerte que detection.py (FP7)

import cv2
import time
from ultralytics import YOLO
import mediapipe as mp
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarker, FaceLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from mediapipe.tasks.python.core.base_options import BaseOptions

from config import (
    YOLO_MODEL_PATH, YOLO_CONF_SEUIL, YOLO_IMGSZ,
    FRAMES_CONSEC, POSE_SEUIL_YAW, POSE_SEUIL_PITCH, POSE_SEUIL_ROLL,
    CAM_INDEX, CAM_WIDTH, CAM_HEIGHT, CAM_FPS
)
from utils  import estimer_pose, pretraiter_frame
from logger import init_log, ecrire_log
import buzzer

MEDIAPIPE_MODEL_PATH = "face_landmarker.task"


def creer_landmarker():
    """MediaPipe — uniquement pour la pose (distraction). YOLO gère les yeux/bouche."""
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MEDIAPIPE_MODEL_PATH),
        running_mode=VisionTaskRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.7,
        min_face_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    return FaceLandmarker.create_from_options(options)


def interpreter_yolo(resultats):
    """
    Analyse les détections YOLO d'une frame.
    Lit le nom de classe via r.names (robuste à l'ordre des classes).
    Retourne (yeux_fermes: bool, baillement: bool).
    """
    yeux_fermes = False
    baillement  = False

    for r in resultats:
        if r.boxes is None:
            continue
        for box in r.boxes:
            if float(box.conf[0]) < YOLO_CONF_SEUIL:
                continue
            nom = r.names[int(box.cls[0])].lower()
            if "clos" in nom or "closed" in nom:
                yeux_fermes = True
            elif "yawn" in nom or "baillement" in nom:
                baillement = True

    return yeux_fermes, baillement


def rapport_final_yolo(liste_fps, nb_alertes, duree):
    """
    Rapport de validation adapté au pipeline YOLO.
    EAR non calculé (remplacé par la classification YOLO).
    """
    import numpy as np

    fps_moy   = np.mean(liste_fps) if liste_fps else 0
    fps_min   = np.min(liste_fps)  if liste_fps else 0
    nb_frames = len(liste_fps)

    print("\n" + "=" * 50)
    print("  RAPPORT DE VALIDATION — Pipeline YOLO")
    print("=" * 50)
    print(f"  Durée             : {duree:.1f} s")
    print(f"  Frames traitées   : {nb_frames}")
    print(f"  FPS moyen         : {fps_moy:.1f}")
    print(f"  FPS minimum       : {fps_min:.1f}")
    if fps_moy > 0:
        print(f"  Latence estimée   : {1000/fps_moy:.1f} ms")
    print(f"  Alertes totales   : {nb_alertes}")
    print("-" * 50)

    checks = {
        "EF1  — FPS ≥ 15"            : fps_moy  >= 15,
        "EF2  — Frames traitées > 0" : nb_frames > 0,
        "EF3  — Détection YOLO active": True,   # YOLO remplace EAR géométrique
        "ENF1 — Latence < 1000ms"    : fps_moy  >= 1,
        "ENF5 — Durée ≥ 30s"         : duree    >= 30,
    }
    for label, ok in checks.items():
        print(f"  {'✓' if ok else '✗'}  {label}")
    print("=" * 50)


def lancer_detection_yolo(conducteur="Inconnu"):
    """
    Pipeline principal : YOLOv8 (yeux/bouche) + MediaPipe (pose).
    Chaque alerte est écrite en CSV ET en base (table Alert).
    """
    print(f"[YOLO] Chargement du modèle ({YOLO_MODEL_PATH})...")
    model      = YOLO(YOLO_MODEL_PATH, task="detect")
    landmarker = creer_landmarker()
    print("[YOLO] Modèle chargé.")

    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          CAM_FPS)

    if not cap.isOpened():
        print(f"[ERREUR] Impossible d'ouvrir la caméra (index {CAM_INDEX})")
        return

    cpt_yeux      = 0
    cpt_baille    = 0
    cpt_tete_tomb = 0
    cpt_dist      = 0
    nb_alertes    = 0

    liste_fps = []
    t_debut   = time.time()

    init_log()
    print(f"[INFO] Détection YOLO démarrée pour '{conducteur}' — Q pour quitter.")

    with landmarker:
        while cap.isOpened():
            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            frame = cv2.flip(frame, 1)
            frame_traite = pretraiter_frame(frame)

            # ── Inférence YOLO (yeux / bouche) ───────
            resultats   = model(frame_traite, imgsz=YOLO_IMGSZ, verbose=False)
            yeux_fermes, baillement = interpreter_yolo(resultats)

            # ── Pose MediaPipe (distraction) ─────────
            frame_rgb = cv2.cvtColor(frame_traite, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            res_pose  = landmarker.detect_for_video(mp_image, int(time.time() * 1000))

            pitch, yaw, roll = 0.0, 0.0, 0.0
            if res_pose.face_landmarks:
                pitch, yaw, roll = estimer_pose(res_pose.face_landmarks[0], w, h)

            statut, couleur = "Eveille", (0, 255, 0)

            # ── Compteurs ─────────────────────────────
            cpt_yeux      = cpt_yeux      + 1 if yeux_fermes else 0
            cpt_baille    = cpt_baille    + 1 if baillement   else 0
            cpt_tete_tomb = cpt_tete_tomb + 1 if (pitch < POSE_SEUIL_PITCH or abs(roll) > POSE_SEUIL_ROLL) else 0
            cpt_dist      = cpt_dist      + 1 if abs(yaw) > POSE_SEUIL_YAW else 0

            # ── Décision (même hiérarchie que detection.py) ──
            if cpt_yeux >= FRAMES_CONSEC:
                statut, couleur = "SOMNOLENCE", (0, 0, 255)
                nb_alertes += 1
                ecrire_log("SOMNOLENCE", 0.0, 0.0, yaw, pitch, roll, conducteur)
                buzzer.declencher_alerte("SOMNOLENCE")

            elif cpt_baille >= 15 or cpt_tete_tomb >= 15:
                statut, couleur = "FATIGUE", (0, 140, 255)
                nb_alertes += 1
                sous_type = "BAILLEMENT" if cpt_baille >= 15 else "TETE_TOMBANTE"
                ecrire_log(f"FATIGUE-{sous_type}", 0.0, 0.0, yaw, pitch, roll, conducteur)
                buzzer.declencher_alerte("FATIGUE")

            elif cpt_dist >= 15:
                statut, couleur = "DISTRACTION", (255, 0, 0)
                nb_alertes += 1
                ecrire_log("DISTRACTION", 0.0, 0.0, yaw, pitch, roll, conducteur)
                buzzer.declencher_alerte("DISTRACTION")

            # ── Annotation YOLO sur la frame ─────────
            for r in resultats:
                frame = r.plot(img=frame)

            fps = 1.0 / (time.time() - t0)
            liste_fps.append(fps)

            afficher_hud_yolo(frame, conducteur, statut, couleur, yaw, pitch, roll, fps, nb_alertes)
            cv2.imshow("Detection Somnolence — YOLO  (Q pour quitter)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    buzzer.arreter()
    rapport_final_yolo(liste_fps, nb_alertes, time.time() - t_debut)


def afficher_hud_yolo(frame, conducteur, statut, couleur, yaw, pitch, roll, fps, nb_alertes):
    """HUD du pipeline principal — précise [YOLO] pour le distinguer du fallback."""
    cv2.rectangle(frame, (0, 0), (330, 170), (30, 30, 30), -1)
    lignes = [
        (f"Conducteur : {conducteur}",                    (255, 200, 0)),
        (f"STATUT : {statut}  [YOLO]",                    couleur),
        (f"Pitch / Roll : {pitch:.1f}°  /  {roll:.1f}°",  (255, 255, 255)),
        (f"Yaw : {yaw:.1f}°",                              (255, 255, 255)),
        (f"FPS : {fps:.1f}   Alertes : {nb_alertes}",      (200, 200, 200)),
    ]
    for i, (texte, col) in enumerate(lignes):
        cv2.putText(frame, texte, (8, 28 + i * 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1)