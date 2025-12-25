"""Modèle utilisateur"""
import pickle
from datetime import datetime
from typing import List, Optional
import numpy as np

from .database import get_db


class UserModel:
    """Gestion des utilisateurs et de leurs encodages faciaux"""

    @staticmethod
    def create(name: str, email: str = None, is_owner: bool = False,
               is_blacklisted: bool = False, custom_message: str = None) -> int:
        """Crée un nouvel utilisateur"""
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (name, email, is_owner, is_blacklisted, custom_message)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, is_owner, is_blacklisted, custom_message))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def get_by_id(user_id: int) -> Optional[dict]:
        """Récupère un utilisateur par son ID"""
        db = get_db()
        return db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))

    @staticmethod
    def get_all(active_only: bool = True) -> List[dict]:
        """Récupère tous les utilisateurs"""
        db = get_db()
        query = "SELECT * FROM users"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY is_owner DESC, name ASC"
        return db.fetch_all(query)

    @staticmethod
    def get_owners() -> List[dict]:
        """Récupère les propriétaires (utilisateurs principaux)"""
        db = get_db()
        return db.fetch_all("SELECT * FROM users WHERE is_owner = TRUE AND is_active = TRUE")

    @staticmethod
    def update(user_id: int, **kwargs) -> bool:
        """Met à jour un utilisateur"""
        allowed_fields = {"name", "email", "is_owner", "is_active", "is_blacklisted", "custom_message"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]

        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def get_blacklisted() -> List[dict]:
        """Récupère les utilisateurs blacklistés"""
        db = get_db()
        return db.fetch_all("SELECT * FROM users WHERE is_blacklisted = TRUE AND is_active = TRUE")

    @staticmethod
    def delete(user_id: int) -> bool:
        """Supprime un utilisateur (et ses encodages via CASCADE)"""
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    # --- Gestion des encodages faciaux ---

    @staticmethod
    def add_face_encoding(user_id: int, encoding: np.ndarray, image_path: str = None) -> int:
        """Ajoute un encodage facial pour un utilisateur"""
        db = get_db()
        encoding_blob = pickle.dumps(encoding)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO face_encodings (user_id, encoding, image_path)
                VALUES (?, ?, ?)
            """, (user_id, encoding_blob, image_path))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def get_face_encodings(user_id: int) -> List[dict]:
        """Récupère les encodages faciaux d'un utilisateur"""
        db = get_db()
        rows = db.fetch_all(
            "SELECT * FROM face_encodings WHERE user_id = ?",
            (user_id,)
        )

        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict["encoding"] = pickle.loads(row_dict["encoding"])
            result.append(row_dict)

        return result

    @staticmethod
    def get_all_face_encodings() -> List[dict]:
        """Récupère tous les encodages faciaux avec les infos utilisateur"""
        db = get_db()
        rows = db.fetch_all("""
            SELECT fe.*, u.name as user_name, u.is_owner, u.is_blacklisted, u.custom_message
            FROM face_encodings fe
            JOIN users u ON fe.user_id = u.id
            WHERE u.is_active = TRUE
        """)

        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict["encoding"] = pickle.loads(row_dict["encoding"])
            result.append(row_dict)

        return result

    @staticmethod
    def delete_face_encoding(encoding_id: int) -> bool:
        """Supprime un encodage facial"""
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM face_encodings WHERE id = ?", (encoding_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def count_face_encodings(user_id: int) -> int:
        """Compte le nombre d'encodages pour un utilisateur"""
        db = get_db()
        result = db.fetch_one(
            "SELECT COUNT(*) as count FROM face_encodings WHERE user_id = ?",
            (user_id,)
        )
        return result["count"] if result else 0
