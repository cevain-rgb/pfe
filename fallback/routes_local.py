# local_api/routes_local.py
# Endpoints API du serveur local (Plan Particulier)

import json
from flask import Blueprint, request, jsonify
import cv2
import numpy as np

from extensions import db
from models import Driver, Alert
from recognition import enregistrer_nouveau_conducteur, calculer_embedding
import state
import buzzer

api_bp = Blueprint("api_local", __name__)


@api_bp.route("/health", methods=["GET"])
def health():
    """Vérifie que le serveur Pi est joignable (utilisé par testConnexionPi)."""
    return jsonify({"status": "ok"}), 200


@api_bp.route("/inscription", methods=["POST"])
def inscription():
    """
    Inscription d'un conducteur — deux flux possibles :

    1) FLUX NORMAL (app mobile) : JSON { nom, embedding: [...] }
        L'embedding (192D, MobileFaceNet) est déjà calculé on-device,
        ce qui garantit la parité avec le modèle utilisé par le Pi
        en temps réel — voir recognition.py.

    2) FLUX DE TEST (sans app mobile) : multipart/form-data { nom, photo }
        Calcule l'embedding côté Pi avec le même modèle MobileFaceNet.
        Pratique pour tester l'authentification avant que l'app existe.
    """
    if request.is_json:
        data = request.get_json()
        nom = data.get("nom")
        embedding = data.get("embedding")

        if not nom or not embedding:
            return jsonify({"erreur": "Champs 'nom' et 'embedding' requis"}), 400

        driver = Driver(nom=nom, embedding=json.dumps(embedding), source="local")
        db.session.add(driver)
        db.session.commit()
        return jsonify({"message": f"Conducteur '{nom}' enregistré", "id": driver.id}), 201

    # ── Flux de test : photo brute, embedding calculé côté Pi ──
    nom = request.form.get("nom")
    photo = request.files.get("photo")

    if not nom or not photo:
        return jsonify({"erreur": "Champs 'nom' + 'photo' (ou JSON 'embedding') requis"}), 400

    img_bytes = np.frombuffer(photo.read(), np.uint8)
    frame = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

    ok = enregistrer_nouveau_conducteur(nom, frame)
    if not ok:
        return jsonify({"erreur": "Aucun visage détecté"}), 422

    return jsonify({"message": f"Conducteur '{nom}' enregistré (test Pi)"}), 201


@api_bp.route("/status", methods=["GET"])
def status():
    """
    État COURANT du conducteur — mis à jour à chaque frame par
    detection.py / detection_yolo.py via state.py.
    Reflète le vrai statut à l'instant T (Eveille, SOMNOLENCE, etc.)
    contrairement à /api/alertes qui ne liste que les événements passés.
    """
    return jsonify(state.lire())


@api_bp.route("/alertes", methods=["GET"])
def alertes():
    """Historique des alertes, paginé."""
    limite = request.args.get("limite", 50, type=int)
    historique = Alert.query.order_by(Alert.timestamp.desc()).limit(limite).all()
    return jsonify([a.to_dict() for a in historique])


@api_bp.route("/drivers", methods=["GET"])
def liste_drivers():
    """Liste des conducteurs enregistrés localement."""
    drivers = Driver.query.all()
    return jsonify([d.to_dict() for d in drivers])


@api_bp.route("/sessions", methods=["GET"])
def liste_sessions():
    """
    Historique des sessions de conduite (LigneUtilisation).
    Chaque session contient : conducteur, date_debut, date_fin,
    statut final et nombre d'alertes.
    """
    from models import LigneUtilisation
    limite = request.args.get("limite", 20, type=int)
    sessions = LigneUtilisation.query.order_by(
        LigneUtilisation.date_debut.desc()
    ).limit(limite).all()
    return jsonify([s.to_dict() for s in sessions])


@api_bp.route("/sessions/courante", methods=["GET"])
def session_courante():
    """Retourne la session en cours (statut temps réel du conducteur)."""
    from models import LigneUtilisation
    session = LigneUtilisation.query.filter_by(
        date_fin=None
    ).order_by(LigneUtilisation.date_debut.desc()).first()
    if not session:
        return jsonify({"message": "Aucune session en cours"}), 404
    return jsonify(session.to_dict())
def buzzer_on():
    """Déclenche le buzzer manuellement depuis l'app mobile."""
    buzzer.declencher_alerte("SOMNOLENCE")
    return jsonify({"message": "Buzzer activé"}), 200


@api_bp.route("/buzzer/off", methods=["POST"])
def buzzer_off():
    """Coupe le buzzer."""
    buzzer.arreter()
    return jsonify({"message": "Buzzer arrêté"}), 200