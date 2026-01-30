# バックエンドアーキテクチャ（中央サーバー）

**作成日:** 2025-10-24

## 技術スタック

- **Webフレームワーク:** Flask + Flask-SocketIO
- **ORM:** SQLAlchemy
- **データベース:** PostgreSQL（本番）/ SQLite（開発）
- **リアルタイム通信:** Socket.IO (threading mode)

## 主要ファイル

### `plc-dashboard/backend/app.py`

**役割:** Flaskアプリケーションのファクトリー

**重要な実装:**
```python
socketio.init_app(app, async_mode='threading', cors_allowed_origins="*")
```

詳細は `plc-dashboard/_docs/decisions/socketio-threading-mode.md` を参照。

### `plc-dashboard/backend/api/routes.py`

**役割:** 全APIエンドポイントとWebSocketイベントハンドラー

**REST APIエンドポイント一覧:**

| エンドポイント | メソッド | 説明 | 実装箇所 |
|------------|--------|------|---------|
| `/api/register` | POST | 設備登録（Raspberry Piからの初期登録） | routes.py:388-432 |
| `/api/equipment` | GET | 全設備一覧取得 | routes.py |
| `/api/equipment/<equipment_id>` | GET | 設備基本情報取得 | routes.py |
| `/api/equipment/<equipment_id>` | PUT | 設備基本情報保存 | routes.py |
| `/api/equipment/search` | GET | 設備検索（cpu_serial_number等） | routes.py |
| `/api/equipment/<equipment_id>/plc_configs` | PUT | PLCデータ設定保存 | routes.py |
| `/api/equipment/<equipment_id>/plc_configs` | GET | PLCデータ設定取得 | routes.py |
| `/api/logs` | POST | PLCログデータ保存 + WebSocket配信 | routes.py:874-912 |
| `/api/logs/<equipment_id>/latest` | GET | 最新ログ取得 | routes.py |
| `/api/logs/<equipment_id>/history` | GET | 履歴データ取得 | routes.py |
| `/api/logs/<equipment_id>/history_optimized` | GET | 最適化履歴取得（期間指定） | routes.py:979-1052 |
| `/api/admin/cleanup` | POST | 手動クリーンアップ実行 | routes.py |
| `/api/admin/stats` | GET | データベース統計取得 | routes.py |
| `/api/admin/create_summary` | POST | 集計データ作成 | routes.py |

**Socket.IOイベント:**

| イベント | 方向 | 説明 | 実装箇所 |
|---------|------|------|---------|
| `connect` | Client → Server | WebSocket接続確立 | routes.py |
| `disconnect` | Client → Server | WebSocket接続切断 | routes.py |
| `join_monitoring` | Client → Server | モニタリングルーム参加 | routes.py:1084-1092 |
| `leave_monitoring` | Client → Server | モニタリングルーム退出 | routes.py |
| `get_realtime_status` | Client → Server | リアルタイム状態取得要求 | routes.py |
| `plc_data_update` | Server → Client | PLCデータ更新通知（全設備） | routes.py:874-912 |
| `equipment_data_update` | Server → Client | 設備別データ更新通知 | routes.py:874-912 |

詳細は `plc-dashboard/_docs/architecture/realtime-communication.md` を参照。

### `plc-dashboard/backend/db/models.py`

**役割:** SQLAlchemyモデル定義

**主要モデル:**

#### Equipment（設備情報）

```python
class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), unique=True)
    cpu_serial_number = db.Column(db.String(100), unique=True)  # 最優先識別子
    mac_address = db.Column(db.String(100))
    manufacturer = db.Column(db.String(50))
    plc_ip = db.Column(db.String(50))
    # ...
```

**識別優先順位:**
1. `cpu_serial_number`（最優先・不変）
2. `mac_address`（準不変）
3. `equipment_id`（可変・ユーザー定義）

詳細は `plc-dashboard/_docs/decisions/equipment-identification-strategy.md` を参照。

#### Log（詳細ログ）

```python
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)  # PLCデータ（JSON形式）
```

**保存期間:** 90日間

#### DailyLogSummary（日次集計）

**保存期間:** 365日間

#### MonthlyLogSummary（月次集計）

**保存期間:** 永続保存

詳細は `plc-dashboard/_docs/decisions/data-archiving-strategy.md` を参照。

### `plc-dashboard/backend/api/scheduler.py`

**役割:** データクリーンアップと集計作成のスケジューラー

**自動実行タスク:**

1. **24時間間隔でクリーンアップ実行**
   - 90日以上前の詳細ログ（`logs`テーブル）を削除
   - 365日以上前の日次集計（`daily_log_summaries`テーブル）を削除
   - 実行時刻: 起動後24時間ごと

2. **前日の日次集計を自動作成**
   - 前日の詳細データから統計値（min, max, avg, median, stddev）を計算
   - `daily_log_summaries`テーブルに保存
   - 実行時刻: 毎日午前0時

3. **前月の月次集計を自動作成**
   - 前月の日次集計から統計値を計算
   - `monthly_log_summaries`テーブルに保存
   - 実行時刻: 毎月1日午前0時

**設定:**

```python
# routes.py
DATA_RETENTION_CONFIG = {
    'raw_data_days': 90,          # 詳細データ保持期間
    'daily_data_days': 365,       # 日次集計保持期間
    'cleanup_interval_hours': 24  # クリーンアップ実行間隔
}
```

### `plc-dashboard/backend/log_manager.py`

**役割:** データ保存期間管理とクリーンアップのCLIツール

**主要コマンド:**
```bash
# 統計表示
python log_manager.py stats

# クリーンアップ
python log_manager.py cleanup --days 90

# 日次集計作成
python log_manager.py daily 2025-01-15
```

## 設計原則

### 1. 設備識別

設備更新時は必ず`cpu_serial_number`で既存設備を検索し、`equipment_id`を更新します。

`routes.py:388-432`

```python
equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()
if equipment:
    equipment.equipment_id = equipment_id  # 更新
```

### 2. Socket.IO初期化

必ず`async_mode='threading'`で初期化してGreenletエラーを回避します。

### 3. データ最適化

短期間（1h, 6h, 24h）は詳細データ、長期間（7d, 30d）は集計データを自動選択します。

詳細は `plc-dashboard/_docs/decisions/query-optimization.md` を参照。

## 重要な実装上の注意点

### 変数シャドーイング問題

**問題:** ループ変数に`config`という名前を使用すると、グローバル変数`config`をシャドーイングしてUnboundLocalErrorが発生します。

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

**実装箇所:** `raspi_agent/agent_app.py:236-271`

### PLCデータ設定の保存

PLCデータ設定は`PUT /api/equipment/<equipment_id>/plc_configs`で一括保存されます。既存設定を削除してから新しい設定を挿入するため、トランザクション内で実行してください。

```python
# routes.py
@app.route('/api/equipment/<equipment_id>/plc_configs', methods=['PUT'])
def update_plc_configs(equipment_id):
    # 既存設定を削除
    PLCDataConfig.query.filter_by(equipment_id=equipment_id).delete()

    # 新しい設定を挿入
    for config in configs:
        plc_config = PLCDataConfig(**config)
        db.session.add(plc_config)

    db.session.commit()  # トランザクションをコミット
```

### データ最適化クエリの実装

短期間（1h, 6h, 24h）は詳細データ、長期間（7d, 30d）は集計データを自動的に選択します：

```python
# routes.py:979-1052 参照
if period in ['1h', '6h', '24h']:
    logs = Log.query.filter(...).all()  # 詳細データ
elif period in ['7d', '30d']:
    summaries = DailyLogSummary.query.filter(...).all()  # 集計データ
```

## 関連ドキュメント

- `plc-dashboard/_docs/decisions/socketio-threading-mode.md` - Socket.IO設定
- `plc-dashboard/_docs/decisions/equipment-identification-strategy.md` - 設備識別戦略
- `plc-dashboard/_docs/decisions/data-archiving-strategy.md` - データアーカイブ戦略
- `plc-dashboard/_docs/decisions/query-optimization.md` - クエリ最適化戦略

---

**最終更新:** 2025-10-30
