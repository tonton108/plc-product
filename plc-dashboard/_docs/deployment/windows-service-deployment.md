# Windowsサービス配布（NSSM + ingest分離）

**作成日:** 2026-07-10
**対象:** Phase 4（中央サーバーをWindowsデスクトップ/サービスとして配布）
**前提:** サービング方式は「ingest/viewer 2プロセス + Redis」で確定
（`_docs/decisions/wsgi-serving-load-verification.md`）。

## 構成（中央サーバー1台）

工場内LANの中央サーバー（例 192.168.1.10）で、以下を **NSSM でWindowsサービス化** して常駐させる。

```
[中央サーバー / Windows]
  ├─ PostgreSQL            … データ保存（サービス）
  ├─ Redis互換(Memurai)    … SocketIOのmessage_queue（サービス）
  ├─ backend(ingest)       … エージェントのPOST受け口     serve_production.py ROLE=ingest
  ├─ backend(viewer)       … 閲覧クライアントのSocket.IO   serve_production.py ROLE=viewer
  └─ frontend(Nuxt静的)    … 配信（任意のHTTPサーバ/内蔵）
```

- **ingest** と **viewer** は同じアプリを2プロセスで起動し、`SOCKETIO_MESSAGE_QUEUE`
  （Redis）を共有する。ingest側の配信emitはRedis経由でviewer側のクライアントに届く。
- これにより、閲覧のlong-pollingがエージェントのingestを巻き込むスループット崩壊を回避する
  （実測: 分離なし14 req/s・p95 22秒 → 分離279 req/s・p95 74ms）。

## Redis（Windows）

Redis は公式にはWindows非対応のため、**Memurai**（Redis互換のネイティブWindowsサービス）を推奨する。
インストールすると Windows サービスとして常駐し、`redis://localhost:6379` で利用できる。
（代替: WSL2上のRedis、またはDocker Desktop上のRedisコンテナ。配布容易性ではMemuraiが有利。）

## ポート割り当てと振り分け

| 用途 | 接続先 | 例 |
|---|---|---|
| エージェント（POST /api/logs 等） | ingestプロセス | `http://<IP>:5000` |
| 閲覧クライアント（ブラウザ/Socket.IO） | viewerプロセス | `http://<IP>:5001` |

- エージェント側の `CENTRAL_SERVER_PORT` を ingest ポートに、Nuxtの `NUXT_PUBLIC_API_BASE` を
  viewer ポートに向ける。
- 単一ポートで見せたい場合はリバースプロキシ（例: nginxやIIS ARR）で
  `/api/logs`→ingest、`/socket.io/`と読み取りAPI→viewer に振り分ける。

## 環境変数（両backendプロセス共通 + 役割別）

```
DATABASE_URL=postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor
SECRET_KEY=<本番用のランダム値>
SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/0
FLASK_DEBUG=0
WAITRESS_THREADS=32          # 閲覧数 + ingest並列に応じて調整
# ↓プロセスごと
ROLE=ingest  / PORT=5000     # ingestプロセス
ROLE=viewer  / PORT=5001     # viewerプロセス
```

`SECRET_KEY` はデフォルト値のままだと `manage.py` のセキュリティチェックで起動が止まる
（`scripts/check_security.py`）。必ず本番用の値を設定すること。

## NSSM でのサービス登録（例）

NSSM（Non-Sucking Service Manager）で各プロセスを登録する。`python` は本番の
仮想環境のものを指定する。

```bat
:: ingest プロセス
nssm install plc-backend-ingest "C:\path\to\venv\Scripts\python.exe" "C:\app\backend\serve_production.py"
nssm set plc-backend-ingest AppDirectory "C:\app\backend"
nssm set plc-backend-ingest AppEnvironmentExtra ROLE=ingest PORT=5000 SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/0 DATABASE_URL=... SECRET_KEY=... FLASK_DEBUG=0 WAITRESS_THREADS=32
nssm set plc-backend-ingest DependOnService MemuraiService postgresql-x64-15
nssm set plc-backend-ingest AppExit Default Restart
nssm start plc-backend-ingest

:: viewer プロセス（PORT/ROLEのみ差し替え）
nssm install plc-backend-viewer "C:\path\to\venv\Scripts\python.exe" "C:\app\backend\serve_production.py"
nssm set plc-backend-viewer AppDirectory "C:\app\backend"
nssm set plc-backend-viewer AppEnvironmentExtra ROLE=viewer PORT=5001 SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/0 DATABASE_URL=... SECRET_KEY=... FLASK_DEBUG=0 WAITRESS_THREADS=32
nssm set plc-backend-viewer DependOnService MemuraiService postgresql-x64-15
nssm set plc-backend-viewer AppExit Default Restart
nssm start plc-backend-viewer
```

- `DependOnService` で PostgreSQL・Memurai(Redis) の後に起動させる。
- `AppExit Default Restart` でプロセス異常終了時に自動再起動。

## 起動順序とマイグレーション

1. PostgreSQL / Memurai(Redis) サービス起動
2. **マイグレーション適用**: `python -m flask --app manage.py db upgrade`
   - Windowsコンソールで実行する場合は `set PYTHONIOENCODING=utf-8` を付けること
     （付けないと絵文字printでcp932エラー…は#20で解消済みだが、他の出力の文字化け回避のため推奨）
3. backend(ingest) / backend(viewer) サービス起動
4. frontend 配信

## ヘルスチェック（死活監視）

各backendプロセスは無認証の `GET /api/health` を持つ。**DB疎通に加え、
`SOCKETIO_MESSAGE_QUEUE` 設定時はRedis疎通も確認**し、いずれか不通なら503を返す。
`role` フィールドで ingest/viewer を識別できる。

```
$ curl http://localhost:5000/api/health
{"database":"connected","message_queue":"connected","role":"ingest","status":"healthy"}   # 200
# Redis断のとき:
{"database":"connected","message_queue":"disconnected","role":"ingest","status":"unhealthy"} # 503
```

- 外形監視やリバースプロキシのヘルスチェックにこの200/503を使う。
- NSSMの `AppExit Restart` はプロセス終了時の再起動のみ。**「起動はしているが503」の
  状態での自動復旧が必要なら**、`/api/health` を叩いて503ならサービスを再起動する
  簡易ウォッチドッグ（タスクスケジューラ + PowerShell）を併用する。

## 小規模構成（分離しない）

閲覧クライアントが数台程度で高負荷にならない環境では、`SOCKETIO_MESSAGE_QUEUE` を
設定せず **単一プロセス**（`serve_production.py` のみ、Redis不要）でも動作する。
その場合 `/api/health` はDBのみ確認する。

## 未整備（今後）

- インストーラー（`.exe`）でのPostgreSQL/Memurai/backend一括セットアップ。
- トレイアプリからのサービス起動/停止・admin画面（SPEC §3.1）。
- リバースプロキシ設定テンプレートの同梱。
