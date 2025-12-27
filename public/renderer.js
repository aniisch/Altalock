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
        this.blacklistedUsers = [];
        this.logs = [];
        this.settings = {
            unknownThreshold: 9,  // 3 secondes * 3 détections/sec
            lockScreenEnabled: true,
            sleepAfterLock: true,
            soundAlert: true,
            alertEmail: '',
            alertMessage: 'Accès non autorisé détecté',
            cameraSource: 0,
            // SMTP settings
            smtp_server: '',
            smtp_port: 587,
            smtp_user: '',
            smtp_password: ''
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
            this.renderBlacklistGrid();
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
            // Séparer utilisateurs autorisés et blacklistés
            this.users = (data.users || []).filter(u => !u.is_blacklisted);
            this.blacklistedUsers = (data.users || []).filter(u => u.is_blacklisted);
            this.renderUsers();
            if (this.currentPage === 'users') {
                this.renderUsersFullPage();
                this.renderBlacklistGrid();
            }
        } catch (error) {
            console.error('Erreur chargement utilisateurs:', error);
            this.users = [];
            this.blacklistedUsers = [];
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
            const thresholdSeconds = parseInt(document.getElementById('unknownThresholdSeconds')?.value || '3');
            const unknownThreshold = thresholdSeconds * 3;  // Convertir secondes en détections
            const lockScreenEnabled = document.getElementById('lockScreenEnabled')?.checked ?? true;
            const sleepAfterLock = document.getElementById('sleepAfterLock')?.checked ?? true;
            const soundAlert = document.getElementById('soundAlert')?.checked ?? true;
            const alertMessage = document.getElementById('alertMessage')?.value || 'Accès non autorisé détecté';
            const alertEmail = document.getElementById('alertEmail')?.value || '';
            const cameraSource = document.getElementById('cameraSource')?.value || '0';

            // SMTP settings
            const smtp_server = document.getElementById('smtpServer')?.value || '';
            const smtp_port = parseInt(document.getElementById('smtpPort')?.value || '587');
            const smtp_user = document.getElementById('smtpUser')?.value || '';
            const smtp_password = document.getElementById('smtpPassword')?.value || '';

            this.settings = {
                unknownThreshold: unknownThreshold,
                lockScreenEnabled,
                sleepAfterLock,
                soundAlert,
                alertMessage,
                alert_message: alertMessage,
                alertEmail,
                alert_email: alertEmail,
                cameraSource: parseInt(cameraSource),
                // SMTP
                smtp_server,
                smtp_port,
                smtp_user,
                smtp_password
            };

            await this.apiCall('/api/settings', {
                method: 'POST',
                body: JSON.stringify(this.settings)
            });

            // Recharger les paramètres depuis le serveur pour s'assurer qu'ils sont à jour
            await this.loadSettings();

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

    async clearHistory() {
        if (!confirm('Êtes-vous sûr de vouloir effacer tout l\'historique ?')) return;

        try {
            await this.apiCall('/api/logs', { method: 'DELETE' });
            this.showNotification('Historique effacé', 'success');
            this.logs = [];
            this.renderLogs();
            this.renderHistory([]);
        } catch (error) {
            this.showNotification(error.message, 'error');
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

    async testEmail() {
        try {
            // Sauvegarder d'abord les paramètres SMTP
            await this.saveSettings();

            this.showNotification('Envoi de l\'email de test...', 'info');
            const data = await this.apiCall('/api/test-email', { method: 'POST' });
            this.showNotification(data.message || 'Email envoyé avec succès!', 'success');
        } catch (error) {
            this.showNotification('Erreur: ' + error.message, 'error');
        }
    }

    // --- Détection ---

    async startDetection() {
        try {
            // Afficher l'overlay de chargement
            this.showLoadingOverlay('Démarrage de la surveillance...');

            await this.apiCall('/api/detection/start', { method: 'POST' });
            this.isDetecting = true;
            this.updateDetectionButton();
            this.showNotification('Surveillance démarrée', 'success');
        } catch (error) {
            this.showNotification(error.message, 'error');
        } finally {
            this.hideLoadingOverlay();
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

    async createUser(name, email, isOwner = false, isBlacklisted = false, customMessage = null) {
        try {
            await this.apiCall('/api/users', {
                method: 'POST',
                body: JSON.stringify({
                    name,
                    email,
                    is_owner: isOwner,
                    is_blacklisted: isBlacklisted,
                    custom_message: customMessage
                })
            });
            const msg = isBlacklisted ? 'Personne ajoutée à la blacklist' : 'Utilisateur créé';
            this.showNotification(msg, 'success');
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

    renderBlacklistGrid() {
        const grid = document.getElementById('blacklistGrid');
        if (!grid) return;

        if (this.blacklistedUsers.length === 0) {
            grid.innerHTML = '<p class="empty-state">Aucune personne blacklistée</p>';
            return;
        }

        grid.innerHTML = this.blacklistedUsers.map(user => `
            <div class="user-card blacklisted">
                <div class="user-avatar" style="background: var(--danger);">
                    ${user.name.charAt(0).toUpperCase()}
                </div>
                <div class="user-info">
                    <h4>${user.name}</h4>
                    <span class="user-meta">${user.face_count || 0} visage(s)</span>
                    <span class="badge" style="background: rgba(239,68,68,0.2); color: var(--danger);">Blacklisté</span>
                    ${user.custom_message ? `<p style="margin-top:8px;font-size:12px;color:var(--warning);font-style:italic;">"${user.custom_message}"</p>` : ''}
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
        // Threshold slider (convertir détections en secondes)
        const thresholdInput = document.getElementById('unknownThresholdSeconds');
        const thresholdValue = document.getElementById('unknownThresholdValue');
        if (thresholdInput && thresholdValue) {
            // Convertir le nombre de détections en secondes (÷3)
            const seconds = Math.round((this.settings.unknownThreshold || 9) / 3);
            thresholdInput.value = Math.max(1, Math.min(5, seconds));
            thresholdValue.textContent = thresholdInput.value;
        }

        // Checkboxes
        const lockScreen = document.getElementById('lockScreenEnabled');
        if (lockScreen) lockScreen.checked = this.settings.lockScreenEnabled;

        const sleepAfterLock = document.getElementById('sleepAfterLock');
        if (sleepAfterLock) sleepAfterLock.checked = this.settings.sleepAfterLock;

        const soundAlert = document.getElementById('soundAlert');
        if (soundAlert) soundAlert.checked = this.settings.soundAlert;

        // Alert message
        const alertMessage = document.getElementById('alertMessage');
        if (alertMessage) alertMessage.value = this.settings.alertMessage || this.settings.alert_message || '';

        // Email
        const alertEmail = document.getElementById('alertEmail');
        if (alertEmail) alertEmail.value = this.settings.alertEmail || this.settings.alert_email || '';

        // Camera
        const cameraSource = document.getElementById('cameraSource');
        if (cameraSource) cameraSource.value = this.settings.cameraSource || '0';

        // SMTP settings
        const smtpServer = document.getElementById('smtpServer');
        if (smtpServer) smtpServer.value = this.settings.smtp_server || '';

        const smtpPort = document.getElementById('smtpPort');
        if (smtpPort) smtpPort.value = this.settings.smtp_port || '587';

        const smtpUser = document.getElementById('smtpUser');
        if (smtpUser) smtpUser.value = this.settings.smtp_user || '';

        const smtpPassword = document.getElementById('smtpPassword');
        if (smtpPassword) smtpPassword.value = this.settings.smtp_password || '';
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
                icon = '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>';
            } else if (log.event_type === 'lock') {
                iconClass = 'lock';
                icon = '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>';
            }

            // Afficher l'image si disponible
            const hasImage = log.image_path;
            let imageFilename = null;
            if (hasImage) {
                // Si c'est un chemin complet (ancien format), extraire le nom
                // Sinon c'est déjà juste le nom du fichier (nouveau format)
                if (log.image_path.includes('/') || log.image_path.includes('\\')) {
                    const parts = log.image_path.replace(/\\/g, '/').split('/');
                    imageFilename = parts[parts.length - 1];
                } else {
                    imageFilename = log.image_path;
                }
            }
            const imageUrl = imageFilename ? `${this.backendUrl}/data/captures/${imageFilename}` : null;

            return `
                <div class="history-item ${hasImage ? 'has-image' : ''}">
                    ${hasImage ? `
                        <div class="history-thumbnail" data-image="${imageFilename}" onclick="app.showImageModal(this.dataset.image)">
                            <img src="${imageUrl}" alt="Capture" onerror="this.style.display='none'">
                        </div>
                    ` : `
                        <div class="history-icon ${iconClass}">${icon}</div>
                    `}
                    <div class="history-details">
                        <h4>${(log.event_type === 'alert' || log.event_type === 'intrusion') ? 'Intrusion détectée' : (log.event_type === 'lock' ? 'Session verrouillée' : log.event_type)}</h4>
                        <p>${log.user_name || (log.details ? (typeof log.details === 'string' ? JSON.parse(log.details).detected_name : log.details.detected_name) : null) || 'Inconnu'}</p>
                    </div>
                    <div class="history-time">
                        <span>${dateStr}</span>
                        <span>${timeStr}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    showImageModal(filename) {
        // filename est maintenant toujours juste le nom du fichier
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'imageModal';
        modal.innerHTML = `
            <div class="modal" style="max-width: 600px; padding: 10px;">
                <img src="${this.backendUrl}/data/captures/${filename}"
                     style="width: 100%; border-radius: 8px;"
                     alt="Capture intrus"
                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📷</text></svg>'">
                <button class="btn btn-secondary" style="margin-top: 10px; width: 100%;" onclick="app.closeImageModal()">Fermer</button>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeImageModal();
        });
    }

    closeImageModal() {
        const modal = document.getElementById('imageModal');
        if (modal) modal.remove();
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

    showLoadingOverlay(message = 'Chargement...') {
        // Supprimer l'ancien overlay s'il existe
        this.hideLoadingOverlay();

        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <p>${message}</p>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    hideLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.remove();
    }

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
                <h3>Ajouter un utilisateur autorisé</h3>
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
                formData.get('is_owner') === 'on',
                false,
                null
            );
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeModal();
        });
    }

    showBlacklistModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'addUserModal';
        modal.innerHTML = `
            <div class="modal">
                <h3 style="color: var(--danger);">Ajouter à la Blacklist</h3>
                <form id="addBlacklistForm">
                    <div class="form-group">
                        <label>Nom de la personne *</label>
                        <input type="text" name="name" required placeholder="Ex: Jean Dupont">
                    </div>
                    <div class="form-group">
                        <label>Message personnalisé</label>
                        <input type="text" name="custom_message" placeholder="Ex: Touche pas à ma machine, {nom}!">
                        <p style="font-size:11px;color:#64748b;margin-top:4px;">Utilisez {nom} pour insérer le nom de la personne</p>
                    </div>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-secondary" onclick="app.closeModal()">Annuler</button>
                        <button type="submit" class="btn btn-danger">Ajouter à la blacklist</button>
                    </div>
                </form>
                <p style="margin-top:15px;font-size:12px;color:#64748b;">
                    Après création, ajoutez une photo pour que le système reconnaisse cette personne.
                </p>
            </div>
        `;

        document.body.appendChild(modal);

        document.getElementById('addBlacklistForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            this.createUser(
                formData.get('name'),
                null,
                false,
                true,
                formData.get('custom_message') || null
            );
        });

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

        const addBlacklistBtn = document.getElementById('addBlacklistBtn');
        if (addBlacklistBtn) {
            addBlacklistBtn.addEventListener('click', () => this.showBlacklistModal());
        }

        // Paramètres - Slider (secondes)
        const thresholdInput = document.getElementById('unknownThresholdSeconds');
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

        // Test email button
        const testEmailBtn = document.getElementById('testEmailBtn');
        if (testEmailBtn) {
            testEmailBtn.addEventListener('click', () => this.testEmail());
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

        // Historique - Effacer
        const clearHistoryBtn = document.getElementById('clearHistoryBtn');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => this.clearHistory());
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
