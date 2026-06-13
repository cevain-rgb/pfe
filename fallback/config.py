# Constantes globales du projet
# Modifier ces valeurs pour calibrer le système

#  Seuils de détection 
EAR_SEUIL = 0.25   # En dessous → œil considéré fermé
MAR_SEUIL = 0.90  # Au dessus  → bâillement détecté
FRAMES_CONSEC = 30     # Frames consécutives → somnolence (~2s à 15fps)

#  Seuils pose céphalique (degrés) 
POSE_SEUIL_YAW   = 20    # Rotation gauche/droite
POSE_SEUIL_PITCH = -20    # Inclinaison haut/bas
POSE_SEUIL_ROLL  = 15    #  Inclinaison gauche/droite

#  Caméra 
CAM_INDEX  = 0 
CAM_WIDTH  = 640
CAM_HEIGHT = 480
CAM_FPS    = 30

#  Indices landmarks MediaPipe
OEIL_GAUCHE = [362, 385, 387, 263, 373, 380]
OEIL_DROIT = [33,  160, 158, 133, 153, 144]
BOUCHE = [61, 291, 39, 181, 0, 17, 269, 405]
# POINTS_POSE = [1, 9, 57, 130, 287, 359] 
POINTS_POSE = [1, 152, 33, 263, 61, 291]

#  Fichier de log 
LOG_FICHIER = "alertes_log.csv"