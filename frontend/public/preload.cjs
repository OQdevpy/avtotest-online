// Renderer'ga faqat kerakli API: ilovani yopish va desktop ekanligi belgisi.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('Electron', {
  isDesktop: true,
  ipcRenderer: {
    send: (channel) => {
      if (channel === 'app-close') ipcRenderer.send(channel);
    },
  },
});
