"""Service d'alertes (email et vocales)"""
import smtplib
import json
import sys
import functools
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from pathlib import Path
from typing import Optional

# Forcer l'affichage des logs dans stderr
print = functools.partial(print, file=sys.stderr, flush=True)

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
        """Prononce un message via text-to-speech (non-bloquant)"""
        def _speak_thread():
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(message)
                engine.runAndWait()
                engine.stop()
                print(f"[TTS] Message prononcé: {message}")
            except Exception as e:
                print(f"[TTS] Erreur: {e}")

        # Lancer dans un thread séparé pour ne pas bloquer
        thread = threading.Thread(target=_speak_thread, daemon=True)
        thread.start()
        return True

    def send_email(self, subject: str, body: str, attachment_path: str = None) -> bool:
        """Envoie un email d'alerte"""
        # Récupérer l'email destinataire depuis les paramètres
        recipient = SettingsModel.get("alert_email") or SettingsModel.get("alertEmail")

        print(f"[EMAIL] Tentative d'envoi à: {recipient}")

        if not recipient:
            print("[EMAIL] ERREUR: Pas d'email configuré pour les alertes")
            return False

        # Récupérer la config SMTP depuis les variables d'environnement
        import os
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.hostinger.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_password = os.environ.get("SMTP_PASSWORD", "")

        print(f"[EMAIL] Config SMTP: server={smtp_server}, port={smtp_port}, user={smtp_user}")
        print(f"[EMAIL] Password configuré: {'Oui' if smtp_password else 'NON'} (longueur: {len(smtp_password)})")

        if not all([smtp_server, smtp_user, smtp_password]):
            print("[EMAIL] ERREUR: Configuration SMTP incomplète - vérifiez le fichier .env")
            return False

        print(f"[EMAIL] Envoi en cours...")

        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = recipient
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "html"))

            # Ajouter la pièce jointe si fournie
            if attachment_path:
                from backend.config import DATA_DIR
                # Construire le chemin complet si c'est juste un nom de fichier
                if not Path(attachment_path).is_absolute():
                    full_path = DATA_DIR / "captures" / attachment_path
                else:
                    full_path = Path(attachment_path)

                if full_path.exists():
                    print(f"[EMAIL] Ajout de la pièce jointe: {full_path.name}")
                    with open(full_path, "rb") as f:
                        img = MIMEImage(f.read())
                        img.add_header("Content-Disposition", "attachment",
                                      filename=full_path.name)
                        msg.attach(img)
                else:
                    print(f"[EMAIL] Pièce jointe non trouvée: {full_path}")

            # Envoyer l'email (SSL sur port 465, TLS sur port 587)
            print(f"[EMAIL] Connexion à {smtp_server}:{smtp_port}...")

            if smtp_port == 465:
                # Connexion SSL directe
                import ssl
                context = ssl.create_default_context()
                print("[EMAIL] Mode SSL (port 465)")
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=10) as server:
                    print("[EMAIL] Connexion SSL établie, login...")
                    server.login(smtp_user, smtp_password)
                    print("[EMAIL] Login OK, envoi du message...")
                    server.send_message(msg)
            else:
                # Connexion TLS (STARTTLS)
                print(f"[EMAIL] Mode TLS/STARTTLS (port {smtp_port})")
                with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                    print("[EMAIL] Connexion établie, STARTTLS...")
                    server.starttls()
                    print("[EMAIL] TLS OK, login...")
                    server.login(smtp_user, smtp_password)
                    print("[EMAIL] Login OK, envoi du message...")
                    server.send_message(msg)

            print(f"[EMAIL] SUCCESS: Email envoyé à {recipient}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"[EMAIL] ERREUR AUTH: Mot de passe incorrect ou compte bloqué - {e}")
            return False
        except smtplib.SMTPConnectError as e:
            print(f"[EMAIL] ERREUR CONNEXION: Impossible de se connecter au serveur - {e}")
            return False
        except Exception as e:
            print(f"[EMAIL] ERREUR: {type(e).__name__}: {e}")
            return False

    def trigger_alert(self, alert_type: str, detected_name: str = "Inconnu",
                     image_path: str = None, user_id: int = None,
                     custom_message: str = None, is_blacklisted: bool = False) -> bool:
        """
        Déclenche une alerte complète (TTS + email + log)

        Args:
            alert_type: Type d'alerte (intrusion, unknown_face, etc.)
            detected_name: Nom de la personne détectée
            image_path: Chemin vers la capture d'écran
            user_id: ID de l'utilisateur si identifié
            custom_message: Message personnalisé pour cette personne
            is_blacklisted: Si la personne est blacklistée
        """
        timestamp = datetime.now()

        # Vérifier si les alertes sonores sont activées (True par défaut)
        sound_setting = SettingsModel.get("soundAlert")
        sound_enabled = sound_setting is None or str(sound_setting).lower() == "true"

        # 1. Alerte vocale avec message personnalisé
        if sound_enabled:
            if custom_message:
                # Message personnalisé (ex: "Touche pas à ma machine, Jean!")
                tts_message = custom_message.replace("{nom}", detected_name)
            elif is_blacklisted:
                tts_message = f"Attention! {detected_name} détecté. Accès interdit!"
            else:
                default_message = SettingsModel.get("alert_message") or "Accès non autorisé détecté"
                tts_message = f"{default_message}. {detected_name} détecté."

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

        # 3. Logger l'événement (type "intrusion" pour regrouper alerte + verrouillage)
        self.log_event(
            event_type="intrusion",
            user_id=user_id,
            details={
                "alert_type": alert_type,
                "detected_name": detected_name,
                "is_blacklisted": is_blacklisted,
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
