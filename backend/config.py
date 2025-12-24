"""Configuration de l'application AltaLock"""
import os
from pathlib import Path

# Chemins de base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FACES_DIR = DATA_DIR / "faces"
DATABASE_PATH = DATA_DIR / "altalock.db"

# Créer les dossiers si nécessaire
DATA_DIR.mkdir(exist_ok=True)
FACES_DIR.mkdir(exist_ok=True)

# Configuration Flask
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "altalock-dev-key-change-in-production")
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

    # Base de données
    DATABASE_PATH = str(DATABASE_PATH)

    # Reconnaissance faciale
    FACE_TOLERANCE = float(os.environ.get("FACE_TOLERANCE", "0.6"))
    FRAME_SKIP = int(os.environ.get("FRAME_SKIP", "2"))
    FRAME_SCALE = float(os.environ.get("FRAME_SCALE", "0.25"))

    # Sécurité
    DETECTION_THRESHOLD = int(os.environ.get("DETECTION_THRESHOLD", "4"))
    AUTO_LOCK = os.environ.get("AUTO_LOCK", "True").lower() == "true"

    # Alertes
    ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
    ALERT_MESSAGE = os.environ.get("ALERT_MESSAGE", "Accès non autorisé détecté")

    # SMTP (pour les alertes email)
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

    # Caméra
    CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))


# Paramètres par défaut pour la DB
DEFAULT_SETTINGS = {
    "detection_threshold": "4",
    "unknownThreshold": "3",
    "frame_skip": "2",
    "tolerance": "0.6",
    "alert_email": "",
    "alertEmail": "",
    "alert_message": "Accès non autorisé détecté",
    "camera_index": "0",
    "cameraSource": "0",
    "auto_lock": "true",
    "lockScreenEnabled": "true",
    "sleepAfterLock": "true",
    "soundAlert": "true",
}
