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
      path.join(__dirname, 'backend')
    ]
  },
  rebuildConfig: {},
  makers: [
    {
      name: '@electron-forge/maker-zip',
      platforms: ['darwin', 'linux', 'win32']
    }
  ]
};
