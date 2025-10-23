# PLC Monitoring Desktop Application

Electron + Vue 3 + Vuetifyで構築されたPLCモニタリングデスクトップアプリケーション

## 機能

- ✅ Flask backendの自動起動・管理
- ✅ タスクトレイ統合（バックグラウンド実行）
- ✅ 設備一覧表示
- ✅ リアルタイムモニタリング（Socket.IO）
- ✅ データグラフ表示（Chart.js）

## 開発環境セットアップ

### 必要な環境

- Node.js 18以上
- Python 3.10以上（Flask backend用）

### インストール

```bash
cd plc-dashboard/desktop-app
npm install
```

### 開発サーバー起動

```bash
# 開発モード（Vite + Electron）
npm run electron:dev
```

**注意:** Flask backendは自動的に起動されますが、事前に以下を確認してください：
- `plc-dashboard/backend`ディレクトリが存在すること
- Flask backendの依存関係がインストールされていること（`pip install -r requirements.txt`）

## ビルド

### Windowsインストーラー作成

```bash
npm run electron:build:win
```

生成されたインストーラーは`dist-electron`ディレクトリに出力されます。

## アーキテクチャ

```
desktop-app/
├── electron/           # Electronメインプロセス
│   ├── main.js        # アプリケーションエントリーポイント、Flask管理
│   └── preload.js     # IPC通信ブリッジ
├── src/               # Vueレンダラープロセス
│   ├── pages/         # ページコンポーネント
│   │   ├── EquipmentList.vue  # 設備一覧
│   │   └── Monitoring.vue     # リアルタイムモニタリング
│   ├── App.vue        # ルートコンポーネント
│   └── main.js        # Vueエントリーポイント
├── public/            # 静的ファイル
└── package.json       # 依存関係とビルド設定
```

## Flask Backend統合

デスクトップアプリ起動時、以下の処理が自動実行されます：

1. Flask backendが既に起動しているかチェック（`http://localhost:5000`）
2. 未起動の場合、`python backend/manage.py run`を子プロセスとして起動
3. Flask起動完了を待機（最大30秒）
4. Electronウィンドウを表示

ウィンドウを閉じてもFlask backendはバックグラウンドで継続します。
完全終了はタスクトレイアイコンの右クリックメニューから「完全終了」を選択してください。

## トラブルシューティング

### Flask backendが起動しない

1. Pythonコマンドが正しくパスに設定されているか確認
2. Flask backendの依存関係がインストールされているか確認
3. `plc-dashboard/backend/manage.py`が存在するか確認

### Socket.IO接続エラー

1. Flask backendが起動しているか確認（`http://localhost:5000/api/equipment`にアクセス）
2. CORSエラーが発生していないか確認（ブラウザ開発者ツール）

## 次のステップ（Phase 2以降）

- [ ] 設備管理機能（設定画面）
- [ ] 認証機能（ローカル認証）
- [ ] 自動更新機能（electron-updater）
- [ ] インストーラーのカスタマイズ
