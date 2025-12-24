/**
 * AltaLock - Main Process (Electron)
 * Gère le cycle de vie de l'application et le backend Python
 */
const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

// Squirrel startup (Windows installer)
if (process.platform === 'win32') {
    const cmd = process.argv[1];
    if (cmd === '--squirrel-install' || cmd === '--squirrel-updated' ||
        cmd === '--squirrel-uninstall' || cmd === '--squirrel-obsolete') {
        app.quit();
    }
}

// Variables globales
let mainWindow = null;
let splashWindow = null;
let tray = null;
let backendProcess = null;

// Mode dev ou production
const isDev = !app.isPackaged;
const BACKEND_PORT = 5000;

// Chemins
const rootPath = isDev
    ? path.join(__dirname, '..')
    : process.resourcesPath;

function log(message) {
    console.log(`[AltaLock] ${message}`);
}

// Vérifier si le backend est prêt
function checkBackendReady() {
    return new Promise((resolve) => {
        const check = () => {
            const req = http.request({
                hostname: '127.0.0.1',
                port: BACKEND_PORT,
                path: '/api/status',
                method: 'GET',
                timeout: 1000
            }, (res) => {
                if (res.statusCode === 200) {
                    resolve(true);
                } else {
                    setTimeout(check, 500);
                }
            });

            req.on('error', () => setTimeout(check, 500));
            req.on('timeout', () => {
                req.destroy();
                setTimeout(check, 500);
            });
            req.end();
        };
        check();
    });
}

// Créer le splash screen
function createSplashWindow() {
    return new Promise((resolve) => {
        log('Creation du splash screen...');

        splashWindow = new BrowserWindow({
            width: 400,
            height: 300,
            frame: false,
            transparent: false,
            alwaysOnTop: true,
            resizable: false,
            skipTaskbar: true,
            show: false,
            backgroundColor: '#0f172a',
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true
            }
        });

        const splashPath = path.join(__dirname, 'splash.html');

        splashWindow.once('ready-to-show', () => {
            log('Splash pret');
            splashWindow.show();
            splashWindow.center();
            resolve();
        });

        splashWindow.on('closed', () => { splashWindow = null; });
        splashWindow.loadFile(splashPath);
    });
}

// Démarrer le backend
function startBackend() {
    return new Promise((resolve, reject) => {
        log('Demarrage du backend...');

        let backendPath;
        let args = [];

        if (isDev) {
            // Dev : lance Python directement
            backendPath = process.platform === 'win32' ? 'python' : 'python3';
            args = [path.join(rootPath, 'backend', 'app.py')];
            log(`Dev mode: ${backendPath} ${args.join(' ')}`);
        } else {
            // Production : lance l'exe PyInstaller
            const possiblePaths = [
                path.join(rootPath, 'backend', 'altalock-backend.exe'),
                path.join(process.resourcesPath, 'backend', 'altalock-backend.exe'),
                path.join(path.dirname(process.execPath), 'backend', 'altalock-backend.exe')
            ];

            backendPath = possiblePaths.find(p => {
                try {
                    fs.accessSync(p);
                    return true;
                } catch {
                    return false;
                }
            }) || possiblePaths[0];

            log(`Prod mode: ${backendPath}`);
        }

        backendProcess = spawn(backendPath, args, {
            cwd: isDev ? rootPath : path.dirname(backendPath),
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: process.platform === 'win32'
        });

        backendProcess.stdout.on('data', (data) => {
            log(`Backend: ${data.toString().trim()}`);
        });

        backendProcess.stderr.on('data', (data) => {
            log(`Backend stderr: ${data.toString().trim()}`);
        });

        backendProcess.on('error', (err) => {
            log(`Erreur backend: ${err.message}`);
            reject(err);
        });

        backendProcess.on('close', (code) => {
            log(`Backend ferme avec code: ${code}`);
        });

        resolve();
    });
}

// Arrêter le backend
function stopBackend() {
    if (backendProcess) {
        log('Arret du backend...');
        if (process.platform === 'win32') {
            spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
        } else {
            backendProcess.kill('SIGTERM');
        }
        backendProcess = null;
    }
}

// Créer la fenêtre principale
function createMainWindow() {
    return new Promise((resolve) => {
        log('Creation de la fenetre principale...');

        mainWindow = new BrowserWindow({
            width: 1400,
            height: 900,
            minWidth: 1000,
            minHeight: 700,
            title: 'AltaLock',
            show: false,
            backgroundColor: '#0f172a',
            webPreferences: {
                preload: path.join(__dirname, 'preload.js'),
                nodeIntegration: false,
                contextIsolation: true
            }
        });

        mainWindow.loadFile(path.join(__dirname, 'index.html'));

        mainWindow.webContents.once('did-finish-load', () => {
            log('Contenu charge');
            setTimeout(resolve, 300);
        });

        mainWindow.on('close', (event) => {
            if (tray) {
                event.preventDefault();
                mainWindow.hide();
            }
        });

        mainWindow.on('closed', () => { mainWindow = null; });

        if (isDev) {
            mainWindow.webContents.openDevTools();
        }
    });
}

// Créer le tray
function createTray() {
    const iconPath = path.join(__dirname, '..', 'assets', 'icons', 'icon.png');
    let icon;

    try {
        icon = nativeImage.createFromPath(iconPath);
        if (icon.isEmpty()) icon = nativeImage.createEmpty();
    } catch {
        icon = nativeImage.createEmpty();
    }

    tray = new Tray(icon);

    const contextMenu = Menu.buildFromTemplate([
        { label: 'Ouvrir AltaLock', click: () => { if (mainWindow) { mainWindow.show(); mainWindow.focus(); } } },
        { type: 'separator' },
        { label: 'Quitter', click: () => { tray = null; app.quit(); } }
    ]);

    tray.setToolTip('AltaLock - Protection Faciale');
    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => { if (mainWindow) { mainWindow.show(); mainWindow.focus(); } });
}

// IPC handlers
ipcMain.handle('get-backend-url', () => `http://localhost:${BACKEND_PORT}`);
ipcMain.on('minimize', () => { if (mainWindow) mainWindow.minimize(); });
ipcMain.on('maximize', () => { if (mainWindow) mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize(); });
ipcMain.on('close', () => { if (mainWindow) mainWindow.close(); });
ipcMain.on('hide-to-tray', () => { if (mainWindow) mainWindow.hide(); });

// Démarrage de l'app
app.whenReady().then(async () => {
    try {
        await createSplashWindow();
        log('Splash affiche');

        startBackend();
        log('Backend lance');

        log('Attente du backend...');
        await checkBackendReady();
        log('Backend pret!');

        await createMainWindow();
        log('Fenetre principale chargee!');

        createTray();

        if (splashWindow && !splashWindow.isDestroyed()) {
            splashWindow.close();
        }
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.show();
            mainWindow.focus();
        }
        log('Application prete!');

    } catch (error) {
        log(`Erreur au demarrage: ${error.message}`);
        if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
        if (!mainWindow) await createMainWindow();
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.show();
    }
});

app.on('window-all-closed', () => {
    stopBackend();
    if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => { stopBackend(); tray = null; });
app.on('quit', () => stopBackend());

// Empêcher plusieurs instances
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
        }
    });
}
