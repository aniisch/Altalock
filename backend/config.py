"""Configuration de l'application AltaLock"""
import os
import sys
from pathlib import Path

# Déterminer si on est en mode production (exe PyInstaller)
IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    # Production: les données sont à côté de l'exe
    # sys.executable pointe vers altalock-backend.exe
    EXE_DIR = Path(sys.executable).parent
    BASE_DIR = EXE_DIR
    DATA_DIR = EXE_DIR / "data"
else:
    # Développement: structure normale du projet
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"

FACES_DIR = DATA_DIR / "faces"
CAPTURES_DIR = DATA_DIR / "captures"
DATABASE_PATH = DATA_DIR / "altalock.db"

# Créer les dossiers si nécessaire
DATA_DIR.mkdir(exist_ok=True)
FACES_DIR.mkdir(exist_ok=True)
CAPTURES_DIR.mkdir(exist_ok=True)

# Log des chemins pour debug
print(f"[CONFIG] IS_FROZEN: {IS_FROZEN}")
print(f"[CONFIG] BASE_DIR: {BASE_DIR}")
print(f"[CONFIG] DATA_DIR: {DATA_DIR}")
print(f"[CONFIG] DATABASE_PATH: {DATABASE_PATH}")

# Configuration Flask
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "altalock-dev-key-change-in-production")
    DEBUG = not IS_FROZEN and os.environ.get("DEBUG", "True").lower() == "true"

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
    "detection_threshold": "9",   # 3 secondes * 3 détections/sec
    "unknownThreshold": "9",      # 3 secondes * 3 détections/sec
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
    # SMTP settings (pour les alertes email) - configurables depuis l'UI
    "smtp_server": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_password": "",
}
