# Constantes globales du projet
# Modifier ces valeurs pour calibrer le système

#  Seuils de détection 
EAR_SEUIL = 0.25   # En dessous → œil considéré fermé
MAR_SEUIL = 0.90  # Au dessus  → bâillement détecté
FRAMES_CONSEC = 3     # Frames consécutives → somnolence (~2s à 15fps)

#  Seuils pose céphalique (degrés) 
POSE_SEUIL_YAW   = 20    # Rotation gauche/droite
POSE_SEUIL_PITCH = -20    # Inclinaison haut/bas
POSE_SEUIL_ROLL  = 15    #  Inclinaison gauche/droite
FRAMES_CONSEC_POSE = 5

#  Caméra 
CAM_INDEX  = 1 
CAM_WIDTH  = 640
CAM_HEIGHT = 480
CAM_FPS    = 30
# CAM_WIDTH  = 224
# CAM_HEIGHT = 224
# CAM_FPS    = 5

#  Indices landmarks MediaPipe
OEIL_GAUCHE = [362, 385, 387, 263, 373, 380]
OEIL_DROIT = [33,  160, 158, 133, 153, 144]
BOUCHE = [61, 291, 39, 181, 0, 17, 269, 405]
# POINTS_POSE = [1, 9, 57, 130, 287, 359] 
POINTS_POSE = [1, 152, 33, 263, 61, 291]

#  Fichier de log 
LOG_FICHIER = "alertes_log.csv"

# ── Reconnaissance faciale — MobileFaceNet (TFLite) ──
# Même modèle que l'app mobile (parité obligatoire des embeddings)
FACE_EMBED_MODEL_PATH = "mobilefacenet.tflite"
FACE_EMBED_INPUT_SIZE = 112    # entrée 112x112x3
EMBEDDING_DIM         = 192    # taille du vecteur de sortie
DB_PATH               = "drivers.db"
SEUIL_RECONNAISSANCE  = 0.45  # ⚠️ valeur de départ — À CALIBRER empiriquement
TIMEOUT_AUTH          = 30     # secondes avant échec
LED_BLUE_PIN          = 18     # GPIO physique (numérotation BCM)
LED_RED_PIN           = 19 
LED_YELLOW_PIN        = 20 

# ── Buzzer (alerte sonore EF5) ───────────────────────
BUZZER_PIN = 24   # GPIO physique (numérotation BCM)

# ── Modèle YOLO (pipeline principal) ─────────────────
YOLO_MODEL_PATH = "best_int8.tflite"
YOLO_CONF_SEUIL = 0.4
YOLO_IMGZ = 352 

# ── Synchronisation Plan Entreprise ──────────────────
CLOUD_URL  = "http://192.168.43.108:8000"  # URL du serveur VPS
NUM_MODULE = 1    # numéro physique de CE Pi (inscrit sur le boîtier)