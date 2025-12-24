const path = require('path');

module.exports = {
  packagerConfig: {
    name: 'AltaLock',
    executableName: 'altalock',
    asar: true,
    icon: path.join(__dirname, '..', 'assets', 'icons', 'icon'),
    ignore: [
      /^\/src/,
      /^\/\.git/,
      /^\/\.vscode/,
      /\.md$/,
      /\.log$/
    ],
    extraResource: [
      './backend'
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
        setupIcon: path.join(__dirname, '..', 'assets', 'icons', 'icon.ico'),
        noMsi: true
      }
    },
    {
      name: '@electron-forge/maker-zip',
      platforms: ['darwin', 'linux', 'win32']
    }
  ]
};
