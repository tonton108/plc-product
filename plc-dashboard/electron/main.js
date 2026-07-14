// PLC監視システム 中央サーバー管理トレイアプリ（Phase 4 Increment 2）
//
// 役割: 中央サーバーPCの常駐トレイから、Phase 4のネイティブWindowsサービス
//   （Memurai / plc-ingest / plc-viewer）の状態監視・起動/停止/再起動と、
//   ダッシュボード(viewer:5001)の表示を行う。
//
// 旧実装はDocker Compose（backend/db/frontend）を管理していたが、Phase 4で
// 本番はネイティブサービス常駐に移行したため全面刷新した。ウィンドウは
// viewerが同一オリジンで配信するSPA(http://127.0.0.1:5001)を直接ロードする
// （レンダラーの再バンドルは不要）。
const { app, BrowserWindow, Tray, Menu, ipcMain, Notification, shell, nativeImage } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs');
const os = require('os');

let mainWindow = null;
let tray = null;

// 管理対象サービス（依存順）。postgresは別管理のため状態表示のみ。
const SERVICES = [
  { key: 'postgres', name: 'postgresql-x64-18', label: 'PostgreSQL', manageable: false },
  { key: 'memurai', name: 'Memurai', label: 'Redis(Memurai)', manageable: true },
  { key: 'ingest', name: 'plc-ingest', label: 'ingest(5000)', manageable: true },
  { key: 'viewer', name: 'plc-viewer', label: 'viewer(5001)', manageable: true },
];
// start/stop対象（依存順。停止は逆順）。postgresは触らない。
const CONTROLLABLE = ['Memurai', 'plc-ingest', 'plc-viewer'];

// 現在の状態（key -> 'Running'|'Stopped'|'不明'）
const status = Object.fromEntries(SERVICES.map(s => [s.key, '不明']));

const CONFIG_PATH = path.join(app.getPath('userData'), 'config.json');
const DEFAULT_CONFIG = {
  viewerUrl: 'http://127.0.0.1:5001',
  logDir: 'C:\\ProgramData\\plc-monitor\\logs',
  minimizeToTray: true,
  startMinimized: false,
};

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8')) };
    }
  } catch (error) {
    console.error('設定ファイル読み込みエラー:', error);
  }
  return { ...DEFAULT_CONFIG };
}

function saveConfig(config) {
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf-8');
    return true;
  } catch (error) {
    console.error('設定ファイル保存エラー:', error);
    return false;
  }
}

// ── サービス状態取得 ────────────────────────────────────────────────
// Get-Service の Status enum は英語固定（Running/Stopped等）で、日本語Windowsでも
// 解析が安定する（sc query の STATE ラベルはロケール依存で崩れるため使わない）。
function queryServiceStatus(name) {
  return new Promise((resolve) => {
    const cmd = `powershell -NoProfile -Command "try { (Get-Service -Name '${name}' -ErrorAction Stop).Status } catch { 'NotFound' }"`;
    exec(cmd, { windowsHide: true }, (error, stdout) => {
      if (error) return resolve('不明');
      resolve((stdout || '').trim() || '不明');
    });
  });
}

async function refreshStatus() {
  await Promise.all(SERVICES.map(async (s) => {
    status[s.key] = await queryServiceStatus(s.name);
  }));
  updateTrayMenu();
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('service:status-update', status);
  }
}

// ── サービス制御（管理者昇格が必要）────────────────────────────────
// start/stop/restart は SCM への書込み権限が要る。トレイアプリは通常非管理者で
// 動くため、その操作だけ UAC 昇格した PowerShell を単発起動して実行する。
function controlServices(action) {
  return new Promise((resolve, reject) => {
    let inner;
    if (action === 'start') {
      inner = CONTROLLABLE.map(n => `Start-Service '${n}'`).join('; ');
    } else if (action === 'stop') {
      inner = [...CONTROLLABLE].reverse().map(n => `Stop-Service '${n}' -Force`).join('; ');
    } else if (action === 'restart') {
      inner = CONTROLLABLE.map(n => `Restart-Service '${n}' -Force`).join('; ');
    } else {
      return reject(new Error(`不明なaction: ${action}`));
    }
    // -Verb RunAs で昇格。内側コマンドはBase64で渡し、クォート地獄とロケール差を避ける。
    const encoded = Buffer.from(inner, 'utf16le').toString('base64');
    const outer = `powershell -NoProfile -Command "Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList '-NoProfile','-EncodedCommand','${encoded}'"`;
    showNotification('サービス操作', `${action} を実行します（UACの許可が必要）`);
    exec(outer, { windowsHide: true }, (error) => {
      if (error) {
        showNotification('エラー', `サービス${action}に失敗（UAC拒否または権限不足）`);
        reject(error);
        return;
      }
      setTimeout(refreshStatus, 1500);
      resolve();
    });
  });
}

// アイコン解決: 指定ファイルが未配置/空(0バイト)なら埋め込みPNGにフォールバックする。
// placeholderのassets/*.pngが0バイトのまま空nativeImageをTrayに渡すとWindowsで例外になるため。
const FALLBACK_ICON_DATA_URL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAO0lEQVR4nGNgoAVQOhr3HxumSDNRhhDSjNcQYjVjNYRUzRiGjBpABQMojkaqJCRiDcGrmZAhRGkmFQAAbvNhgFLqI94AAAAASUVORK5CYII=';

function resolveIcon(fileName, fallbackFileName) {
  for (const name of [fileName, fallbackFileName].filter(Boolean)) {
    const p = path.join(__dirname, 'assets', name);
    if (fs.existsSync(p)) {
      const img = nativeImage.createFromPath(p);
      if (!img.isEmpty()) return img;
    }
  }
  return nativeImage.createFromDataURL(FALLBACK_ICON_DATA_URL);
}

// ── ウィンドウ ──────────────────────────────────────────────────────
function createWindow() {
  const config = loadConfig();
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    icon: resolveIcon('icon.png', 'tray-icon.png'),
    title: 'PLC監視 中央サーバー',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    show: !config.startMinimized,
  });

  loadViewer();

  mainWindow.on('close', (event) => {
    const cfg = loadConfig();
    if (cfg.minimizeToTray && !app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      if (!mainWindow.hasBeenMinimized) {
        showNotification('PLC監視', 'トレイで実行中です。アイコンから操作できます。');
        mainWindow.hasBeenMinimized = true;
      }
    }
  });
  mainWindow.on('closed', () => { mainWindow = null; });
}

// viewerのSPAをロード。未起動で接続不可のときは案内を表示して再試行できるようにする。
function loadViewer() {
  const { viewerUrl } = loadConfig();
  mainWindow.loadURL(viewerUrl).catch(() => {});
  mainWindow.webContents.on('did-fail-load', () => {
    const html = `<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
      <style>body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;
      display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0}
      button{margin-top:20px;padding:10px 24px;font-size:15px;background:#0891b2;color:#fff;border:none;border-radius:6px;cursor:pointer}
      p{color:#94a3b8}</style></head><body>
      <h2>ダッシュボード(viewer)に接続できません</h2>
      <p>${viewerUrl} が応答していません。plc-viewer サービスの状態を確認してください。</p>
      <button onclick="location.reload()">再試行</button>
      </body></html>`;
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  });
}

// ── トレイ ──────────────────────────────────────────────────────────
function createTray() {
  tray = new Tray(resolveIcon('tray-icon.png', 'icon.png'));
  updateTrayMenu();
  tray.setToolTip('PLC監視 中央サーバー管理');
  tray.on('double-click', () => showMainWindow());
}

// 状態を絵文字で可視化（Electronトレイのラベルアイコンは扱いにくいため文字で表現）
function statusMark(v) {
  if (v === 'Running') return '🟢';
  if (v === 'Stopped') return '🔴';
  if (v === 'NotFound') return '⚫';
  return '⚪';
}

function updateTrayMenu() {
  if (!tray) return;
  const statusItems = SERVICES.map(s => ({
    label: `${statusMark(status[s.key])} ${s.label}: ${status[s.key]}`,
    enabled: false,
  }));
  const allRunning = CONTROLLABLE.every(n => {
    const s = SERVICES.find(x => x.name === n);
    return s && status[s.key] === 'Running';
  });

  const menu = Menu.buildFromTemplate([
    { label: 'PLC監視 中央サーバー', enabled: false },
    { type: 'separator' },
    ...statusItems,
    { type: 'separator' },
    { label: 'サービスを起動', click: () => controlServices('start').catch(() => {}), enabled: !allRunning },
    { label: 'サービスを停止', click: () => controlServices('stop').catch(() => {}) },
    { label: 'サービスを再起動', click: () => controlServices('restart').catch(() => {}) },
    { label: '状態を更新', click: () => refreshStatus() },
    { type: 'separator' },
    { label: 'ダッシュボードを表示', click: () => showMainWindow() },
    { label: 'ブラウザで開く', click: () => shell.openExternal(loadConfig().viewerUrl) },
    { label: 'ログフォルダを開く', click: () => shell.openPath(loadConfig().logDir) },
    { type: 'separator' },
    { label: '初回サーバーセットアップ（管理者）', click: () => runServerSetup() },
    { label: 'セットアップフォルダを開く', click: () => shell.openPath(getServerDir()) },
    { type: 'separator' },
    { label: '終了', click: () => { app.isQuitting = true; app.quit(); } },
  ]);
  tray.setContextMenu(menu);
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow();
    return;
  }
  if (mainWindow.isVisible()) {
    mainWindow.focus();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
}

function showNotification(title, body) {
  if (Notification.isSupported()) new Notification({ title, body }).show();
}

// ── 同梱サーバー資産のパス解決 ──────────────────────────────────────
// パッケージ時: resources/server/ 配下（extraResourcesで setup-all.ps1 が期待する
//   相対レイアウト = <server>/{backend,.output/public,scripts/windows-service} を保持）。
// 開発時: リポジトリ（plc-dashboard/）配下をそのまま使う。
function getServerDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'server', 'scripts', 'windows-service')
    : path.join(__dirname, '..', 'scripts', 'windows-service');
}

function setupScriptPath() {
  return path.join(getServerDir(), 'setup-all.ps1');
}

// 初回サーバーセットアップ: setup-all.ps1 を管理者権限で対話起動する。
// -PgSuperPassword が必須パラメータのため、可視ウィンドウ＋-NoExitで起動して
// プロンプトと結果（生成されたadminパスワード・APIキー）を残す。
function runServerSetup() {
  const script = setupScriptPath();
  if (!fs.existsSync(script)) {
    showNotification('サーバーセットアップ', 'setup-all.ps1 が見つかりません:\n' + script);
    return;
  }
  // 内側コマンドはBase64(EncodedCommand)で渡し、クォート地獄とロケール差を回避（controlServices同様）。
  const inner = `Set-Location -LiteralPath '${getServerDir()}'; & '${script}'`;
  const encoded = Buffer.from(inner, 'utf16le').toString('base64');
  const outer = `powershell -NoProfile -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand','${encoded}'"`;
  showNotification('サーバーセットアップ', '管理者PowerShellを起動します（UAC許可が必要）。postgresパスワードの入力を求められます。');
  exec(outer, { windowsHide: true }, (err) => {
    if (err) showNotification('サーバーセットアップ', '起動に失敗しました（UAC拒否など）:\n' + err.message);
  });
}

// ── ログ取得（C:\ProgramData\plc-monitor\logs 配下の各サービスログ）─────
function readServiceLog(serviceKey) {
  return new Promise((resolve) => {
    const { logDir } = loadConfig();
    // Shawlは <service>.log / <service>.err などに出力する想定。存在する最新を末尾100行返す。
    let dir;
    try { dir = fs.readdirSync(logDir); } catch { return resolve('(ログフォルダを読めません: ' + logDir + ')'); }
    const svc = SERVICES.find(s => s.key === serviceKey);
    const target = svc ? svc.name : serviceKey;
    const files = dir.filter(f => f.toLowerCase().includes(target.toLowerCase()));
    if (files.length === 0) return resolve('(該当ログなし: ' + target + ')');
    try {
      const contents = files.map(f => {
        const p = path.join(logDir, f);
        const text = fs.readFileSync(p, 'utf-8');
        const tail = text.split(/\r?\n/).slice(-100).join('\n');
        return `===== ${f} =====\n${tail}`;
      });
      resolve(contents.join('\n\n'));
    } catch (e) {
      resolve('(ログ読取エラー: ' + e.message + ')');
    }
  });
}

// ── IPC ─────────────────────────────────────────────────────────────
function setupIPCHandlers() {
  ipcMain.handle('service:status', async () => status);
  ipcMain.handle('service:start', async () => controlServices('start'));
  ipcMain.handle('service:stop', async () => controlServices('stop'));
  ipcMain.handle('service:restart', async () => controlServices('restart'));
  ipcMain.handle('service:refresh', async () => { await refreshStatus(); return status; });
  ipcMain.handle('logs:get', async (_e, serviceKey) => readServiceLog(serviceKey));
  ipcMain.handle('system:info', async () => ({
    platform: os.platform(), arch: os.arch(), hostname: os.hostname(),
    cpus: os.cpus().length, totalMemory: os.totalmem(), freeMemory: os.freemem(),
  }));
  ipcMain.handle('config:get', async () => loadConfig());
  ipcMain.handle('config:save', async (_e, config) => saveConfig(config));
  ipcMain.on('window:minimize-to-tray', () => { if (mainWindow) mainWindow.hide(); });
  ipcMain.on('window:show', () => showMainWindow());
  ipcMain.on('app:quit', () => { app.isQuitting = true; app.quit(); });
  ipcMain.on('notification:show', (_e, { title, body }) => showNotification(title, body));
}

// ── 起動 ────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  createWindow();
  createTray();
  setupIPCHandlers();
  await refreshStatus();
  // 10秒ごとに状態ポーリング（読み取りのみ・非管理者で可）
  setInterval(refreshStatus, 10000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
app.on('before-quit', () => { app.isQuitting = true; });
