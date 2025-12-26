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
    {
      name: '@electron-forge/maker-squirrel',
      config: {
        name: 'AltaLock',
        authors: 'aniisch',
        description: 'Application de securite avec reconnaissance faciale',
        iconUrl: 'file://' + path.join(__dirname, 'assets', 'icons', 'icon.ico'),
        setupIcon: path.join(__dirname, 'assets', 'icons', 'icon.ico'),
        // Splash personnalisé pendant l'installation (remplace le vert par défaut)
        loadingGif: path.join(__dirname, 'assets', 'loading.gif'),
        noMsi: true
      }
    },
    {
      name: '@electron-forge/maker-zip',
      platforms: ['darwin', 'linux', 'win32']
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
