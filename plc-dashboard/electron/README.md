# PLC監視 中央サーバー管理トレイアプリ（Electron）

中央サーバーPC用の常駐トレイアプリです。**Phase 4 でネイティブWindowsサービス構成へ移行**したため、
旧Docker Compose管理から刷新しました（`_docs/deployment/windows-service-setup.md` 参照）。

## 機能

- ✅ ネイティブサービス（Memurai / plc-ingest / plc-viewer）の状態監視（10秒ポーリング）
- ✅ サービスの起動 / 停止 / 再起動（UAC昇格して実行）
- ✅ システムトレイ常駐（状態を 🟢/🔴 で表示）
- ✅ ダッシュボード(viewer:5001)をウィンドウに直接表示（SPA再バンドル不要）
- ✅ 「ブラウザで開く」「ログフォルダを開く」
- ✅ デスクトップ通知

> PostgreSQL(`postgresql-x64-18`) は別管理のため、状態表示のみ（起動/停止対象外）。

## 前提

- `setup-all.ps1` でサービス（Memurai/plc-ingest/plc-viewer）が導入済みであること。
- Node.js 18以上（開発・ビルド時）。

## セットアップと起動

```bash
cd electron
npm install     # 依存インストール（初回のみ）
npm start       # 起動（= electron .）
```

- ウィンドウは既定で `http://127.0.0.1:5001`（viewer）をロードする。viewerが未起動なら
  接続エラー画面と「再試行」ボタンを表示する。
- ウィンドウを閉じてもトレイに常駐する（`minimizeToTray`）。トレイアイコンのダブルクリックで再表示。

## ビルド（配布用パッケージ）

```bash
npm run build:win     # Windows(nsis)。dist/ に出力
# 参考: build:mac / build:linux も定義あり
```

- 生成物: `dist/PLC-Dashboard-Setup-<version>.exe`（NSISインストーラ）。
- インストーラ仕様: `oneClick=false`（インストール先を選択可）・`perMachine=true`（全ユーザー向け・要管理者）・
  デスクトップ/スタートメニューショートカット（名称「PLC監視 中央サーバー」）・インストーラ言語 ja_JP。
- サービス管理に管理者権限が要るため `perMachine` にしている（インストール時にUAC昇格を要求）。

> ウィンドウは viewer(5001) をリモートロードするため、Nuxtの静的生成（`npm run generate`）の
> 同梱は不要。本アプリのパッケージには `main.js` / `preload.js` / `assets/` のみを含む。

### ⚠️ ビルド時の既知の落とし穴（winCodeSign のシンボリックリンク）

electron-builder は Windows ビルド時に `winCodeSign` パッケージを展開するが、その中身に mac 用の
`.dylib` シンボリックリンクが含まれ、**Windows でシンボリックリンクを作るには特権が必要**。
Developer Mode が無効かつ非管理者だと `7za` の展開が
`Cannot create symbolic link : クライアントは要求された特権を保有していません` で失敗する。

回避策（いずれか）:

1. **管理者権限でビルドを1回実行**する（`winCodeSign` がキャッシュされれば以降は非管理者でも可）。
2. Windows の **開発者モードを有効化**する（設定 → プライバシーとセキュリティ → 開発者向け）。

> 署名は行っていないため（社内配布・イントラネット前提）、`winCodeSign` は本来不要だが
> electron-builder が既定で展開する。上記いずれかで一度キャッシュを作れば解消する。

## 設定

`%APPDATA%\plc-dashboard-electron\config.json` に保存される。

```json
{
  "viewerUrl": "http://127.0.0.1:5001",
  "logDir": "C:\\ProgramData\\plc-monitor\\logs",
  "minimizeToTray": true,
  "startMinimized": false
}
```

## アイコン

`electron/assets/` に配置：`icon.png`（アプリ・256px以上の正方形。electron-builderがWindows用`.ico`を自動生成）、
`tray-icon.png`（トレイ・16/32px）。空ファイル/未配置でも起動時に埋め込みPNGへフォールバックする（`resolveIcon()`）。

## トラブルシューティング

- **ウィンドウが接続エラー**: `plc-viewer` サービスが Running か確認（トレイの状態表示 / `Get-Service plc-viewer`）。
- **起動/停止が効かない**: UAC（管理者許可）を拒否していないか確認。SCM操作には昇格が必要。
- **状態が「不明/⚫」**: サービス名が異なる可能性（既定: `postgresql-x64-18`/`Memurai`/`plc-ingest`/`plc-viewer`）。
- **ウィンドウが表示されない**: トレイアイコンをダブルクリック、または右クリック →「ダッシュボードを表示」。
