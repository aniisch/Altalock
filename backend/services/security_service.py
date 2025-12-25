"""Service de sécurité (verrouillage Windows, captures)"""
import cv2
import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np

from backend.config import DATA_DIR
from backend.models.settings import SettingsModel
from backend.models.database import get_db


class SecurityService:
    """Service de gestion de la sécurité système"""

    def __init__(self):
        self.captures_dir = DATA_DIR / "captures"
        self.captures_dir.mkdir(exist_ok=True)

    def lock_workstation(self) -> bool:
        """Verrouille la session Windows"""
        # Vérifier le paramètre (supporter les deux noms)
        lock_enabled = SettingsModel.get_bool("lockScreenEnabled")
        if lock_enabled is None:
            lock_enabled = SettingsModel.get_bool("auto_lock")

        if not lock_enabled:
            print("Verrouillage désactivé dans les paramètres")
            return False

        if platform.system() != "Windows":
            print("Le verrouillage n'est disponible que sur Windows")
            return False

        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return True
        except Exception as e:
            print(f"Erreur verrouillage: {e}")
            return False

    def capture_frame(self, frame: np.ndarray, prefix: str = "capture") -> Optional[str]:
        """
        Sauvegarde un frame comme image

        Args:
            frame: Image numpy (BGR)
            prefix: Préfixe du nom de fichier

        Returns:
            Nom du fichier sauvegardé (pas le chemin complet)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.jpg"
        filepath = self.captures_dir / filename

        try:
            cv2.imwrite(str(filepath), frame)
            # Retourner seulement le nom du fichier, pas le chemin complet
            return filename
        except Exception as e:
            print(f"Erreur capture: {e}")
            return None

    def capture_screenshot(self) -> Optional[str]:
        """Capture l'écran complet (Windows uniquement)"""
        if platform.system() != "Windows":
            return None

        try:
            import mss
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = self.captures_dir / filename

            with mss.mss() as sct:
                sct.shot(output=str(filepath))

            return str(filepath)
        except ImportError:
            print("mss non installé, capture d'écran non disponible")
            return None
        except Exception as e:
            print(f"Erreur screenshot: {e}")
            return None

    def log_event(self, event_type: str, user_id: int = None,
                  details: dict = None, image_path: str = None):
        """Enregistre un événement dans les logs"""
        db = get_db()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logs (event_type, user_id, details, image_path)
                VALUES (?, ?, ?, ?)
            """, (
                event_type,
                user_id,
                json.dumps(details) if details else None,
                image_path
            ))
            conn.commit()

    def trigger_security_response(self, frame: np.ndarray = None,
                                  detected_name: str = "Inconnu") -> dict:
        """
        Déclenche la réponse de sécurité complète

        Args:
            frame: Frame actuel de la caméra
            detected_name: Nom de la personne détectée

        Returns:
            Dictionnaire avec les résultats des actions
        """
        results = {
            "locked": False,
            "capture_path": None,
            "screenshot_path": None,
            "timestamp": datetime.now().isoformat()
        }

        # Capturer le frame de la caméra
        if frame is not None:
            results["capture_path"] = self.capture_frame(frame, "intrusion")

        # Capturer l'écran
        results["screenshot_path"] = self.capture_screenshot()

        # Verrouiller la session
        results["locked"] = self.lock_workstation()

        # Note: Le log est géré par alert_service.trigger_alert() pour éviter les doublons

        return results

    def cleanup_old_captures(self, days: int = 30) -> int:
        """
        Supprime les captures plus anciennes que N jours

        Args:
            days: Nombre de jours à conserver

        Returns:
            Nombre de fichiers supprimés
        """
        from datetime import timedelta
        import os

        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        for filepath in self.captures_dir.iterdir():
            if filepath.is_file():
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if mtime < cutoff:
                    filepath.unlink()
                    deleted += 1

        return deleted


# Instance globale
_security_service_instance = None


def get_security_service() -> SecurityService:
    """Retourne l'instance du service de sécurité"""
    global _security_service_instance
    if _security_service_instance is None:
        _security_service_instance = SecurityService()
    return _security_service_instance
