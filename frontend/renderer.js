/**
 * AltaLock - Renderer (Interface utilisateur)
 * Gère l'UI et la communication avec le backend via WebSocket
 */

class AltaLockApp {
    constructor() {
        this.socket = null;
        this.isDetecting = false;
        this.backendUrl = 'http://localhost:5000';
        this.currentPage = 'dashboard';
        this.users = [];
        this.logs = [];
        this.settings = {
            unknownThreshold: 3,
            lockScreenEnabled: true,
            sleepAfterLock: true,
            soundAlert: true,
            alertEmail: '',
            cameraSource: 0
        };
    }

    async init() {
        console.log('AltaLock init...');

        // Récupérer l'URL du backend depuis Electron
        if (window.electronAPI) {
            try {
                this.backendUrl = await window.electronAPI.getBackendUrl();
                console.log('Backend URL:', this.backendUrl);
            } catch (e) {
                console.log('Utilisation de l\'URL par défaut');
            }

            // Écouter les actions du tray
            window.electronAPI.onTrayAction((action) => {
                if (action === 'start') this.startDetection();
                if (action === 'stop') this.stopDetection();
            });
        }

        this.setupEventListeners();
        this.connectWebSocket();

        // Attendre un peu que le backend soit prêt
        setTimeout(() => this.loadInitialData(), 1000);
    }

    // --- Navigation ---

    navigateTo(pageName) {
        console.log('Navigation vers:', pageName);

        // Mettre à jour les liens nav
        document.querySelectorAll('.main-nav a').forEach(link => {
            link.classList.toggle('active', link.dataset.page === pageName);
        });

        // Afficher la bonne page
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });

        const targetPage = document.getElementById(`page-${pageName}`);
        if (targetPage) {
            targetPage.classList.add('active');
        }

        this.currentPage = pageName;

        // Charger les données spécifiques à la page
        if (pageName === 'users') {
            this.renderUsersFullPage();
        } else if (pageName === 'settings') {
            this.loadSettings();
        } else if (pageName === 'history') {
            this.loadHistory();
        }
    }

    // --- WebSocket ---

    connectWebSocket() {
        // Charger Socket.IO depuis le CDN
        if (typeof io === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.socket.io/4.6.0/socket.io.min.js';
            script.onload = () => this.initSocket();
            script.onerror = () => console.error('Erreur chargement Socket.IO');
            document.head.appendChild(script);
        } else {
            this.initSocket();
        }
    }

    initSocket() {
        try {
            this.socket = io(this.backendUrl, {
                transports: ['websocket', 'polling']
            });

            this.socket.on('connect', () => {
                console.log('WebSocket connecté');
                this.updateStatus('Connecté', 'success');
            });

            this.socket.on('disconnect', () => {
                console.log('WebSocket déconnecté');
                this.updateStatus('Déconnecté', 'error');
            });

            this.socket.on('frame', (data) => this.handleFrame(data));
            this.socket.on('alert', (data) => this.handleAlert(data));
            this.socket.on('status', (data) => this.handleStatusUpdate(data));
            this.socket.on('error', (data) => this.showNotification(data.message, 'error'));
            this.socket.on('face_captured', () => {
                this.showNotification('Visage capturé avec succès', 'success');
                this.loadUsers();
            });
        } catch (e) {
            console.error('Erreur WebSocket:', e);
        }
    }

    // --- Gestion des frames vidéo ---

    handleFrame(data) {
        const videoContainer = document.getElementById('videoContainer');
        if (!videoContainer) return;

        let img = document.getElementById('videoFrame');
        if (!img) {
            img = document.createElement('img');
            img.id = 'videoFrame';
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'contain';
            videoContainer.innerHTML = '';
            videoContainer.appendChild(img);
        }
        img.src = `data:image/jpeg;base64,${data.image}`;
        this.updateDetectionInfo(data.faces);
    }

    updateDetectionInfo(faces) {
        const overlay = document.getElementById('detectionOverlay');
        if (!overlay) return;

        if (!faces || faces.length === 0) {
            overlay.innerHTML = '<span class="no-face">Aucun visage détecté</span>';
            return;
        }

        overlay.innerHTML = faces.map(face => {
            const statusClass = face.is_owner ? 'owner' : (face.user_id ? 'known' : 'unknown');
            const confidence = Math.round(face.confidence * 100);
            return `<span class="face-tag ${statusClass}">${face.name} (${confidence}%)</span>`;
        }).join('');
    }

    // --- Gestion des alertes ---

    handleAlert(data) {
        this.showNotification(data.message, 'warning');
        this.addLogEntry({ type: 'alert', message: data.message, timestamp: new Date().toISOString() });

        // Si verrouillage effectué et option "sleep after lock" activée
        if (data.locked && this.settings.sleepAfterLock) {
            console.log('Verrouillage détecté - Mise en veille de la surveillance');
            setTimeout(() => {
                this.stopDetection();
                this.showNotification('Surveillance mise en veille après verrouillage', 'info');
            }, 1000);
        }
    }

    // --- API Calls ---

    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.backendUrl}${endpoint}`, {
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erreur API');
            }

            return data;
        } catch (error) {
            console.error(`Erreur API ${endpoint}:`, error);
            throw error;
        }
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadUsers(),
                this.loadLogs(),
                this.loadStatus(),
                this.loadSettings()
            ]);
        } catch (error) {
            console.error('Erreur chargement données:', error);
        }
    }

    async loadUsers() {
        try {
            const data = await this.apiCall('/api/users');
            this.users = data.users || [];
            this.renderUsers();
            if (this.currentPage === 'users') {
                this.renderUsersFullPage();
            }
        } catch (error) {
            console.error('Erreur chargement utilisateurs:', error);
            this.users = [];
            this.renderUsers();
        }
    }

    async loadLogs() {
        try {
            const data = await this.apiCall('/api/logs?limit=50');
            this.logs = data.logs || [];
            this.renderLogs();
        } catch (error) {
            console.error('Erreur chargement logs:', error);
        }
    }

    async loadStatus() {
        try {
            const data = await this.apiCall('/api/status');
            this.isDetecting = data.detection_active;
            this.updateDetectionButton();
            this.updateStatusPanel(data);
        } catch (error) {
            console.error('Erreur chargement status:', error);
        }
    }

    async loadSettings() {
        try {
            const data = await this.apiCall('/api/settings');
            if (data) {
                this.settings = { ...this.settings, ...data };
                this.renderSettings();
            }
        } catch (error) {
            console.error('Erreur chargement paramètres:', error);
            this.renderSettings();
        }
    }

    async saveSettings() {
        try {
            // Récupérer les valeurs depuis le formulaire
            const unknownThreshold = document.getElementById('unknownThreshold')?.value || 3;
            const lockScreenEnabled = document.getElementById('lockScreenEnabled')?.checked ?? true;
            const sleepAfterLock = document.getElementById('sleepAfterLock')?.checked ?? true;
            const soundAlert = document.getElementById('soundAlert')?.checked ?? true;
            const alertEmail = document.getElementById('alertEmail')?.value || '';
            const cameraSource = document.getElementById('cameraSource')?.value || '0';

            this.settings = {
                unknownThreshold: parseInt(unknownThreshold),
                lockScreenEnabled,
                sleepAfterLock,
                soundAlert,
                alertEmail,
                cameraSource: parseInt(cameraSource)
            };

            await this.apiCall('/api/settings', {
                method: 'POST',
                body: JSON.stringify(this.settings)
            });

            this.showNotification('Paramètres sauvegardés', 'success');
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async loadHistory() {
        try {
            const data = await this.apiCall('/api/logs?limit=100');
            this.renderHistory(data.logs || []);
        } catch (error) {
            console.error('Erreur chargement historique:', error);
            this.renderHistory([]);
        }
    }

    async importLegacyFaces() {
        try {
            this.showNotification('Import en cours...', 'info');
            const data = await this.apiCall('/api/import-legacy', { method: 'POST' });
            this.showNotification(data.message, 'success');
            this.loadUsers();
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    // --- Détection ---

    async startDetection() {
        try {
            await this.apiCall('/api/detection/start', { method: 'POST' });
            this.isDetecting = true;
            this.updateDetectionButton();
            this.showNotification('Surveillance démarrée', 'success');
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async stopDetection() {
        try {
            await this.apiCall('/api/detection/stop', { method: 'POST' });
            this.isDetecting = false;
            this.updateDetectionButton();
            this.showNotification('Surveillance arrêtée', 'info');

            const videoContainer = document.getElementById('videoContainer');
            if (videoContainer) {
                videoContainer.innerHTML = '<div class="video-placeholder"><p>Surveillance arrêtée</p></div>';
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    toggleDetection() {
        if (this.isDetecting) {
            this.stopDetection();
        } else {
            this.startDetection();
        }
    }

    // --- Gestion des utilisateurs ---

    async createUser(name, email, isOwner = false) {
        try {
            await this.apiCall('/api/users', {
                method: 'POST',
                body: JSON.stringify({ name, email, is_owner: isOwner })
            });
            this.showNotification('Utilisateur créé', 'success');
            this.loadUsers();
            this.closeModal();
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async deleteUser(userId) {
        if (!confirm('Supprimer cet utilisateur ?')) return;

        try {
            await this.apiCall(`/api/users/${userId}`, { method: 'DELETE' });
            this.showNotification('Utilisateur supprimé', 'success');
            this.loadUsers();
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    // Upload d'image pour un utilisateur
    async uploadUserFace(userId) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/jpeg,image/png,image/jpg';

        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('image', file);

            try {
                const response = await fetch(`${this.backendUrl}/api/users/${userId}/faces`, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Erreur upload');
                }

                this.showNotification('Visage ajouté avec succès !', 'success');
                this.loadUsers();
            } catch (error) {
                this.showNotification(error.message, 'error');
            }
        };

        input.click();
    }

    // --- Rendu UI ---

    renderUsers() {
        const grid = document.getElementById('usersGrid');
        if (!grid) return;

        if (this.users.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <p>Aucun utilisateur enregistré</p>
                    <button class="btn btn-primary" onclick="app.showAddUserModal()">
                        Ajouter un utilisateur
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.users.map(user => `
            <div class="user-card ${user.is_owner ? 'owner' : ''}">
                <div class="user-avatar">
                    ${user.name.charAt(0).toUpperCase()}
                </div>
                <div class="user-info">
                    <h4>${user.name}</h4>
                    <span class="user-meta">${user.face_count || 0} visage(s)</span>
                    ${user.is_owner ? '<span class="badge owner">Propriétaire</span>' : ''}
                </div>
                <div class="user-actions">
                    <button class="btn-icon" onclick="app.uploadUserFace(${user.id})" title="Ajouter une photo">
                        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M19 7v2.99s-1.99.01-2 0V7h-3s.01-1.99 0-2h3V2h2v3h3v2h-3zm-3 4V8h-3V5H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-8h-3zM5 19l3-4 2 3 3-4 4 5H5z"/></svg>
                    </button>
                    <button class="btn-icon danger" onclick="app.deleteUser(${user.id})" title="Supprimer">
                        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderUsersFullPage() {
        const grid = document.getElementById('usersFullGrid');
        if (!grid) return;

        if (this.users.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <p>Aucun utilisateur enregistré</p>
                    <button class="btn btn-primary" onclick="app.showAddUserModal()">
                        Ajouter un utilisateur
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.users.map(user => `
            <div class="user-card ${user.is_owner ? 'owner' : ''}">
                <div class="user-avatar">
                    ${user.name.charAt(0).toUpperCase()}
                </div>
                <div class="user-info">
                    <h4>${user.name}</h4>
                    <span class="user-meta">${user.face_count || 0} visage(s) enregistré(s)</span>
                    ${user.is_owner ? '<span class="badge owner">Propriétaire</span>' : ''}
                    ${user.email ? `<p style="margin-top:4px;font-size:12px;color:var(--text-muted)">${user.email}</p>` : ''}
                </div>
                <div class="user-actions">
                    <button class="btn-icon" onclick="app.uploadUserFace(${user.id})" title="Ajouter une photo">
                        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M19 7v2.99s-1.99.01-2 0V7h-3s.01-1.99 0-2h3V2h2v3h3v2h-3zm-3 4V8h-3V5H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-8h-3zM5 19l3-4 2 3 3-4 4 5H5z"/></svg>
                    </button>
                    <button class="btn-icon danger" onclick="app.deleteUser(${user.id})" title="Supprimer">
                        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderSettings() {
        // Threshold slider
        const thresholdInput = document.getElementById('unknownThreshold');
        const thresholdValue = document.getElementById('unknownThresholdValue');
        if (thresholdInput && thresholdValue) {
            thresholdInput.value = this.settings.unknownThreshold;
            thresholdValue.textContent = this.settings.unknownThreshold;
        }

        // Checkboxes
        const lockScreen = document.getElementById('lockScreenEnabled');
        if (lockScreen) lockScreen.checked = this.settings.lockScreenEnabled;

        const sleepAfterLock = document.getElementById('sleepAfterLock');
        if (sleepAfterLock) sleepAfterLock.checked = this.settings.sleepAfterLock;

        const soundAlert = document.getElementById('soundAlert');
        if (soundAlert) soundAlert.checked = this.settings.soundAlert;

        // Email
        const alertEmail = document.getElementById('alertEmail');
        if (alertEmail) alertEmail.value = this.settings.alertEmail || '';

        // Camera
        const cameraSource = document.getElementById('cameraSource');
        if (cameraSource) cameraSource.value = this.settings.cameraSource || '0';
    }

    renderLogs() {
        const container = document.getElementById('logContainer');
        if (!container) return;

        if (this.logs.length === 0) {
            container.innerHTML = '<p class="empty-state">Aucune activité récente</p>';
            return;
        }

        container.innerHTML = this.logs.slice(0, 20).map(log => {
            const date = new Date(log.created_at);
            const timeStr = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
            const typeClass = log.event_type === 'alert' ? 'alert' : 'info';

            return `
                <div class="log-entry ${typeClass}">
                    <span class="log-time">${timeStr}</span>
                    <span class="log-type">${log.event_type}</span>
                    <span class="log-message">${log.user_name || 'Système'}</span>
                </div>
            `;
        }).join('');
    }

    renderHistory(logs) {
        const container = document.getElementById('historyList');
        if (!container) return;

        if (!logs || logs.length === 0) {
            container.innerHTML = '<p class="empty-state">Aucun événement enregistré</p>';
            return;
        }

        container.innerHTML = logs.map(log => {
            const date = new Date(log.created_at);
            const dateStr = date.toLocaleDateString('fr-FR');
            const timeStr = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

            let iconClass = 'detection';
            let icon = '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>';

            if (log.event_type === 'alert' || log.event_type === 'intrusion') {
                iconClass = 'alert';
                icon = '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>';
            } else if (log.event_type === 'lock') {
                iconClass = 'lock';
                icon = '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>';
            }

            return `
                <div class="history-item">
                    <div class="history-icon ${iconClass}">${icon}</div>
                    <div class="history-details">
                        <h4>${log.event_type}</h4>
                        <p>${log.user_name || 'Système'}</p>
                    </div>
                    <div class="history-time">
                        <span>${dateStr}</span>
                        <span>${timeStr}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateStatusPanel(data) {
        const statusItems = document.querySelector('.status-items');
        if (!statusItems) return;

        statusItems.innerHTML = `
            <div class="status-item">
                <span class="status-label">État</span>
                <span class="status-value ${data.detection_active ? 'active' : 'inactive'}">
                    ${data.detection_active ? 'Surveillance active' : 'En veille'}
                </span>
            </div>
            <div class="status-item">
                <span class="status-label">Caméra</span>
                <span class="status-value ${data.camera_connected ? 'active' : 'error'}">
                    ${data.camera_connected ? 'Connectée' : 'Déconnectée'}
                </span>
            </div>
            <div class="status-item">
                <span class="status-label">Visages enregistrés</span>
                <span class="status-value">${data.encodings_loaded || 0}</span>
            </div>
        `;
    }

    updateDetectionButton() {
        const btn = document.getElementById('toggleDetectionBtn');
        if (!btn) return;

        btn.textContent = this.isDetecting ? 'Arrêter' : 'Démarrer';
        btn.className = `btn ${this.isDetecting ? 'btn-danger' : 'btn-primary'}`;
    }

    updateStatus(message, type) {
        const statusEl = document.getElementById('connectionStatus');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `connection-status ${type}`;
        }
    }

    // --- UI Helpers ---

    showNotification(message, type = 'info') {
        let container = document.getElementById('notifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications';
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        container.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    addLogEntry(entry) {
        this.logs.unshift(entry);
        this.renderLogs();
    }

    showAddUserModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'addUserModal';
        modal.innerHTML = `
            <div class="modal">
                <h3>Ajouter un utilisateur</h3>
                <form id="addUserForm">
                    <div class="form-group">
                        <label>Nom *</label>
                        <input type="text" name="name" required placeholder="Nom de l'utilisateur">
                    </div>
                    <div class="form-group">
                        <label>Email (optionnel)</label>
                        <input type="email" name="email" placeholder="email@exemple.com">
                    </div>
                    <div class="form-group checkbox">
                        <label>
                            <input type="checkbox" name="is_owner">
                            Propriétaire (utilisateur principal)
                        </label>
                    </div>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-secondary" onclick="app.closeModal()">Annuler</button>
                        <button type="submit" class="btn btn-primary">Créer</button>
                    </div>
                </form>
                <p style="margin-top:15px;font-size:12px;color:#64748b;">
                    Après création, cliquez sur l'icône photo pour ajouter une image du visage.
                </p>
            </div>
        `;

        document.body.appendChild(modal);

        document.getElementById('addUserForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            this.createUser(
                formData.get('name'),
                formData.get('email'),
                formData.get('is_owner') === 'on'
            );
        });

        // Fermer si on clique en dehors
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeModal();
        });
    }

    closeModal() {
        const modal = document.getElementById('addUserModal');
        if (modal) modal.remove();
    }

    handleStatusUpdate(data) {
        if (data.detecting !== undefined) {
            this.isDetecting = data.detecting;
            this.updateDetectionButton();
        }
    }

    // --- Event Listeners ---

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.main-nav a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                if (page) this.navigateTo(page);
            });
        });

        // Bouton de détection
        const toggleBtn = document.getElementById('toggleDetectionBtn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleDetection());
        }

        // Boutons d'ajout d'utilisateur
        const addUserBtn = document.getElementById('addUserBtn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => this.showAddUserModal());
        }

        const addUserBtnPage = document.getElementById('addUserBtnPage');
        if (addUserBtnPage) {
            addUserBtnPage.addEventListener('click', () => this.showAddUserModal());
        }

        // Paramètres - Slider
        const thresholdInput = document.getElementById('unknownThreshold');
        const thresholdValue = document.getElementById('unknownThresholdValue');
        if (thresholdInput && thresholdValue) {
            thresholdInput.addEventListener('input', (e) => {
                thresholdValue.textContent = e.target.value;
            });
        }

        // Paramètres - Boutons
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }

        const importLegacyBtn = document.getElementById('importLegacyBtn');
        if (importLegacyBtn) {
            importLegacyBtn.addEventListener('click', () => this.importLegacyFaces());
        }

        // Historique - Filtre
        const historyFilter = document.getElementById('historyFilter');
        if (historyFilter) {
            historyFilter.addEventListener('change', async (e) => {
                const filter = e.target.value;
                try {
                    let endpoint = '/api/logs?limit=100';
                    if (filter !== 'all') {
                        endpoint += `&type=${filter}`;
                    }
                    const data = await this.apiCall(endpoint);
                    this.renderHistory(data.logs || []);
                } catch (error) {
                    console.error('Erreur filtre historique:', error);
                }
            });
        }

        // Contrôles de fenêtre (Electron)
        const minimizeBtn = document.getElementById('minimizeBtn');
        const maximizeBtn = document.getElementById('maximizeBtn');
        const closeBtn = document.getElementById('closeBtn');

        if (window.electronAPI) {
            if (minimizeBtn) {
                minimizeBtn.addEventListener('click', () => {
                    console.log('Minimize clicked');
                    window.electronAPI.minimize();
                });
            }
            if (maximizeBtn) {
                maximizeBtn.addEventListener('click', () => {
                    console.log('Maximize clicked');
                    window.electronAPI.maximize();
                });
            }
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    console.log('Close clicked');
                    window.electronAPI.hideToTray();
                });
            }
        } else {
            console.warn('electronAPI non disponible');
        }

        // Rafraîchir les données périodiquement
        setInterval(() => {
            if (!this.isDetecting) {
                this.loadStatus();
            }
        }, 10000);
    }
}

// Initialiser l'application quand le DOM est prêt
let app;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM ready, initializing AltaLock...');
    app = new AltaLockApp();
    app.init();
});

// Exposer globalement
window.app = null;
setTimeout(() => { window.app = app; }, 100);
