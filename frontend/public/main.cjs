const { app, BrowserWindow, ipcMain, globalShortcut } = require('electron');
const path = require('path');

// Electron oynasini yaratish
function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    frame:false,
    icon: path.join(__dirname, 'static-images/icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'), // Agar kerak bo'lsa, preload skriptini qo'shish
      nodeIntegration: true,
      contextIsolation: false, // React va Electron o'rtasida uzviy aloqani ta'minlash
      devTools:false
    },
  });

  // 'index.html' faylini yuklash
  win.loadFile(path.join(__dirname, 'index.html'));

  // Developer Tools-ni o'chirish
  // win.webContents.on('devtools-opened', () => {
  //   win.webContents.closeDevTools();
  // });

  win.setFullScreen(true); // Bu oynani to'liq ekran rejimida ochadi


  // Faqat harflar, sonlar va chap-o'ng tugmalarini o‘rnatish
  // Klaviatura cheklovlarini o‘rnatish
  win.webContents.on('before-input-event', (event, input) => {
    const validKeys = [
      'Enter', 'Backspace', 'ArrowLeft', 'ArrowRight', // Harakat uchun tugmalar
      ...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('') // Faqat harflar va sonlar
    ];

    if (!validKeys.includes(input.key)) {
      event.preventDefault(); // Noto'g'ri tugmani bosishga yo'l qo'ymaslik
    }
  });
}

// Ilova ishga tushganda oynani yaratish
app.whenReady().then(() => {
  createWindow();

  // MacOS uchun Cmd+Q ishga tushirish
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Ilova tugagandan so'ng, barcha oynalar yopilishi kerak
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
