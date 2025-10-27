#!/bin/bash
#
# PostgreSQLデータベースバックアップスクリプト
#
# このスクリプトは以下を実行します:
# 1. PostgreSQLのpg_dumpを使ってデータベースをバックアップ
# 2. バックアップファイルを圧縮（gzip）
# 3. 古いバックアップファイルを自動削除（デフォルト7日分保持）
#
# 使用方法:
#   ./scripts/backup_database.sh
#
# cron設定例（毎日午前2時に実行）:
#   0 2 * * * /path/to/plc-dashboard/scripts/backup_database.sh >> /var/log/plc_backup.log 2>&1
#

set -e  # エラー時に即座に終了

# 設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=7  # バックアップ保持期間（日数）

# 環境変数を読み込み
if [ -f "${PROJECT_DIR}/.env" ]; then
    export $(grep -v '^#' "${PROJECT_DIR}/.env" | xargs)
fi

# 必須環境変数の確認
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo "❌ エラー: 環境変数が設定されていません"
    echo "   以下の環境変数を.envファイルに設定してください:"
    echo "   - POSTGRES_USER"
    echo "   - POSTGRES_PASSWORD"
    echo "   - POSTGRES_DB"
    echo "   - POSTGRES_PORT (オプション、デフォルト: 5432)"
    exit 1
fi

# デフォルト値
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"

# バックアップディレクトリ作成
mkdir -p "${BACKUP_DIR}"

# バックアップファイル名（日時付き）
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/plc_monitor_${TIMESTAMP}.sql"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

echo "=========================================="
echo "📦 PostgreSQLバックアップを開始します"
echo "=========================================="
echo "データベース: ${POSTGRES_DB}"
echo "ホスト: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "バックアップ先: ${BACKUP_FILE_GZ}"
echo ""

# pg_dumpを実行
echo "⏳ バックアップ中..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    -F p \
    -f "${BACKUP_FILE}"

# バックアップファイルが作成されたか確認
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "❌ エラー: バックアップファイルの作成に失敗しました"
    exit 1
fi

# ファイルサイズ取得
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "✅ バックアップ完了: ${BACKUP_SIZE}"

# gzip圧縮
echo "⏳ 圧縮中..."
gzip "${BACKUP_FILE}"

# 圧縮後のファイルサイズ取得
COMPRESSED_SIZE=$(du -h "${BACKUP_FILE_GZ}" | cut -f1)
echo "✅ 圧縮完了: ${COMPRESSED_SIZE}"

# 古いバックアップファイルを削除（RETENTION_DAYS日以上前のファイル）
echo ""
echo "🗑️  古いバックアップファイルを削除中（${RETENTION_DAYS}日以上前）..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "plc_monitor_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    echo "✅ ${DELETED_COUNT} 個のファイルを削除しました"
else
    echo "ℹ️  削除対象のファイルはありませんでした"
fi

# バックアップファイル一覧表示
echo ""
echo "📋 現在のバックアップファイル:"
ls -lh "${BACKUP_DIR}"/plc_monitor_*.sql.gz 2>/dev/null || echo "   （バックアップファイルがありません）"

echo ""
echo "=========================================="
echo "✅ バックアップが正常に完了しました"
echo "=========================================="
echo "バックアップファイル: ${BACKUP_FILE_GZ}"
echo "圧縮後サイズ: ${COMPRESSED_SIZE}"
echo ""
