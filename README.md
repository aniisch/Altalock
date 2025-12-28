# AltaLock

Application de sécurité qui utilise la reconnaissance faciale pour protéger un PC des accès non autorisés.

## Version 2.0.0

> **Note de release :** La v2.0.0 est distribuée en **version portable (ZIP)** uniquement.
> Le backend intègre les DLLs cuDNN nécessaires pour dlib/face_recognition avec support GPU,
> ce qui porte la taille totale à ~1.5 Go. Cette taille dépasse la limite supportée par
> l'installeur Squirrel (~1 Go), nous avons donc opté pour une distribution portable.
>
> **Installation :** Extraire le ZIP et lancer `altalock.exe`.

## Fonctionnalités

- **Reconnaissance faciale en temps réel** via webcam
- **Verrouillage automatique** si visage non autorisé détecté
- **Alertes** par email et vocales (text-to-speech)
- **Gestion des utilisateurs** avec multi-visages par personne
- **Interface moderne** avec dashboard temps réel
- **Icône système** pour surveillance en arrière-plan

## Installation

### Prérequis

- Python 3.8+
- Node.js 18+
- Windows 10/11 (pour le verrouillage de session)

### 1. Cloner le projet

```bash
git clone https://github.com/aniisch/Altalock.git
cd Altalock
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

> **Note:** L'installation de `face-recognition` nécessite CMake et un compilateur C++.
> Sur Windows, installez Visual Studio Build Tools.

### 3. Installer les dépendances Node.js

```bash
npm install
```

### 4. Configuration

Copier le fichier d'exemple et configurer :

```bash
cp .env.example .env
```

Éditer `.env` avec vos paramètres SMTP pour les alertes email.

## Utilisation

### Mode développement

```bash
# Démarrer l'application (lance le backend automatiquement)
npm start
```

### Premier lancement

1. Ajoutez un nouvel utilisateur avec le bouton "+ Ajouter"
2. Capturez votre visage via la webcam
3. Cochez "Propriétaire" pour vous définir comme utilisateur principal
4. Cliquez sur "Démarrer la surveillance"

### Logique de sécurité

- Si le **propriétaire** est détecté → tout va bien
- Si un **inconnu** est détecté 4x consécutivement → alerte + verrouillage
- Le seuil est configurable dans les paramètres

## Structure du projet

```
Altalock/
├── backend/                    # Backend Python (Flask)
│   ├── app.py                  # Application Flask principale
│   ├── config.py               # Configuration
│   ├── models/                 # Modèles de données (SQLite)
│   ├── services/               # Services métier
│   └── routes/                 # API REST endpoints
├── electron/                   # Process principal Electron
│   ├── main.js                 # Point d'entrée Electron
│   ├── preload.js              # Bridge sécurisé
│   └── splash.html             # Écran de chargement
├── public/                     # Frontend (renderer)
│   ├── index.html              # Interface principale
│   ├── renderer.js             # Logique UI
│   └── styles.css              # Styles CSS
├── assets/                     # Ressources
│   ├── icons/                  # Icônes (ico, png)
│   └── loading.gif             # Animation d'installation
├── data/                       # Données utilisateur
│   ├── altalock.db             # Base de données SQLite
│   ├── faces/                  # Images des visages
│   └── captures/               # Captures de détection
├── package.json                # Config npm + Electron Forge
├── forge.config.js             # Config Electron Forge
├── build_backend.py            # Script build backend
├── build_release.py            # Script build complet
└── requirements.txt            # Dépendances Python
```

## API

L'API REST est disponible sur `http://localhost:5000`.

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | État du système |
| `POST /api/detection/start` | Démarrer la surveillance |
| `POST /api/detection/stop` | Arrêter la surveillance |
| `GET /api/users` | Liste des utilisateurs |
| `POST /api/users` | Créer un utilisateur |
| `POST /api/users/:id/faces/capture` | Capturer un visage |
| `GET /api/settings` | Paramètres |
| `PUT /api/settings` | Modifier paramètres |
| `GET /api/logs` | Historique d'activité |

## Paramètres configurables

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `detection_threshold` | 4 | Nombre de détections avant alerte |
| `frame_skip` | 2 | Traiter 1 frame sur N |
| `tolerance` | 0.6 | Seuil de similarité faciale |
| `auto_lock` | true | Verrouiller automatiquement |
| `alert_email` | - | Email pour les alertes |
| `alert_message` | - | Message vocal personnalisé |

## Build Release

Pour créer une release Windows :

```bash
python build_release.py
```

Cela va :
1. Compiler le backend Python avec PyInstaller (inclut les DLLs cuDNN pour le support GPU)
2. Packager l'application Electron avec Electron Forge
3. Générer le ZIP portable dans `out/make/zip/win32/x64/`

### Fichier généré

- `AltaLock-win32-x64-X.X.X.zip` - Version portable (~1.5 Go)
- pas de `AltaLock-X.X.X Setup.exe` - Installateur Windows

> **Pourquoi pas d'installeur ?** Le backend avec les DLLs cuDNN (dlib/face_recognition)
> pèse ~1 Go, ce qui dépasse la limite de Squirrel. La version portable fonctionne
> parfaitement : extraire et lancer `altalock.exe`.

## Technologies

- **Frontend:** Electron, Vanilla JS, CSS3
- **Backend:** Flask, Flask-SocketIO
- **Reconnaissance:** face_recognition, OpenCV, dlib
- **Base de données:** SQLite
- **Alertes:** pyttsx3 (TTS), smtplib (email)
- **Build:** PyInstaller, Electron Forge

## Licence

MIT License - voir [LICENSE](LICENSE)

## Auteur

aniisch
