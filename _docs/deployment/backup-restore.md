# バックアップ・リストアガイド

**作成日:** 2025-01-24

## 概要

このドキュメントでは、PLC監視システムのデータベースバックアップとリストアの手順を説明します。

## バックアップ戦略

### 自動バックアップ（推奨）

**頻度:** 毎日午前2時（cron）

**保持期間:** 7日分（デフォルト）

**バックアップ先:** `plc-dashboard/backups/`

### 手動バックアップ

必要に応じて手動でバックアップを実行できます。

## バックアップの実行

### 1. スクリプトに実行権限を付与

```bash
chmod +x plc-dashboard/scripts/backup_database.sh
chmod +x plc-dashboard/scripts/restore_database.sh
```

### 2. 手動バックアップの実行

```bash
cd plc-dashboard
./scripts/backup_database.sh
```

**実行結果:**
```
==========================================
📦 PostgreSQLバックアップを開始します
==========================================
データベース: plc_monitor
ホスト: localhost:5432
バックアップ先: /path/to/plc-dashboard/backups/plc_monitor_20250124_020000.sql.gz

⏳ バックアップ中...
✅ バックアップ完了: 12M
⏳ 圧縮中...
✅ 圧縮完了: 2.5M

🗑️  古いバックアップファイルを削除中（7日以上前）...
✅ 3 個のファイルを削除しました

📋 現在のバックアップファイル:
-rw-r--r-- 1 user user 2.5M Jan 24 02:00 plc_monitor_20250124_020000.sql.gz
-rw-r--r-- 1 user user 2.4M Jan 23 02:00 plc_monitor_20250123_020000.sql.gz
...

==========================================
✅ バックアップが正常に完了しました
==========================================
```

### 3. 自動バックアップの設定（cron）

#### Linux/Raspberry Pi

```bash
# cron編集
crontab -e

# 以下を追加（毎日午前2時に実行）
0 2 * * * /path/to/plc-dashboard/scripts/backup_database.sh >> /var/log/plc_backup.log 2>&1
```

#### Windows（タスクスケジューラ）

1. タスクスケジューラを開く
2. 「基本タスクの作成」をクリック
3. 名前: `PLC Database Backup`
4. トリガー: 毎日午前2時
5. 操作: `bash.exe`
6. 引数: `/path/to/plc-dashboard/scripts/backup_database.sh`

## リストアの実行

### 1. 最新のバックアップからリストア

```bash
cd plc-dashboard
./scripts/restore_database.sh
```

**実行結果:**
```
==========================================
📦 PostgreSQLリストアを開始します
==========================================
データベース: plc_monitor
ホスト: localhost:5432
バックアップファイル: backups/plc_monitor_20250124_020000.sql.gz

ℹ️  最新のバックアップファイルを使用します

⚠️  警告: 既存のデータベースが上書きされます。続行しますか？ (yes/no): yes

⏳ バックアップファイルを解凍中...
✅ 解凍完了
⏳ データベースをリストア中...
...
✅ リストアが正常に完了しました
```

### 2. 特定のバックアップからリストア

```bash
cd plc-dashboard
./scripts/restore_database.sh backups/plc_monitor_20250123_020000.sql.gz
```

## バックアップファイルの管理

### バックアップファイルの確認

```bash
ls -lh plc-dashboard/backups/
```

### バックアップファイルのサイズ

| 期間 | データ量（推定） | 圧縮後サイズ |
|-----|----------------|------------|
| 1ヶ月（詳細データ90日） | 50-100MB | 10-20MB |
| 3ヶ月（日次集計含む） | 100-200MB | 20-40MB |
| 1年（月次集計含む） | 200-500MB | 40-100MB |

**注:** 実際のサイズはPLC台数とデータ収集間隔により変動します。

### バックアップファイルの保持期間変更

`scripts/backup_database.sh`の`RETENTION_DAYS`を編集:

```bash
RETENTION_DAYS=30  # 30日分保持
```

## 外部ストレージへのバックアップ

### NAS/ネットワークドライブへのコピー

```bash
# rsyncを使った同期（推奨）
rsync -av --delete plc-dashboard/backups/ /mnt/nas/plc_backups/

# scpを使ったリモートコピー
scp plc-dashboard/backups/*.sql.gz user@backup-server:/backups/plc/
```

### クラウドストレージへのアップロード（オプション）

```bash
# AWS S3へのアップロード例
aws s3 sync plc-dashboard/backups/ s3://your-bucket/plc-backups/

# Google Driveへのアップロード（rclone）
rclone sync plc-dashboard/backups/ gdrive:plc-backups/
```

**注意:** クラウドストレージを使用する場合は、機密情報の暗号化を検討してください。

## トラブルシューティング

### pg_dumpコマンドが見つからない

**原因:** PostgreSQLクライアントツールがインストールされていない

**解決方法:**

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql

# Windows
# PostgreSQLインストーラーに含まれています
# https://www.postgresql.org/download/windows/
```

### 認証エラー

**エラー:**
```
psql: FATAL:  password authentication failed for user "plc_user"
```

**解決方法:**

1. `.env`ファイルのパスワードを確認
2. PostgreSQLが起動しているか確認: `pg_isready -h localhost -p 5432`
3. 接続テスト: `psql -h localhost -U plc_user -d plc_monitor`

### ディスク容量不足

**エラー:**
```
No space left on device
```

**解決方法:**

1. ディスク使用量を確認: `df -h`
2. 古いバックアップを手動削除: `rm plc-dashboard/backups/plc_monitor_20250101_*.sql.gz`
3. ログファイルをクリーンアップ: `journalctl --vacuum-time=7d`

## ベストプラクティス

1. **定期的なリストアテスト**
   - 月に1回、バックアップからのリストアをテストして、正常に復元できることを確認

2. **複数世代のバックアップ**
   - 日次バックアップ: 7日分
   - 週次バックアップ: 4週分
   - 月次バックアップ: 12ヶ月分

3. **外部ストレージへのコピー**
   - バックアップファイルを別のサーバーまたはNASにコピー
   - 物理的に異なる場所に保管（災害対策）

4. **バックアップの暗号化**
   - 機密性の高いデータの場合、gpgで暗号化:
   ```bash
   gpg --symmetric --cipher-algo AES256 backups/plc_monitor_20250124_020000.sql.gz
   ```

5. **監視とアラート**
   - バックアップの失敗を検知してアラート送信
   - ディスク使用量の監視

## 関連ドキュメント

- `_docs/deployment/environment-variables.md` - 環境変数設定
- `_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティング

---

**最終更新:** 2025-01-24
