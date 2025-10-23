#!/bin/bash

# PLCモニタリングシステム - Docker開発環境スクリプト

set -e

echo "🏭 PLCモニタリングシステム - Docker開発環境"
echo "=" * 60

case "$1" in
    "start" | "up")
        echo "🚀 開発環境を起動しています..."
        docker compose up --build
        ;;
    
    "stop" | "down")
        echo "⏹️ 開発環境を停止しています..."
        docker compose down
        ;;
    
    "restart")
        echo "🔄 開発環境を再起動しています..."
        docker compose down
        docker compose up --build
        ;;
    
    "logs")
        echo "📄 ログを表示しています..."
        docker compose logs -f
        ;;
    
    "backend-logs")
        echo "📄 バックエンドのログを表示しています..."
        docker compose logs -f backend
        ;;
    
    "frontend-logs")
        echo "📄 フロントエンドのログを表示しています..."
        docker compose logs -f frontend
        ;;
    
    "clean")
        echo "🧹 Docker環境をクリーンアップしています..."
        docker compose down --volumes --rmi all
        docker system prune -f
        ;;
    
    "shell-backend")
        echo "🐚 バックエンドコンテナにシェルアクセス..."
        docker compose exec backend bash
        ;;
    
    "shell-frontend")
        echo "🐚 フロントエンドコンテナにシェルアクセス..."
        docker compose exec frontend sh
        ;;
    
    *)
        echo "使用方法:"
        echo "  ./docker-dev.sh start      # 開発環境を起動"
        echo "  ./docker-dev.sh stop       # 開発環境を停止"
        echo "  ./docker-dev.sh restart    # 開発環境を再起動"
        echo "  ./docker-dev.sh logs       # 全体のログを表示"
        echo "  ./docker-dev.sh backend-logs   # バックエンドのログを表示"
        echo "  ./docker-dev.sh frontend-logs  # フロントエンドのログを表示"
        echo "  ./docker-dev.sh clean      # Docker環境をクリーンアップ"
        echo "  ./docker-dev.sh shell-backend  # バックエンドコンテナにアクセス"
        echo "  ./docker-dev.sh shell-frontend # フロントエンドコンテナにアクセス"
        echo ""
        echo "開発サーバー:"
        echo "  フロントエンド: http://localhost:3000"
        echo "  バックエンドAPI: http://localhost:5000"
        ;;
esac 