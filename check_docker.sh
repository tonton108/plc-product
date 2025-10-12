#!/bin/bash

echo "=========================================="
echo "Docker環境チェック"
echo "=========================================="
echo ""

# Dockerバージョン確認
echo "📦 Dockerバージョン:"
docker --version 2>&1
echo ""

# Docker Desktopの起動状態確認
echo "🐳 Docker Desktopの状態:"
if docker info > /dev/null 2>&1; then
    echo "✅ Docker Desktop is running"
    echo ""
    
    # 既存のコンテナ確認
    echo "📋 既存のコンテナ:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers"
    echo ""
    
    # Docker Composeファイルの確認
    echo "📄 docker-compose.yml の検証:"
    if docker compose config > /dev/null 2>&1; then
        echo "✅ docker-compose.yml is valid"
    else
        echo "❌ docker-compose.yml has errors"
    fi
else
    echo "❌ Docker Desktop is not running"
    echo ""
    echo "💡 解決方法:"
    echo "   1. Docker Desktopアプリケーションを起動してください"
    echo "   2. タスクトレイのDockerアイコンが緑色になるまで待ちます"
    echo "   3. 再度このスクリプトを実行してください"
fi

echo ""
echo "=========================================="
