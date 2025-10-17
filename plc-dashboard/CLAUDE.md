# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

PLCから取得したデータをリアルタイムで監視・分析するWebアプリケーションです。Raspberry Pi経由でPLCからデータを収集し、Flask APIで保存・配信、Nuxt.js UIでリアルタイム表示を行います。

### アーキテクチャ構成

- **フロントエンド**: Nuxt.js 3 + Vuetify 3 + Chart.js + Socket.IO Client
- **バックエンド**: Flask + Flask-SocketIO + SQLAlchemy
- **データベース**: PostgreSQL（推奨・本番環境・開発環境共通）
- **リアルタイム通信**: Socket.IO（threading mode）
- **データ収集**: Raspberry Pi + Python（PLCとModbus通信）

**重要**: このプロジェクトでは**PostgreSQLを優先して使用**してください。SQLiteはフォールバック用ですが、開発環境でもPostgreSQLを使用することを強く推奨します。

### データフロー

```
[PLC] ─Modbus─> [Raspberry Pi] ─HTTP POST─> [Flask API] ─WebSocket─> [Nuxt UI]
                                                    ↓
                                            [PostgreSQL/SQLite]
```

## 開発コマンド

### フロントエンド（Nuxt.js）

```bash
# 開発サーバー起動（ポート3000）
npm run dev

# プロダクションビルド
npm run build

# プレビュー
npm run preview
```

### バックエンド（Flask）

```bash
# Flaskアプリケーション起動
cd backend
flask --app manage.py run --host=0.0.0.0 --port=5000

# または仮想環境で
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app manage.py run
```

### データベース管理

```bash
# マイグレーション実行
cd backend
flask --app manage.py db upgrade

# 初回のみ（マイグレーション初期化）
flask --app manage.py db init

# 新しいマイグレーション作成
flask --app manage.py db migrate -m "マイグレーション名"

# テーブル確認
python backend/check_tables.py

# データベース初期化（開発用）
python init_db.py
```

### データ管理ツール

```bash
# データベース統計表示
python backend/log_manager.py stats

# 古いデータのクリーンアップ（90日以上）
python backend/log_manager.py cleanup --days 90

# 日次集計を手動作成
python backend/log_manager.py daily 2025-01-15

# 月次集計を手動作成
python backend/log_manager.py monthly 2025 1
```

### デモツール

```bash
# PLCデータ送信シミュレーション（2秒間隔で連続送信）
python backend/demo_data_sender.py --mode continuous --interval 2.0

# 単発データ送信テスト
python backend/demo_data_sender.py --mode single

# 設備登録のみ
python backend/demo_data_sender.py --mode register --equipment-id DEMO_001
```

### Docker環境

```bash
# Docker Composeで全体を起動
docker-compose up -d

# ログ確認
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止
docker-compose down
```

## コードアーキテクチャ

### バックエンド構造

#### `backend/app.py`
Flaskアプリケーションのファクトリー関数を定義。CORS設定、SQLAlchemy初期化、Socket.IO初期化（threading mode）、ルート登録を行います。

**重要**: Socket.IOは`async_mode='threading'`で初期化されており、greenletエラーを回避しています。

#### `backend/api/routes.py`
全APIエンドポイントとWebSocketイベントハンドラーを定義：

**REST API**:
- `POST /api/register` - 設備登録（Raspberry Piからの初期登録）
- `GET /api/equipment` - 全設備一覧取得
- `GET /api/equipment/<equipment_id>` - 設備基本情報取得
- `PUT /api/equipment/<equipment_id>` - 設備基本情報保存
- `GET /api/equipment/search?cpu_serial_number=XXX` - CPU番号で設備検索
- `PUT /api/equipment/<equipment_id>/plc_configs` - PLCデータ設定保存
- `GET /api/equipment/<equipment_id>/plc_configs` - PLCデータ設定取得
- `POST /api/logs` - PLCログデータ保存 + WebSocket配信
- `GET /api/logs/<equipment_id>/latest` - 最新ログ取得
- `GET /api/logs/<equipment_id>/history` - 履歴データ取得
- `GET /api/logs/<equipment_id>/history_optimized?period=24h` - 最適化履歴取得
- `POST /api/admin/cleanup` - 手動クリーンアップ実行
- `GET /api/admin/stats` - データベース統計取得
- `POST /api/admin/create_summary` - 集計データ作成

**Socket.IO イベント**:
- `connect` - WebSocket接続確立
- `disconnect` - WebSocket接続切断
- `join_monitoring` - モニタリングルーム参加
- `leave_monitoring` - モニタリングルーム退出
- `get_realtime_status` - リアルタイム状態取得要求
- `plc_data_update` - PLCデータ更新通知（サーバー→クライアント）
- `equipment_data_update` - 設備別データ更新通知（サーバー→クライアント）

**自動スケジューラー**:
- 24時間間隔で自動クリーンアップ実行
- 前日の日次集計自動作成
- 月初に前月の月次集計自動作成

#### `backend/db/models.py`
SQLAlchemyモデル定義：

- **Equipment**: 設備情報（equipment_id, manufacturer, series, ip, plc_ip, mac_address, cpu_serial_number, etc.）
- **PLCDataConfig**: PLCデータ項目設定（data_type, address, scale_factor, plc_data_type）
- **Log**: 詳細ログデータ（90日間保存）
- **DailyLogSummary**: 日次集計データ（365日間保存）
- **MonthlyLogSummary**: 月次集計データ（永続保存）

**重要な識別子の優先順位**:
1. `cpu_serial_number`（Raspberry PiのCPUシリアル番号、不変識別子）
2. `mac_address`（MACアドレス、準不変）
3. `equipment_id`（ユーザー定義ID、可変）

設備検索・更新時は必ずこの優先順位で検索してください。

#### `backend/log_manager.py`
データ保存期間管理とクリーンアップのCLIツール。バックグラウンドで自動実行されるほか、手動実行も可能です。

#### `raspi_agent/agent_app.py`
Raspberry Pi用FlaskアプリケーションとPLCエージェント管理。初期設定画面、モニタリング画面、認証機能を提供します。

**重要な実装上の注意点**:

1. **変数シャドーイング問題**: ループ変数に`config`という名前を使用すると、グローバル変数`config`をシャドーイングしてUnboundLocalErrorが発生します。ループ変数には`plc_config`など別の名前を使用してください。

```python
# ❌ 悪い例（変数シャドーイング）
config = load_config()
for config in plc_configs:  # グローバルのconfigをシャドーイング
    process(config)

# ✅ 良い例
config = load_config()
for plc_config in plc_configs:  # 別の変数名を使用
    process(plc_config)
```

2. **動的PLC設定の読み取り**: 初回設定画面から送信されるPLC設定は`plc_configs_json`フィールドにJSON形式で格納されています（`agent_app.py:236-271`）。

### フロントエンド構造

#### `pages/index.vue`
トップページ - 設備一覧表示

#### `pages/equipment/[id].vue`
設備設定ページ - 基本設定とPLCデータ項目設定（Raspberry Piからのセットアップフロー）

#### `pages/monitoring/[id].vue`
リアルタイムモニタリングページ - Socket.IOでリアルタイムデータ受信、Chart.jsでグラフ表示

#### `plugins/socket.io.client.ts`
Socket.IO Clientの初期化設定（`/monitoring/[id].vue`内で直接使用）

#### `plugins/vuetify.ts`
Vuetify 3設定（Material Design Icons含む）

## データベース設計の特徴

### 階層化アーカイブシステム

1. **詳細データ（logs）**: 90日間保存、リアルタイム監視・詳細分析用
2. **日次集計（daily_log_summaries）**: 365日間保存、週次・月次トレンド分析用
3. **月次集計（monthly_log_summaries）**: 永続保存、長期比較・年次計画用

### 最適化されたインデックス

- `idx_logs_timestamp` - タイムスタンプ検索の高速化
- `idx_logs_equipment_timestamp` - 設備別期間検索の高速化
- `idx_daily_summary_equipment_date` - 日次集計検索の高速化
- `idx_monthly_summary_equipment_year_month` - 月次集計検索の高速化

### データ保存戦略

`backend/api/routes.py`の`DATA_RETENTION_CONFIG`で設定：
- `raw_data_days`: 90（詳細データ保持期間）
- `daily_data_days`: 365（日次集計保持期間）
- `cleanup_interval_hours`: 24（クリーンアップ実行間隔）

## リアルタイム通信の実装

### Socket.IO接続フロー

1. Nuxt UIが`/monitoring/[id]`ページを開く
2. Socket.IO Clientが`ws://localhost:5000`に接続
3. `join_monitoring`イベントでルーム参加
4. Raspberry Piが`POST /api/logs`でデータ送信
5. Flask APIがDB保存 + `emit('plc_data_update')`で配信
6. Nuxt UIがリアルタイムでグラフ更新

### WebSocketルーム設計

- `monitoring` - 全モニタリングクライアント
- `equipment_{equipment_id}` - 特定設備のモニタリングクライアント

## 環境変数設定

### 初回セットアップ手順

**重要**: プロジェクトを初めて起動する前に、必ず.envファイルを作成してください。

```bash
# プロジェクトルートで.envファイルを作成
cd plc-dashboard
cp .env.example .env

# バックエンドディレクトリにもコピー
cp .env backend/.env
```

### バックエンド（`backend/.env`）

**PostgreSQL設定（推奨）**:

```env
DATABASE_URL=postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

**PostgreSQL接続確認**:

```bash
# PostgreSQL接続テスト
psql -U plc_user -h localhost -d plc_monitor -c "SELECT version();"

# マイグレーション実行
cd backend
flask --app manage.py db upgrade
```

**SQLiteフォールバック（非推奨）**:

DATABASE_URL未設定時はSQLiteにフォールバックしますが、**本番環境・開発環境ともにPostgreSQLの使用を強く推奨します**。

```python
# backend/app.py:26-28
database_url = f'sqlite:///{db_path}'  # フォールバック用
```

### Raspberry Piエージェント（`raspi_agent/.env`）

```env
# PLC接続設定
PLC_IP=192.168.0.10
PLC_PORT=5000
PLC_MANUFACTURER=Mitsubishi
LOG_INTERVAL_MS=5000
USE_DUMMY_PLC=false

# エラー処理設定
MAX_RETRY_ATTEMPTS=3
CONNECTION_TIMEOUT=5
READ_TIMEOUT=3

# PLCセキュリティ設定（2025-01追加）
# IPホワイトリスト: 許可するPLC IPアドレス（カンマ区切り）
ALLOWED_PLC_IPS=192.168.0.10,192.168.0.20,192.168.0.30

# 読み取り専用モード: trueの場合、PLCへの書き込みを禁止
READ_ONLY_MODE=true
```

**セキュリティ設定の重要性**:
- `ALLOWED_PLC_IPS`: 空の場合はすべてのIPを許可（推奨しません）
- `READ_ONLY_MODE`: 本番環境では必ずtrueに設定（データ改ざん防止）

## 重要な実装上の注意点

### Socket.IOのGreenletエラー回避

Flask-SocketIOは`async_mode='threading'`で初期化する必要があります：

```python
socketio.init_app(
    app,
    cors_allowed_origins=["http://localhost:3000"],
    async_mode='threading',
    logger=False,
    engineio_logger=False
)
```

### 設備の識別と更新

設備の更新時は必ず`cpu_serial_number`で既存設備を検索し、見つかった場合は`equipment_id`を更新します。これにより、Raspberry Piの再起動やIP変更があっても設備情報を正しく維持できます。

```python
# routes.py:388-432 参照
equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()
if equipment:
    equipment.equipment_id = equipment_id  # 設備IDを新しい値に更新
```

### PLCデータ設定の保存

PLCデータ設定は`PUT /api/equipment/<equipment_id>/plc_configs`で一括保存されます。既存設定を削除してから新しい設定を挿入するため、トランザクション内で実行してください。

### データ最適化クエリ

短期間（1h, 6h, 24h）は詳細データ、長期間（7d, 30d）は集計データを自動的に選択します：

```python
# routes.py:979-1052 参照
if period in ['1h', '6h', '24h']:
    logs = Log.query.filter(...).all()  # 詳細データ
elif period in ['7d', '30d']:
    summaries = DailyLogSummary.query.filter(...).all()  # 集計データ
```

### PLCエンディアン処理（2025-01修正）

すべてのPLCメーカー（三菱、オムロン、キーエンス、シーメンス）はBig-Endianで通信します。

**三菱PLCのfloat32/dword読み取り例**:
```python
# raspi_agent/plc_agent.py:442-463 参照
# 2ワード読み取り (32bit)
word_values = plc.batchread_wordunits(headdevice="D100", readsize=2)

# Big-Endian形式で結合（修正前はLittle-Endianで誤っていた）
word1, word2 = word_values[0], word_values[1]
combined = (word1 << 16) | word2
float_value = struct.unpack('>f', struct.pack('>I', combined))[0]  # '>f' = Big-Endian
```

**重要**: `pymcprotocol`や`fins`ライブラリは内部で自動エンディアン変換を行うため、通常は手動変換は不要ですが、複数ワードを結合する場合は明示的にBig-Endianを指定してください。

### PLCセキュリティとアクセス制御（2025-01追加）

`raspi_agent/plc_agent.py`には以下のセキュリティ機能が実装されています：

1. **IPホワイトリスト検証**
```python
# raspi_agent/plc_agent.py:111-131 参照
def validate_plc_ip(ip_address):
    """PLCのIPアドレスをホワイトリストで検証"""
    if ip_address not in ALLOWED_PLC_IPS:
        logger.error(f"🚫 不正なPLC IPアドレス: {ip_address}")
        return False
    return True

# 各PLC接続関数で自動チェック
plc = connect_mitsubishi_plc(ip, port)  # 内部でvalidate_plc_ip()を呼び出し
```

2. **読み取り専用モード**
```python
# raspi_agent/plc_agent.py:133-143 参照
def check_write_permission():
    """PLC書き込み権限をチェック"""
    if READ_ONLY_MODE:
        logger.warning("🔒 書き込み保護モードが有効です")
        return False
    return True
```

3. **全接続関数でのセキュリティチェック**
   - `connect_mitsubishi_plc()` - 三菱PLC接続前にIP検証
   - `connect_omron_plc()` - オムロンPLC接続前にIP検証
   - `connect_keyence_plc()` - キーエンスPLC接続前にIP検証
   - `connect_siemens_plc()` - シーメンスPLC接続前にIP検証

### パフォーマンス監視（2025-01追加）

`raspi_agent/plc_agent.py`には包括的なパフォーマンス統計機能が実装されています：

**監視指標**:
- 通信成功率（目標: 95%以上）
- 平均応答時間（目標: 100ms以下）
- エラー率（目標: 5%以下）
- 総試行回数、成功回数、失敗回数
- 最大・最小応答時間
- 稼働時間

**統計の自動記録**:
```python
# raspi_agent/plc_agent.py:143-185 参照
update_error_stats(success=True, response_time_ms=50.5)  # 成功時
update_error_stats(success=False, error_type="connection")  # 失敗時
```

**統計の表示**:
```python
# 100回の通信ごとに自動表示
print_error_stats()  # 通信成功率、平均応答時間、エラー率などを表示
```

**応答時間の測定**:
```python
# raspi_agent/plc_agent.py:477-520 参照
start_time = time.time()
result = read_from_real_plc(...)
response_time_ms = (time.time() - start_time) * 1000  # ミリ秒に変換
update_error_stats(True, response_time_ms=response_time_ms)
```

## テストとデバッグ

### デモデータ送信の実行順序

1. バックエンド起動: `flask --app manage.py run`
2. フロントエンド起動: `npm run dev`
3. デモ送信開始: `python backend/demo_data_sender.py --mode continuous`
4. ブラウザで確認: `http://localhost:3000/monitoring/DEMO_001`

### ログの確認

- Flask側: ターミナル出力に詳細なデバッグログ（`📥 PLCデータ受信`, `📡 WebSocket送信完了`等）
- Nuxt側: ブラウザの開発者コンソールでSocket.IOイベント確認

### トラブルシューティング

#### データベース接続エラー

**PostgreSQL接続確認**:
```bash
# PostgreSQL接続テスト
psql -U plc_user -h localhost -d plc_monitor -c "SELECT version();"

# マイグレーション実行
cd backend
flask --app manage.py db upgrade
```

#### Alembicマイグレーション履歴の不整合

**症状**: `flask db upgrade`実行時に`Can't locate revision identified by 'XXXXX'`エラーが発生

**原因**: PostgreSQLのalembic_versionテーブルの値が、migrationsディレクトリ内の最新リビジョンと一致していない

**解決方法**:

```bash
# 1. 最新のマイグレーションファイルを確認
ls -lt backend/migrations/versions/ | head -5
grep "revision = " backend/migrations/versions/*.py | tail -3

# 2. alembic_versionテーブルの現在値を確認
psql -U plc_user -h localhost -d plc_monitor -c "SELECT * FROM alembic_version;"

# 3. 最新リビジョンに更新（例：31ebb7e53291）
psql -U plc_user -h localhost -d plc_monitor -c "UPDATE alembic_version SET version_num = '31ebb7e53291';"

# 4. マイグレーション再実行
cd backend
flask --app manage.py db upgrade
```

#### 設備が登録されない・ローカル設定と表示される

**症状**: 初回設定画面で設備を登録したが、モニタリング画面に「ローカル設定」と表示され、中央サーバーに登録されていない

**原因**: ローカルのplc_config.jsonに設備情報が保存されているが、中央サーバーには登録されていない

**解決方法**:

```bash
# 1. ラズパイエージェントを停止
lsof -ti :5001 | xargs kill -9

# 2. ローカル設定をクリア（バックアップ作成）
cd raspi_agent
cp config/plc_config.json config/plc_config.json.backup
echo '{}' > config/plc_config.json

# 3. ラズパイエージェントを再起動
python3 agent_app.py

# 4. ブラウザで http://localhost:5001/ にアクセスし、初回設定画面から再登録
```

#### Socket.IO接続エラー
- CORSオリジン設定を確認（`backend/app.py:18-20, 60`）
- ポート5000が開いているか確認

#### データが表示されない
1. `GET /api/logs/DEMO_001/latest` でデータ存在確認
2. Socket.IOイベント受信確認（ブラウザコンソール）
3. Flaskログでデータ受信・配信を確認

---

## PLC基礎知識

このセクションでは、PLCとの通信に関する技術的な基礎知識を提供します。

### 対応メーカーとプロトコル

このシステムは以下のPLCメーカーとプロトコルに対応しています：

| メーカー | プロトコル | Pythonライブラリ | ポート | 対応状況 |
|---------|-----------|----------------|-------|---------|
| 三菱電機 | MC Protocol (SLMP) | pymcprotocol | 5000/5007 | ✅ 実装済み |
| オムロン | FINS over TCP | fins | 9600 | ✅ 実装済み |
| キーエンス | Modbus TCP | pymodbus | 502 | ✅ 実装済み |
| シーメンス | S7 Protocol | python-snap7 | 102 | 🚧 未実装 |

### PLCデータ型とバイト長

PLCで扱う主なデータ型とそのバイト長、値の範囲：

| データ型 | バイト長 | ビット数 | 範囲 | 用途 |
|---------|---------|---------|------|------|
| `bit` | - | 1 | 0 or 1 | リレー、接点状態、ON/OFF信号 |
| `word` | 2 | 16 | 0 ~ 65,535（unsigned）<br>-32,768 ~ 32,767（signed） | カウンタ、タイマー、設定値 |
| `dword` | 4 | 32 | 0 ~ 4,294,967,295（unsigned）<br>-2,147,483,648 ~ 2,147,483,647（signed） | 大きな整数値、累積カウンタ |
| `float32` | 4 | 32 | ±1.18×10⁻³⁸ ~ ±3.4×10³⁸ | 温度、圧力、流量などの実数値 |

**重要な注意点：**
- `float32`はIEEE 754標準に準拠
- 三菱PLCの`D`レジスタは16bit単位なので、`dword`や`float32`は2ワード連続で読み取る必要がある
- ビット指定の場合、アドレス形式は`D100.5`（D100の5ビット目）のように指定

### エンディアン（バイトオーダー）

PLCとPC間でデータを交換する際、バイトオーダー（エンディアン）の違いに注意が必要です。

#### Big-Endian vs Little-Endian

| 方式 | バイト順序 | 使用例 | 値 `0x12345678` の格納順 |
|------|----------|--------|------------------------|
| **Big-Endian** | 上位バイトを先に格納 | ほとんどのPLC、ネットワークプロトコル | `12 34 56 78` |
| **Little-Endian** | 下位バイトを先に格納 | x86/x64 CPU (Intel/AMD)、Raspberry Pi | `78 56 34 12` |

#### メーカー別エンディアン

| メーカー | エンディアン | 備考 |
|---------|------------|------|
| 三菱電機 | Big-Endian | MC Protocolでは16bitワード単位 |
| オムロン | Big-Endian | FINSプロトコルもBig-Endian |
| キーエンス | Big-Endian | Modbus TCPもBig-Endian |
| シーメンス | Big-Endian | S7プロトコルもBig-Endian |

#### Pythonでのバイトオーダー変換

```python
import struct

# Big-Endian（PLC）からLittle-Endian（PC）への変換例
plc_bytes = b'\x12\x34\x56\x78'  # PLCから受信した4バイト

# Big-Endianとして解釈（'>I' = Big-Endian unsigned int）
value_big = struct.unpack('>I', plc_bytes)[0]  # 0x12345678 = 305419896

# Little-Endianとして解釈（'<I' = Little-Endian unsigned int）
value_little = struct.unpack('<I', plc_bytes)[0]  # 0x78563412 = 2018915346

# float32の場合（三菱PLCのD100, D101から読み取った2ワード）
word1 = 0x4048  # D100
word2 = 0xF5C3  # D101
float_bytes = struct.pack('>HH', word1, word2)  # Big-Endianで2ワードをパック
float_value = struct.unpack('>f', float_bytes)[0]  # IEEE 754としてfloat変換
```

**注意：** `pymcprotocol`や`fins`ライブラリは、内部で自動的にエンディアン変換を行うため、通常は手動変換は不要です。

### MC Protocol（三菱電機）

MC Protocol（MELSEC Communication Protocol）は、三菱電機PLCとの通信に使用される産業用プロトコルです。正式名称はSLMP（Seamless Message Protocol）。

#### フレームフォーマット

**3Eフレーム（バイナリ形式）** - 最も一般的

```
[サブヘッダ] [アクセス経路] [要求データ長] [CPU監視タイマ] [コマンド] [サブコマンド] [デバイスコード] [先頭アドレス] [点数]
   2byte       5byte          2byte           2byte        2byte      2byte       1byte         3byte        2byte
```

**4Eフレーム** - シリアル番号付き、大規模システム向け

#### コマンド例

| コマンド | サブコマンド | 機能 |
|---------|------------|------|
| `0x0401` | `0x0000` | ワード単位一括読み出し |
| `0x0401` | `0x0001` | ビット単位一括読み出し |
| `0x1401` | `0x0000` | ワード単位一括書き込み |
| `0x1401` | `0x0001` | ビット単位一括書き込み |

#### デバイスコード

| デバイス | コード | 用途 | 例 |
|---------|-------|------|-----|
| D | `0xA8` | データレジスタ | D0, D100, D9999 |
| M | `0x90` | 内部リレー | M0, M100, M9999 |
| X | `0x9C` | 入力リレー | X0, X1F, X3F |
| Y | `0x9D` | 出力リレー | Y0, Y1F, Y3F |
| B | `0xA0` | リンクリレー | B0, B1FFF |
| W | `0xB4` | リンクレジスタ | W0, W1FFF |

#### pymcprotocolライブラリの使用例

```python
import pymcprotocol

# PLC接続設定
plc = pymcprotocol.Type3E()
plc.connect("192.168.0.10", 5007)

# D100から10ワード読み取り
data = plc.batchread_wordunits("D100", 10)
print(f"D100-D109: {data}")

# D200に値を書き込み
plc.batchwrite_wordunits("D200", [100, 200, 300])

# M0ビットの状態を読み取り
bit_data = plc.batchread_bitunits("M0", 16)
print(f"M0-M15: {bit_data}")

# 接続を閉じる
plc.close()
```

**重要な設定項目：**
- **ポート番号**: デフォルトは5007（バイナリ）、5000（ASCII）
- **タイムアウト**: 通常2〜5秒（ネットワーク環境により調整）
- **再接続**: 通信エラー時は自動再接続を実装すること

### FINSプロトコル（オムロン）

FINS (Factory Interface Network Service) は、オムロンPLCとの通信プロトコルです。Ethernet経由の通信には「FINS/TCP」または「FINS/UDP」を使用します。

#### FINSフレーム構造

```
[FINSヘッダ] [コマンドコード] [メモリエリアコード] [先頭アドレス] [読み取り/書き込みサイズ] [データ]
  10byte        2byte           1byte              3byte              2byte              可変
```

#### コマンドコード

| コマンド | コード | 機能 |
|---------|-------|------|
| Memory Area Read | `0x0101` | メモリエリアの読み取り |
| Memory Area Write | `0x0102` | メモリエリアの書き込み |
| Memory Area Fill | `0x0103` | メモリエリアの一括書き込み |
| Run | `0x0401` | PLCを運転モードに変更 |
| Stop | `0x0402` | PLCを停止モードに変更 |

#### メモリエリアコード

| エリア | コード | 説明 | アドレス範囲 |
|-------|-------|------|------------|
| CIO | `0xB0` | CIOエリア（I/O、内部補助リレー） | CIO 0 ~ CIO 6143 |
| W | `0xB1` | ワークエリア | W0 ~ W511 |
| H | `0xB2` | 保持リレーエリア | H0 ~ H511 |
| D | `0x82` | データメモリ | D0 ~ D32767 |
| EM | `0xA0-0xBF` | 拡張データメモリ | EM0 ~ EM32767 (Bank 0-F) |

#### エラーコード

| コード | 名称 | 説明 |
|-------|------|------|
| `0x0000` | Normal | 正常終了 |
| `0x0101` | Local node error | ローカルノードがエラー状態 |
| `0x0102` | Destination node error | 宛先ノードが存在しない |
| `0x1101` | Command too long | コマンドが長すぎる |
| `0x1103` | Not executable in current mode | 現在のモードで実行不可 |

#### finsライブラリの使用例

```python
from fins.udp import UDPFinsConnection

# PLC接続（オムロンCP1E/CP1L/CP1H等）
fins_instance = UDPFinsConnection()
fins_instance.connect('192.168.0.10')
fins_instance.dest_node_add = 1
fins_instance.srce_node_add = 25

# D100から10ワード読み取り
data = fins_instance.memory_area_read(
    fins.FinsPLCMemoryAreas().DATA_MEMORY,  # D領域
    100,  # 開始アドレス
    10    # 読み取りワード数
)
print(f"D100-D109: {data}")

# CIO100に値を書き込み
fins_instance.memory_area_write(
    fins.FinsPLCMemoryAreas().CIO,
    100,
    [1, 0, 1, 0],  # ON, OFF, ON, OFF
    1  # ビット単位
)

# 接続を閉じる
fins_instance.close()
```

**重要な設定項目：**
- **ポート番号**: デフォルトは9600（UDP/TCP）
- **ノードアドレス**: 送信元・宛先ノードアドレスを正しく設定すること
- **タイムアウト**: 2〜5秒推奨

### Modbus TCP（キーエンス等）

Modbus TCPは、産業用標準プロトコルとして広く採用されており、キーエンスPLCでも使用されています。

#### レジスタタイプ

| レジスタ | 機能コード | アクセス | アドレス範囲（論理） | アドレス範囲（実際） |
|---------|----------|---------|-------------------|-------------------|
| Coil | 0x01（読取）, 0x05（単一書込）, 0x0F（複数書込） | Read/Write | 00001 ~ 09999 | 0 ~ 9998 |
| Discrete Input | 0x02 | Read Only | 10001 ~ 19999 | 0 ~ 9998 |
| Input Register | 0x04 | Read Only | 30001 ~ 39999 | 0 ~ 9998 |
| Holding Register | 0x03（読取）, 0x06（単一書込）, 0x10（複数書込） | Read/Write | 40001 ~ 49999 | 0 ~ 9998 |

**重要な注意点：アドレスマッピング**

Modbusプロトコルでは、**論理アドレス**と**実際のレジスタアドレス**が1つずれています。

例：
- 論理アドレス `40001` = 実際のレジスタアドレス `0`
- 論理アドレス `40100` = 実際のレジスタアドレス `99`

Pythonライブラリ（pymodbus）では実際のアドレス（0始まり）を指定します。

#### pymodbusライブラリの使用例

```python
from pymodbus.client import ModbusTcpClient

# PLC接続
client = ModbusTcpClient('192.168.0.10', port=502)
client.connect()

# Holding Registerの読み取り（アドレス0から10個 = 論理アドレス40001-40010）
result = client.read_holding_registers(address=0, count=10, unit=1)
if not result.isError():
    print(f"Registers 40001-40010: {result.registers}")

# Holding Registerへの書き込み（アドレス100 = 論理アドレス40101）
client.write_register(address=100, value=1234, unit=1)

# 複数レジスタへの書き込み
client.write_registers(address=200, values=[100, 200, 300, 400], unit=1)

# Coilの読み取り（ビット単位）
coil_result = client.read_coils(address=0, count=16, unit=1)
print(f"Coils 00001-00016: {coil_result.bits}")

# 接続を閉じる
client.close()
```

**重要な設定項目：**
- **ポート番号**: 502（標準）
- **Unit ID**: 通常は1（複数のスレーブがある場合は個別に設定）
- **タイムアウト**: 2〜5秒推奨

### python-snap7（シーメンスS7 PLC）

シーメンスS7シリーズPLCとの通信には、`python-snap7`ライブラリを使用します。S7プロトコルは、S7-200/300/400/1200/1500シリーズに対応しています。

#### メモリエリア

| エリア | 説明 | アクセス |
|-------|------|---------|
| DB | データブロック（Data Block） | Read/Write |
| I | 入力（Input） | Read Only |
| Q | 出力（Output） | Read/Write |
| M | メモリ（Merker） | Read/Write |
| T | タイマー | Read/Write |
| C | カウンタ | Read/Write |

#### python-snap7の使用例（未実装・参考用）

```python
import snap7

# PLC接続（例：S7-1200）
plc = snap7.client.Client()
plc.connect('192.168.0.10', 0, 1)  # IP, rack, slot

# DB1の0バイト目から10バイト読み取り
db_data = plc.db_read(db_number=1, start=0, size=10)
print(f"DB1, Byte 0-9: {db_data}")

# DB1の0バイト目に値を書き込み
data_to_write = bytearray([0x01, 0x02, 0x03, 0x04])
plc.db_write(db_number=1, start=0, data=data_to_write)

# Mエリアの読み取り（M0.0から10バイト）
m_data = plc.mb_read(start=0, size=10)
print(f"M0.0-M9.7: {m_data}")

# 接続を閉じる
plc.disconnect()
```

**重要な設定項目：**
- **ポート番号**: 102（S7プロトコル標準）
- **Rack/Slot**: S7-300/400は通常Rack=0, Slot=2、S7-1200/1500はSlot=1
- **接続前の確認**: PLCの設定で「PUT/GET通信許可」が有効になっている必要がある

### セキュリティとアクセス制御

PLC通信は産業制御システム（ICS）の一部であり、セキュリティ対策が重要です。

#### 推奨セキュリティ対策

1. **ネットワークセグメンテーション**
   - PLCネットワークと情報系ネットワークを物理的または論理的に分離
   - VLAN（仮想LAN）の活用
   - ファイアウォールによるアクセス制御

2. **ポート制御**
   - 必要最小限のポートのみ開放
   ```bash
   # iptablesでの例（Raspberry Pi側）
   sudo iptables -A INPUT -p tcp --dport 5007 -s 192.168.0.10 -j ACCEPT  # 三菱PLC
   sudo iptables -A INPUT -p udp --dport 9600 -s 192.168.0.20 -j ACCEPT  # オムロンPLC
   sudo iptables -A INPUT -p tcp --dport 502 -s 192.168.0.30 -j ACCEPT   # Modbus TCP
   sudo iptables -A INPUT -p tcp --dport 102 -s 192.168.0.40 -j ACCEPT   # S7 Protocol
   sudo iptables -A INPUT -j DROP  # その他はすべて拒否
   ```

3. **認証とアクセス制御**
   - PLC側で書き込み保護（パスワード設定）
   - 読み取り専用モードの活用（本番環境では書き込み無効化）
   - IPアドレスホワイトリスト

4. **通信の暗号化**
   - PLCプロトコル自体は暗号化未対応のため、VPN（OpenVPN, WireGuard）を使用
   - TLS/SSLトンネリング（stunnel等）

5. **ログとモニタリング**
   - すべてのPLC通信をログ記録
   - 異常なアクセスパターンの検知（頻度、送信元IP）
   - `raspi_agent/plc_agent.py`でエラー統計を記録

6. **ソフトウェア更新**
   - PLCファームウェアの定期更新
   - Raspberry PiのOS・ライブラリの更新
   - 脆弱性情報（CVE）の監視

#### アクセス制御の実装例（raspi_agent）

```python
# plc_agent.pyでの実装例
ALLOWED_PLC_IPS = ["192.168.0.10", "192.168.0.20", "192.168.0.30"]
READ_ONLY_MODE = True  # 本番環境ではTrue

def validate_plc_ip(ip_address):
    """PLCのIPアドレスをホワイトリストで検証"""
    if ip_address not in ALLOWED_PLC_IPS:
        logging.error(f"不正なPLC IPアドレス: {ip_address}")
        return False
    return True

def read_from_plc(config):
    """PLCからデータを読み取り（読み取り専用）"""
    if not validate_plc_ip(config['plc_ip']):
        return None
    # 読み取り処理...

def write_to_plc(config, data):
    """PLCにデータを書き込み（書き込み保護）"""
    if READ_ONLY_MODE:
        logging.warning("書き込み保護モードが有効です")
        return False
    if not validate_plc_ip(config['plc_ip']):
        return False
    # 書き込み処理...
```

### パフォーマンス最適化

PLC通信のパフォーマンスを最適化するためのベストプラクティス。

#### ポーリング間隔の最適化

| データの種類 | 推奨ポーリング間隔 | 理由 |
|------------|-----------------|------|
| 高速変化データ（回転数、瞬時電流） | 100ms ~ 500ms | リアルタイム性が重要 |
| 中速変化データ（温度、圧力） | 1s ~ 5s | 変化が緩やか |
| 低速変化データ（設定値、累積値） | 10s ~ 60s | ほとんど変化しない |
| 状態監視（エラー、アラーム） | 500ms ~ 2s | 即座に検知が必要 |

**`raspi_agent/plc_agent.py`での設定例:**

```python
POLLING_INTERVALS = {
    'high_speed': 0.5,    # 500ms
    'medium_speed': 2.0,  # 2秒
    'low_speed': 10.0,    # 10秒
    'alarm': 1.0          # 1秒
}

# データ項目ごとに間隔を設定
data_configs = [
    {'address': 'D100', 'type': 'word', 'interval': 'high_speed'},  # 回転数
    {'address': 'D200', 'type': 'float32', 'interval': 'medium_speed'},  # 温度
    {'address': 'D300', 'type': 'dword', 'interval': 'low_speed'},  # 累積値
]
```

#### バッチ読み取りの活用（2025-01実装）

連続したアドレスはバッチ読み取りで一括取得することで、通信回数を削減できます。

**基本的な例:**

```python
# 非効率な例（10回の通信が発生）
for i in range(10):
    value = plc.batchread_wordunits(f"D{100+i}", 1)

# 効率的な例（1回の通信で完了）
values = plc.batchread_wordunits("D100", 10)  # D100-D109を一括取得
```

**実装されたバッチ読み取り最適化:**

`raspi_agent/plc_agent.py`には、連続したwordアドレスを自動的にグループ化してバッチ読み取りを行う機能が実装されています。

**1. 連続アドレス検出関数（lines 298-316, 317-402）**

```python
def extract_address_number(address):
    """アドレス文字列から数値部分を抽出（例: "D100" → 100）"""
    import re
    address_base = address.split('.')[0]
    match = re.search(r'\d+', address_base)
    if match:
        return int(match.group())
    return None

def group_continuous_word_addresses(data_points, device_type='D'):
    """
    連続したwordアドレスをグループ化

    Returns:
        [
            {
                'keys': ['temp1', 'temp2', 'temp3'],
                'start_address': 100,
                'count': 3,
                'settings': [{...}, {...}, {...}]
            },
            ...
        ]
    """
    # wordデータ型のみをフィルタ（dword, float32, bitは除外）
    # アドレス番号でソート
    # 連続アドレスをグループ化
```

**2. 三菱PLC用バッチ読み取り（lines 450-496）**

```python
# 連続したwordアドレスをグループ化
word_groups = group_continuous_word_addresses(data_points, device_type='D')

for group in word_groups:
    if group['count'] == 1:
        # 単独アドレス → 個別読み取り
        raw_values = plc.batchread_wordunits(f"D{group['start_address']}", 1)
    else:
        # 連続アドレス → バッチ読み取り（最適化）
        logger.info(f"🚀 バッチ読み取り: D{group['start_address']}-D{group['start_address'] + group['count'] - 1}")
        raw_values = plc.batchread_wordunits(f"D{group['start_address']}", group['count'])

    # 読み取った値を各項目に割り当て
    for i, key in enumerate(group['keys']):
        data[key] = raw_values[i] / scale if scale > 1 else raw_values[i]
```

**3. オムロンPLC用バッチ読み取り（lines 910-961）**

```python
# 連続したwordアドレスをグループ化（DMアドレス）
word_groups = group_continuous_word_addresses(data_points, device_type='DM')

for group in word_groups:
    if group['count'] == 1:
        addr_bytes = b'\x00' + start_addr.to_bytes(2, byteorder='big')
        mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, 1)
    else:
        # バッチ読み取り（最適化）
        logger.info(f"🚀 バッチ読み取り: DM{start_addr}-DM{start_addr + count - 1}")
        mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, count)

    # 読み取った値を各項目に割り当て
    for i, key in enumerate(group['keys']):
        raw_value = int.from_bytes(mem_area[offset:offset+2], byteorder='big')
        data[key] = raw_value / scale if scale > 1 else raw_value
```

**4. キーエンスPLC用バッチ読み取り（lines 861-909）**

```python
# 連続したwordアドレスをグループ化（DMアドレス）
word_groups = group_continuous_word_addresses(data_points, device_type='DM')

for group in word_groups:
    if group['count'] == 1:
        result = client.read_holding_registers(address=start_addr, count=1, unit=1)
    else:
        # バッチ読み取り（最適化）
        logger.info(f"🚀 バッチ読み取り: DM{start_addr}-DM{start_addr + count - 1}")
        result = client.read_holding_registers(address=start_addr, count=count, unit=1)

    # 読み取った値を各項目に割り当て
    for i, key in enumerate(group['keys']):
        data[key] = result.registers[i] / scale if scale > 1 else result.registers[i]
```

**バッチ読み取りの効果:**

- **通信回数削減**: 連続したN個のアドレスをN回の通信から1回に削減（最大N倍高速化）
- **ネットワーク負荷軽減**: プロトコルオーバーヘッドの削減により、ネットワーク帯域を効率的に使用
- **応答時間短縮**: 特にネットワーク遅延が大きい環境で効果的
- **対象データ型**: wordタイプのみ（bit, dword, float32は個別処理）
- **エラー時の再試行**: バッチ読み取りエラー時は個別に再試行して確実にデータ取得

**例：10個の連続アドレス（D100-D109）の場合**

- 従来: 10回の通信（個別読み取り）
- 最適化後: 1回の通信（バッチ読み取り）
- **効果**: 通信回数90%削減、応答時間最大10倍高速化

#### ネットワーク遅延への対応

1. **タイムアウトの適切な設定**
   ```python
   plc = pymcprotocol.Type3E()
   plc.settimeout(3.0)  # 3秒タイムアウト（デフォルトは10秒）
   ```

2. **再接続ロジックの実装**
   ```python
   def read_with_retry(plc, address, count, max_retries=3):
       for attempt in range(max_retries):
           try:
               return plc.batchread_wordunits(address, count)
           except Exception as e:
               logging.warning(f"読み取り失敗（{attempt+1}/{max_retries}）: {e}")
               if attempt < max_retries - 1:
                   time.sleep(1)  # 1秒待機して再試行
                   plc.close()
                   plc.connect(plc_ip, plc_port)
               else:
                   raise
   ```

3. **コネクションプールの使用**
   - 頻繁に接続・切断を繰り返すとオーバーヘッドが大きい
   - 長時間接続を維持する（キープアライブ）

4. **非同期処理の検討**
   ```python
   import asyncio

   async def read_plc_async(plc, address, count):
       loop = asyncio.get_event_loop()
       result = await loop.run_in_executor(
           None,  # デフォルトのExecutorを使用
           plc.batchread_wordunits,
           address,
           count
       )
       return result
   ```

#### データ圧縮とストレージ最適化

`backend/api/routes.py`で実装されている階層化アーカイブシステムにより、長期データのストレージを最適化：

- **詳細データ（logs）**: 90日間保存、2秒〜5秒間隔
- **日次集計（daily_log_summaries）**: 365日間保存、1日1レコード（99.9%圧縮）
- **月次集計（monthly_log_summaries）**: 永続保存、1ヶ月1レコード（99.99%圧縮）

#### パフォーマンス指標

以下の指標を定期的にモニタリングすること：

- **通信成功率**: 95%以上を維持
- **平均応答時間**: 100ms以下（ローカルネットワーク）
- **エラー率**: 5%以下
- **データ欠損率**: 1%以下

`raspi_agent/plc_agent.py`では、これらの統計を記録し、異常を検知します。

---

## CLAUDE.md 更新ルール

このセクションでは、作業完了時にCLAUDE.mdを更新するためのガイドラインを提供します。

### 更新が必要なケース

以下のいずれかに該当する場合、**作業完了前に必ずCLAUDE.mdを更新**してください：

1. **新しい機能や重要な変更を実装した場合**
   - 新しいAPIエンドポイントの追加
   - データベースモデルの変更
   - 新しいページやコンポーネントの追加
   - プロトコルやライブラリの追加・変更

2. **アーキテクチャやデータフローが変更された場合**
   - システム構成の変更
   - 通信プロトコルの追加・変更
   - データ保存戦略の変更

3. **重要なバグ修正やトラブルシューティング情報を追加した場合**
   - 新しいエラーパターンと解決方法
   - パフォーマンス問題の解決策
   - セキュリティ脆弱性の修正

4. **開発コマンドやツールが追加・変更された場合**
   - 新しいスクリプトの追加
   - ビルドプロセスの変更
   - デプロイ手順の更新

5. **外部依存関係が変更された場合**
   - 新しいPythonライブラリの追加
   - npmパッケージの追加
   - Dockerイメージの更新

6. **ドキュメント化すべき重要な技術知識を得た場合**
   - PLCプロトコルの詳細情報
   - パフォーマンス最適化のベストプラクティス
   - セキュリティ対策の追加

### 更新方法

1. **該当セクションを特定**
   - 変更内容に最も関連するセクションを見つける
   - 新しいセクションが必要な場合は、適切な場所に追加

2. **簡潔かつ具体的に記述**
   - 技術的に正確な情報を記載
   - コード例を含める（必要に応じて）
   - ファイルパスや行番号を明記

3. **日本語で記述**
   - すべての説明は日本語で記述
   - コードコメントも可能な限り日本語

4. **更新履歴を残さない**
   - ドキュメント内に「更新日」や「変更履歴」は不要
   - 最新の状態のみを反映

### 更新例

**良い例：**

```markdown
#### `backend/api/routes.py`
全APIエンドポイントとWebSocketイベントハンドラーを定義：

**REST API**:
- `POST /api/register` - 設備登録（Raspberry Piからの初期登録）
- `POST /api/equipment/<equipment_id>/maintenance` - メンテナンス記録の保存（NEW）
```

**悪い例：**

```markdown
#### `backend/api/routes.py`
- 2025-01-15: メンテナンスAPIを追加しました
- TODO: 後で実装する予定
```
