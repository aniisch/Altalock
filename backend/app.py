"""Application Flask principale avec WebSocket"""
import os
import sys

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from backend.config import Config
from backend.routes import users_bp, settings_bp, logs_bp
from backend.services.face_recognition_service import get_face_service
from backend.services.alert_service import get_alert_service
from backend.services.security_service import get_security_service
from backend.models.database import get_db

# Créer l'application Flask
app = Flask(__name__)
app.config.from_object(Config)

# Activer CORS pour le développement
CORS(app, origins=["http://localhost:*", "file://*"])

# Configurer Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Enregistrer les blueprints
app.register_blueprint(users_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(logs_bp)


# --- Routes système ---

@app.route("/api/status", methods=["GET"])
def get_status():
    """Retourne l'état du système"""
    face_service = get_face_service()

    return jsonify({
        "status": "running",
        "detection_active": face_service.is_running,
        "camera_connected": face_service.camera is not None and face_service.camera.isOpened(),
        "encodings_loaded": len(face_service.known_encodings),
        "consecutive_unknown": face_service.consecutive_unknown
    })


@app.route("/api/detection/start", methods=["POST"])
def start_detection():
    """Démarre la détection"""
    face_service = get_face_service()

    if face_service.is_running:
        return jsonify({"message": "Détection déjà en cours"})

    # Charger les encodages
    count = face_service.load_encodings()

    if count == 0:
        return jsonify({
            "error": "Aucun visage enregistré. Ajoutez des utilisateurs d'abord."
        }), 400

    # Démarrer la caméra
    if not face_service.start_camera():
        return jsonify({"error": "Impossible d'accéder à la caméra"}), 500

    # Démarrer la boucle de détection
    face_service.start_detection_loop(
        frame_callback=on_frame,
        detection_callback=on_detection
    )

    return jsonify({
        "message": "Détection démarrée",
        "encodings_loaded": count
    })


@app.route("/api/detection/stop", methods=["POST"])
def stop_detection():
    """Arrête la détection"""
    face_service = get_face_service()

    face_service.stop_detection_loop()
    face_service.stop_camera()

    return jsonify({"message": "Détection arrêtée"})


@app.route("/api/import-legacy", methods=["POST"])
def import_legacy():
    """Importe les visages de l'ancienne application"""
    from backend.utils.helpers import import_legacy_faces

    legacy_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "RD-face_recognition-master", "imgs"
    )

    results = import_legacy_faces(legacy_dir)

    success_count = sum(1 for _, success, _ in results if success)
    failed_count = len(results) - success_count

    return jsonify({
        "message": f"Import terminé: {success_count} réussis, {failed_count} échoués",
        "results": [{"name": n, "success": s, "message": m} for n, s, m in results]
    })


@app.route("/api/system-info", methods=["GET"])
def system_info():
    """Informations système"""
    from backend.utils.helpers import get_system_info
    return jsonify(get_system_info())


# --- Callbacks WebSocket ---

def on_frame(frame_b64: str, detections: list):
    """Appelé pour chaque frame traité"""
    socketio.emit("frame", {
        "image": frame_b64,
        "faces": [
            {
                "user_id": d.user_id,
                "name": d.name,
                "is_owner": d.is_owner,
                "confidence": d.confidence,
                "box": d.box
            }
            for d in detections
        ]
    })


def on_detection(detections: list):
    """Appelé quand des visages sont détectés"""
    face_service = get_face_service()

    # Vérifier si une alerte doit être déclenchée
    if face_service.should_trigger_alert():
        alert_service = get_alert_service()
        security_service = get_security_service()

        # Trouver le nom de l'intrus
        intruder = next(
            (d for d in detections if not d.is_owner),
            detections[0] if detections else None
        )
        intruder_name = intruder.name if intruder else "Inconnu"

        # Capturer le frame actuel
        frame = face_service.get_frame()
        capture_path = None
        if frame is not None:
            capture_path = security_service.capture_frame(frame, "intrusion")

        # Déclencher l'alerte
        alert_service.trigger_alert(
            alert_type="intrusion",
            detected_name=intruder_name,
            image_path=capture_path,
            user_id=intruder.user_id if intruder else None
        )

        # Réponse de sécurité (verrouillage)
        security_result = security_service.trigger_security_response(
            frame=frame,
            detected_name=intruder_name
        )

        # Émettre l'événement d'alerte
        socketio.emit("alert", {
            "type": "intrusion",
            "message": f"Accès non autorisé: {intruder_name}",
            "locked": security_result["locked"],
            "capture_path": capture_path
        })

        # Réinitialiser le compteur
        face_service.reset_counters()


# --- Events WebSocket ---

@socketio.on("connect")
def handle_connect():
    """Client connecté"""
    print("Client WebSocket connecté")
    emit("status", {"connected": True})


@socketio.on("disconnect")
def handle_disconnect():
    """Client déconnecté"""
    print("Client WebSocket déconnecté")


@socketio.on("start_detection")
def handle_start_detection():
    """Démarre la détection via WebSocket"""
    face_service = get_face_service()

    if not face_service.is_running:
        count = face_service.load_encodings()

        if count == 0:
            emit("error", {"message": "Aucun visage enregistré"})
            return

        if not face_service.start_camera():
            emit("error", {"message": "Impossible d'accéder à la caméra"})
            return

        face_service.start_detection_loop(
            frame_callback=on_frame,
            detection_callback=on_detection
        )

    emit("status", {"detecting": True, "encodings": len(face_service.known_encodings)})


@socketio.on("stop_detection")
def handle_stop_detection():
    """Arrête la détection via WebSocket"""
    face_service = get_face_service()
    face_service.stop_detection_loop()
    face_service.stop_camera()
    emit("status", {"detecting": False})


@socketio.on("capture_face")
def handle_capture_face(data):
    """Capture un visage pour un utilisateur"""
    user_id = data.get("user_id")

    if not user_id:
        emit("error", {"message": "user_id requis"})
        return

    face_service = get_face_service()

    # S'assurer que la caméra est active
    if not face_service.camera or not face_service.camera.isOpened():
        if not face_service.start_camera():
            emit("error", {"message": "Impossible d'accéder à la caméra"})
            return

    frame = face_service.get_frame()

    if frame is None:
        emit("error", {"message": "Impossible de capturer le frame"})
        return

    encoding = face_service.encode_face_from_frame(frame)

    if encoding is None:
        emit("error", {"message": "Aucun visage détecté"})
        return

    from backend.models import UserModel
    from backend.config import FACES_DIR
    from datetime import datetime
    import cv2

    # Sauvegarder l'image
    user_dir = FACES_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = user_dir / f"capture_{timestamp}.jpg"
    cv2.imwrite(str(image_path), frame)

    # Sauvegarder l'encodage
    encoding_id = UserModel.add_face_encoding(user_id, encoding, str(image_path))
    face_service.load_encodings()

    emit("face_captured", {
        "encoding_id": encoding_id,
        "image_path": str(image_path)
    })


# --- Point d'entrée ---

def create_app():
    """Factory pour créer l'application"""
    # Initialiser la base de données
    get_db()
    return app, socketio


if __name__ == "__main__":
    app, socketio = create_app()
    print("Démarrage du serveur AltaLock...")
    print("API disponible sur http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=Config.DEBUG)
