"""Gestion de la base de données SQLite"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from backend.config import Config, DEFAULT_SETTINGS


class Database:
    """Gestionnaire de base de données SQLite"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._init_db()

    def _init_db(self):
        """Initialise la base de données avec les tables nécessaires"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Table des utilisateurs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    is_owner BOOLEAN DEFAULT FALSE,
                    is_blacklisted BOOLEAN DEFAULT FALSE,
                    custom_message TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration: ajouter les colonnes si elles n'existent pas
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_blacklisted BOOLEAN DEFAULT FALSE")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN custom_message TEXT")
            except sqlite3.OperationalError:
                pass

            # Table des encodages faciaux
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_encodings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    encoding BLOB NOT NULL,
                    image_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Table des paramètres
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table des logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    user_id INTEGER,
                    details TEXT,
                    image_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Index pour améliorer les performances
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_face_user ON face_encodings(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON logs(created_at)")

            # Initialiser les paramètres par défaut
            for key, value in DEFAULT_SETTINGS.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
                """, (key, value))

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Context manager pour les connexions à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()):
        """Exécute une requête et retourne les résultats"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor

    def fetch_one(self, query: str, params: tuple = ()):
        """Récupère une seule ligne"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()):
        """Récupère toutes les lignes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


# Instance globale
_db_instance = None


def get_db() -> Database:
    """Retourne l'instance de la base de données"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
