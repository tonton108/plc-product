#!/bin/bash

set -e

echo "=========================================="
echo "PLC監視システム - 統合起動スクリプト"
echo "=========================================="
echo ""

# 環境変数ファイルの確認
if [ ! -f .env ]; then
    echo "⚠️  .envファイルが見つかりません。.env.exampleからコピーしています..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .envファイルを作成しました。必要に応じて編集してください。"
        echo ""
    else
        echo "❌ .env.exampleが見つかりません。"
        exit 1
    fi
fi

# 起動モード選択
echo "起動モードを選択してください:"
echo ""
echo "  1) 中央サーバーのみ（DB + API + フロントエンド）"
echo "  2) 全機能（中央サーバー + Raspberry Piエージェント）"
echo "  3) Raspberry Piエージェントのみ（開発・テスト用）"
echo "  4) データベースとバックエンドのみ"
echo ""
read -p "選択 [1-4]: " mode

case $mode in
    1)
        echo ""
        echo "📊 中央サーバーを起動します..."
        echo "   - PostgreSQLデータベース"
        echo "   - Flask バックエンドAPI"
        echo "   - Nuxt.js フロントエンド"
        echo ""
        docker compose up -d db backend frontend
        ;;
    2)
        echo ""
        echo "🚀 全機能を起動します..."
        echo "   - PostgreSQLデータベース"
        echo "   - Flask バックエンドAPI"
        echo "   - Nuxt.js フロントエンド"
        echo "   - Raspberry Piエージェント"
        echo ""
        docker compose --profile full up -d
        ;;
    3)
        echo ""
        echo "🤖 Raspberry Piエージェントを起動します..."
        echo "   - PostgreSQLデータベース"
        echo "   - Flask バックエンドAPI"
        echo "   - Raspberry Piエージェント"
        echo ""
        docker compose --profile agent up -d
        ;;
    4)
        echo ""
        echo "🔧 データベースとバックエンドを起動します..."
        echo "   - PostgreSQLデータベース"
        echo "   - Flask バックエンドAPI"
        echo ""
        docker compose up -d db backend
        ;;
    *)
        echo "❌ 無効な選択です。"
        exit 1
        ;;
esac

echo ""
echo "⏳ コンテナの起動を待機中..."
sleep 5

echo ""
echo "✅ 起動完了！"
echo ""
echo "=========================================="
echo "アクセスURL:"
echo "=========================================="

if [ "$mode" == "1" ] || [ "$mode" == "2" ]; then
    echo "  🌐 フロントエンド（Nuxt.js）:    http://localhost:3000"
fi

if [ "$mode" != "3" ]; then
    echo "  🔌 バックエンドAPI（Flask）:    http://localhost:5000"
    echo "  🗄️  PostgreSQLデータベース:      localhost:5432"
fi

if [ "$mode" == "2" ] || [ "$mode" == "3" ]; then
    echo "  🤖 Raspberry PiエージェントUI:  http://localhost:5001"
fi

echo ""
echo "=========================================="
echo "コンテナ状態:"
echo "=========================================="
docker compose ps

echo ""
echo "=========================================="
echo "ログ確認:"
echo "=========================================="
echo "  全てのログ:        docker compose logs -f"
echo "  バックエンド:      docker compose logs -f backend"
echo "  フロントエンド:    docker compose logs -f frontend"
echo "  エージェント:      docker compose logs -f raspi-agent"
echo ""
echo "=========================================="
echo "停止:"
echo "=========================================="
echo "  docker compose down"
echo ""
