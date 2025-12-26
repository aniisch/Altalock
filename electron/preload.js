/**
 * AltaLock - Preload Script
 * Bridge sécurisé entre le renderer et le main process
 */
const { contextBridge, ipcRenderer } = require('electron');

// Exposer une API sécurisée au renderer
contextBridge.exposeInMainWorld('electronAPI', {
    // Fenêtre
    minimize: () => ipcRenderer.send('minimize'),
    maximize: () => ipcRenderer.send('maximize'),
    close: () => ipcRenderer.send('close'),
    hideToTray: () => ipcRenderer.send('hide-to-tray'),

    // Informations
    getAppPath: () => ipcRenderer.invoke('get-app-path'),
    getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),

    // Écouter les actions du tray
    onTrayAction: (callback) => {
        ipcRenderer.on('tray-action', (event, action) => callback(action));
    },

    // Supprimer les listeners
    removeAllListeners: (channel) => {
        ipcRenderer.removeAllListeners(channel);
    }
});

// Informer que le preload est chargé
console.log('AltaLock preload script chargé');
