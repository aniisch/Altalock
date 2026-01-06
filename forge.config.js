const path = require('path');

module.exports = {
  packagerConfig: {
    name: 'AltaLock',
    executableName: 'altalock',
    asar: true,
    icon: path.join(__dirname, 'assets', 'icons', 'icon'),
    ignore: [
      // Ignorer le backend Python source
      /^\/backend/,
      // Ignorer l'ancien dossier frontend
      /^\/frontend/,
      // Ignorer electron/backend (il est en extraResource, pas dans asar)
      /^\/electron\/backend/,
      // Ignorer node_modules sauf electron-squirrel-startup
      /^\/node_modules\/(?!(electron-squirrel-startup))/,
      // Ignorer les fichiers de config/dev
      /^\/\.git/,
      /^\/\.vscode/,
      /^\/\.claude/,
      /^\/RD-face_recognition-master/,
      /^\/dist/,
      /^\/build/,
      /^\/out/,
      /^\/data/,
      /\.md$/,
      /\.log$/,
      /\.spec$/,
      /\.txt$/,
      /\.py$/,
      /requirements\.txt$/,
      /\.env/
    ],
    // Le backend exe va dans resources (pas bundled dans asar)
    extraResource: [
      './electron/backend'
    ]
  },
  rebuildConfig: {},
  makers: [
    // Installeur Squirrel (pour version CPU légère < 1 Go)
    {
      name: '@electron-forge/maker-squirrel',
      config: {
        name: 'AltaLock',
        authors: 'aniisch',
        description: 'Application de sécurité avec reconnaissance faciale',
        iconUrl: 'https://raw.githubusercontent.com/aniisch/Altalock/main/assets/icons/icon.ico',
        setupIcon: path.join(__dirname, 'assets', 'icons', 'icon.ico'),
        loadingGif: path.join(__dirname, 'assets', 'loading.gif')
      }
    },
    // ZIP portable (toujours disponible)
    {
      name: '@electron-forge/maker-zip',
      platforms: ['win32']
    },
    {
      name: '@electron-forge/maker-deb',
      config: {
        options: {
          name: 'altalock',
          productName: 'AltaLock',
          maintainer: 'aniisch',
          categories: ['Utility', 'Security']
        }
      }
    }
  ]
};
