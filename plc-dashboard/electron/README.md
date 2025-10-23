# PLC Dashboard - Electronアプリ

中央サーバーPC用のデスクトップ管理アプリケーションです。

## 機能

- ✅ Docker Composeサービスの起動/停止/再起動
- ✅ システムトレイ常駐
- ✅ サーバー状態のリアルタイム監視
- ✅ デスクトップ通知
- ✅ Nuxt.jsダッシュボードの埋め込み表示

## 開発環境セットアップ

### 1. 依存関係のインストール

```bash
cd electron
npm install
```

### 2. Nuxt.jsの静的ファイル生成

```bash
cd ..  # plc-dashboardディレクトリに戻る
npm run generate
```

生成されたファイルが`electron/renderer/`にコピーされます。

### 3. 開発モードで起動

```bash
cd electron
npm start
```

開発モード時は、Nuxt.jsの開発サーバー（http://localhost:3000）に接続します。

## ビルド

### macOS

```bash
npm run build:mac
```

### Windows

```bash
npm run build:win
```

### Linux

```bash
npm run build:linux
```

ビルドされたアプリは`electron/dist/`に出力されます。

## アイコンの配置

以下のアイコンファイルを`electron/assets/`に配置してください：

- `icon.png` - アプリケーションアイコン（512x512px推奨）
- `tray-icon.png` - システムトレイアイコン（16x16px or 32x32px推奨）
- `icon.icns` - macOS用アイコン
- `icon.ico` - Windows用アイコン

## 設定

アプリケーション設定は以下に保存されます：

- **macOS**: `~/Library/Application Support/plc-dashboard-electron/config.json`
- **Windows**: `%APPDATA%\plc-dashboard-electron\config.json`
- **Linux**: `~/.config/plc-dashboard-electron/config.json`

### 設定項目

```json
{
  "dockerComposePath": "/path/to/plc-product",
  "autoStartDocker": true,
  "minimizeToTray": true,
  "startMinimized": false
}
```

## システム要件

- Node.js 18以上
- Docker & Docker Compose
- macOS 10.13+ / Windows 10+ / Linux (Ubuntu 18.04+推奨)

## トラブルシューティング

### Docker起動エラー

- Docker Desktopが起動しているか確認
- `docker compose`コマンドが利用可能か確認

### ウィンドウが表示されない

- システムトレイのアイコンをダブルクリック
- または右クリック → 「ダッシュボードを表示」

### アイコンが表示されない

- `electron/assets/`にアイコンファイルが配置されているか確認
- デフォルトでは空のアイコンが表示されます
