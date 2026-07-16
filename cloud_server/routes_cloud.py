# cloud_server/routes_cloud.py
# Aligné sur les nouveaux modèles :
#   - Module (num_module Integer, statut Enum)
#   - Driver (nom + prenom séparés, email optionnel)
#   - LigneUtilisation (date_debut, date_fin, statut conducteur)

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, verify_jwt_in_request
)

from extensions import db
from models import Admin, Group, Module, Driver, LigneUtilisation, Alerte

api_bp = Blueprint("api_cloud", __name__)


# ══════════════════════════════════════════════════════
# AUTH ADMIN
# ══════════════════════════════════════════════════════

@api_bp.route("/auth/register", methods=["POST"])
def register_admin():
    data = request.get_json()
    nom, prenom = data.get("nom", ""), data.get("prenom", "")
    email, password = data.get("email"), data.get("password")
    if not email or not password:
        return jsonify({"erreur": "email et password requis"}), 400
    if Admin.query.filter_by(email=email).first():
        return jsonify({"erreur": "Email déjà utilisé"}), 409

    admin = Admin(
        nom=nom, prenom=prenom,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({"message": "Admin créé", "id": admin.id}), 201


@api_bp.route("/auth/login", methods=["POST"])
def login_admin():
    data = request.get_json()
    admin = Admin.query.filter_by(email=data.get("email")).first()
    if not admin or not check_password_hash(admin.password_hash, data.get("password", "")):
        return jsonify({"erreur": "Identifiants invalides"}), 401

    idt = str(admin.id)
    return jsonify({
        "access_token":  create_access_token(identity=idt),
        "refresh_token": create_refresh_token(identity=idt),
        "admin":         admin.to_dict()
    })


@api_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    return jsonify({"access_token": create_access_token(identity=get_jwt_identity())})


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def me():
    admin = Admin.query.get(int(get_jwt_identity()))
    if not admin:
        return jsonify({"erreur": "Admin introuvable"}), 404
    return jsonify(admin.to_dict())


# ══════════════════════════════════════════════════════
# GROUPES
# ══════════════════════════════════════════════════════

@api_bp.route("/groups", methods=["POST"])
@jwt_required()
def ajouter_groupe():
    admin_id = int(get_jwt_identity())
    data     = request.get_json()
    if not data.get("nom"):
        return jsonify({"erreur": "nom requis"}), 400

    groupe = Group(nom=data["nom"], admin_id=admin_id)
    db.session.add(groupe)
    db.session.commit()
    return jsonify(groupe.to_dict()), 201


@api_bp.route("/groups", methods=["GET"])
@jwt_required()
def liste_groupes():
    admin_id = int(get_jwt_identity())
    return jsonify([g.to_dict() for g in Group.query.filter_by(admin_id=admin_id).all()])


# ══════════════════════════════════════════════════════
# MODULES (Pi)
# ══════════════════════════════════════════════════════

@api_bp.route("/devices", methods=["POST"])
@jwt_required()
def ajouter_module():
    admin_id = int(get_jwt_identity())
    data     = request.get_json()
    num      = data.get("num_module")
    if num is None:
        return jsonify({"erreur": "num_module requis"}), 400

    group_id = data.get("group_id")
    if group_id:
        g = Group.query.get(group_id)
        if not g or g.admin_id != admin_id:
            return jsonify({"erreur": "Groupe non autorisé"}), 403

    module = Module(
        num_module=num,
        nom=data.get("nom", f"Module #{num}"),
        admin_id=admin_id,
        group_id=group_id,
        statut="inactif",
    )
    db.session.add(module)
    db.session.commit()
    return jsonify(module.to_dict()), 201


@api_bp.route("/devices", methods=["GET"])
@jwt_required()
def liste_modules():
    admin_id = int(get_jwt_identity())
    return jsonify([m.to_dict() for m in Module.query.filter_by(admin_id=admin_id).all()])


@api_bp.route("/devices/<int:module_id>/groupe", methods=["PUT"])
@jwt_required()
def assigner_module_groupe(module_id):
    admin_id = int(get_jwt_identity())
    module   = Module.query.get(module_id)
    if not module or module.admin_id != admin_id:
        return jsonify({"erreur": "Module non autorisé"}), 403

    group_id = request.get_json().get("group_id")
    if group_id:
        g = Group.query.get(group_id)
        if not g or g.admin_id != admin_id:
            return jsonify({"erreur": "Groupe non autorisé"}), 403

    module.group_id = group_id
    db.session.commit()
    return jsonify(module.to_dict())


@api_bp.route("/devices/<int:module_id>/statut", methods=["PUT"])
@jwt_required()
def changer_statut_module(module_id):
    """Permet de marquer un module actif/inactif depuis l'app admin."""
    admin_id = int(get_jwt_identity())
    module   = Module.query.get(module_id)
    if not module or module.admin_id != admin_id:
        return jsonify({"erreur": "Module non autorisé"}), 403

    statut = request.get_json().get("statut")
    if statut not in ("actif", "inactif"):
        return jsonify({"erreur": "statut invalide ('actif' ou 'inactif')"}), 400

    module.statut = statut
    db.session.commit()
    return jsonify(module.to_dict())


# ══════════════════════════════════════════════════════
# CONDUCTEURS
# ══════════════════════════════════════════════════════

@api_bp.route("/drivers", methods=["POST"])
@jwt_required()
def ajouter_driver():
    admin_id = int(get_jwt_identity())
    data     = request.get_json()
    nom, prenom = data.get("nom"), data.get("prenom")
    if not nom or not prenom:
        return jsonify({"erreur": "nom et prenom requis"}), 400

    group_id = data.get("group_id")
    if group_id:
        g = Group.query.get(group_id)
        if not g or g.admin_id != admin_id:
            return jsonify({"erreur": "Groupe non autorisé"}), 403

    driver = Driver(
        nom=nom, prenom=prenom,
        email=data.get("email"),
        embedding=json.dumps(data.get("embedding", [])),
        group_id=group_id,
    )
    db.session.add(driver)
    db.session.commit()
    return jsonify(driver.to_dict()), 201


@api_bp.route("/drivers/<int:driver_id>/groupe", methods=["PUT"])
@jwt_required()
def assigner_driver_groupe(driver_id):
    admin_id = int(get_jwt_identity())
    driver   = Driver.query.get(driver_id)
    if not driver:
        return jsonify({"erreur": "Conducteur introuvable"}), 404

    group_id = request.get_json().get("group_id")
    if group_id:
        g = Group.query.get(group_id)
        if not g or g.admin_id != admin_id:
            return jsonify({"erreur": "Groupe non autorisé"}), 403

    driver.group_id = group_id
    db.session.commit()
    return jsonify(driver.to_dict())


@api_bp.route("/drivers", methods=["GET"])
def liste_drivers():
    """
    Deux usages :
    1) Pi → GET /api/drivers?num_module=X  (sync, pas de JWT)
    2) Admin → GET /api/drivers?group_id=X (JWT requis)
    """
    num_module   = request.args.get("num_module",  type=int)
    group_id_qp  = request.args.get("group_id",    type=int)

    # ── Sync Pi ──────────────────────────────────────
    if num_module:
        module = Module.query.filter_by(num_module=num_module).first()
        if not module:
            return jsonify({"erreur": "Module inconnu"}), 404
        if not module.group_id:
            return jsonify([])

        module.last_sync = datetime.utcnow()
        module.statut    = "actif"
        db.session.commit()

        drivers = Driver.query.filter_by(group_id=module.group_id).all()
        return jsonify([
            {"name": f"{d.prenom} {d.nom}", "embedding": json.loads(d.embedding)}
            for d in drivers
        ])

    # ── Vue admin ────────────────────────────────────
    if group_id_qp:
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"erreur": "Authentification requise"}), 401

        admin_id = int(get_jwt_identity())
        g = Group.query.get(group_id_qp)
        if not g or g.admin_id != admin_id:
            return jsonify({"erreur": "Groupe non autorisé"}), 403

        drivers = Driver.query.filter_by(group_id=group_id_qp).all()
        return jsonify([d.to_dict() for d in drivers])

    return jsonify({"erreur": "num_module ou group_id requis"}), 400


# ══════════════════════════════════════════════════════
# SESSIONS DE CONDUITE (LigneUtilisation)
# ══════════════════════════════════════════════════════

@api_bp.route("/sessions", methods=["GET"])
@jwt_required()
def liste_sessions():
    """Sessions de conduite pour tous les conducteurs des groupes de l'admin."""
    admin_id = int(get_jwt_identity())
    groupes  = Group.query.filter_by(admin_id=admin_id).all()
    group_ids = [g.id for g in groupes]

    drivers = Driver.query.filter(Driver.group_id.in_(group_ids)).all()
    driver_ids = [d.id for d in drivers]

    limite   = request.args.get("limite", 50, type=int)
    sessions = LigneUtilisation.query\
        .filter(LigneUtilisation.driver_id.in_(driver_ids))\
        .order_by(LigneUtilisation.date_debut.desc())\
        .limit(limite).all()

    return jsonify([s.to_dict() for s in sessions])



@api_bp.route("/sessions/courante", methods=["GET"])
@jwt_required()
def session_courante():
    """Retourne la session en cours pour un conducteur."""
    admin_id = int(get_jwt_identity())
    driver_id = request.args.get("driver_id", type=int)
    
    if not driver_id:
        return jsonify({"erreur": "driver_id requis"}), 400
    
    driver = Driver.query.get(driver_id)
    if not driver:
        return jsonify({"erreur": "Conducteur introuvable"}), 404
    
    g = Group.query.get(driver.group_id)
    if not g or g.admin_id != admin_id:
        return jsonify({"erreur": "Conducteur non autorisé"}), 403
    
    session = LigneUtilisation.query.filter_by(
        driver_id=driver_id, date_fin=None
    ).first()
    
    if not session:
        return jsonify({"message": "Aucune session en cours"}), 404
    return jsonify(session.to_dict())


# ══════════════════════════════════════════════════════
# HEALTH & STATUS
# ══════════════════════════════════════════════════════

@api_bp.route("/health", methods=["GET"])
def health():
    """Vérifie que le serveur cloud est joignable."""
    return jsonify({"status": "ok"}), 200


@api_bp.route("/status", methods=["GET"])
def status():
    """
    État global du système :
    - Nombre de modules actifs
    - Nombre de conducteurs enregistrés
    - Sessions en cours
    """
    total_modules = Module.query.count()
    active_modules = Module.query.filter_by(statut="actif").count()
    total_drivers = Driver.query.count()
    sessions_en_cours = LigneUtilisation.query.filter_by(date_fin=None).count()
    
    return jsonify({
        "modules_total": total_modules,
        "modules_actifs": active_modules,
        "conducteurs_total": total_drivers,
        "sessions_en_cours": sessions_en_cours
    })


# ══════════════════════════════════════════════════════
# ALERTES
# ══════════════════════════════════════════════════════

@api_bp.route("/alertes", methods=["GET"])
@jwt_required()
def alertes():
    """
    Historique des alertes pour les conducteurs de l'admin,
    paginé et trié par date décroissante.
    """
    admin_id = int(get_jwt_identity())
    groupes  = Group.query.filter_by(admin_id=admin_id).all()
    group_ids = [g.id for g in groupes]

    drivers = Driver.query.filter(Driver.group_id.in_(group_ids)).all()
    driver_ids = [d.id for d in drivers]

    limite   = request.args.get("limite", 50, type=int)
    alertes_list = Alerte.query\
        .filter(Alerte.driver_id.in_(driver_ids))\
        .order_by(Alerte.timestamp.desc())\
        .limit(limite).all()
    
    return jsonify([a.to_dict() for a in alertes_list])


# ══════════════════════════════════════════════════════
# CONTRÔLES (BUZZER, LED, etc.)
# ══════════════════════════════════════════════════════

@api_bp.route("/buzzer/on", methods=["POST"])
@jwt_required()
def buzzer_on():
    """
    Déclenche le buzzer du module Pi via le syncing.
    À implémenter selon votre système de messaging.
    """
    module_id = request.get_json().get("module_id")
    if not module_id:
        return jsonify({"erreur": "module_id requis"}), 400
    
    admin_id = int(get_jwt_identity())
    module = Module.query.get(module_id)
    if not module or module.admin_id != admin_id:
        return jsonify({"erreur": "Module non autorisé"}), 403
    
    # TODO: Implémenter le système d'envoi de commandes au Pi
    # (WebSocket, Queue, API directe, etc.)
    
    return jsonify({"message": "Commande buzzer envoyée au module"}), 200


@api_bp.route("/buzzer/off", methods=["POST"])
@jwt_required()
def buzzer_off():
    """
    Arrête le buzzer du module Pi.
    À implémenter selon votre système de messaging.
    """
    module_id = request.get_json().get("module_id")
    if not module_id:
        return jsonify({"erreur": "module_id requis"}), 400
    
    admin_id = int(get_jwt_identity())
    module = Module.query.get(module_id)
    if not module or module.admin_id != admin_id:
        return jsonify({"erreur": "Module non autorisé"}), 403
    
    # TODO: Implémenter le système d'envoi de commandes au Pi
    
    return jsonify({"message": "Buzzer arrêté"}), 200
