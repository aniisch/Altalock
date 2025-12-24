# Plan d'Architecture AltaLock v2.0

## Vue d'ensemble

Architecture **Client-Serveur locale** avec communication temps réel :
- **Frontend** : Electron + Vanilla JS (abandon de React pour simplifier)
- **Backend** : Flask + Flask-SocketIO
- **Recognition Engine** : Python avec face_recognition + OpenCV
- **Base de données** : SQLite (légère, portable, pas de serveur)
- **Communication** : WebSocket (temps réel) + REST API (CRUD)

```
┌─────────────────────────────────────────────────────────────────┐
│                        ELECTRON APP                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  main.js    │    │ preload.js  │    │    renderer.js      │  │
│  │  (Main)     │◄──►│   (Bridge)  │◄──►│  (UI + WebSocket)   │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket (localhost:5000)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  REST API   │    │  SocketIO   │    │  Face Recognition   │  │
│  │  (CRUD)     │    │  (Realtime) │    │     Engine          │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│         │                  │                      │              │
│         └──────────────────┼──────────────────────┘              │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    SQLite Database                          ││
│  │  users | face_encodings | settings | logs                   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Structure des fichiers

```
Altalock/
├── backend/
│   ├── app.py                 # Flask app + SocketIO
│   ├── config.py              # Configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py        # SQLite setup
│   │   ├── user.py            # User model
│   │   └── settings.py        # Settings model
│   ├── services/
│   │   ├── __init__.py
│   │   ├── face_recognition_service.py  # Moteur de reconnaissance
│   │   ├── alert_service.py   # Email + TTS
│   │   └── security_service.py # Verrouillage Windows
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── users.py           # CRUD utilisateurs
│   │   ├── settings.py        # Configuration
│   │   └── logs.py            # Historique
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── frontend/
│   ├── main.js                # Electron main process
│   ├── preload.js             # Bridge sécurisé IPC
│   ├── renderer.js            # Logique UI + WebSocket
│   ├── index.html             # Interface principale
│   ├── styles.css             # Styles
│   └── pages/
│       ├── dashboard.html     # Vue monitoring
│       ├── users.html         # Gestion utilisateurs
│       ├── settings.html      # Paramètres
│       └── history.html       # Historique
├── assets/
│   ├── icons/
│   └── images/
├── data/
│   ├── altalock.db            # Base SQLite
│   └── faces/                 # Images des visages
├── requirements.txt
├── package.json
├── .env.example
└── README.md
```

---

## Base de données SQLite

### Tables

```sql
-- Utilisateurs autorisés
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    is_owner BOOLEAN DEFAULT FALSE,  -- Propriétaire principal (ex: "anis")
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Encodages faciaux (128 dimensions par face_recognition)
CREATE TABLE face_encodings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    encoding BLOB NOT NULL,          -- numpy array sérialisé
    image_path TEXT,                 -- chemin vers l'image source
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Paramètres de l'application
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Journaux d'événements
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,        -- detection, alert, lock, login, etc.
    user_id INTEGER,
    details TEXT,                    -- JSON avec détails
    image_path TEXT,                 -- capture au moment de l'événement
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Paramètres par défaut

| Clé | Valeur | Description |
|-----|--------|-------------|
| `detection_threshold` | `4` | Frames consécutives avant alerte |
| `frame_skip` | `2` | Traiter 1 frame sur N |
| `tolerance` | `0.6` | Seuil de similarité faciale |
| `alert_email` | `""` | Email pour alertes |
| `alert_message` | `"Accès non autorisé détecté"` | Message TTS |
| `camera_index` | `0` | Index webcam |
| `auto_lock` | `true` | Verrouiller automatiquement |

---

## API REST

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users` | Liste tous les utilisateurs |
| GET | `/api/users/:id` | Détails d'un utilisateur |
| POST | `/api/users` | Créer un utilisateur |
| PUT | `/api/users/:id` | Modifier un utilisateur |
| DELETE | `/api/users/:id` | Supprimer un utilisateur |
| POST | `/api/users/:id/faces` | Ajouter un visage |
| DELETE | `/api/users/:id/faces/:faceId` | Supprimer un visage |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Tous les paramètres |
| PUT | `/api/settings` | Mettre à jour les paramètres |

### Logs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/logs` | Historique (avec pagination) |
| GET | `/api/logs/:id` | Détails d'un événement |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | État du système |
| POST | `/api/detection/start` | Démarrer la détection |
| POST | `/api/detection/stop` | Arrêter la détection |

---

## WebSocket Events

### Server → Client
| Event | Payload | Description |
|-------|---------|-------------|
| `frame` | `{image: base64, faces: [...]}` | Frame avec détections |
| `detection` | `{user_id, name, confidence, box}` | Visage détecté |
| `alert` | `{type, message, user_id}` | Alerte déclenchée |
| `status` | `{detecting, camera_ok, ...}` | État du système |

### Client → Server
| Event | Payload | Description |
|-------|---------|-------------|
| `start_detection` | `{}` | Démarrer |
| `stop_detection` | `{}` | Arrêter |
| `capture_face` | `{user_id}` | Capturer nouveau visage |

---

## Services Backend

### 1. FaceRecognitionService

```python
class FaceRecognitionService:
    def __init__(self):
        self.known_encodings = []  # Chargés depuis DB
        self.known_names = []
        self.camera = None
        self.is_running = False
        self.consecutive_unknown = 0

    def load_encodings(self):
        """Charge tous les encodages depuis la DB"""

    def start_detection(self):
        """Démarre la boucle de détection"""

    def process_frame(self, frame):
        """Traite un frame et retourne les détections"""

    def encode_face(self, image_path):
        """Encode un nouveau visage"""

    def compare_face(self, encoding):
        """Compare un encodage avec les connus"""
```

### 2. AlertService

```python
class AlertService:
    def send_email(self, subject, body, attachment=None):
        """Envoie email via SMTP"""

    def speak(self, message):
        """Text-to-Speech avec pyttsx3"""

    def trigger_alert(self, alert_type, details):
        """Déclenche une alerte complète"""
```

### 3. SecurityService

```python
class SecurityService:
    def lock_workstation(self):
        """Verrouille Windows via ctypes"""

    def capture_screenshot(self, path):
        """Capture l'écran/webcam"""
```

---

## Frontend - Flux de données

### renderer.js

```javascript
class AltaLockApp {
    constructor() {
        this.socket = null;
        this.isDetecting = false;
    }

    // Connexion WebSocket
    connect() {
        this.socket = io('http://localhost:5000');
        this.socket.on('frame', this.handleFrame.bind(this));
        this.socket.on('detection', this.handleDetection.bind(this));
        this.socket.on('alert', this.handleAlert.bind(this));
    }

    // Affichage du flux vidéo
    handleFrame(data) {
        // Affiche le frame + overlay des détections
    }

    // Navigation SPA
    navigate(page) {
        // Charge le contenu de la page
    }

    // API calls
    async fetchUsers() { }
    async createUser(data) { }
    async updateSettings(data) { }
}
```

### preload.js (Sécurité Electron)

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    // Expose seulement les fonctions nécessaires
    minimize: () => ipcRenderer.send('minimize'),
    close: () => ipcRenderer.send('close'),
    getAppPath: () => ipcRenderer.invoke('get-app-path')
});
```

---

## Workflow de détection

```
1. Démarrage
   └─► Charger encodages depuis DB
   └─► Initialiser webcam
   └─► Démarrer boucle de détection

2. Pour chaque frame (1 sur N)
   ├─► Réduire taille (25%) pour performance
   ├─► Détecter visages (face_recognition.face_locations)
   ├─► Encoder visages détectés
   ├─► Comparer avec encodages connus
   │   ├─► Match trouvé → identifier utilisateur
   │   └─► Pas de match → marquer "inconnu"
   ├─► Envoyer frame + détections via WebSocket
   └─► Logique de sécurité:
       ├─► Owner présent → reset compteur
       └─► Inconnu ou non-owner:
           ├─► Incrémenter compteur
           └─► Si compteur >= seuil:
               ├─► Déclencher alerte (email + TTS)
               ├─► Sauvegarder capture
               ├─► Logger événement
               └─► Verrouiller session
```

---

## Ordre d'implémentation

### Phase 1 : Backend Core
1. Structure du projet backend
2. Configuration et .env
3. Base de données SQLite + models
4. Service de reconnaissance faciale (sans UI)
5. Tests unitaires du moteur

### Phase 2 : API REST
1. Routes users (CRUD)
2. Routes settings
3. Routes logs
4. Tests des endpoints

### Phase 3 : WebSocket + Temps réel
1. Setup Flask-SocketIO
2. Streaming vidéo
3. Events de détection
4. Events d'alertes

### Phase 4 : Services auxiliaires
1. AlertService (email + TTS)
2. SecurityService (lock Windows)
3. Logging complet

### Phase 5 : Frontend
1. Refactoring main.js (sécurité)
2. Création preload.js
3. Création renderer.js
4. Intégration WebSocket client
5. UI dynamique (users, settings, logs)

### Phase 6 : Intégration & Tests
1. Tests end-to-end
2. Gestion d'erreurs
3. Performance tuning

### Phase 7 : Packaging
1. Configuration Electron Builder
2. Bundling Python (PyInstaller)
3. Création installateur Windows

---

## Décisions techniques

| Choix | Raison |
|-------|--------|
| **SQLite** vs PostgreSQL | Portable, pas de serveur, suffisant pour usage local |
| **Vanilla JS** vs React | Simplicité, moins de build, app desktop pas besoin de SPA complexe |
| **WebSocket** vs Polling | Temps réel obligatoire pour le flux vidéo |
| **Flask** vs FastAPI | Maturité, Flask-SocketIO bien intégré |
| **face_recognition** | Bibliothèque prouvée, utilisée dans l'ancienne app |

---

## Questions en suspens

1. **SharePoint** : À intégrer plus tard ou prioritaire ?
2. **Multi-utilisateurs owners** : Un seul owner ou plusieurs ?
3. **Mode "invité"** : Autoriser temporairement des non-owners ?
4. **Historique images** : Garder toutes les captures ou rotation ?

---

## Prêt à implémenter

Une fois ce plan approuvé, je commence par :
1. Créer la structure de dossiers
2. Implémenter le backend avec le moteur de reconnaissance
3. Tester avec les images existantes dans `RD-face_recognition-master/imgs/`
