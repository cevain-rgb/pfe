# recognition.py
# Reconnaissance faciale — MobileFaceNet (TFLite)

import json

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import \
    VisionTaskRunningMode
from mediapipe.tasks.python.vision.face_landmarker import (
    FaceLandmarker, FaceLandmarkerOptions)

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    # Fallback PC si tflite-runtime n'est pas installé (dev hors Pi)
    import tensorflow.lite as tflite

from config import (FACE_EMBED_INPUT_SIZE, FACE_EMBED_MODEL_PATH,
                    SEUIL_RECONNAISSANCE)
from extensions import db
from models import Driver

MEDIAPIPE_MODEL_PATH = "face_landmarker.task"   # même fichier que detection.py

# ── Chargement paresseux des modèles (une seule fois) ──
_landmarker = None
_interpreter = None
_input_details = None
_output_details = None


def _get_landmarker():
    """MediaPipe en mode IMAGE (détection ponctuelle, pas de flux vidéo)."""
    global _landmarker
    if _landmarker is None:
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MEDIAPIPE_MODEL_PATH),
            running_mode=VisionTaskRunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.6,
        )
        _landmarker = FaceLandmarker.create_from_options(options)
    return _landmarker


def _get_interpreter():
    """Charge l'interpréteur TFLite MobileFaceNet une seule fois."""
    global _interpreter, _input_details, _output_details
    if _interpreter is None:
        _interpreter = tflite.Interpreter(model_path=FACE_EMBED_MODEL_PATH)
        _interpreter.allocate_tensors()
        _input_details = _interpreter.get_input_details()
        _output_details = _interpreter.get_output_details()
    return _interpreter, _input_details, _output_details


def _extraire_visage(frame):
    """
    Détecte le visage (MediaPipe) et retourne un crop recadré + redimensionné
    à FACE_EMBED_INPUT_SIZE, prêt pour l'embedder. None si aucun visage.
    """
    h, w = frame.shape[:2]
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

    res = _get_landmarker().detect(mp_image)
    if not res.face_landmarks:
        return None

    lm = res.face_landmarks[0]
    xs = [p.x * w for p in lm]
    ys = [p.y * h for p in lm]
    x_min, x_max = int(min(xs)), int(max(xs))
    y_min, y_max = int(min(ys)), int(max(ys))

    # Marge de 20% autour du visage détecté
    marge_x = int((x_max - x_min) * 0.2)
    marge_y = int((y_max - y_min) * 0.2)
    x_min = max(0, x_min - marge_x)
    y_min = max(0, y_min - marge_y)
    x_max = min(w, x_max + marge_x)
    y_max = min(h, y_max + marge_y)

    visage = frame[y_min:y_max, x_min:x_max]
    if visage.size == 0:
        return None

    return cv2.resize(visage, (FACE_EMBED_INPUT_SIZE, FACE_EMBED_INPUT_SIZE))


def calculer_embedding(frame):
    """
    Calcule l'embedding MobileFaceNet (192D) du visage détecté.
    Retourne None si aucun visage.

    ⚠️ Normalisation [-1, 1] = convention la plus courante pour
    MobileFaceNet/InsightFace. À VALIDER empiriquement avec le fichier
    .tflite réellement utilisé (cf. §calibration plus bas).
    """
    visage = _extraire_visage(frame)
    if visage is None:
        return None

    interpreter, input_details, output_details = _get_interpreter()

    img = cv2.cvtColor(visage, cv2.COLOR_BGR2RGB).astype(np.float32)
    img = (img - 127.5) / 128.0          # normalisation [-1, 1] — à vérifier
    img = np.expand_dims(img, axis=0)

    interpreter.set_tensor(input_details[0]['index'], img)
    interpreter.invoke()
    embedding = interpreter.get_tensor(output_details[0]['index'])[0]

    return embedding.tolist()


def distance_cosinus(emb1, emb2):
    """
    Distance cosinus entre deux embeddings.
    0.0 = identique | plus la valeur augmente, plus les visages diffèrent.
    """
    a = np.array(emb1)
    b = np.array(emb2)
    similarite = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    return 1 - similarite


def identifier_conducteur(frame):
    """
    Compare le visage de la frame avec tous les conducteurs en base.
    Fonctionne quelle que soit l'origine de l'embedding stocké (Pi ou
    mobile), tant que c'est le MÊME modèle MobileFaceNet des deux côtés.
    """
    embedding_live = calculer_embedding(frame)
    if embedding_live is None:
        return None, None

    conducteurs = Driver.query.all()
    if not conducteurs:
        return None, None

    meilleur_nom, meilleure_distance = None, float("inf")

    for driver in conducteurs:
        embedding_ref = json.loads(driver.embedding)
        d = distance_cosinus(embedding_live, embedding_ref)
        if d < meilleure_distance:
            meilleure_distance, meilleur_nom = d, driver.name

    if meilleure_distance < SEUIL_RECONNAISSANCE:
        return meilleur_nom, round(meilleure_distance, 4)

    return None, round(meilleure_distance, 4)


def enregistrer_nouveau_conducteur(nom, frame):
    """
    Inscription DEPUIS LE PI - utile pour tester avant que l'app mobile
    n'existe. En production, l'inscription normale passera par l'app
    (embedding déjà calculé on-device, voir routes_local.py).
    """
    embedding = calculer_embedding(frame)
    if embedding is None:
        print("[ERREUR] Aucun visage détecté pour l'inscription.")
        return False

    driver = Driver(name=nom, embedding=json.dumps(embedding), source="local")
    db.session.add(driver)
    db.session.commit()
    print(f"[DB] Conducteur '{nom}' enregistré.")
    return True