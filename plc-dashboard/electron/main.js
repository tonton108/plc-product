const { app, BrowserWindow, Tray, Menu, ipcMain, Notification, dialog } = require('electron');
const path = require('path');
const { exec, spawn } = require('child_process');
const fs = require('fs');
const os = require('os');

// アプリケーション状態
let mainWindow = null;
let tray = null;
let dockerProcess = null;
let dockerStatus = {
  backend: 'stopped',
  db: 'stopped',
  frontend: 'stopped'
};

// プロジェクトルートディレクトリ（electron/の親ディレクトリ）
const PROJECT_ROOT = path.join(__dirname, '..');

// 設定ファイルパス
const CONFIG_PATH = path.join(app.getPath('userData'), 'config.json');

// デフォルト設定
const DEFAULT_CONFIG = {
  dockerComposePath: PROJECT_ROOT,
  autoStartDocker: true,
  minimizeToTray: true,
  startMinimized: false
};

/**
 * 設定ファイルの読み込み
 */
function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    }
  } catch (error) {
    console.error('設定ファイル読み込みエラー:', error);
  }
  return DEFAULT_CONFIG;
}

/**
 * 設定ファイルの保存
 */
function saveConfig(config) {
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf-8');
    return true;
  } catch (error) {
    console.error('設定ファイル保存エラー:', error);
    return false;
  }
}

/**
 * メインウィンドウの作成
 */
function createWindow() {
  const config = loadConfig();

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    show: !config.startMinimized
  });

  // Nuxt.jsの生成物を読み込み
  const rendererPath = path.join(__dirname, 'renderer', 'index.html');

  if (fs.existsSync(rendererPath)) {
    mainWindow.loadFile(rendererPath);
  } else {
    // 開発モード: Nuxt.js開発サーバーに接続
    mainWindow.loadURL('http://localhost:3000');
  }

  // 開発ツールを開く（開発時のみ）
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  // ウィンドウを閉じる動作をカスタマイズ
  mainWindow.on('close', (event) => {
    if (config.minimizeToTray && !app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();

      // 初回のみ通知を表示
      if (!mainWindow.hasBeenMinimized) {
        showNotification(
          'PLC Dashboard',
          'アプリはバックグラウンドで実行中です。システムトレイから操作できます。'
        );
        mainWindow.hasBeenMinimized = true;
      }
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * システムトレイの作成
 */
function createTray() {
  // トレイアイコンのパス（後で適切なアイコンに変更）
  const iconPath = path.join(__dirname, 'assets', 'tray-icon.png');
  const fallbackIcon = path.join(__dirname, 'assets', 'icon.png');

  const trayIconPath = fs.existsSync(iconPath) ? iconPath : fallbackIcon;

  tray = new Tray(trayIconPath);

  updateTrayMenu();

  tray.setToolTip('PLC Dashboard - 中央サーバー管理');

  // トレイアイコンをダブルクリックでウィンドウ表示
  tray.on('double-click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

/**
 * トレイメニューの更新
 */
function updateTrayMenu() {
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'PLC Dashboard',
      type: 'normal',
      enabled: false
    },
    { type: 'separator' },
    {
      label: `Backend: ${dockerStatus.backend}`,
      icon: getStatusIcon(dockerStatus.backend),
      enabled: false
    },
    {
      label: `Database: ${dockerStatus.db}`,
      icon: getStatusIcon(dockerStatus.db),
      enabled: false
    },
    { type: 'separator' },
    {
      label: 'サーバーを起動',
      click: () => startDockerServices(),
      enabled: dockerStatus.backend !== 'running'
    },
    {
      label: 'サーバーを停止',
      click: () => stopDockerServices(),
      enabled: dockerStatus.backend === 'running'
    },
    {
      label: 'サーバーを再起動',
      click: () => restartDockerServices()
    },
    { type: 'separator' },
    {
      label: 'ダッシュボードを表示',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: 'ログを表示',
      click: () => {
        // TODO: ログウィンドウを実装
        showNotification('未実装', 'ログ表示機能は近日実装予定です');
      }
    },
    { type: 'separator' },
    {
      label: '終了',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
}

/**
 * ステータスアイコンの取得
 */
function getStatusIcon(status) {
  // Electronのネイティブアイコンは使用不可のため、空文字列を返す
  // 代わりに、ラベルの色分けで表現
  return null;
}

/**
 * Docker Composeサービスの起動
 */
async function startDockerServices() {
  return new Promise((resolve, reject) => {
    const config = loadConfig();
    const cwd = config.dockerComposePath;

    showNotification('Docker起動中', 'サーバーを起動しています...');

    exec('docker compose up -d db backend', { cwd }, (error, stdout, stderr) => {
      if (error) {
        console.error('Docker起動エラー:', error);
        showNotification('エラー', `サーバーの起動に失敗しました: ${error.message}`);
        reject(error);
        return;
      }

      console.log('Docker起動成功:', stdout);
      showNotification('起動完了', 'サーバーが起動しました');

      // ステータスを更新
      setTimeout(() => {
        updateDockerStatus();
      }, 2000);

      resolve(stdout);
    });
  });
}

/**
 * Docker Composeサービスの停止
 */
async function stopDockerServices() {
  return new Promise((resolve, reject) => {
    const config = loadConfig();
    const cwd = config.dockerComposePath;

    showNotification('Docker停止中', 'サーバーを停止しています...');

    exec('docker compose down', { cwd }, (error, stdout, stderr) => {
      if (error) {
        console.error('Docker停止エラー:', error);
        showNotification('エラー', `サーバーの停止に失敗しました: ${error.message}`);
        reject(error);
        return;
      }

      console.log('Docker停止成功:', stdout);
      showNotification('停止完了', 'サーバーが停止しました');

      // ステータスを更新
      dockerStatus.backend = 'stopped';
      dockerStatus.db = 'stopped';
      updateTrayMenu();

      resolve(stdout);
    });
  });
}

/**
 * Docker Composeサービスの再起動
 */
async function restartDockerServices() {
  await stopDockerServices();
  setTimeout(async () => {
    await startDockerServices();
  }, 1000);
}

/**
 * Dockerサービスのステータス確認
 */
function updateDockerStatus() {
  const config = loadConfig();
  const cwd = config.dockerComposePath;

  exec('docker compose ps --format json', { cwd }, (error, stdout, stderr) => {
    if (error) {
      console.error('Dockerステータス取得エラー:', error);
      return;
    }

    try {
      // docker compose ps の出力をパース
      const lines = stdout.trim().split('\n').filter(line => line);
      const containers = lines.map(line => JSON.parse(line));

      // ステータスを更新
      dockerStatus.backend = 'stopped';
      dockerStatus.db = 'stopped';

      containers.forEach(container => {
        const isRunning = container.State === 'running';
        if (container.Service === 'backend') {
          dockerStatus.backend = isRunning ? 'running' : 'stopped';
        } else if (container.Service === 'db') {
          dockerStatus.db = isRunning ? 'running' : 'stopped';
        }
      });

      updateTrayMenu();

      // メインウィンドウにステータスを送信
      if (mainWindow) {
        mainWindow.webContents.send('docker:status-update', dockerStatus);
      }
    } catch (parseError) {
      console.error('Dockerステータスパースエラー:', parseError);
    }
  });
}

/**
 * 通知の表示
 */
function showNotification(title, body) {
  if (Notification.isSupported()) {
    new Notification({ title, body }).show();
  }
}

/**
 * IPCハンドラーの登録
 */
function setupIPCHandlers() {
  // Docker管理
  ipcMain.handle('docker:start', async () => {
    return await startDockerServices();
  });

  ipcMain.handle('docker:stop', async () => {
    return await stopDockerServices();
  });

  ipcMain.handle('docker:restart', async () => {
    return await restartDockerServices();
  });

  ipcMain.handle('docker:status', async () => {
    return dockerStatus;
  });

  // システム情報
  ipcMain.handle('system:info', async () => {
    return {
      platform: os.platform(),
      arch: os.arch(),
      hostname: os.hostname(),
      cpus: os.cpus().length,
      totalMemory: os.totalmem(),
      freeMemory: os.freemem()
    };
  });

  // 設定管理
  ipcMain.handle('config:get', async () => {
    return loadConfig();
  });

  ipcMain.handle('config:save', async (event, config) => {
    return saveConfig(config);
  });

  // ウィンドウ制御
  ipcMain.on('window:minimize-to-tray', () => {
    if (mainWindow) {
      mainWindow.hide();
    }
  });

  ipcMain.on('window:show', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  ipcMain.on('app:quit', () => {
    app.isQuitting = true;
    app.quit();
  });

  // 通知
  ipcMain.on('notification:show', (event, { title, body }) => {
    showNotification(title, body);
  });

  // ログ取得
  ipcMain.handle('logs:get', async (event, service) => {
    return new Promise((resolve, reject) => {
      const config = loadConfig();
      const cwd = config.dockerComposePath;

      exec(`docker compose logs --tail=100 ${service}`, { cwd }, (error, stdout, stderr) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(stdout);
      });
    });
  });
}

/**
 * アプリケーションの初期化
 */
app.whenReady().then(async () => {
  createWindow();
  createTray();
  setupIPCHandlers();

  // 初回のDockerステータス確認
  updateDockerStatus();

  // 定期的にDockerステータスを確認（30秒ごと）
  setInterval(() => {
    updateDockerStatus();
  }, 30000);

  // 設定に基づいて自動起動
  const config = loadConfig();
  if (config.autoStartDocker) {
    setTimeout(async () => {
      await startDockerServices();
    }, 2000);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // macOS以外ではウィンドウが全て閉じられたら終了
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
});
