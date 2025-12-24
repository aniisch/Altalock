"""Fonctions utilitaires"""
import shutil
from pathlib import Path
from typing import List, Tuple

from backend.config import FACES_DIR
from backend.models import UserModel
from backend.services.face_recognition_service import get_face_service


def import_legacy_faces(legacy_dir: str) -> List[Tuple[str, bool, str]]:
    """
    Importe les visages depuis l'ancienne application.

    Args:
        legacy_dir: Chemin vers le dossier contenant les images .jpg

    Returns:
        Liste de tuples (nom, succès, message)
    """
    legacy_path = Path(legacy_dir)
    results = []

    if not legacy_path.exists():
        return [("", False, f"Dossier {legacy_dir} non trouvé")]

    face_service = get_face_service()

    # Chercher tous les fichiers .jpg
    for image_path in legacy_path.glob("*.jpg"):
        name = image_path.stem  # nom sans extension

        # Ignorer les fichiers de capture
        if name.startswith("capture"):
            continue

        try:
            # Vérifier si l'utilisateur existe déjà
            existing_users = UserModel.get_all(active_only=False)
            existing_user = next(
                (u for u in existing_users if u["name"].lower() == name.lower()),
                None
            )

            if existing_user:
                user_id = existing_user["id"]
            else:
                # Créer l'utilisateur (le premier est owner par défaut si c'est "anis")
                is_owner = name.lower() == "anis"
                user_id = UserModel.create(name=name, is_owner=is_owner)

            # Créer le dossier utilisateur
            user_dir = FACES_DIR / str(user_id)
            user_dir.mkdir(exist_ok=True)

            # Copier l'image
            dest_path = user_dir / f"imported_{image_path.name}"
            shutil.copy2(image_path, dest_path)

            # Encoder le visage
            encoding = face_service.encode_face_from_image(str(dest_path))

            if encoding is not None:
                UserModel.add_face_encoding(user_id, encoding, str(dest_path))
                results.append((name, True, "Importé avec succès"))
            else:
                dest_path.unlink()  # Supprimer l'image si pas de visage
                results.append((name, False, "Aucun visage détecté"))

        except Exception as e:
            results.append((name, False, str(e)))

    # Recharger les encodages
    face_service.load_encodings()

    return results


def get_system_info() -> dict:
    """Retourne des informations sur le système"""
    import platform
    import cv2

    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "opencv_version": cv2.__version__,
    }

    # Tester la disponibilité de la caméra
    try:
        cap = cv2.VideoCapture(0)
        info["camera_available"] = cap.isOpened()
        if cap.isOpened():
            info["camera_width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            info["camera_height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
    except Exception:
        info["camera_available"] = False

    return info
