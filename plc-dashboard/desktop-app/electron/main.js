const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const axios = require('axios')
const express = require('express')
const fs = require('fs')
const net = require('net')
const { promisify } = require('util')

const execFile = promisify(spawn)

// 開発環境とプロダクション環境の判定（app.whenReady()内で初期化）
let isDev = true  // デフォルト値
const NUXT_UI_PORT = 3000
const NUXT_UI_URL = `http://localhost:${NUXT_UI_PORT}`  // Nuxt UIのURL

let mainWindow = null
let tray = null
let flaskProcess = null
let postgresProcess = null
let nuxtServer = null
const FLASK_PORT = 5000
let POSTGRES_PORT = 5432

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

// PostgreSQL Portableのパス
const getPostgresPath = () => {
  const backendPath = getFlaskPath()
  return path.join(backendPath, 'postgres-portable')
}

/**
 * 利用可能なポートを自動検出（ポート衝突回避）
 */
function findAvailablePort(startPort = 5432) {
  return new Promise((resolve, reject) => {
    const server = net.createServer()

    server.listen(startPort, () => {
      const port = server.address().port
      server.close(() => {
        console.log(`[PostgreSQL] ポート ${port} が利用可能です`)
        resolve(port)
      })
    })

    server.on('error', () => {
      // ポートが使用中なら次のポートを試す
      console.log(`[PostgreSQL] ポート ${startPort} は使用中、次のポートを試します`)
      resolve(findAvailablePort(startPort + 1))
    })
  })
}

/**
 * Flask backendが起動しているかチェック
 */
async function checkFlaskRunning() {
  try {
    // IPv6の問題を避けるため、localhostではなく127.0.0.1を使用
    console.log(`[Flask Health] ヘルスチェック開始: http://127.0.0.1:${FLASK_PORT}/api/health`)
    const response = await axios.get(`http://127.0.0.1:${FLASK_PORT}/api/health`, { timeout: 5000 })
    console.log(`[Flask Health] レスポンス: status=${response.status}, data=`, response.data)
    const isHealthy = response.status === 200 && response.data.status === 'healthy'
    console.log(`[Flask Health] 判定: ${isHealthy}`)
    return isHealthy
  } catch (error) {
    console.error(`[Flask Health] エラー: ${error.message}`)
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

    // Windows用のpythonコマンド（フルパスで指定）
    const pythonCmd = process.platform === 'win32'
      ? 'C:\\Users\\ton_1\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
      : 'python3'

    console.log(`[Flask] Pythonコマンド: ${pythonCmd}`)
    console.log(`[Flask] manage.pyパス: ${managePath}`)

    let flaskReady = false

    // flask runではなくpython manage.pyを直接実行（リローダーをバイパス）
    flaskProcess = spawn(pythonCmd, [managePath], {
      cwd: flaskPath,
      env: {
        ...process.env,
        FLASK_ENV: 'development',  // デスクトップアプリはセキュリティチェック不要（単一ユーザー向け）
        FLASK_DEBUG: '0',  // デバッグモードを無効化（自動リローダーも無効化）
        PORT: FLASK_PORT.toString(),  // manage.pyがPORTを読み取る
        DATABASE_PORT: POSTGRES_PORT.toString(),
        PYTHONIOENCODING: 'utf-8',  // Python出力をUTF-8に設定
        PYTHONUTF8: '1'  // Python 3.7以降でUTF-8モードを有効化
      },
      shell: true
    })

    flaskProcess.stdout.on('data', (data) => {
      console.log(`[Flask] ${data.toString()}`)
    })

    flaskProcess.stderr.on('data', (data) => {
      const output = data.toString()
      console.error(`[Flask] ${output}`)

      // "Running on"メッセージを検知したらFlask起動完了とみなす（ANSIカラーコードを考慮）
      if (output.includes('Running on') && output.includes(':' + FLASK_PORT)) {
        if (!flaskReady) {
          flaskReady = true
          console.log('[Flask] Flaskサーバーが起動しました、ヘルスチェックを開始します')
        }
      }
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

    // Flask起動待機（最大60秒）
    let retries = 60
    const checkInterval = setInterval(async () => {
      // flaskReadyフラグがtrueの場合のみヘルスチェックを実行
      if (flaskReady) {
        const running = await checkFlaskRunning()
        if (running) {
          clearInterval(checkInterval)
          console.log('[Flask] Flask backend起動完了（ヘルスチェック成功）')
          resolve()
        } else if (--retries <= 0) {
          clearInterval(checkInterval)
          console.error('[Flask] Flask起動タイムアウト')
          reject(new Error('Flask起動タイムアウト'))
        }
      } else if (--retries <= 0) {
        clearInterval(checkInterval)
        console.error('[Flask] Flask起動タイムアウト（Flaskサーバーが起動しませんでした）')
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
 * PostgreSQLデータベースの初期化（初回起動時のみ）
 */
async function initializePostgres() {
  const postgresPath = getPostgresPath()
  const pgDataPath = path.join(postgresPath, 'data')

  // 初回起動チェック（dataディレクトリの有無）
  if (fs.existsSync(pgDataPath)) {
    console.log('[PostgreSQL] データディレクトリが存在します。初期化をスキップします。')
    return
  }

  console.log('[PostgreSQL] 初回起動：データベースを初期化中...')

  const initdbPath = path.join(postgresPath, 'bin', 'initdb.exe')

  // initdbを実行
  return new Promise((resolve, reject) => {
    const initdbProcess = spawn(
      initdbPath,
      [
        '-D', pgDataPath,
        '-U', 'postgres',
        '-E', 'UTF8',
        '--locale=C',
        '--auth=trust'  // 開発用：パスワード不要
      ],
      { cwd: postgresPath }
    )

    initdbProcess.stdout.on('data', (data) => {
      console.log(`[PostgreSQL initdb] ${data.toString()}`)
    })

    initdbProcess.stderr.on('data', (data) => {
      console.log(`[PostgreSQL initdb] ${data.toString()}`)
    })

    initdbProcess.on('error', (err) => {
      console.error('[PostgreSQL] initdb実行エラー:', err)
      reject(err)
    })

    initdbProcess.on('exit', (code) => {
      if (code === 0) {
        console.log('[PostgreSQL] データベース初期化完了')

        // postgresql.confを自動設定
        const configPath = path.join(pgDataPath, 'postgresql.conf')
        const configContent = `
# PLC Monitoring System設定
port = ${POSTGRES_PORT}
max_connections = 50
shared_buffers = 128MB
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
`
        fs.appendFileSync(configPath, configContent)
        console.log('[PostgreSQL] postgresql.conf設定完了')
        resolve()
      } else {
        console.error(`[PostgreSQL] initdb異常終了 (code: ${code})`)
        reject(new Error(`initdb failed with code ${code}`))
      }
    })
  })
}

/**
 * PostgreSQLを起動
 */
function startPostgres() {
  return new Promise(async (resolve, reject) => {
    console.log('[PostgreSQL] PostgreSQLを起動中...')

    const postgresPath = getPostgresPath()
    const pgBinPath = path.join(postgresPath, 'bin', 'postgres.exe')
    const pgDataPath = path.join(postgresPath, 'data')

    // PostgreSQLプロセスを起動
    postgresProcess = spawn(
      pgBinPath,
      ['-D', pgDataPath, '-p', POSTGRES_PORT.toString()],
      {
        cwd: postgresPath,
        env: { ...process.env }
      }
    )

    postgresProcess.stdout.on('data', (data) => {
      const message = data.toString()
      console.log(`[PostgreSQL] ${message}`)

      // 起動完了メッセージを検知
      if (message.includes('database system is ready to accept connections')) {
        console.log('[PostgreSQL] PostgreSQL起動完了')
        resolve()
      }
    })

    postgresProcess.stderr.on('data', (data) => {
      const message = data.toString()
      console.log(`[PostgreSQL] ${message}`)

      // 起動完了メッセージを検知（stderrにも出力される場合がある）
      if (message.includes('database system is ready to accept connections')) {
        console.log('[PostgreSQL] PostgreSQL起動完了')
        resolve()
      }
    })

    postgresProcess.on('error', (err) => {
      console.error('[PostgreSQL] PostgreSQL起動エラー:', err)
      reject(err)
    })

    postgresProcess.on('exit', (code) => {
      console.log(`[PostgreSQL] PostgreSQL終了 (code: ${code})`)
      if (code !== 0 && code !== null) {
        console.error('[PostgreSQL] PostgreSQL異常終了')
      }
    })

    // タイムアウト処理（3秒に短縮 - 通常は1-2秒で起動する）
    setTimeout(() => {
      if (postgresProcess && !postgresProcess.killed) {
        console.log('[PostgreSQL] 起動メッセージが確認できませんでしたが、継続します')
        resolve()
      }
    }, 3000)
  })
}

/**
 * PostgreSQLを停止
 */
function stopPostgres() {
  if (postgresProcess) {
    console.log('[PostgreSQL] PostgreSQLを停止中...')

    const postgresPath = getPostgresPath()
    const pgCtlPath = path.join(postgresPath, 'bin', 'pg_ctl.exe')
    const pgDataPath = path.join(postgresPath, 'data')

    // pg_ctlを使用してグレースフルシャットダウン
    const stopProcess = spawn(
      pgCtlPath,
      ['stop', '-D', pgDataPath, '-m', 'fast'],
      { cwd: postgresPath }
    )

    stopProcess.on('exit', (code) => {
      console.log(`[PostgreSQL] PostgreSQL停止完了 (code: ${code})`)
    })

    postgresProcess = null
  }
}

/**
 * Nuxt UI（静的ファイル）をserve
 */
function startNuxtServer() {
  return new Promise((resolve, reject) => {
    console.log('[Nuxt] Nuxt UIサーバーを起動中...')

    // Nuxt静的ファイルのパス
    const nuxtDistPath = isDev
      ? path.join(__dirname, '..', 'nuxt-dist')  // 開発時
      : path.join(process.resourcesPath, 'nuxt-dist')  // プロダクション時

    // Expressサーバーを作成
    const expressApp = express()

    // 静的ファイルをserve
    expressApp.use(express.static(nuxtDistPath))

    // SPAのため、すべてのルートをindex.htmlにリダイレクト
    expressApp.get('*', (req, res) => {
      res.sendFile(path.join(nuxtDistPath, 'index.html'))
    })

    // サーバー起動
    nuxtServer = expressApp.listen(NUXT_UI_PORT, () => {
      console.log(`[Nuxt] Nuxt UIサーバー起動完了: http://localhost:${NUXT_UI_PORT}`)
      resolve()
    })

    nuxtServer.on('error', (err) => {
      console.error('[Nuxt] Nuxt UIサーバー起動エラー:', err)
      reject(err)
    })
  })
}

/**
 * Nuxt UIサーバーを停止
 */
function stopNuxtServer() {
  if (nuxtServer) {
    console.log('[Nuxt] Nuxt UIサーバーを停止中...')
    nuxtServer.close()
    nuxtServer = null
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

  // 開発時・本番時ともにNuxt UIを表示
  mainWindow.loadURL(NUXT_UI_URL)

  // 開発時のみDevToolsを開く
  if (isDev) {
    mainWindow.webContents.openDevTools()
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

  // 開発環境とプロダクション環境の判定
  isDev = !app.isPackaged

  try {
    // 1. ポート自動選択（PostgreSQL）
    // 既存のPostgreSQLと競合しないように5433から開始
    POSTGRES_PORT = await findAvailablePort(5433)
    console.log(`[App] PostgreSQLポート: ${POSTGRES_PORT}`)

    // 2. PostgreSQLデータベースを初期化（初回のみ）
    await initializePostgres()

    // 3. メインウィンドウを早期に作成（ユーザー体感速度向上）
    createWindow()

    // 4. タスクトレイを作成
    createTray()

    // 5. バックグラウンドでサービスを起動（ウィンドウ表示をブロックしない）
    // PostgreSQLを起動
    startPostgres().catch(err => console.error('[App] PostgreSQL起動エラー:', err))

    // Nuxt UIサーバーを起動（静的ファイル）
    startNuxtServer().catch(err => console.error('[App] Nuxt UI起動エラー:', err))

    // Flask backendを起動（PostgreSQLのポートを環境変数で渡す）
    process.env.DATABASE_PORT = POSTGRES_PORT.toString()
    startFlaskBackend().catch(err => console.error('[App] Flask起動エラー:', err))

    console.log('[App] アプリケーション起動完了（バックエンドサービスはバックグラウンドで起動中）')
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
  stopPostgres()
  stopNuxtServer()
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
