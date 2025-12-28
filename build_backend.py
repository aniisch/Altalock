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

    # Trouver les DLLs cuDNN (nécessaires pour dlib avec CUDA)
    cudnn_dlls = []
    if sys.platform == "win32":
        print("2b. Recherche des DLLs cuDNN...")
        conda_prefix = os.environ.get("CONDA_PREFIX", "")
        cuda_path = os.environ.get("CUDA_PATH", "")

        search_paths = [
            Path(conda_prefix) / "Library" / "bin" if conda_prefix else None,
            Path(cuda_path) / "bin" if cuda_path else None,
            Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.8/bin"),
            Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.0/bin"),
        ]

        for search_path in search_paths:
            if search_path and search_path.exists():
                for dll in search_path.glob("cudnn*.dll"):
                    cudnn_dlls.append(dll)
                    size_mb = dll.stat().st_size / (1024 * 1024)
                    print(f"   Trouvé: {dll.name} ({size_mb:.0f} Mo)")
                if cudnn_dlls:
                    break  # On a trouvé les DLLs, pas besoin de chercher ailleurs

        if not cudnn_dlls:
            print("   ATTENTION: Aucune DLL cuDNN trouvée! L'exe pourrait ne pas fonctionner.")
        else:
            total_size = sum(dll.stat().st_size for dll in cudnn_dlls) / (1024 * 1024)
            print(f"   Total DLLs cuDNN: {total_size:.0f} Mo")

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
    ]

    # Ajouter les DLLs cuDNN si trouvées
    for dll in cudnn_dlls:
        cmd.extend(["--add-binary", f"{dll}{sep}."])

    # Fichier d'entrée (doit être à la fin)
    cmd.append(str(entry_file))

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
