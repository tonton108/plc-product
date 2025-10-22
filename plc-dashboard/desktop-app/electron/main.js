import { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } from 'electron'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import axios from 'axios'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// 開発環境とプロダクション環境の判定
const isDev = process.env.NODE_ENV !== 'production'
const VITE_DEV_SERVER_URL = 'http://localhost:5173'

let mainWindow = null
let tray = null
let flaskProcess = null
const FLASK_PORT = 5000

// Flask backendのパス（プロダクション時はapp.getAppPath()を使用）
const getFlaskPath = () => {
  if (isDev) {
    // 開発時: desktop-app/../backend
    return path.join(__dirname, '..', '..', 'backend')
  } else {
    // プロダクション時: resources/backend
    return path.join(process.resourcesPath, 'backend')
  }
}

/**
 * Flask backendが起動しているかチェック
 */
async function checkFlaskRunning() {
  try {
    const response = await axios.get(`http://localhost:${FLASK_PORT}/api/equipment`, { timeout: 2000 })
    return response.status === 200
  } catch (error) {
    return false
  }
}

/**
 * Flask backendを起動
 */
function startFlaskBackend() {
  return new Promise(async (resolve, reject) => {
    // 既に起動している場合はスキップ
    const isRunning = await checkFlaskRunning()
    if (isRunning) {
      console.log('[Flask] Flask backendは既に起動しています')
      resolve()
      return
    }

    console.log('[Flask] Flask backendを起動中...')
    const flaskPath = getFlaskPath()
    const managePath = path.join(flaskPath, 'manage.py')

    // Windows用のpythonコマンド（.venv/Scripts/python.exe or python）
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

    flaskProcess = spawn(pythonCmd, [managePath, 'run', '--host=0.0.0.0', '--port=' + FLASK_PORT], {
      cwd: flaskPath,
      env: { ...process.env, FLASK_ENV: 'production' },
      shell: true
    })

    flaskProcess.stdout.on('data', (data) => {
      console.log(`[Flask] ${data.toString()}`)
    })

    flaskProcess.stderr.on('data', (data) => {
      console.error(`[Flask] ${data.toString()}`)
    })

    flaskProcess.on('error', (err) => {
      console.error('[Flask] Flask起動エラー:', err)
      reject(err)
    })

    flaskProcess.on('exit', (code) => {
      console.log(`[Flask] Flask終了 (code: ${code})`)
      if (code !== 0 && code !== null) {
        console.error('[Flask] Flask異常終了')
      }
    })

    // Flask起動待機（最大30秒）
    let retries = 30
    const checkInterval = setInterval(async () => {
      const running = await checkFlaskRunning()
      if (running) {
        clearInterval(checkInterval)
        console.log('[Flask] Flask backend起動完了')
        resolve()
      } else if (--retries <= 0) {
        clearInterval(checkInterval)
        console.error('[Flask] Flask起動タイムアウト')
        reject(new Error('Flask起動タイムアウト'))
      }
    }, 1000)
  })
}

/**
 * Flask backendを停止
 */
function stopFlaskBackend() {
  if (flaskProcess) {
    console.log('[Flask] Flask backendを停止中...')
    flaskProcess.kill()
    flaskProcess = null
  }
}

/**
 * メインウィンドウを作成
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '..', 'public', 'icon.png'),
    title: 'PLC Monitoring System'
  })

  // 開発時はViteサーバーから、プロダクション時はビルド済みファイルをロード
  if (isDev) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  // ウィンドウを閉じる時（×ボタン）→ 最小化してタスクトレイに隠す
  mainWindow.on('close', (event) => {
    if (!app.isQuiting) {
      event.preventDefault()
      mainWindow.hide()
      return false
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

/**
 * タスクトレイを作成
 */
function createTray() {
  // アイコン画像（開発時とプロダクション時で異なるパス）
  const iconPath = isDev
    ? path.join(__dirname, '..', 'public', 'icon.png')
    : path.join(process.resourcesPath, 'icon.png')

  const icon = nativeImage.createFromPath(iconPath)
  tray = new Tray(icon.resize({ width: 16, height: 16 }))

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'ダッシュボードを開く',
      click: () => {
        if (mainWindow) {
          mainWindow.show()
          mainWindow.focus()
        } else {
          createWindow()
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Flask サーバー状態',
      submenu: [
        {
          label: 'サーバー稼働中',
          enabled: false
        },
        {
          label: 'ポート: ' + FLASK_PORT,
          enabled: false
        }
      ]
    },
    { type: 'separator' },
    {
      label: '完全終了',
      click: () => {
        app.isQuiting = true
        stopFlaskBackend()
        app.quit()
      }
    }
  ])

  tray.setToolTip('PLC Monitoring System')
  tray.setContextMenu(contextMenu)

  // トレイアイコンダブルクリックでウィンドウ表示
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

/**
 * アプリケーション起動時
 */
app.whenReady().then(async () => {
  console.log('[App] アプリケーション起動中...')

  try {
    // Flask backendを起動
    await startFlaskBackend()

    // メインウィンドウを作成
    createWindow()

    // タスクトレイを作成
    createTray()

    console.log('[App] アプリケーション起動完了')
  } catch (error) {
    console.error('[App] 起動エラー:', error)
    app.quit()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

/**
 * すべてのウィンドウが閉じられた時
 */
app.on('window-all-closed', () => {
  // macOS以外はアプリを終了しない（バックグラウンドで継続）
  if (process.platform !== 'darwin') {
    // Flask backendはバックグラウンドで継続
    console.log('[App] ウィンドウは閉じられましたが、Flask backendはバックグラウンドで継続中')
  }
})

/**
 * アプリケーション終了前
 */
app.on('before-quit', () => {
  app.isQuiting = true
})

/**
 * アプリケーション終了時
 */
app.on('will-quit', () => {
  stopFlaskBackend()
})

/**
 * IPC通信: Flask状態チェック
 */
ipcMain.handle('check-flask-status', async () => {
  const isRunning = await checkFlaskRunning()
  return {
    running: isRunning,
    port: FLASK_PORT,
    url: `http://localhost:${FLASK_PORT}`
  }
})
