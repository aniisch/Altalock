# AltaLock - Journal de Développement

## État du projet
🟢 **v2.1 - Paramètre frame_scale configurable**
📅 Dernière mise à jour : 05/01/2026

## Légende
- ✅ Terminé
- 🟡 En cours
- ⭕ Non commencé
- ❌ Bloqué/Problèmes

---

## 1. Configuration initiale ✅
### 1.1 Environnement de développement
- [x] Installation de Python et des dépendances (OpenCV, Dlib, face_recognition)
- [x] Configuration de l'environnement virtuel
- [x] Installation de Node.js et Electron
- [x] Mise en place de Git et structure du projet

### 1.2 Configuration des outils
- [x] Structure du projet créée (backend/, frontend/, data/, assets/)
- [x] Fichiers de configuration (.env.example, requirements.txt, package.json)
- [ ] Configuration de l'API SharePoint (optionnel, pour plus tard)

---

## 2. Module de reconnaissance faciale ✅
### 2.1 Capture d'image
- [x] Implémentation de la capture vidéo avec OpenCV
- [x] Optimisation du taux de capture (frame_skip configurable)
- [x] Gestion des erreurs de la webcam
- [x] Prétraitement des images (réduction 25% pour performance)

### 2.2 Détection de visage
- [x] Intégration de l'algorithme de détection avec face_recognition
- [x] Paramètres de détection configurables (tolerance)
- [x] Gestion des cas multiples visages
- [x] Encodage vers base64 pour WebSocket

### 2.3 Reconnaissance faciale
- [x] Implémentation de l'encodage des visages (128 dimensions)
- [x] Base de données SQLite pour les encodages
- [x] Algorithme de comparaison avec seuil de confiance
- [x] Cache des encodages en mémoire pour performance

**Fichier principal:** `backend/services/face_recognition_service.py`

---

## 3. Gestion des utilisateurs ✅
### 3.1 Base de données
- [x] Schéma SQLite (users, face_encodings, settings, logs)
- [x] CRUD utilisateurs complet
- [x] Gestion des sessions via Flask
- [x] Index pour performance

### 3.2 Gestion des visages
- [x] Upload d'images pour nouveaux visages
- [x] Capture depuis webcam
- [x] Suppression avec cascade
- [x] Import depuis l'ancienne app (RD-face_recognition-master)

**Fichiers:** `backend/models/`, `backend/routes/users.py`

---

## 4. Système de sécurité ✅
### 4.1 Verrouillage de session
- [x] Verrouillage Windows via ctypes
- [x] Compteur de détections consécutives
- [x] Seuil configurable (detection_threshold)
- [x] Capture automatique lors d'intrusion

### 4.2 Système d'alertes
- [x] Alertes email via SMTP
- [x] Text-to-Speech avec pyttsx3
- [x] Configuration via paramètres
- [x] Logs complets avec historique

**Fichiers:** `backend/services/alert_service.py`, `backend/services/security_service.py`

---

## 5. Interface utilisateur ✅
### 5.1 Frontend
- [x] Design moderne dark theme
- [x] Vanilla JS (pas de React, simplifié)
- [x] WebSocket pour temps réel
- [x] Navigation Dashboard/Users/Settings/History
- [x] Notifications toast

### 5.2 Backend API
- [x] Architecture REST API complète
- [x] WebSocket avec Flask-SocketIO
- [x] CORS configuré
- [x] Endpoints documentés dans PLAN.md

**Fichiers:** `backend/app.py`, `frontend/renderer.js`

---

## 6. Packaging et déploiement 🟡
### 6.1 Electron
- [x] Configuration sécurisée (contextIsolation, preload)
- [x] Intégration frontend complète
- [x] Démarrage automatique du backend Python
- [x] Icône système tray

### 6.2 Distribution
- [x] Configuration electron-builder
- [ ] Création de l'installateur Windows
- [ ] Tests sur Windows
- [ ] Documentation utilisateur finale

**Fichiers:** `frontend/main.js`, `frontend/package.json`

---

## API Endpoints

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | Liste tous les utilisateurs |
| GET | `/api/users/:id` | Détails d'un utilisateur |
| POST | `/api/users` | Créer un utilisateur |
| DELETE | `/api/users/:id` | Supprimer un utilisateur |
| POST | `/api/users/:id/faces` | Ajouter un visage (upload) |
| POST | `/api/users/:id/faces/capture` | Capturer un visage (webcam) |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Tous les paramètres |
| PUT | `/api/settings` | Mettre à jour |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | État du système |
| POST | `/api/detection/start` | Démarrer détection |
| POST | `/api/detection/stop` | Arrêter détection |
| POST | `/api/import-legacy` | Importer anciens visages |

---

## Journal des modifications

### 05/01/2026 - v2.1.0 Paramètre frame_scale configurable & Version CPU
- ✨ Ajout du paramètre `frame_scale` configurable dans les paramètres
- ✨ Interface utilisateur mise à jour avec un slider pour ajuster la qualité de détection
- 🔧 Amélioration de la détection de visages à distance (augmenter frame_scale)
- 🔧 Correction du redimensionnement des boîtes de détection
- 📦 **Nouvelle version CPU-only** : Build léger (~200-300 Mo) avec installeur Windows
- 📦 Script `build_release_cpu.py` pour version sans DLLs cuDNN
- 📝 Documentation de la détection multi-échelles dans les améliorations futures

### 24/12/2025 - v2.0 Architecture complète
- ✨ Refonte complète de l'architecture
- ✨ Backend Flask avec API REST et WebSocket
- ✨ Base de données SQLite
- ✨ Service de reconnaissance faciale modulaire
- ✨ Services d'alertes (email + TTS)
- ✨ Service de sécurité (verrouillage Windows)
- ✨ Frontend Electron moderne et sécurisé
- ✨ Design dark theme professionnel
- 📝 Documentation complète (PLAN.md, DEVBOOK.md)

### 04/02/2025 - v1.0 Setup initial
- 📝 Création initiale du DEVBOOK
- 📝 Définition des étapes de développement
- ✨ Mise en place de la structure du projet
- ✨ Création de l'interface utilisateur moderne
- 📦 Ajout des fichiers de configuration

---

## Prochaines étapes


**Améliorations futures**
   - Intégration SharePoint
   - Mode multi-utilisateurs owners
   - Historique des captures avec galerie
   - **Détection multi-échelles** : Implémenter une détection à plusieurs échelles pour améliorer la reconnaissance des visages éloignés
     - Si aucun visage détecté avec l'échelle actuelle, réessayer avec un zoom digital sur le centre
     - Permettrait une meilleure détection à distance sans ralentissement constant
