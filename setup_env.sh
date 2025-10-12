#!/bin/bash

# ========================================
# PLC監視システム - 環境セットアップスクリプト
# ========================================

set -e

echo "========================================="
echo "PLC監視システム - 環境セットアップ"
echo "========================================="
echo ""

# .envファイルが既に存在するか確認
if [ -f ".env" ]; then
    echo "⚠️  .envファイルが既に存在します。"
    read -p "上書きしますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "セットアップをキャンセルしました。"
        exit 0
    fi
fi

# .env.exampleから.envを作成
echo "📄 .env.exampleから.envを作成中..."
cp .env.example .env

# ランダムなSECRET_KEYを生成
echo "🔐 SECRET_KEYを生成中..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
sed -i "s/CHANGE_ME_TO_RANDOM_SECRET_KEY/$SECRET_KEY/" .env

# ランダムなPostgreSQLパスワードを生成
echo "🔐 PostgreSQLパスワードを生成中..."
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
sed -i "s/CHANGE_ME_TO_STRONG_PASSWORD/$POSTGRES_PASSWORD/" .env

# 管理者パスワードの設定
echo ""
echo "管理者パスワードを設定してください（デフォルト: admin123）"
read -p "管理者パスワード（Enterでデフォルト）: " -s ADMIN_PASSWORD
echo

if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD="admin123"
    echo "⚠️  デフォルトパスワード（admin123）を使用します。本番環境では必ず変更してください！"
fi

# パスワードのハッシュを生成
ADMIN_PASSWORD_HASH=$(python3 -c "import hashlib; password='$ADMIN_PASSWORD'; print(hashlib.sha256(password.encode()).hexdigest())")
sed -i "s/CHANGE_ME_AFTER_RUNNING_HASH_SCRIPT/$ADMIN_PASSWORD_HASH/" .env

echo ""
echo "✅ 環境設定ファイル（.env）を作成しました！"
echo ""
echo "生成された設定:"
echo "  - SECRET_KEY: ランダム生成完了"
echo "  - POSTGRES_PASSWORD: ランダム生成完了"
echo "  - ADMIN_PASSWORD: 設定完了"
echo ""
echo "次のステップ:"
echo "  1. .envファイルを確認・編集してください"
echo "  2. docker compose up -d でシステムを起動してください"
echo ""
echo "========================================="
