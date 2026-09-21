// preload.js (agar kerak bo'lsa)
const { contextBridge } = require('electron');

// Electron API'ni React yoki boshqa frontendga taqdim etish
contextBridge.exposeInMainWorld('electron', {
  // O'zgarishlar yoki custom API-lar qo'shish mumkin
});
