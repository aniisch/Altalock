import cv2
import face_recognition

print("1. Test webcam...")
cap = cv2.VideoCapture(0)
ret, frame = cap.read()

if not ret:
    print("ERREUR: Impossible d'accéder à la webcam")
    exit(1)

print("   Webcam OK!")

print("2. Test détection de visage...")
rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
face_locations = face_recognition.face_locations(rgb_frame)

print(f"   {len(face_locations)} visage(s) détecté(s)")

if face_locations:
    print("3. Test encodage...")
    encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    print(f"   {len(encodings)} encodage(s) généré(s)")
    print("   Taille encodage:", len(encodings[0]), "dimensions")

cap.release()
print("\n=== TOUS LES TESTS OK ===")