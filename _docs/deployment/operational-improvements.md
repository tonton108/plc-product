# 運用改善実装ガイド

**作成日:** 2025-01-24

## 概要

このドキュメントでは、PLC監視システムの運用上の懸念点に対する改善実装をまとめています。

## 実装済み改善項目

### 1. セキュリティ強化 🔒

#### デフォルトパスワードのチェック機能

**実装箇所:**
- `plc-dashboard/scripts/check_security.py`
- `plc-dashboard/backend/manage.py`（起動時に自動チェック）

**機能:**
- 本番環境（`FLASK_ENV=production`）起動時に自動でセキュリティチェック
- デフォルトパスワードを検出したら起動を中止
- パスワード強度の検証（最低12文字）
- CORS設定の確認

**使用方法:**
```bash
# 手動でセキュリティチェックを実行
cd plc-dashboard
python scripts/check_security.py

# 本番環境で起動（自動チェックあり）
export FLASK_ENV=production
python backend/manage.py
```

**チェック項目:**
- `SECRET_KEY`: デフォルト値でないか
- `POSTGRES_PASSWORD`: デフォルト値でないか、12文字以上か
- `ADMIN_PASSWORD_HASH`: デフォルトハッシュ値でないか
- `CORS_ORIGINS`: ワイルドカード（`*`）使用の警告
- `FLASK_ENV`: 本番環境で`production`になっているか

### 2. データバックアップ・リストア機能 💾

#### 自動バックアップスクリプト

**実装箇所:**
- `plc-dashboard/scripts/backup_database.sh`
- `plc-dashboard/scripts/restore_database.sh`
- `_docs/deployment/backup-restore.md`（詳細ドキュメント）

**機能:**
- PostgreSQLの自動バックアップ（pg_dump）
- gzip圧縮による容量削減
- 古いバックアップの自動削除（デフォルト7日分保持）
- バックアップからのリストア機能

**使用方法:**
```bash
# 手動バックアップ
cd plc-dashboard
chmod +x scripts/backup_database.sh
./scripts/backup_database.sh

# 自動バックアップ（cron設定）
crontab -e
# 毎日午前2時に実行
0 2 * * * /path/to/plc-dashboard/scripts/backup_database.sh >> /var/log/plc_backup.log 2>&1

# リストア（最新のバックアップ）
chmod +x scripts/restore_database.sh
./scripts/restore_database.sh

# リストア（特定のバックアップ）
./scripts/restore_database.sh backups/plc_monitor_20250124_020000.sql.gz
```

**バックアップファイル:**
- 保存先: `plc-dashboard/backups/`
- ファイル名: `plc_monitor_YYYYMMDD_HHMMSS.sql.gz`
- 保持期間: 7日（`RETENTION_DAYS`で変更可能）

### 3. Nuxt UI認証機能 🔐

#### ログイン機能の実装

**実装箇所:**
- `plc-dashboard/pages/login.vue`（ログインページ）
- `plc-dashboard/middleware/auth.ts`（認証ミドルウェア）
- `plc-dashboard/pages/index.vue`（認証適用済み）
- `plc-dashboard/pages/monitoring/[id].vue`（認証適用済み）

**機能:**
- シンプルなログイン画面
- localStorage基づくセッション管理
- 未認証ユーザーのリダイレクト
- ログアウト機能

**デフォルトユーザー:**
| ユーザー名 | パスワード | 用途 |
|-----------|-----------|------|
| `admin` | `plc-monitor-2025` | 管理者 |
| `operator` | `operator-2025` | オペレーター |

**⚠️ 重要:** 本番環境では必ずデフォルトパスワードを変更してください。

**カスタマイズ方法:**
```javascript
// plc-dashboard/pages/login.vue の DEFAULT_USERS を編集
const DEFAULT_USERS = [
  { username: 'admin', password: 'your-strong-password' },
  { username: 'operator', password: 'operator-password' }
]
```

**将来の拡張:**
- バックエンドAPI認証への移行（`/api/auth/login`）
- JWT トークンベース認証
- 権限管理（管理者 vs 読み取り専用）

### 4. システム監視（ヘルスチェック）📊

#### ヘルスチェックエンドポイント

**実装箇所:**
- `plc-dashboard/backend/api/routes.py` - `/api/health`

**機能:**
- システム稼働状態の確認
- データベース接続チェック
- 登録設備数の取得
- 最新ログデータの確認（1時間以内か）
- アプリケーションバージョン情報

**使用方法:**
```bash
# ヘルスチェック実行
curl http://localhost:5000/api/health

# レスポンス例（正常時）
{
  "status": "healthy",
  "timestamp": "2025-01-24T10:30:00.123456",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "equipment": {
      "status": "healthy",
      "count": 5
    },
    "latest_log": {
      "status": "healthy",
      "timestamp": "2025-01-24T10:25:00.000000",
      "equipment_id": "DEMO_001",
      "age_seconds": 300
    }
  },
  "system": {
    "version": "1.0.0",
    "environment": "production"
  }
}
```

**ステータスコード:**
- `200 OK`: すべてのチェックが正常
- `503 Service Unavailable`: いずれかのチェックが異常

**監視ツールとの連携:**
```bash
# Nagios/Icingaでの監視例
check_http -H localhost -p 5000 -u /api/health -s "healthy"

# Prometheusでの監視例（blackbox_exporter）
curl http://localhost:5000/api/health | jq -r '.status'
```

### 5. ログローテーション設定 📁

#### Raspberry Piエージェント（自動実行）

**実装箇所:**
- `plc-dashboard/raspi_agent/log_rotator.py`（ローテーション処理）
- `plc-dashboard/raspi_agent/agent_app.py:897-903`（起動時に自動実行）

**機能:**
- ✅ **追加設定不要** - エージェント起動時に自動実行
- ✅ ログファイル1MB以上で自動ローテーション
- ✅ gzip圧縮（容量90%削減）
- ✅ 7日分保持、古いログは自動削除

**使用方法:**
```bash
# 設定不要！agent_app.py を起動するだけでOK
python3 agent_app.py

# 起動時の出力例:
# 🚀 PLC UI システム起動中...
# 📁 ログローテーションチェック開始
# 🔄 ログローテーション開始: plc_agent.log
#    ✅ ローテーション完了: plc_agent.log
#    ✅ 圧縮完了: 89.5% 削減
#    🗑️  2 個の古いログを削除
```

**詳細:** `_docs/deployment/log-rotation.md` を参照

#### Flask中央サーバー（オプション）

**実装箇所:**
- `plc-dashboard/backend/logrotate.conf`（従来のlogrotate設定）

**インストール:**
```bash
sudo cp plc-dashboard/backend/logrotate.conf /etc/logrotate.d/plc_dashboard
sudo chmod 644 /etc/logrotate.d/plc_dashboard
```

**対象ログファイル:**
- `/var/log/plc_dashboard/flask.log` - Flaskアプリケーションログ（30日保持）
- `/var/log/postgresql/postgresql-*.log` - PostgreSQLログ（4週保持、オプション）
- `/var/log/nginx/plc_dashboard_*.log` - Nginxログ（オプション）

### 6. ローカルバッファ保持期間の延長 ⏱️

#### 変更内容

**実装箇所:**
- `plc-dashboard/raspi_agent/db_utils.py:248`

**変更:**
```python
# 変更前
def cleanup_buffer(self, days=7):

# 変更後
def cleanup_buffer(self, days=30):
```

**効果:**
- ネットワーク障害時のデータ保全期間: 7日 → 30日
- 年末年始等の長期休暇中のデータロスリスク軽減
- ディスク使用量の増加: 約4倍（監視が必要）

**ディスク使用量の目安:**
| PLC台数 | 収集間隔 | 30日分の容量（推定） |
|---------|---------|-------------------|
| 1台 | 5秒 | 約50-100MB |
| 5台 | 5秒 | 約250-500MB |
| 10台 | 5秒 | 約500MB-1GB |

**ディスク使用量の監視:**
```bash
# SQLiteデータベースサイズ確認
du -h plc-dashboard/raspi_agent/local_buffer.db

# ディスク使用量確認
df -h
```

## 運用チェックリスト

### デプロイ前の確認事項

- [ ] デフォルトパスワードを変更（SECRET_KEY, POSTGRES_PASSWORD, ADMIN_PASSWORD_HASH）
- [ ] セキュリティチェックスクリプトを実行して合格
- [ ] バックアップスクリプトをcronに登録
- [ ] ログローテーションが起動時に自動実行されることを確認（Raspberry Piエージェント - 設定不要）
- [ ] ヘルスチェックエンドポイントが正常に動作することを確認
- [ ] ログイン認証が正常に機能することを確認
- [ ] ローカルバッファの保持期間が30日に設定されていることを確認

### 定期メンテナンス

**日次:**
- [ ] ヘルスチェックエンドポイントの確認（`/api/health`）
- [ ] バックアップファイルの確認（自動実行）

**週次:**
- [ ] ログファイルのサイズ確認
- [ ] ディスク使用量の確認
- [ ] バックアップからのリストアテスト（月1回推奨）

**月次:**
- [ ] セキュリティチェックの実行
- [ ] ログファイルの確認とアーカイブ
- [ ] データベース統計の確認（`GET /api/admin/stats`）

### トラブルシューティング

**ヘルスチェックが失敗する場合:**
```bash
# 詳細を確認
curl http://localhost:5000/api/health | jq

# データベース接続確認
psql -U plc_user -h localhost -d plc_monitor -c "SELECT version();"

# 最新ログ確認
psql -U plc_user -h localhost -d plc_monitor -c "SELECT equipment_id, timestamp FROM logs ORDER BY timestamp DESC LIMIT 5;"
```

**バックアップが失敗する場合:**
```bash
# PostgreSQL接続確認
pg_isready -h localhost -p 5432

# 環境変数確認
grep POSTGRES plc-dashboard/.env

# 手動バックアップ実行（デバッグ）
cd plc-dashboard
bash -x scripts/backup_database.sh
```

**ログインできない場合:**
```bash
# ブラウザのlocalStorageをクリア
# 開発者コンソールで実行:
localStorage.clear()

# デフォルトユーザーを確認
cat plc-dashboard/pages/login.vue | grep DEFAULT_USERS -A 5
```

## 関連ドキュメント

- `_docs/deployment/backup-restore.md` - バックアップ・リストア詳細ガイド
- `_docs/deployment/environment-variables.md` - 環境変数設定
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティング
- `_docs/IMPLEMENTATION_CHECKLIST.md` - 実装状況チェックリスト

---

**最終更新:** 2025-01-24
