# DB設計レビュー - PLC設備モニタリングシステム

**作成日:** 2025-10-29
**レビュー対象:** `plc-dashboard/backend/db/models.py`

## 📊 総合評価: **8.5/10 (優秀)**

現在のDB設計は、PLCモニタリングシステムの要件を概ね満たしており、パフォーマンスとスケーラビリティのバランスが取れた設計になっています。

---

## ✅ 優れている点

### 1. 階層化アーカイブ戦略 ⭐⭐⭐⭐⭐

**設計:**
- **Log (詳細データ)**: 90日間保存
- **DailyLogSummary (日次集計)**: 365日間保存
- **MonthlyLogSummary (月次集計)**: 永続保存

**評価:**
- ストレージコストとクエリ速度を両立
- データ粒度と保存期間のバランスが最適
- 工場の運用サイクル（3ヶ月）に適合

**根拠:** `plc-dashboard/_docs/decisions/data-archiving-strategy.md`

### 2. 設備識別戦略 ⭐⭐⭐⭐⭐

**優先順位:**
1. `cpu_serial_number` (不変・ハードウェアレベル)
2. `mac_address` (準不変)
3. `equipment_id` (可変・ユーザー定義)

**評価:**
- ハードウェア交換や再設定に強い設計
- SD カード交換でも設備を維持可能
- ユーザーフレンドリーなequipment_idも併用

**根拠:** `plc-dashboard/_docs/decisions/equipment-identification-strategy.md`

### 3. 動的データ対応 (JSON型カラム) ⭐⭐⭐⭐⭐

```sql
-- Log テーブル
data JSON  -- 動的なPLCデータ項目

-- DailyLogSummary / MonthlyLogSummary テーブル
data_summary JSON  -- 動的な集計データ
```

**評価:**
- PLCごとに異なるデータ項目に対応
- スキーマ変更なしで新しいセンサー追加可能
- 後方互換性を維持（既存カラムも保持）

**利点:**
- 製造ラインごとのカスタマイズが容易
- マイグレーション不要で運用変更に対応
- 将来の拡張性が高い

### 4. PLCDataConfig テーブルの柔軟性 ⭐⭐⭐⭐

```python
class PLCDataConfig(db.Model):
    name = db.Column(db.String(100))           # ユーザー定義項目名
    icon = db.Column(db.String(10))            # 絵文字アイコン
    unit = db.Column(db.String(20))            # 単位
    plc_data_type = db.Column(db.String(20))   # bit, word, dword, float32
    address = db.Column(db.String(20))         # PLCアドレス
    scale_factor = db.Column(db.Integer)       # 倍率
```

**評価:**
- 動的なPLC項目設定に完全対応
- UI表示に必要な情報を完備
- スケールファクターで実数値への変換に対応

### 5. 複合インデックス戦略 ⭐⭐⭐⭐

**想定されるインデックス:**
```sql
-- logs テーブル
CREATE INDEX idx_logs_equipment_timestamp
ON logs(equipment_id, timestamp);

-- daily_log_summaries テーブル
CREATE INDEX idx_daily_summary_equipment_date
ON daily_log_summaries(equipment_id, date);

-- monthly_log_summaries テーブル
CREATE INDEX idx_monthly_summary_equipment_year_month
ON monthly_log_summaries(equipment_id, year, month);
```

**評価:**
- 典型的なクエリパターンに最適化
- 期間別検索が高速（500-1000倍高速化）

**根拠:** `plc-dashboard/_docs/decisions/query-optimization.md`

### 6. リレーションシップとカスケード削除 ⭐⭐⭐⭐

```python
# Equipment モデル
plc_configs = db.relationship('PLCDataConfig',
                               backref='equipment',
                               lazy=True,
                               cascade='all, delete-orphan')
```

**評価:**
- 設備削除時にPLC設定も自動削除
- データ整合性を維持
- orphan（孤立レコード）を防止

---

## ⚠️ 改善が必要な点

### 1. インデックスの不完全な実装 ⚠️⚠️⚠️

**問題:**
マイグレーションファイル `193f267a3e72` を確認したところ、**インデックスが作成されていません**。

```python
# 193f267a3e72_ログテーブル最適化とインデックス追加.py
def upgrade():
    op.create_table('daily_log_summaries', ...)
    op.create_table('monthly_log_summaries', ...)
    # ❌ インデックス作成のコードがない！
```

**影響:**
- クエリ最適化の効果が発揮されない
- 期間検索が遅い（特にデータ量が増えると顕著）
- ドキュメント（query-optimization.md）と実装が乖離

**推奨対応:**
新しいマイグレーションファイルでインデックスを追加：

```python
def upgrade():
    # logs テーブル
    op.create_index('idx_logs_timestamp', 'logs', ['timestamp'])
    op.create_index('idx_logs_equipment_timestamp', 'logs',
                    ['equipment_id', 'timestamp'])

    # daily_log_summaries テーブル
    op.create_index('idx_daily_summary_equipment_date',
                    'daily_log_summaries',
                    ['equipment_id', 'date'])

    # monthly_log_summaries テーブル
    op.create_index('idx_monthly_summary_equipment_year_month',
                    'monthly_log_summaries',
                    ['equipment_id', 'year', 'month'])
```

### 2. Equipment.equipment_id の外部キー ⚠️⚠️

**問題:**
`Log`, `DailyLogSummary`, `MonthlyLogSummary` テーブルは `equipment_id` を `Integer` 型の外部キー（`equipments.id`）として参照していますが、実際のクエリでは `Equipment.equipment_id` (String型) を使用している可能性があります。

```python
# models.py の現在の設計
class Log(db.Model):
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'))
    # ↑ equipments.id を参照（正しい）

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), unique=True)
    # equipment_id は String型のユーザー定義ID
```

**評価:**
- ✅ 外部キー設計は正しい（`equipments.id` を参照）
- ⚠️ ただし、APIレスポンスやフロントエンドでは `equipment_id` (String) を使用
- ⚠️ JOIN時に注意が必要

**推奨:**
現在の設計は正しいですが、コードレビュー時に以下を確認：
- APIで `equipment_id` (String) を使ってログを取得する際、正しく `equipments.id` (Integer) に変換しているか
- フロントエンドに返すJSONで適切にequipment_id (String) を返しているか

### 3. タイムスタンプのタイムゾーン ⚠️

**問題:**
```python
timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

**懸念:**
- `datetime.utcnow` は naive datetime (タイムゾーン情報なし)
- PostgreSQLの `TIMESTAMP WITHOUT TIME ZONE` 型として保存される
- 異なるタイムゾーンでの運用時に混乱の可能性

**推奨対応:**
```python
from datetime import datetime, timezone

timestamp = db.Column(db.DateTime(timezone=True),
                     default=lambda: datetime.now(timezone.utc))
```

または、PostgreSQL側で：
```sql
ALTER TABLE logs ALTER COLUMN timestamp TYPE TIMESTAMP WITH TIME ZONE;
```

### 4. equipment_id の命名の混乱 ⚠️

**問題:**
`equipment_id` という名前が2つの異なる意味で使われています：

1. **Equipment.equipment_id** (String型): ユーザー定義ID（例: "LINE_A_001"）
2. **Log.equipment_id** (Integer型): Equipment.id への外部キー

**推奨:**
可読性のため、外部キーを `equipment_ref_id` または `equipment_fk` にリネーム：

```python
class Log(db.Model):
    equipment_ref_id = db.Column(db.Integer,
                                  db.ForeignKey('equipments.id'))
```

ただし、**既存のマイグレーションとの互換性を考慮すると、現状維持も妥当**です。

### 5. PLCDataConfig のユニーク制約 ⚠️

**現在の設計:**
```python
# 27e1e8566303 マイグレーションで削除
batch_op.drop_constraint('uq_equipment_data_type', type_='unique')
```

**懸念:**
- 同じ設備で同じdata_typeの項目を複数登録できてしまう
- 例: equipment_id=1, data_type="temperature" が2つ登録可能

**推奨:**
動的項目対応のため制約を削除したのは正しい判断ですが、以下の対策を検討：

**対策案1: 複合ユニーク制約（name + address）**
```python
__table_args__ = (
    db.UniqueConstraint('equipment_id', 'name', 'address',
                       name='uq_equipment_name_address'),
)
```

**対策案2: アプリケーション層でバリデーション**
```python
# routes.py で重複チェック
existing = PLCDataConfig.query.filter_by(
    equipment_id=equipment_id,
    name=name
).first()
if existing:
    return jsonify({"error": "この項目名は既に存在します"}), 400
```

### 6. MonthlyLogSummary の pressure_max/min 欠落 ⚠️

**問題:**
```python
class DailyLogSummary:
    pressure_max = db.Column(db.Float())
    pressure_min = db.Column(db.Float())

class MonthlyLogSummary:
    pressure_avg = db.Column(db.Float())
    # ❌ pressure_max, pressure_min がない
```

**影響:**
- 月次レポートで圧力の最大・最小値が取得できない
- 日次集計と月次集計でデータ粒度が不一致

**推奨:**
マイグレーションで追加：
```python
def upgrade():
    with op.batch_alter_table('monthly_log_summaries') as batch_op:
        batch_op.add_column(sa.Column('pressure_max', sa.Float()))
        batch_op.add_column('pressure_min', sa.Float()))
```

---

## 🔍 追加検討事項

### 1. 監査ログ（Audit Log）の検討

**現状:**
データの変更履歴が記録されていない

**検討すべきケース:**
- 設備設定の変更履歴（誰がいつ何を変更したか）
- PLC設定の変更履歴
- ユーザーアクション（ログイン、設定変更、データエクスポート）

**推奨テーブル:**
```python
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50))
    action = db.Column(db.String(50))  # 'CREATE', 'UPDATE', 'DELETE'
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    old_value = db.Column(db.JSON)
    new_value = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
```

**優先度:** 中（セキュリティ要件による）

### 2. アラート・通知テーブルの検討

**現状:**
アラート設定がデータベースに保存されていない

**推奨テーブル:**
```python
class AlertRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'))
    data_type = db.Column(db.String(50))  # 'temperature', 'current'等
    condition = db.Column(db.String(20))  # '>', '<', '>=', '<='
    threshold = db.Column(db.Float)
    enabled = db.Column(db.Boolean, default=True)

class AlertHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'))
    alert_rule_id = db.Column(db.Integer, db.ForeignKey('alert_rules.id'))
    value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.String(50))
    acknowledged_at = db.Column(db.DateTime)
```

**優先度:** 高（アラート機能が必要な場合）

### 3. ダウンタイム記録テーブル

**推奨テーブル:**
```python
class Downtime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipments.id'))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)  # 計算値
    reason = db.Column(db.String(200))  # 'maintenance', 'error', 'planned'
    notes = db.Column(db.Text)
```

**用途:**
- 設備稼働率（OEE）の計算
- メンテナンス記録
- ダウンタイム分析

**優先度:** 中

### 4. ユーザー管理テーブル

**現状:**
ユーザー認証がハードコードされている可能性

**推奨テーブル:**
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20))  # 'admin', 'operator', 'viewer'
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
```

**優先度:** 高（セキュリティ要件による）

---

## 📈 スケーラビリティ評価

### データ量見積もり（1設備あたり）

| 期間 | ログ件数 | ストレージ | 備考 |
|-----|---------|----------|------|
| 1日 | 17,280件 | 8.6MB | 5秒間隔 |
| 90日 | 1,555,200件 | 775MB | 詳細ログ保存期間 |
| 1年（日次） | 365件 | 73KB | 日次集計 |
| 10年（月次） | 120件 | 24KB | 月次集計 |

**10設備・5年間の総容量:**
- 詳細ログ（90日分）: 7.8GB
- 日次集計（5年分）: 3.7MB
- 月次集計（5年分）: 1.2MB
- **合計**: 約8GB

**評価:** スケーラビリティは十分。100設備でも80GBで管理可能。

### クエリパフォーマンス（PostgreSQL前提）

| 操作 | 件数 | 予想時間 | 評価 |
|------|------|---------|------|
| 最新データ取得 | 1件 | <10ms | ⭐⭐⭐⭐⭐ |
| 24時間履歴 | 17,280件 | 100-500ms | ⭐⭐⭐⭐ |
| 7日間履歴（集計） | 7件 | <20ms | ⭐⭐⭐⭐⭐ |
| 30日間履歴（集計） | 30件 | <50ms | ⭐⭐⭐⭐⭐ |
| 設備一覧取得 | 10-100件 | <50ms | ⭐⭐⭐⭐⭐ |

---

## 🎯 推奨アクションプラン

### 🔴 優先度: 高（即座に対応）

1. **インデックスの追加**
   - `idx_logs_equipment_timestamp`
   - `idx_daily_summary_equipment_date`
   - `idx_monthly_summary_equipment_year_month`
   - **影響:** クエリ速度が500-1000倍向上

2. **MonthlyLogSummary への pressure_max/min 追加**
   - データ整合性のため
   - **影響:** 月次レポートの完全性

### 🟡 優先度: 中（計画的に対応）

3. **タイムゾーン対応**
   - `TIMESTAMP WITH TIME ZONE` への変更
   - **影響:** 国際展開時の問題回避

4. **ユーザー管理テーブルの追加**
   - セキュリティ強化
   - **影響:** 監査要件への対応

5. **アラートテーブルの追加**
   - 機能拡張
   - **影響:** 実用性向上

### 🟢 優先度: 低（将来的に検討）

6. **監査ログの追加**
   - コンプライアンス対応
   - **影響:** セキュリティ監査への対応

7. **ダウンタイム記録テーブルの追加**
   - OEE計算のため
   - **影響:** 生産性分析の向上

---

## 📝 まとめ

### 総合評価: 8.5/10

**強み:**
- ✅ 階層化アーカイブ戦略が優秀
- ✅ 設備識別戦略が堅牢
- ✅ 動的データ対応（JSON型）で拡張性が高い
- ✅ スケーラビリティに問題なし

**改善点:**
- ⚠️ インデックスが未実装（最重要）
- ⚠️ MonthlyLogSummary のカラム不足
- ⚠️ タイムゾーン対応が不十分

**推奨:**
まず**インデックスの追加**を最優先で実施してください。これだけでパフォーマンスが劇的に向上します。その他の改善は、プロジェクトの要件に応じて順次対応で問題ありません。

---

**レビュー実施者:** Claude (Sonnet 4.5)
**レビュー日:** 2025-10-29
**次回レビュー推奨日:** 2026-01-29（3ヶ月後）
