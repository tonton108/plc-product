# データアーカイブ戦略

**作成日:** 2025-10-24

## 結論

**階層化アーカイブシステム**を採用し、データを3層で管理します。

## 階層構造

### 1. 詳細データ（logs）

**保存期間:** 90日間
**用途:** リアルタイム監視、詳細分析
**データ粒度:** 5秒間隔（設定可能）

```sql
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    equipment_id VARCHAR(50),
    timestamp TIMESTAMP,
    data JSON
);
```

**インデックス:**
- `idx_logs_timestamp` - タイムスタンプ検索高速化
- `idx_logs_equipment_timestamp` - 設備別期間検索高速化

### 2. 日次集計（daily_log_summaries）

**保存期間:** 365日間
**用途:** 週次・月次トレンド分析
**データ粒度:** 1日ごと（平均、最小、最大、合計）

```sql
CREATE TABLE daily_log_summaries (
    id SERIAL PRIMARY KEY,
    equipment_id VARCHAR(50),
    date DATE,
    data_point VARCHAR(100),
    avg_value FLOAT,
    min_value FLOAT,
    max_value FLOAT,
    sum_value FLOAT,
    count INTEGER
);
```

**インデックス:**
- `idx_daily_summary_equipment_date` - 日次集計検索高速化

### 3. 月次集計（monthly_log_summaries）

**保存期間:** 永続保存
**用途:** 長期比較、年次レポート
**データ粒度:** 1ヶ月ごと（平均、最小、最大、合計）

```sql
CREATE TABLE monthly_log_summaries (
    id SERIAL PRIMARY KEY,
    equipment_id VARCHAR(50),
    year INTEGER,
    month INTEGER,
    data_point VARCHAR(100),
    avg_value FLOAT,
    min_value FLOAT,
    max_value FLOAT,
    sum_value FLOAT,
    count INTEGER
);
```

**インデックス:**
- `idx_monthly_summary_equipment_year_month` - 月次集計検索高速化

## 自動スケジューラー

`plc-dashboard/backend/api/scheduler.py`

### 1. 古いログの削除

**頻度:** 24時間ごと
**処理:** 90日以上前の詳細ログを削除

```python
def cleanup_old_logs():
    cutoff_date = datetime.now() - timedelta(days=90)
    Log.query.filter(Log.timestamp < cutoff_date).delete()
```

### 2. 日次集計作成

**頻度:** 毎日0時
**処理:** 前日の日次集計を自動作成

```python
def create_daily_summary(date):
    # 前日のログデータを集計
    logs = Log.query.filter(
        func.date(Log.timestamp) == date
    ).all()
    # 平均、最小、最大、合計を計算
    summary = DailyLogSummary(...)
    db.session.add(summary)
```

### 3. 月次集計作成

**頻度:** 毎月1日0時
**処理:** 前月の月次集計を自動作成

```python
def create_monthly_summary(year, month):
    # 前月の日次集計を集計
    summaries = DailyLogSummary.query.filter(
        extract('year', DailyLogSummary.date) == year,
        extract('month', DailyLogSummary.date) == month
    ).all()
    # 月次集計を作成
    monthly = MonthlyLogSummary(...)
    db.session.add(monthly)
```

## 手動実行

`plc-dashboard/backend/log_manager.py`

```bash
# 統計表示
python log_manager.py stats

# 90日以上前のログを削除
python log_manager.py cleanup --days 90

# 特定日の日次集計を作成
python log_manager.py daily 2025-01-15

# 特定月の月次集計を作成
python log_manager.py monthly 2025 1
```

## パフォーマンス効果

### ストレージ削減

- **中期データ（日次集計）:** 99.9%圧縮（2400件→1件/日）
- **長期データ（月次集計）:** 99.99%圧縮（72,000件→12件/年）

### クエリ速度向上

- **短期データ（1h, 6h, 24h）:** 詳細データから直接取得
- **中期データ（7d, 30d）:** 日次集計から取得（50-150倍高速化）
- **長期データ（1年以上）:** 月次集計から取得

詳細は `_docs/decisions/query-optimization.md` を参照。

## 判断理由

### なぜ階層化アーカイブなのか

**問題:**
- すべてのデータを永続保存すると、ストレージが膨大
- 古いデータのクエリが遅い
- データベースメンテナンスが困難

**解決策:**
- 詳細データは90日で削除（リアルタイム監視に十分）
- 日次・月次集計で長期トレンドを保持
- ストレージ削減とクエリ速度向上を両立

### なぜ90日間なのか

**根拠:**
- 工場の月次レポートサイクル（3ヶ月分）
- トラブルシューティング期間（過去2-3ヶ月）
- ストレージコストとのバランス

## 関連ドキュメント

- `_docs/decisions/query-optimization.md` - クエリ最適化戦略
- `_docs/decisions/performance-optimization.md` - パフォーマンス最適化
- `_docs/architecture/backend.md` - バックエンドアーキテクチャ

---

**最終更新:** 2025-10-24
