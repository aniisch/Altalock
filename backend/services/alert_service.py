"""Service d'alertes (email et vocales)"""
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.models.settings import SettingsModel
from backend.models.database import get_db


class AlertService:
    """Service de gestion des alertes"""

    def __init__(self):
        self._tts_engine = None

    def _get_tts_engine(self):
        """Initialise le moteur TTS de manière lazy"""
        if self._tts_engine is None:
            try:
                import pyttsx3
                self._tts_engine = pyttsx3.init()
            except Exception as e:
                print(f"Erreur initialisation TTS: {e}")
        return self._tts_engine

    def speak(self, message: str) -> bool:
        """Prononce un message via text-to-speech"""
        engine = self._get_tts_engine()
        if engine:
            try:
                engine.say(message)
                engine.runAndWait()
                return True
            except Exception as e:
                print(f"Erreur TTS: {e}")
        return False

    def send_email(self, subject: str, body: str, attachment_path: str = None) -> bool:
        """Envoie un email d'alerte"""
        recipient = SettingsModel.get("alert_email")

        if not recipient:
            print("Pas d'email configuré pour les alertes")
            return False

        # Récupérer la config SMTP depuis les variables d'environnement
        import os
        smtp_server = os.environ.get("SMTP_SERVER", "")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_password = os.environ.get("SMTP_PASSWORD", "")

        if not all([smtp_server, smtp_user, smtp_password]):
            print("Configuration SMTP incomplète")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = recipient
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "html"))

            # Ajouter la pièce jointe si fournie
            if attachment_path and Path(attachment_path).exists():
                with open(attachment_path, "rb") as f:
                    img = MIMEImage(f.read())
                    img.add_header("Content-Disposition", "attachment",
                                  filename=Path(attachment_path).name)
                    msg.attach(img)

            # Envoyer l'email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Erreur envoi email: {e}")
            return False

    def trigger_alert(self, alert_type: str, detected_name: str = "Inconnu",
                     image_path: str = None, user_id: int = None) -> bool:
        """
        Déclenche une alerte complète (TTS + email + log)

        Args:
            alert_type: Type d'alerte (intrusion, unknown_face, etc.)
            detected_name: Nom de la personne détectée
            image_path: Chemin vers la capture d'écran
            user_id: ID de l'utilisateur si identifié
        """
        timestamp = datetime.now()
        alert_message = SettingsModel.get("alert_message") or "Accès non autorisé détecté"

        # 1. Alerte vocale
        tts_message = f"{alert_message}. {detected_name} détecté."
        self.speak(tts_message)

        # 2. Alerte email
        email_subject = f"[AltaLock] Alerte de sécurité - {alert_type}"
        email_body = f"""
        <html>
        <body>
            <h2>Alerte de sécurité AltaLock</h2>
            <p><strong>Type:</strong> {alert_type}</p>
            <p><strong>Date:</strong> {timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Personne détectée:</strong> {detected_name}</p>
            <p>Une tentative d'accès non autorisée a été détectée sur votre machine.</p>
            <p>La session a été verrouillée automatiquement.</p>
        </body>
        </html>
        """
        email_sent = self.send_email(email_subject, email_body, image_path)

        # 3. Logger l'événement
        self.log_event(
            event_type="alert",
            user_id=user_id,
            details={
                "alert_type": alert_type,
                "detected_name": detected_name,
                "email_sent": email_sent,
                "timestamp": timestamp.isoformat()
            },
            image_path=image_path
        )

        return True

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

    def get_logs(self, limit: int = 100, offset: int = 0,
                 event_type: str = None) -> list:
        """Récupère les logs avec pagination"""
        db = get_db()

        query = """
            SELECT l.*, u.name as user_name
            FROM logs l
            LEFT JOIN users u ON l.user_id = u.id
        """
        params = []

        if event_type:
            query += " WHERE l.event_type = ?"
            params.append(event_type)

        query += " ORDER BY l.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return db.fetch_all(query, tuple(params))


# Instance globale
_alert_service_instance = None


def get_alert_service() -> AlertService:
    """Retourne l'instance du service d'alertes"""
    global _alert_service_instance
    if _alert_service_instance is None:
        _alert_service_instance = AlertService()
    return _alert_service_instance
