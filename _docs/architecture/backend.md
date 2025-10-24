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

詳細は `_docs/decisions/socketio-threading-mode.md` を参照。

### `plc-dashboard/backend/api/routes.py`

**役割:** 全APIエンドポイントとWebSocketイベントハンドラー

**主要エンドポイント:**

| エンドポイント | メソッド | 説明 |
|------------|--------|------|
| `/api/register` | POST | Raspberry Piからの設備登録 |
| `/api/logs` | POST | PLCログデータ保存 + WebSocket配信 |
| `/api/logs/<equipment_id>/history_optimized` | GET | 最適化履歴取得 |
| `/api/equipment` | GET | 設備一覧取得 |
| `/api/equipment/search` | GET | 設備検索（cpu_serial_number等） |

**Socket.IOイベント:**

| イベント | 方向 | 説明 |
|---------|------|------|
| `connect` | Client → Server | WebSocket接続確立 |
| `join_monitoring` | Client → Server | モニタリングルーム参加 |
| `plc_data_update` | Server → Client | PLCデータ更新通知 |
| `equipment_data_update` | Server → Client | 設備別データ更新通知 |

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

詳細は `_docs/decisions/equipment-identification-strategy.md` を参照。

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

詳細は `_docs/decisions/data-archiving-strategy.md` を参照。

### `plc-dashboard/backend/api/scheduler.py`

**役割:** データクリーンアップと集計作成のスケジューラー

**自動実行タスク:**
- 24時間間隔で90日以上古いログを削除
- 前日の日次集計を自動作成
- 月初に前月の月次集計を自動作成

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

詳細は `_docs/decisions/query-optimization.md` を参照。

## 関連ドキュメント

- `_docs/decisions/socketio-threading-mode.md` - Socket.IO設定
- `_docs/decisions/equipment-identification-strategy.md` - 設備識別戦略
- `_docs/decisions/data-archiving-strategy.md` - データアーカイブ戦略
- `_docs/decisions/query-optimization.md` - クエリ最適化戦略

---

**最終更新:** 2025-10-24
