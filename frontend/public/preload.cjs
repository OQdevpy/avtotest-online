// Renderer'ga faqat kerakli API: ilovani yopish va desktop ekanligi belgisi.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('Electron', {
  isDesktop: true,
  // Kompyuter ID'si (sha256) — kirish kodi bitta kompyuterga biriktiriladi
  getMachineId: () => ipcRenderer.invoke('machine-id'),
  // Bir marta kiritilgan kirish kodi — ilova qayta ochilsa ham so'ralmaydi
  getSavedCode: () => ipcRenderer.invoke('saved-code-get'),
  setSavedCode: (code) => ipcRenderer.invoke('saved-code-set', String(code || '')),
  ipcRenderer: {
    send: (channel) => {
      if (channel === 'app-close') ipcRenderer.send(channel);
    },
  },
});
