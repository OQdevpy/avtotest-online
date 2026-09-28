const { app, BrowserWindow, ipcMain, session } = require('electron');
const fs = require('fs');
const path = require('path');

// Versiya o'zgarganda (yangi o'rnatish/yangilash) eski localStorage, IndexedDB,
// cookie va kesh tozalanadi — eski `quizToken` va eski ma'lumot qolmaydi.
const VERSION_FILE = path.join(app.getPath('userData'), 'app-version.txt');

async function resetStorageOnNewVersion() {
  let previous = null;
  try {
    previous = fs.readFileSync(VERSION_FILE, 'utf8').trim();
  } catch {
    // birinchi ishga tushirish
  }
  if (previous === app.getVersion()) return;

  await session.defaultSession.clearStorageData();
  await session.defaultSession.clearCache();
  fs.mkdirSync(path.dirname(VERSION_FILE), { recursive: true });
  fs.writeFileSync(VERSION_FILE, app.getVersion());
}

// Electron oynasini yaratish
function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    frame: false,
    icon: path.join(__dirname, 'static-images/icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      // Renderer Node API ishlatmaydi — faqat preload orqali `window.Electron`
      nodeIntegration: false,
      contextIsolation: true,
      devTools: false,
    },
  });

  // 'index.html' faylini yuklash (HashRouter — file:// da ham to'g'ri)
  win.loadFile(path.join(__dirname, 'index.html'));

  win.setFullScreen(true); // Bu oynani to'liq ekran rejimida ochadi

  // Faqat harflar, sonlar va chap-o'ng tugmalarini o'rnatish
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

// Faqat bitta nusxa: ikkinchi marta ochilsa — mavjud oyna oldinga chiqadi.
// Aks holda ikki nusxa bir xil profil papkasini band qiladi.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const [win] = BrowserWindow.getAllWindows();
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });
}

// Navbar'dagi yopish tugmasi (kod bilan) — ilovadan chiqish
ipcMain.on('app-close', () => {
  app.quit();
});

// Ilova ishga tushganda oynani yaratish
app.whenReady().then(async () => {
  try {
    await resetStorageOnNewVersion();
  } catch (error) {
    console.error('Storage tozalanmadi:', error);
  }
  createWindow();

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
