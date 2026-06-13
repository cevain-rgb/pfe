# Fonctions de calcul : EAR, MAR, Pose de la tete

import cv2
import numpy as np
from config import POINTS_POSE

""" calcule de la distance entre deux points """
def dist(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def calculer_EAR(landmarks, indices):
    """
    Eye Aspect Ratio - Soukupová & Čech (2016)
    EAR = (||p2-p6|| + ||p3-p5||) / (2 × ||p1-p4||)
    Ouvert ≈ 0.30  |  Fermé ≈ 0.00  |  Seuil somnolence < 0.25
    """
    pts = [(landmarks[i].x, landmarks[i].y) for i in indices]
    A = dist(pts[1], pts[5])
    B = dist(pts[2], pts[4])
    C = dist(pts[0], pts[3])
    return (A + B) / (2.0 * C) if C != 0 else 0.0


def calculer_MAR(landmarks, indices):
    """
    Mouth Aspect Ratio
    Fermée ≈ 0.25 | Bâillement > 0.60
    """
    pts = [(landmarks[i].x, landmarks[i].y) for i in indices]
    A = dist(pts[2], pts[6])
    B = dist(pts[3], pts[5])
    C = dist(pts[0], pts[4])
    horiz = dist(pts[0], pts[1])
    return (A + B + C) / (2.0 * horiz) if horiz != 0 else 0.0


def estimer_pose(landmarks, w, h):
    """
    Estimation Pitch / Yaw / Roll via méthode PnP (OpenCV solvePnP).
    Utilisé pour la détection de la fatigue(Pitch/Yaw) et la distraction(Roll) (EF4).
    """
    model_3d = np.array([
        [ 0.0,   0.0,   0.0 ],
        [ 0.0, -63.6, -12.5 ],
        [-43.3,  32.7, -26.0],
        [ 43.3,  32.7, -26.0],
        [-28.9, -28.9, -24.1],
        [ 28.9, -28.9, -24.1],
    ], dtype=np.float64)

    pts_2d = np.array([
        (landmarks[i].x * w, landmarks[i].y * h)
        for i in POINTS_POSE
    ], dtype=np.float64)

    focal = float(w)
    K = np.array([
        [focal, 0,     w/2],
        [0,     focal, h/2],
        [0,     0,     1  ]
    ], dtype=np.float64)

    ok, rvec, _ = cv2.solvePnP(
        model_3d, pts_2d, K,
        np.zeros((4, 1)),
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not ok:
        return 0.0, 0.0, 0.0

    rmat, _ = cv2.Rodrigues(rvec)
    angles, *_ = cv2.RQDecomp3x3(rmat)
    return angles[0], angles[1], angles[2]  # pitch, yaw, roll


def pretraiter_frame(frame):
    """
    Égalisation CLAHE sur canal L (LAB).
    Améliore la robustesse en faible luminosité.
    """
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return cv2.cvtColor(cv2.merge([clahe.apply(l), a, b]), cv2.COLOR_LAB2BGR)