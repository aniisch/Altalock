"""Modèle des paramètres"""
from datetime import datetime
from typing import Dict, Any, Optional

from .database import get_db
from backend.config import DEFAULT_SETTINGS


class SettingsModel:
    """Gestion des paramètres de l'application"""

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Récupère la valeur d'un paramètre"""
        db = get_db()
        result = db.fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
        return result["value"] if result else DEFAULT_SETTINGS.get(key)

    @staticmethod
    def get_int(key: str) -> int:
        """Récupère un paramètre comme entier"""
        value = SettingsModel.get(key)
        return int(value) if value else 0

    @staticmethod
    def get_float(key: str) -> float:
        """Récupère un paramètre comme float"""
        value = SettingsModel.get(key)
        return float(value) if value else 0.0

    @staticmethod
    def get_bool(key: str) -> bool:
        """Récupère un paramètre comme booléen"""
        value = SettingsModel.get(key)
        return value.lower() == "true" if value else False

    @staticmethod
    def get_all() -> Dict[str, str]:
        """Récupère tous les paramètres"""
        db = get_db()
        rows = db.fetch_all("SELECT key, value FROM settings")

        # Commencer avec les valeurs par défaut
        result = dict(DEFAULT_SETTINGS)

        # Écraser avec les valeurs de la DB
        for row in rows:
            result[row["key"]] = row["value"]

        return result

    @staticmethod
    def set(key: str, value: Any) -> bool:
        """Définit la valeur d'un paramètre"""
        db = get_db()
        str_value = str(value).lower() if isinstance(value, bool) else str(value)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, str_value, datetime.now().isoformat()))
            conn.commit()
            return True

    @staticmethod
    def set_many(settings: Dict[str, Any]) -> bool:
        """Définit plusieurs paramètres à la fois"""
        for key, value in settings.items():
            SettingsModel.set(key, value)
        return True

    @staticmethod
    def reset_to_defaults() -> bool:
        """Réinitialise tous les paramètres aux valeurs par défaut"""
        return SettingsModel.set_many(DEFAULT_SETTINGS)
