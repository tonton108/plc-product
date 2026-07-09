# データベース設計

**作成日:** 2025-10-30
**最終更新:** 2025-10-30

## データベース選択

**推奨:** PostgreSQL（本番環境・開発環境共通）

**理由:**
- トランザクション性能が高い
- JSON型のサポート
- 高度なインデックス機能
- 本番環境との一貫性

**フォールバック:** SQLite（DATABASE_URL未設定時）

```python
# backend/app.py:26-28
database_url = f'sqlite:///{db_path}'  # フォールバック用
```

## データモデル

### Equipment（設備情報）

**役割:** Raspberry Piとその接続先PLCの設備情報を管理

```python
class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), unique=True)
    cpu_serial_number = db.Column(db.String(100), unique=True)  # 最優先識別子
    mac_address = db.Column(db.String(100))
    manufacturer = db.Column(db.String(50))  # PLCメーカー
    series = db.Column(db.String(50))       # PLCシリーズ
    ip = db.Column(db.String(50))           # Raspberry PiのIP
    plc_ip = db.Column(db.String(50))       # PLCのIP
    plc_port = db.Column(db.Integer)        # PLCポート
    plc_configs_json = db.Column(db.Text)   # PLCデータ設定（JSON）
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
```

**識別優先順位:**
1. `cpu_serial_number`（Raspberry PiのCPUシリアル番号、不変識別子）
2. `mac_address`（MACアドレス、準不変）
3. `equipment_id`（ユーザー定義ID、可変）

詳細は `_docs/decisions/equipment-identification-strategy.md` を参照。

### PLCDataConfig（PLCデータ項目設定）

**役割:** 各設備が監視するPLCデータ項目の定義

```python
class PLCDataConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50))
    data_type = db.Column(db.String(50))        # 項目名（任意。temperature等の固定名も可）
    address = db.Column(db.String(50))          # D100, M10, etc.
    scale_factor = db.Column(db.Float)          # スケール係数（0.1など）
    plc_data_type = db.Column(db.String(20))    # word, dword, float32, bit
    unit = db.Column(db.String(20))             # ℃, kPa, etc.
    word_order = db.Column(db.String(20))       # high_first / low_first（Phase 2追加）
```

**データ型:**
- `word`: 16ビット整数
- `dword`: 32ビット整数
- `float32`: 32ビット浮動小数点数
- `bit`: ビット

**word_order（Phase 2・マイグレーション j1k2l3m4n5o6）:**
- 32bit値（dword/float32）のワード間順序。既定 `low_first`（三菱MELSEC）
- `low_first`: 先頭アドレス=下位ワード（三菱）/ `high_first`: 先頭アドレス=上位（シーメンス）
- 詳細は `_docs/plc-knowledge/endianness.md`

**data_type（Phase 2）:**
- ホワイトリスト（固定6種）から形式検証（英数字・_・-、1〜50字）に変更し、任意項目名を許可
- `equipment_id` / `timestamp` / `status` は予約語で使用不可

**動的データ項目（Phase 2）:** 固定カラム以外の項目は `Log.data`(JSON) に保存され、
日次/月次集計では `DailyLogSummary.data_summary` / `MonthlyLogSummary.data_summary`(JSON)に
`<項目名>_avg/_max/_min` の形で集約される。

### Log（詳細ログデータ）

**役割:** PLCから収集した詳細データを時系列で保存

```python
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), index=True)
    timestamp = db.Column(db.DateTime, index=True)
    data = db.Column(db.JSON)  # {temperature: 25.5, pressure: 101.3, ...}
```

**保存期間:** 90日間

**インデックス:**
- `idx_logs_timestamp` - タイムスタンプ検索の高速化
- `idx_logs_equipment_timestamp` - 設備別期間検索の高速化

### DailyLogSummary（日次集計データ）

**役割:** 1日単位の統計データを保存（圧縮率99.9%）

```python
class DailyLogSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50))
    date = db.Column(db.Date)
    data_type = db.Column(db.String(50))
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    avg_value = db.Column(db.Float)
    median_value = db.Column(db.Float)
    stddev_value = db.Column(db.Float)
    record_count = db.Column(db.Integer)
```

**保存期間:** 365日間

**インデックス:**
- `idx_daily_summary_equipment_date` - 設備別日付検索の高速化

### MonthlyLogSummary（月次集計データ）

**役割:** 1ヶ月単位の統計データを保存（圧縮率99.99%）

```python
class MonthlyLogSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50))
    year = db.Column(db.Integer)
    month = db.Column(db.Integer)
    data_type = db.Column(db.String(50))
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    avg_value = db.Column(db.Float)
    median_value = db.Column(db.Float)
    stddev_value = db.Column(db.Float)
    record_count = db.Column(db.Integer)
```

**保存期間:** 永続保存

**インデックス:**
- `idx_monthly_summary_equipment_year_month` - 設備別年月検索の高速化

## 階層化アーカイブシステム

**設計思想:** データの鮮度に応じて保存期間と粒度を調整し、ストレージコストを最適化

### 3層構造

```
[詳細データ: 90日間]
  ↓ 日次集計（99.9%圧縮）
[日次集計: 365日間]
  ↓ 月次集計（99.99%圧縮）
[月次集計: 永続保存]
```

### 保存期間の根拠

| データ層 | 保存期間 | 用途 | 根拠 |
|---------|---------|------|------|
| **詳細データ** | 90日間 | リアルタイム監視、詳細分析 | トラブルシューティングに必要な期間 |
| **日次集計** | 365日間 | 週次・月次トレンド分析 | 年間比較に必要な期間 |
| **月次集計** | 永続 | 長期比較、年次計画 | 数年単位の傾向分析に必要 |

### データ圧縮率

**例:** 5秒間隔でデータ収集する場合

- **1日あたりの詳細レコード数:** 17,280件（86,400秒 ÷ 5秒）
- **日次集計レコード数:** 1件/日
- **圧縮率:** 99.994%（17,280件 → 1件）

詳細は `_docs/decisions/data-archiving-strategy.md` を参照。

## データ保存戦略

### 自動クリーンアップ

`backend/api/routes.py`の`DATA_RETENTION_CONFIG`で設定：

```python
DATA_RETENTION_CONFIG = {
    'raw_data_days': 90,          # 詳細データ保持期間
    'daily_data_days': 365,       # 日次集計保持期間
    'cleanup_interval_hours': 24  # クリーンアップ実行間隔
}
```

### 自動スケジューラー

`backend/api/scheduler.py`で以下を自動実行：

1. **24時間間隔でクリーンアップ実行**
   - 90日以上前の詳細ログを削除
   - 365日以上前の日次集計を削除

2. **前日の日次集計を自動作成**
   - 毎日午前0時に実行
   - 前日の詳細データから統計値を計算

3. **前月の月次集計を自動作成**
   - 毎月1日に実行
   - 前月の日次集計から統計値を計算

## クエリ最適化

### 期間別データ選択

短期間は詳細データ、長期間は集計データを自動選択してクエリ性能を最適化：

```python
# routes.py:979-1052 参照
if period in ['1h', '6h', '24h']:
    logs = Log.query.filter(...).all()  # 詳細データ
elif period in ['7d', '30d']:
    summaries = DailyLogSummary.query.filter(...).all()  # 集計データ
```

### インデックス戦略

| インデックス名 | 対象テーブル | 対象カラム | 目的 |
|--------------|------------|-----------|------|
| `idx_logs_timestamp` | logs | timestamp | タイムスタンプ検索 |
| `idx_logs_equipment_timestamp` | logs | equipment_id, timestamp | 設備別期間検索 |
| `idx_daily_summary_equipment_date` | daily_log_summaries | equipment_id, date | 日次集計検索 |
| `idx_monthly_summary_equipment_year_month` | monthly_log_summaries | equipment_id, year, month | 月次集計検索 |

詳細は `_docs/decisions/query-optimization.md` を参照。

## マイグレーション

### 基本コマンド

```bash
cd plc-dashboard/backend

# マイグレーション適用
flask --app manage.py db upgrade

# 新しいマイグレーション作成
flask --app manage.py db migrate -m "説明"

# マイグレーション履歴確認
flask --app manage.py db history
```

### トラブルシューティング

#### Alembicマイグレーション履歴の不整合

**症状:** `flask db upgrade`実行時に`Can't locate revision identified by 'XXXXX'`エラー

**原因:** PostgreSQLの`alembic_version`テーブルの値が、migrationsディレクトリ内の最新リビジョンと一致していない

**解決方法:**

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

## パフォーマンス指標

### 目標値

- **クエリ応答時間:** 100ms以下（1万件のログ検索）
- **書き込みスループット:** 100件/秒以上
- **ストレージ増加率:** 1GB/月以下（10設備の場合）

### モニタリング

```bash
# データベース統計表示
python backend/log_manager.py stats

# テーブルサイズ確認
psql -U plc_user -h localhost -d plc_monitor -c "\dt+"
```

## 関連ドキュメント

- `_docs/decisions/data-archiving-strategy.md` - アーカイブ戦略の詳細
- `_docs/decisions/query-optimization.md` - クエリ最適化の詳細
- `_docs/decisions/equipment-identification-strategy.md` - 設備識別戦略
- `_docs/commands/development.md` - 開発コマンド集

---

**最終更新:** 2025-10-30
