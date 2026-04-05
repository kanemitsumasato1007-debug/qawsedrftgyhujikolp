const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fileManager = require('./modules/fileManager');
const dashboardUpdater = require('./modules/dashboardUpdater');

let mainWindow;

// CrowdWorksログイン状態
let cwLoggedIn = false;
const CW_PARTITION = 'persist:crowdworks';

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'データ蓄積・学習マネージャー',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

// データ保存先のベースパス
function getDataPath() {
  return path.join(__dirname, '..', '履歴　学習用');
}

// CrowdWorksログインウィンドウを開く
ipcMain.handle('cw-login', async () => {
  return await new Promise((resolve) => {
    const loginWin = new BrowserWindow({
      width: 900,
      height: 700,
      title: 'CrowdWorks ログイン',
      webPreferences: {
        partition: CW_PARTITION,
        contextIsolation: true,
        nodeIntegration: false
      }
    });

    loginWin.setMenuBarVisibility(false);

    let resolved = false;

    // ページ遷移を監視
    // Googleログインの場合: crowdworks → accounts.google.com → crowdworks
    loginWin.webContents.on('did-navigate', (event, url) => {
      if (resolved) return;
      // Google認証中はスキップ
      if (url.includes('accounts.google.com') || url.includes('google.com/signin')) return;

      // CrowdWorksのログイン/認証関連以外のページに到達したら成功
      if (url.includes('crowdworks.jp') &&
          !url.includes('/login') &&
          !url.includes('/auth/') &&
          !url.includes('/user_sessions') &&
          !url.includes('/oauth/')) {
        resolved = true;
        cwLoggedIn = true;
        setTimeout(() => {
          loginWin.close();
        }, 1000);
        resolve({ success: true });
      }
    });

    loginWin.on('closed', () => {
      if (!resolved) {
        resolved = true;
        resolve({ success: false, error: 'ログインがキャンセルされました' });
      }
    });

    loginWin.loadURL('https://crowdworks.jp/login');
  });
});

// ログイン状態確認
ipcMain.handle('cw-login-status', async () => {
  return { loggedIn: cwLoggedIn };
});

// データ保存
ipcMain.handle('save-data', async (event, { category, data }) => {
  const basePath = getDataPath();
  const result = await fileManager.saveData(basePath, category, data);
  if (result.success) {
    await dashboardUpdater.update(basePath);
  }
  return result;
});

// データ読み込み
ipcMain.handle('load-data', async (event, { category }) => {
  const basePath = getDataPath();
  return await fileManager.loadData(basePath, category);
});

// ダッシュボード取得
ipcMain.handle('get-dashboard', async () => {
  const basePath = getDataPath();
  return await fileManager.getAllData(basePath);
});

// 隠しウィンドウでページを取得してタイトルを返す
function fetchPageTitle(url) {
  return new Promise((resolve) => {
    const fetchWin = new BrowserWindow({
      width: 800,
      height: 600,
      show: false,
      webPreferences: {
        partition: CW_PARTITION,
        contextIsolation: true,
        nodeIntegration: false
      }
    });

    let resolved = false;

    fetchWin.webContents.on('did-finish-load', async () => {
      if (resolved) return;
      try {
        const currentUrl = fetchWin.webContents.getURL();

        if (currentUrl.includes('/login')) {
          resolved = true;
          fetchWin.close();
          resolve({ success: false, error: 'ログインが必要です。設定画面でCrowdWorksにログインしてください' });
          return;
        }

        const title = await fetchWin.webContents.executeJavaScript('document.title');
        resolved = true;
        fetchWin.close();

        if (title) {
          let cleanTitle = title.trim();
          if (cleanTitle.includes('ログイン')) {
            resolve({ success: false, error: 'ログインが必要です。設定画面でCrowdWorksにログインしてください' });
            return;
          }
          cleanTitle = cleanTitle.replace(/\s*[|｜].*$/, '');
          cleanTitle = cleanTitle.replace(/\s*の仕事$/, '');
          resolve({ success: true, title: cleanTitle });
        } else {
          resolve({ success: false, error: 'タイトルを取得できませんでした' });
        }
      } catch (e) {
        if (!resolved) {
          resolved = true;
          fetchWin.close();
          resolve({ success: false, error: e.message });
        }
      }
    });

    setTimeout(() => {
      if (!resolved) {
        resolved = true;
        fetchWin.close();
        resolve({ success: false, error: 'タイムアウト: ページの読み込みに時間がかかりすぎました' });
      }
    }, 15000);

    fetchWin.loadURL(url);
  });
}

// URLから案件名を取得
ipcMain.handle('fetch-title-from-url', async (event, { url }) => {
  try {
    return await fetchPageTitle(url);
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// データ更新
ipcMain.handle('update-data', async (event, { category, filename, data }) => {
  const basePath = getDataPath();
  const result = await fileManager.updateData(basePath, category, filename, data);
  if (result.success) {
    await dashboardUpdater.update(basePath);
  }
  return result;
});

// データ削除
ipcMain.handle('delete-data', async (event, { category, filename }) => {
  const basePath = getDataPath();
  const result = await fileManager.deleteData(basePath, category, filename);
  if (result.success) {
    await dashboardUpdater.update(basePath);
  }
  return result;
});
