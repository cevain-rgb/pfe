# local_api/routes_local.py
# Endpoints API du serveur local (Plan Particulier)

import json
from flask import Blueprint, request, jsonify
import cv2
import numpy as np

from extensions import db
from models import Driver, Alert
from recognition import enregistrer_nouveau_conducteur

api = Blueprint("api_local", __name__)


@api.route("/inscription", methods=["POST"])
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

        driver = Driver(name=nom, embedding=json.dumps(embedding), source="local")
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


@api.route("/status", methods=["GET"])
def status():
    """État courant — dernière alerte enregistrée (polling depuis l'app)."""
    derniere = Alert.query.order_by(Alert.timestamp.desc()).first()
    if not derniere:
        return jsonify({"statut": "Eveille", "message": "Aucune alerte enregistrée"})
    return jsonify(derniere.to_dict())


@api.route("/alertes", methods=["GET"])
def alertes():
    """Historique des alertes, paginé."""
    limite = request.args.get("limite", 50, type=int)
    historique = Alert.query.order_by(Alert.timestamp.desc()).limit(limite).all()
    return jsonify([a.to_dict() for a in historique])


@api.route("/drivers", methods=["GET"])
def liste_drivers():
    """Liste des conducteurs enregistrés localement."""
    drivers = Driver.query.all()
    return jsonify([d.to_dict() for d in drivers])