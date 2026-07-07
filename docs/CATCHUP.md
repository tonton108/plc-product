# CATCHUP.md — プロジェクト再開のための現状把握メモ

> 作成日: 2026-07-06 / 対象コミット: `c464a19`（main最新, 2026-04-26）
> 目的: 久しぶりの再開にあたり「何が動いていて、何が壊れていて、次に何をやるか」を、実コードと突き合わせて整理する。
> 根拠は基本的に `ファイルパス:行番号` で示す。振り返りメモ（`plc-dashboard/_docs/history/`）とコードで食い違う箇所は明記した。

---

## 🆕 追記: CI完全グリーン化（2026-07-07）

**2025-10-30以降ずっと赤だったCIを、両ワークフローとも緑にした**（PR #7 / ブランチ `fix/ci-migration-dup-index-and-test-import`）。CIジョブ結果: Backend Linting ✓ / Backend Tests ✓ / Frontend Tests ✓ / Security ✓ / Docker Build ✓ / Playwright `test` ✓。

| 項目 | 状態 | 内容 | 検証 |
|---|---|---|---|
| P0-1 マイグレーション重複インデックス | ✅ 修正・CI緑 | `g1h2i3j4k5l6_add_performance_indexes.py` から `idx_logs_equipment_timestamp`/`idx_logs_timestamp` の再作成を除去（`a1b2c3d4e5f6` が作成済みのため）。新規4本のみ作成、downgradeも対称化。コミット `d4260d0`。 | 実PostgresでのマイグレーションがPlaywright CIで通過（緑）。 |
| P0-2 テストのimportエラー | ✅ 修正・CI緑 | `plc_drivers/keyence.py:23` の `from ..config.constants` → `from config.constants`（絶対import規約に統一）。コミット `d4260d0`。 | CI Backend Tests が収集エラーなく **68 passed / 1 skipped**。 |
| ① black整形 | ✅ 修正・CI緑 | `plc_drivers/` と `tests/` を black 整形（17ファイル）。コミット `0f1654a`。 | ローカル `black --check` 19ファイルOK。 |
| ② pylint誤検知 | ✅ 修正・CI緑 | `.pylintrc` で任意ベンダーlib（pymodbus/pymcprotocol/fins/snap7）の import-error を無視。コミット `9f23fd5`。 | pylint **7.20/10**（閾値7.0）。 |
| ③ カバレッジ44%割れ | ✅ 修正・CI緑 | 何もテストしていなかった `tests/test_load_simulation.py`（`test_`関数ゼロ）に純粋関数の実テスト4本を追加。**閾値44%は下げずに** 42%→45% へ改善。コミット `f836716`。 | ローカル実測 44.51%→表示45%。 |
| ④ Playwrightログインタイムアウト | ✅ 修正・CI緑 | `scripts/test_monitoring_chart.py` のログインボタン特定を日本語テキスト `button:has-text("ログイン")` → 言語非依存の `button[type="submit"]` に変更。原因は `nuxt.config.ts` の `detectBrowserLanguage` 有効＋CI英語ロケールでボタンが "Login" 表示になっていたこと。コミット `831789f`。 | Playwright `test` ジョブ緑（2m47s）。 |

**次にやると良い（今回未対応・別スコープ）**:
- **demo_data_sender の設備登録が壊れている**: CIログで `null value in column "plc_ip" ... violates not-null constraint`（500）→ DBに設備/データが1件も入らない。さらにPlaywrightテストは `LINE_A_001` を見に行くのに sender は `DEMO_001` を登録しようとしており**ID不一致**。現状テストは `chart_cards==0` をWARNING（成功扱い）＋`.glass-card` はヘッダーが無条件描画のため緑になるが、**グラフ描画の実検証にはなっていない**。データ投入を直せばE2Eが実効化する。
- カバレッジの段階引き上げ（45%→60%→…、`ci.yml` のTODO）。`plc_agent.py`/`error_reporter.py`/`log_rotator.py` 等が0%。
補足: マイグレーション内の `print("✅ …")` は Windowsの非UTF-8コンソールで直接 `flask db upgrade` するとUnicodeEncodeErrorになり得る（Docker/CI/Linuxでは無問題・既存挙動）。

---

## 1. このプロジェクトは何をするものか

工場内LAN（イントラネット）で稼働する **PLC（Programmable Logic Controller）データの収集・監視・分析システム**。各設備に接続した Raspberry Pi が PLC からデータを収集し（Modbus / FINS / MC Protocol）、中央サーバー（Flask API + PostgreSQL）へHTTP POSTで送信、Flaskがデータを保存しつつ Socket.IO でリアルタイム配信し、不特定多数のクライアント端末（PC・タブレット・スマホ）がブラウザで Nuxt.js 製ダッシュボードにアクセスして時系列グラフ・稼働状態・エラー/アラームを閲覧する。将来的には中央サーバー一式（PostgreSQL＋Flask＋Nuxt）を Electron デスクトップアプリとしてパッケージ配布する構想（`CLAUDE.md` のアーキテクチャ図、`plc-dashboard/desktop-app/`）。

---

## 2. サービス構成とデータフロー

### サービス一覧

| サービス | 技術 | ポート | 場所 | 役割 |
|---|---|---|---|---|
| **db** | PostgreSQL 15 | ホスト5433→5432 | `docker-compose.yml:3` | 共通データベース |
| **backend** | Flask + Flask-SocketIO + SQLAlchemy | 5000 | `plc-dashboard/backend/` | 中央API・WebSocket配信・集計スケジューラ |
| **frontend** | Nuxt.js 3 + Vuetify 3 + Chart.js（SPA, `ssr:false`） | 3000 | `plc-dashboard/pages/` ほか | ブラウザ用ダッシュボード |
| **raspi-agent** | Flask WebUI + PLCポーリング | 5001 | `plc-dashboard/raspi_agent/` | 各ラズパイ上でPLC収集・送信 |
| **desktop-app** | Electron + Vue3 | — | `plc-dashboard/desktop-app/` | 中央サーバー内蔵のデスクトップ版（将来の本番形態） |

- 補足: ホストのPostgreSQL衝突回避のため公開ポートは **5433**（`docker-compose.yml:12`）。`.mcp.json` のDB接続もこれに合わせて修正済み（`plc-dashboard/.mcp.json:8`, 直近コミット `c464a19`）。

### データフロー（サービスを跨ぐ部分を丁寧に）

```
[PLC] --(Modbus/FINS/MC)--> [Raspberry Pi: raspi_agent]
   plc_agent.py のポーリングループ (plc_agent.py:286-382)
   ├─ ドライバで読取: mitsubishi/omron/keyence（siemensはスタブ）
   │    実PLC失敗時は自動的にダミーデータへフォールバック (plc_agent.py:109-142)
   ├─ アラーム判定
   └─ ① ローカルSQLiteバッファに必ず保存 (api_client.py:288-309, local_buffer.py)
        │
        ▼ ② HTTP POST http://{CENTRAL}:5000/api/logs  (api_client.py:293)
        │     送信成功→mark_as_sent(削除) / 失敗→残置し再送(60秒毎・100件・7日保持)
        │     ※ base_url 既定は 192.168.1.10:5000 (config/constants.py:32-33)
        ▼
[中央サーバー: Flask backend]
   POST /api/logs (logs.py:38)
   ├─ 設備識別: cpu_serial_number > mac_address > equipment_id の優先順
   ├─ Log行をDB保存（固定列 + 動的項目JSON列 `data`）
   └─ ③ Socket.IO emit 'plc_data_update' → room 'monitoring' (logs.py:114)
        │
        ▼ ④ WebSocket
[ブラウザ: Nuxt SPA]
   monitoring/[id].vue が $socket 接続 (plugins/socket.io.client.ts)
   ├─ 'join_monitoring' emit → room参加 (composables/useRealtimeMonitoring.js:55,67)
   ├─ 'plc_data_update' 受信 → Chart.js グラフ更新（canvasのみ更新）
   └─ 履歴/最新値/設備情報は REST fetch: /api/logs/{id}/latest, /history_optimized, /api/equipment/{id}
        apiBase = NUXT_PUBLIC_API_BASE || http://localhost:5000 (nuxt.config.ts:95-101)

[並行] エラー/アラーム経路:
   raspi_agent/error_reporter.py
   → POST /api/equipment/{id}/error_logs (error_reporter.py:56)
   → POST /api/equipment/{id}/alarms     (error_reporter.py:117)
   → 中央DBに記録、/errors-alarms ページで確認・確認/解除/解決操作

[並行] 集計・クリーンアップ（backend内 daemon スレッド, 24時間毎, scheduler.py:353-388）:
   ├─ 前日分の日次集計 create_daily_summary
   ├─ 月初のみ前月の月次集計 create_monthly_summary
   └─ 古いデータ削除: raw 90日 / daily 365日 / error_log 30日 / alarm_history 30日(解除済のみ)
```

### 階層化アーカイブ（クエリ最適化）

`/api/logs/{id}/history_optimized`（`logs.py:169`）が期間に応じて参照先を自動選択:
- 短期（`1h/6h/24h`）→ 生ログ `logs` テーブル
- 長期（`7d/30d`）→ 日次集計 `daily_log_summaries`
- `period` はホワイトリスト検証済み（`logs.py:178`, 直近コミット `220bf5f`）、履歴limitは上限10000（`logs.py:155`）。

---

## 3. 現在地（動くもの / 未完・壊れているもの）

### ⚠️ 最重要: CI は両ワークフローとも「赤」が継続中（※2026-07-07に解消済み → 冒頭の「追記」参照）

> **更新（2026-07-07）**: 以下は修正前の状況記録。下記の根本原因はすべて修正し、CIは両ワークフローとも緑化済み（PR #7）。詳細はファイル冒頭の「🆕 追記」を参照。

`gh run list` の結果、**最後にPlaywrightが緑だったのは 2025-10-30**。それ以降 `CI - PLC Monitoring System` と `Playwright Tests` は連続失敗している。根本原因を失敗ログで特定済み:

1. **Playwright Tests の失敗** = マイグレーション破損
   `flask db upgrade` が `g1h2i3j4k5l6`（Phase 3インデックス）で停止:
   ```
   psycopg2.errors.DuplicateTable: relation "idx_logs_equipment_timestamp" already exists
   ```
   → クリーンDBのセットアップ自体が完了しない（後述 §5-①）。

2. **CI Backend Tests の失敗** = テスト収集エラー
   `raspi_agent/tests/test_plc_drivers_base.py` が
   `ImportError: attempted relative import beyond top-level package`
   で pytest 収集に失敗（51件収集で中断）。直近コミット `489ca91`（テスト修正）でも解消し切れていない。

> メモとの食い違い: `_docs/history/IMPLEMENTATION_CHECKLIST.md:104-129,213` は「CI/CD 100%実装済み ✅」「総合92%完了」「ドキュメントと実装は整合」と記載。実態はCIが長期赤。チェックリストは**動作保証ではなく“ファイルの存在確認”に留まっている**点に注意。

### ✅ 実装済みで動作していると見られるもの

- **中央API（Flask）**: 設備登録・一覧・PLCデータ受信・履歴/最適化履歴・エラー/アラーム（Phase 7: acknowledge/clear/resolve）・health・admin統計/手動クリーンアップ。Blueprint分割済み（`api/routes/` パッケージ）。エンドポイント詳細は §末尾参照。
- **Socket.IO**: `async_mode='threading'` で初期化（`app.py:73-79`）。`plc_data_update` 配信、`join_monitoring` 等のハンドラ実装済み（`api/routes/websocket.py`）。
- **DBモデル/集計**: Equipment / PLCDataConfig / Log(+JSON動的列) / DailyLogSummary / MonthlyLogSummary / CommunicationErrorLog / AlarmHistory / PLCStatus。N+1解消済みの集計（`scheduler.py:175,264`）。
- **PLCドライバ**: 三菱(MC)・オムロン(FINS)・キーエンス(Modbus)は実通信実装済み。Big-Endian・タイムアウト（接続5秒/読取3秒, `plc_drivers/base.py:39-41`）。
- **ローカルバッファリング**: SQLite、送信失敗時の再送、リトライ上限、期限クリーンアップ。ネットワーク障害耐性あり。
- **フロントUI**: login / index（設備一覧）/ monitoring/[id]（リアルタイム）/ equipment/[id]（設備詳細）/ errors-alarms / logs（CSV出力）。コンポーネント分割・テーマ切替・トースト。
- **多言語対応(i18n)**: フロントは `@nuxtjs/i18n`（ja/en/zh, `nuxt.config.ts:29-51`）、raspi_agentは別系統で Flask-Babel。
- **本番向け土台**: `wsgi.py`（Gunicorn/GeventWebSocketWorker想定）、DB接続プール（`app.py:57-67`, pool_size=20/max_overflow=50）、CORSの環境変数化（`app.py:25-27`）、エラーハンドラ登録（`error_handlers.py`）、セキュリティチェック（`scripts/check_security.py`）、バックアップ/リストア/logrotate。→ improvements.md の指摘の多くは対応済み（§4参照）。

### ⚠️ 部分実装・スタブ・未完

- **Siemens ドライバ**: スタブのみ。`read_siemens_plc` は読取ロジックが無く空 `{}` を返す（`plc_drivers/siemens.py:64-107`, TODO `:90`）。優先度低（メモと一致）。
- **バックエンド認証**: **存在しない**。全API無認証で `POST /api/register` `POST /api/logs` も誰でも叩ける。
- **フロント認証**: `middleware/auth.ts` はあるが、資格情報が **フロント内ハードコード**（`login.vue:111-114`, `localStorage`トークン）。認証適用は index と monitoring/[id] の **2ページのみ**。errors-alarms / logs / equipment/[id] は未保護。
  > メモとの食い違い: `IMPLEMENTATION_CHECKLIST.md:250-263` は「Nuxt UI認証機能 ✅」とするが、実態はクライアント側ダミー認証＋一部ページのみ＋バックエンド未連携。
- **`error_reporter.update_plc_status`**: 実質no-op（Phase 2 APIに更新エンドポイントが無いため, `error_reporter.py:158-175`）。
- **`agent_app.py` の `/test-connection`**: 接続テスト未実装で `success = True`（仮, `agent_app.py:479-490`）。
- **モバイルUI実機検証**: 未実施（メモの未確認項目, `IMPLEMENTATION_CHECKLIST.md:169-181`）。

---

## 4. 次にやることの候補（優先度つき）

### 🔴 P0（再開直後にやるべき / 環境が立ち上がらない・CIが赤）

1. **マイグレーション重複インデックスの修正**（§5-① 詳細）
   `g1h2i3j4k5l6_add_performance_indexes.py` が `a1b2c3d4e5f6` と同名の `idx_logs_equipment_timestamp` / `idx_logs_timestamp` を再作成 → クリーンDBで必ず失敗。
   対応案: g1h2側で重複2本を削除、または `IF NOT EXISTS`／事前drop、または a1b2との統合。**これを直さないと fresh な `flask db upgrade` もPlaywright CIも通らない。**
2. **raspi_agent テストの import エラー修正**
   `raspi_agent/tests/test_plc_drivers_base.py` の相対import（`attempted relative import beyond top-level package`）を修正し、CI Backend Tests を復旧。

### 🟠 P1（品質・整合性）

3. **モデルとマイグレーションの不整合解消**
   `MonthlyLogSummary` の `pressure_max`/`pressure_min` がモデルでコメントアウト（`db/models/logs.py:120-122,164`）なのに、マイグレーション `b2c3d4e5f6a7` はDBに追加している。どちらかに揃える。
4. **CIの実効性を上げる**
   現状 CI Backend ジョブは `raspi_agent/` しかテストせず、Flask `backend/` の `tests/` は実行対象外。ESLintは `|| true` で非ブロッキング（`.github/workflows/ci.yml:109`）、pylint/blackは `plc_drivers/` のみ。カバレッジ閾値44%（`ci.yml:54-57` にTODOで85%目標）。backendテストの取り込みと閾値の段階引き上げ。

### 🟡 P2（本番化・セキュリティ）

5. **認証の本実装**: バックエンドにトークン/セッション認証を入れ、全ページ・全API（特に `POST /api/register` `POST /api/logs`）を保護。フロントのハードコード資格情報を排除。
6. **本番起動経路の一本化**: `docker-compose.yml:39` は `flask run`（開発サーバ）、`Dockerfile:29` の `CMD` は `python manage.py`、本番用は `wsgi.py`(Gunicorn) と**3系統**が併存。本番形態（Electron同梱 or Gunicorn）を決めて統一。
7. **既定シークレットの排除**: `docker-compose.yml` の `POSTGRES_PASSWORD:-plc_pass` / `SECRET_KEY:-development-secret-key` 等の弱いデフォルト。

### 🟢 P3（任意）

8. モバイルUI実機検証（→ `_docs/testing/mobile-ui-validation.md`）。
9. Siemensドライバ実装（`python-snap7`）。優先度低。

---

## 5. 気になった点（壊れてそう・中途半端・設計判断が読み取れない）

### ① 【壊れている・確証あり】マイグレーションが単一チェーン上で同名インデックスを二重作成

- チェーンは直線（head = `h1i2j3k4l5m6`）。`a1b2c3d4e5f6`（2025-10-29）が `idx_logs_timestamp` と `idx_logs_equipment_timestamp` を作成（`a1b2c3d4e5f6_...py:27,31`）。
- その子孫 `g1h2i3j4k5l6`（2025-11-03, Phase 3）が同名2本を **DESC付きで再作成**（`g1h2i3j4k5l6_...py:36,45`）。`IF NOT EXISTS` も事前dropも無い。
- **CIログで実際に失敗を確認**: `Running upgrade f1g2h3i4j5k6 -> g1h2i3j4k5l6 ... psycopg2.errors.DuplicateTable: relation "idx_logs_equipment_timestamp" already exists`。
- 影響: クリーンDBへの `flask db upgrade` が完了しない → Playwright CIが常時赤。既存の稼働DBは段階適用で回避できていた可能性があるが、新規セットアップは不可。

### ② 【中途半端】テストとCIの実効カバレッジが薄い

- CIの「Backend Tests」は名前に反し `raspi_agent/` のみ対象（`ci.yml:31-41`）。Flask `backend/tests/`（`test_api.py` 等）はCI未実行。
- その唯一のバックエンドテストも import エラーで収集失敗中（P0-2）。つまり**現状バックエンド系テストは1件も走っていない**。
- ESLint非ブロッキング（`|| true`）、lint対象も一部ディレクトリのみ。「CIが通る＝品質担保」には現状なっていない。

### ③ 【設計判断が読み取れない】起動経路が3系統

- `docker-compose.yml:39` → `flask run`（Werkzeug開発サーバ。Socket.IOのWebSocket transportは本来この起動では不安定）
- `Dockerfile:29` → `python manage.py`（`socketio.run`, `allow_unsafe_werkzeug=debug_mode`）
- `wsgi.py` → Gunicorn（本番想定）
  直近の「デバッグ露出防止」修正（`4bc8eae`）は manage.py を固めたが、compose は manage.py を使わず `flask run` で上書きしているため、その修正はcompose開発経路には効かない。どれを正とするか不明確。

### ④ 【要確認】認証まわりの実態がメモと乖離

- バックエンドは完全無認証、フロントはハードコード資格情報＋一部ページのみ保護（§3）。メモ（チェックリスト）は「認証機能 ✅」。イントラネット前提とはいえ、`POST /api/register`・`POST /api/logs` が無認証で書き込み可能な設計を意図通りか要確認。

### ⑤ 【軽微】振り返りメモ全体が2025-10〜11時点でスナップショット的

- `_docs/history/` の4文書（統合サマリ・改善提案・実装チェックリスト・リファクタ計画）は当時の記録。`improvements.md` のCritical/High指摘（.gitignore欠如, CORS固定, DB接続プール, NUXT_PUBLIC_API_BASE=backend:5000, versionフィールド, エラーハンドラ, ログ管理 等）は**その後のコミットでほぼ解消済み**（`app.py`, `nuxt.config.ts`, `.gitignore`, `error_handlers.py` 等で確認）。ただし「本番サーバ(compose)」「マイグレーション整合」「テスト健全性」は未解決 or 悪化。メモは"やることリスト"としてはもう古く、本CATCHUPの §4 を最新版として扱うのが良い。

### ⑥ 【軽微】ルート `README.md` がほぼ空（タイトルのみ, `README.md:1`）

再開者向けの入口としては `CLAUDE.md` と `plc-dashboard/_docs/` が実質のドキュメント。

---

## 付録: 主要APIエンドポイント（Blueprint分割済み `plc-dashboard/backend/api/routes/`）

| メソッド | パス | 用途 | 実装 |
|---|---|---|---|
| POST | `/api/register` | 設備登録（ラズパイから） | `equipment.py:35` |
| GET | `/api/equipment` | 全設備一覧 | `equipment.py:130` |
| GET/PUT | `/api/equipment/<id>` | 基本設定 取得/保存 | `equipment.py:157,170` |
| GET/PUT | `/api/equipment/<id>/plc_configs` | PLCデータ設定 | `equipment.py:321,335` |
| POST | `/api/logs` | **PLCデータ受信＋WS配信** | `logs.py:38` |
| GET | `/api/logs/<id>/latest` | 最新値 | `logs.py:131` |
| GET | `/api/logs/<id>/history` | 履歴（limit≤10000） | `logs.py:149` |
| GET | `/api/logs/<id>/history_optimized` | 期間別 最適化履歴 | `logs.py:169` |
| POST/GET | `/api/equipment/<id>/error_logs` | エラー 記録/一覧 | `errors_alarms.py:31,74` |
| PATCH | `/api/equipment/<id>/error_logs/<lid>/resolve` | エラー解決 | `errors_alarms.py:95` |
| POST/GET | `/api/equipment/<id>/alarms` | アラーム 記録/一覧 | `errors_alarms.py:130,162` |
| PATCH | `/api/equipment/<id>/alarms/<aid>/acknowledge` | アラーム確認 | `errors_alarms.py:183` |
| PATCH | `/api/equipment/<id>/alarms/<aid>/clear` | アラーム解除 | `errors_alarms.py:221` |
| GET | `/api/equipment/<id>/plc_status` | PLC通信状態 | `errors_alarms.py:256` |
| GET | `/api/health` | ヘルスチェック | `health.py:12` |
| POST/GET | `/api/admin/cleanup`, `/api/admin/stats`, `/api/admin/create_summary` | 運用管理 | `admin.py:28,53,97` |

---

*本メモは読み取り専用調査の結果であり、コードは一切変更していない。次アクションの起点は §4。*
