"""
Script pour créer l'exécutable du backend AltaLock avec PyInstaller
Usage: python build_backend.py
"""
import os
import subprocess
import shutil
import sys
from pathlib import Path

def build():
    print("=" * 50)
    print("BUILD BACKEND - AltaLock v2.0")
    print("=" * 50)

    root = Path(__file__).parent

    # Créer le fichier d'entrée pour PyInstaller
    entry_file = root / "backend_entry.py"
    entry_content = '''# -*- coding: utf-8 -*-
"""Point d'entree pour le backend AltaLock"""
import sys
import os

# Ajouter le dossier parent au path pour les imports
if getattr(sys, 'frozen', False):
    # Si on est dans un exe PyInstaller
    base_path = sys._MEIPASS
    os.chdir(os.path.dirname(sys.executable))
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

# Configurer les chemins pour les donnees
os.environ["ALTALOCK_BASE_PATH"] = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else base_path

from backend.app import app, socketio
from backend.config import Config

if __name__ == "__main__":
    print("=" * 50)
    print("AltaLock Backend v2.0")
    print("=" * 50)
    print(f"API: http://127.0.0.1:5000")
    print("=" * 50)
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)
'''

    print(f"1. Creation du fichier d'entree: {entry_file}")
    with open(entry_file, 'w', encoding='utf-8') as f:
        f.write(entry_content)

    # Déterminer le séparateur pour --add-data selon l'OS
    sep = ";" if sys.platform == "win32" else ":"

    # Trouver le chemin des modèles face_recognition
    print("2. Recherche des modèles face_recognition...")
    import face_recognition_models
    models_path = Path(face_recognition_models.__file__).parent / "models"
    print(f"   Modèles trouvés: {models_path}")

    # Commande PyInstaller
    print("3. Lancement de PyInstaller...")

    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "altalock-backend",
        "--clean",
        "--noconfirm",
        # Hidden imports pour Flask et SocketIO
        "--hidden-import", "flask",
        "--hidden-import", "flask_socketio",
        "--hidden-import", "flask_cors",
        "--hidden-import", "engineio.async_drivers.threading",
        "--hidden-import", "socketio",
        "--hidden-import", "eventlet",
        "--hidden-import", "dns.resolver",
        "--hidden-import", "dns.rdatatype",
        # Hidden imports pour face_recognition
        "--hidden-import", "face_recognition",
        "--hidden-import", "face_recognition_models",
        "--hidden-import", "dlib",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        # Hidden imports pour alertes
        "--hidden-import", "pyttsx3",
        "--hidden-import", "pyttsx3.drivers",
        "--hidden-import", "pyttsx3.drivers.sapi5",
        # Hidden imports pour SQLite
        "--hidden-import", "sqlite3",
        # Ajouter les fichiers source
        f"--add-data", f"backend{sep}backend",
        # IMPORTANT: Ajouter les modèles face_recognition
        f"--add-data", f"{models_path}{sep}face_recognition_models/models",
        # Fichier d'entrée
        str(entry_file)
    ]

    result = subprocess.run(cmd, cwd=root)

    if result.returncode != 0:
        print("ERREUR: PyInstaller a échoué!")
        return False

    # Nettoyer le fichier temporaire
    print("4. Nettoyage du fichier temporaire...")
    if entry_file.exists():
        entry_file.unlink()
        print(f"   Supprimé: {entry_file}")

    print("")
    print("=" * 50)
    print("BUILD BACKEND TERMINÉ!")
    print("=" * 50)

    if sys.platform == "win32":
        print(f"Backend: dist/altalock-backend.exe")
    else:
        print(f"Backend: dist/altalock-backend")

    return True

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
