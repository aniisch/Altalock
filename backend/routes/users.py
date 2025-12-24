"""Routes API pour la gestion des utilisateurs"""
import os
import shutil
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from backend.models import UserModel
from backend.config import FACES_DIR
from backend.services.face_recognition_service import get_face_service

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@users_bp.route("", methods=["GET"])
def get_users():
    """Liste tous les utilisateurs"""
    active_only = request.args.get("active_only", "true").lower() == "true"
    users = UserModel.get_all(active_only=active_only)

    # Ajouter le nombre d'encodages pour chaque utilisateur
    for user in users:
        user["face_count"] = UserModel.count_face_encodings(user["id"])

    return jsonify({"users": users})


@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Détails d'un utilisateur"""
    user = UserModel.get_by_id(user_id)

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    user["face_count"] = UserModel.count_face_encodings(user_id)
    user["faces"] = UserModel.get_face_encodings(user_id)

    # Ne pas renvoyer les encodages bruts (trop volumineux)
    for face in user["faces"]:
        del face["encoding"]

    return jsonify(user)


@users_bp.route("", methods=["POST"])
def create_user():
    """Crée un nouvel utilisateur"""
    data = request.json

    if not data or not data.get("name"):
        return jsonify({"error": "Le nom est requis"}), 400

    user_id = UserModel.create(
        name=data["name"],
        email=data.get("email"),
        is_owner=data.get("is_owner", False)
    )

    return jsonify({
        "id": user_id,
        "message": "Utilisateur créé"
    }), 201


@users_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Met à jour un utilisateur"""
    data = request.json

    if not data:
        return jsonify({"error": "Données requises"}), 400

    success = UserModel.update(user_id, **data)

    if not success:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    return jsonify({"message": "Utilisateur mis à jour"})


@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Supprime un utilisateur"""
    user = UserModel.get_by_id(user_id)

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    # Supprimer les images associées
    user_faces_dir = FACES_DIR / str(user_id)
    if user_faces_dir.exists():
        shutil.rmtree(user_faces_dir)

    success = UserModel.delete(user_id)

    if success:
        # Recharger les encodages
        get_face_service().load_encodings()

    return jsonify({"message": "Utilisateur supprimé"})


@users_bp.route("/<int:user_id>/faces", methods=["POST"])
def add_face(user_id):
    """Ajoute un visage pour un utilisateur (via upload d'image)"""
    user = UserModel.get_by_id(user_id)

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if "image" not in request.files:
        return jsonify({"error": "Image requise"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "Aucun fichier sélectionné"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Format d'image non supporté"}), 400

    # Créer le dossier de l'utilisateur
    user_dir = FACES_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)

    # Sauvegarder l'image
    filename = secure_filename(file.filename)
    face_count = UserModel.count_face_encodings(user_id)
    image_path = user_dir / f"face_{face_count + 1}_{filename}"
    file.save(str(image_path))

    # Encoder le visage
    face_service = get_face_service()
    encoding = face_service.encode_face_from_image(str(image_path))

    if encoding is None:
        image_path.unlink()  # Supprimer l'image
        return jsonify({"error": "Aucun visage détecté dans l'image"}), 400

    # Sauvegarder l'encodage
    encoding_id = UserModel.add_face_encoding(user_id, encoding, str(image_path))

    # Recharger les encodages
    face_service.load_encodings()

    return jsonify({
        "id": encoding_id,
        "message": "Visage ajouté",
        "image_path": str(image_path)
    }), 201


@users_bp.route("/<int:user_id>/faces/capture", methods=["POST"])
def capture_face(user_id):
    """Capture un visage depuis la webcam"""
    user = UserModel.get_by_id(user_id)

    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    face_service = get_face_service()

    # S'assurer que la caméra est démarrée
    if not face_service.camera or not face_service.camera.isOpened():
        if not face_service.start_camera():
            return jsonify({"error": "Impossible d'accéder à la caméra"}), 500

    # Capturer un frame
    frame = face_service.get_frame()

    if frame is None:
        return jsonify({"error": "Impossible de capturer le frame"}), 500

    # Encoder le visage
    encoding = face_service.encode_face_from_frame(frame)

    if encoding is None:
        return jsonify({"error": "Aucun visage détecté"}), 400

    # Sauvegarder l'image
    user_dir = FACES_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = user_dir / f"capture_{timestamp}.jpg"

    import cv2
    cv2.imwrite(str(image_path), frame)

    # Sauvegarder l'encodage
    encoding_id = UserModel.add_face_encoding(user_id, encoding, str(image_path))

    # Recharger les encodages
    face_service.load_encodings()

    return jsonify({
        "id": encoding_id,
        "message": "Visage capturé",
        "image_path": str(image_path)
    }), 201


@users_bp.route("/<int:user_id>/faces/<int:face_id>", methods=["DELETE"])
def delete_face(user_id, face_id):
    """Supprime un encodage facial"""
    # Vérifier que l'utilisateur existe
    user = UserModel.get_by_id(user_id)
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    # Récupérer l'encodage pour supprimer l'image associée
    faces = UserModel.get_face_encodings(user_id)
    face_to_delete = next((f for f in faces if f["id"] == face_id), None)

    if not face_to_delete:
        return jsonify({"error": "Encodage non trouvé"}), 404

    # Supprimer l'image si elle existe
    if face_to_delete.get("image_path"):
        from pathlib import Path
        image_path = Path(face_to_delete["image_path"])
        if image_path.exists():
            image_path.unlink()

    # Supprimer l'encodage
    success = UserModel.delete_face_encoding(face_id)

    if success:
        # Recharger les encodages
        get_face_service().load_encodings()

    return jsonify({"message": "Visage supprimé"})


@users_bp.route("/owners", methods=["GET"])
def get_owners():
    """Liste les propriétaires (utilisateurs principaux)"""
    owners = UserModel.get_owners()
    return jsonify({"owners": owners})
