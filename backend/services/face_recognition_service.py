"""Service de reconnaissance faciale"""
import cv2
import numpy as np
import face_recognition
import base64
import threading
import time
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass

from backend.models import UserModel
from backend.models.settings import SettingsModel


@dataclass
class DetectionResult:
    """Résultat d'une détection de visage"""
    user_id: Optional[int]
    name: str
    is_owner: bool
    is_blacklisted: bool
    custom_message: Optional[str]
    confidence: float
    box: Tuple[int, int, int, int]  # (top, right, bottom, left)


class FaceRecognitionService:
    """Service de reconnaissance faciale en temps réel"""

    def __init__(self):
        self.known_encodings: List[np.ndarray] = []
        self.known_metadata: List[Dict] = []  # user_id, name, is_owner
        self.camera: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self._detection_thread: Optional[threading.Thread] = None
        self._frame_callback: Optional[Callable] = None
        self._detection_callback: Optional[Callable] = None
        self._lock = threading.Lock()

        # Compteurs pour la logique de sécurité
        self.consecutive_unknown = 0
        self.last_owner_seen = None

    def load_encodings(self) -> int:
        """Charge tous les encodages faciaux depuis la base de données"""
        with self._lock:
            self.known_encodings = []
            self.known_metadata = []

            encodings_data = UserModel.get_all_face_encodings()

            for data in encodings_data:
                self.known_encodings.append(data["encoding"])
                self.known_metadata.append({
                    "user_id": data["user_id"],
                    "name": data["user_name"],
                    "is_owner": bool(data["is_owner"]),
                    "is_blacklisted": bool(data.get("is_blacklisted", False)),
                    "custom_message": data.get("custom_message"),
                    "encoding_id": data["id"]
                })

            return len(self.known_encodings)

    def encode_face_from_image(self, image_path: str) -> Optional[np.ndarray]:
        """Encode un visage depuis une image"""
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)

            if encodings:
                return encodings[0]
            return None
        except Exception as e:
            print(f"Erreur encodage image {image_path}: {e}")
            return None

    def encode_face_from_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Encode un visage depuis un frame de caméra"""
        try:
            # Convertir BGR (OpenCV) vers RGB (face_recognition)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Trouver les visages
            face_locations = face_recognition.face_locations(rgb_frame)

            if not face_locations:
                return None

            # Encoder le premier visage trouvé
            encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            if encodings:
                return encodings[0]
            return None
        except Exception as e:
            print(f"Erreur encodage frame: {e}")
            return None

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[DetectionResult]]:
        """
        Traite un frame et retourne les détections de visages.

        Args:
            frame: Image BGR depuis OpenCV

        Returns:
            Tuple (frame annoté, liste des détections)
        """
        scale = SettingsModel.get_float("frame_scale") or 0.25
        tolerance = SettingsModel.get_float("tolerance") or 0.6

        # Réduire la taille pour plus de performance
        small_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Détecter les visages
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        detections = []

        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Comparer avec les visages connus
            result = self._match_face(face_encoding, tolerance)

            # Remettre à l'échelle les coordonnées
            top, right, bottom, left = face_location
            scale_factor = int(1 / scale)
            top *= scale_factor
            right *= scale_factor
            bottom *= scale_factor
            left *= scale_factor

            detection = DetectionResult(
                user_id=result["user_id"],
                name=result["name"],
                is_owner=result["is_owner"],
                is_blacklisted=result.get("is_blacklisted", False),
                custom_message=result.get("custom_message"),
                confidence=result["confidence"],
                box=(top, right, bottom, left)
            )
            detections.append(detection)

            # Dessiner le rectangle sur le frame
            # Rouge pour blacklisté, vert pour owner, orange pour connu, rouge pour inconnu
            if result.get("is_blacklisted"):
                color = (0, 0, 255)  # Rouge pour blacklisté
            elif result["is_owner"]:
                color = (0, 255, 0)  # Vert pour owner
            elif result["user_id"]:
                color = (0, 165, 255)  # Orange pour connu
            else:
                color = (0, 0, 255)  # Rouge pour inconnu
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Label avec le nom
            label = f"{result['name']} ({result['confidence']:.0%})"
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

        return frame, detections

    def _match_face(self, face_encoding: np.ndarray, tolerance: float) -> Dict:
        """Compare un encodage avec les visages connus"""
        if not self.known_encodings:
            return {
                "user_id": None,
                "name": "Inconnu",
                "is_owner": False,
                "is_blacklisted": False,
                "custom_message": None,
                "confidence": 0.0
            }

        # Calculer les distances
        face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)

        if len(face_distances) == 0:
            return {
                "user_id": None,
                "name": "Inconnu",
                "is_owner": False,
                "is_blacklisted": False,
                "custom_message": None,
                "confidence": 0.0
            }

        # Trouver la meilleure correspondance
        best_match_idx = np.argmin(face_distances)
        best_distance = face_distances[best_match_idx]

        # Vérifier si c'est en dessous du seuil de tolérance
        if best_distance <= tolerance:
            metadata = self.known_metadata[best_match_idx]
            confidence = 1.0 - best_distance  # Convertir distance en confiance

            return {
                "user_id": metadata["user_id"],
                "name": metadata["name"],
                "is_owner": metadata["is_owner"],
                "is_blacklisted": metadata.get("is_blacklisted", False),
                "custom_message": metadata.get("custom_message"),
                "confidence": confidence
            }

        return {
            "user_id": None,
            "name": "Inconnu",
            "is_owner": False,
            "is_blacklisted": False,
            "custom_message": None,
            "confidence": 1.0 - best_distance
        }

    def start_camera(self, camera_index: int = None) -> bool:
        """Démarre la caméra"""
        if camera_index is None:
            camera_index = SettingsModel.get_int("camera_index")

        self.camera = cv2.VideoCapture(camera_index)

        if not self.camera.isOpened():
            # Essayer l'index 0 si l'index configuré ne fonctionne pas
            if camera_index != 0:
                self.camera = cv2.VideoCapture(0)

        return self.camera.isOpened() if self.camera else False

    def stop_camera(self):
        """Arrête la caméra"""
        if self.camera:
            self.camera.release()
            self.camera = None

    def get_frame(self) -> Optional[np.ndarray]:
        """Capture un frame de la caméra"""
        if not self.camera or not self.camera.isOpened():
            return None

        ret, frame = self.camera.read()
        return frame if ret else None

    def frame_to_base64(self, frame: np.ndarray) -> str:
        """Convertit un frame en base64 pour l'envoi via WebSocket"""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buffer).decode('utf-8')

    def start_detection_loop(self, frame_callback: Callable = None,
                            detection_callback: Callable = None):
        """Démarre la boucle de détection en arrière-plan"""
        if self.is_running:
            return

        self._frame_callback = frame_callback
        self._detection_callback = detection_callback
        self.is_running = True
        self.consecutive_unknown = 0

        self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._detection_thread.start()

    def stop_detection_loop(self):
        """Arrête la boucle de détection"""
        self.is_running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=2.0)
            self._detection_thread = None

    def _detection_loop(self):
        """Boucle principale de détection"""
        frame_skip = SettingsModel.get_int("frame_skip") or 2
        frame_count = 0

        while self.is_running:
            frame = self.get_frame()

            if frame is None:
                time.sleep(0.1)
                continue

            frame_count += 1

            # Traiter seulement 1 frame sur N
            if frame_count % frame_skip == 0:
                annotated_frame, detections = self.process_frame(frame)

                # Appeler le callback de frame
                if self._frame_callback:
                    frame_b64 = self.frame_to_base64(annotated_frame)
                    self._frame_callback(frame_b64, detections)

                # Mettre à jour les compteurs de sécurité AVANT le callback
                self._update_security_counters(detections)

                # Appeler le callback de détection (qui vérifie should_trigger_alert)
                if self._detection_callback and detections:
                    self._detection_callback(detections)

            # Petit délai pour ne pas surcharger le CPU
            time.sleep(0.033)  # ~30 FPS max

    def _update_security_counters(self, detections: List[DetectionResult]):
        """Met à jour les compteurs pour la logique de sécurité"""
        owner_present = any(d.is_owner for d in detections)
        unknown_present = any(d.user_id is None for d in detections)

        if owner_present:
            self.consecutive_unknown = 0
            self.last_owner_seen = time.time()
        elif unknown_present or (detections and not owner_present):
            self.consecutive_unknown += 1

        # Si aucun visage détecté, on ne change rien
        if not detections:
            pass  # Garder le compteur actuel

    def should_trigger_alert(self) -> bool:
        """Vérifie si une alerte doit être déclenchée"""
        # Essayer unknownThreshold (frontend) puis detection_threshold (backend)
        threshold = SettingsModel.get_int("unknownThreshold")
        if threshold == 0:
            threshold = SettingsModel.get_int("detection_threshold") or 4
        return self.consecutive_unknown >= threshold

    def reset_counters(self):
        """Réinitialise les compteurs de sécurité"""
        self.consecutive_unknown = 0


# Instance globale du service
_face_service_instance = None


def get_face_service() -> FaceRecognitionService:
    """Retourne l'instance du service de reconnaissance faciale"""
    global _face_service_instance
    if _face_service_instance is None:
        _face_service_instance = FaceRecognitionService()
    return _face_service_instance
