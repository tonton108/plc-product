#!/bin/bash
#
# PostgreSQLデータベースリストアスクリプト
#
# このスクリプトは、backup_database.shで作成したバックアップファイルから
# データベースを復元します。
#
# 使用方法:
#   ./scripts/restore_database.sh [バックアップファイル]
#
# 例:
#   ./scripts/restore_database.sh backups/plc_monitor_20250124_020000.sql.gz
#
# バックアップファイルを指定しない場合、最新のバックアップを使用します。
#

set -e  # エラー時に即座に終了

# 設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"

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

# バックアップファイルの決定
if [ -n "$1" ]; then
    BACKUP_FILE="$1"
else
    # 最新のバックアップファイルを自動選択
    BACKUP_FILE=$(ls -t "${BACKUP_DIR}"/plc_monitor_*.sql.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo "❌ エラー: バックアップファイルが見つかりません"
        echo "   ${BACKUP_DIR} ディレクトリを確認してください"
        exit 1
    fi
    echo "ℹ️  最新のバックアップファイルを使用します: ${BACKUP_FILE}"
fi

# バックアップファイルの存在確認
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ エラー: バックアップファイルが見つかりません: ${BACKUP_FILE}"
    exit 1
fi

echo "=========================================="
echo "📦 PostgreSQLリストアを開始します"
echo "=========================================="
echo "データベース: ${POSTGRES_DB}"
echo "ホスト: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "バックアップファイル: ${BACKUP_FILE}"
echo ""

# 確認プロンプト
read -p "⚠️  警告: 既存のデータベースが上書きされます。続行しますか？ (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "❌ リストアを中止しました"
    exit 0
fi

# 一時ファイルの準備
TEMP_SQL="/tmp/plc_restore_$$.sql"

# gzファイルの場合は解凍
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "⏳ バックアップファイルを解凍中..."
    gunzip -c "$BACKUP_FILE" > "$TEMP_SQL"
else
    cp "$BACKUP_FILE" "$TEMP_SQL"
fi

echo "✅ 解凍完了"

# psqlでリストア
echo "⏳ データベースをリストア中..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -f "$TEMP_SQL"

# 一時ファイルを削除
rm -f "$TEMP_SQL"

echo ""
echo "=========================================="
echo "✅ リストアが正常に完了しました"
echo "=========================================="
echo ""
echo "📋 次のステップ:"
echo "1. アプリケーションを再起動してください"
echo "2. データが正しく復元されたか確認してください"
echo ""
