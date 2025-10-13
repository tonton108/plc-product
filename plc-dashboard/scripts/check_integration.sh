#!/bin/bash

echo "======================================"
echo "PLC監視システム統合版 - 構成確認"
echo "======================================"
echo ""

# ディレクトリ構造確認
echo "📁 ディレクトリ構造確認:"
echo ""

directories=(
    "backend"
    "backend/api"
    "backend/db"
    "raspi_agent"
    "raspi_agent/templates"
    "raspi_agent/config"
    "pages"
    "components"
    "plugins"
)

for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (見つかりません)"
    fi
done

echo ""
echo "📝 重要ファイル確認:"
echo ""

files=(
    "docker-compose.yml"
    ".env.example"
    "backend/app.py"
    "backend/manage.py"
    "backend/api/routes.py"
    "backend/db/models.py"
    "raspi_agent/agent_app.py"
    "raspi_agent/plc_agent.py"
    "raspi_agent/db_utils.py"
    "raspi_agent/Dockerfile.agent"
    "raspi_agent/scp_bulk_push.sh"
    "nuxt.config.ts"
    "package.json"
    "README_INTEGRATED.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (見つかりません)"
    fi
done

echo ""
echo "======================================"
echo "確認完了"
echo "======================================"
echo ""
echo "次のステップ:"
echo "  1. 環境設定: cp .env.example .env"
echo "  2. 中央サーバー起動: docker compose up -d db backend"
echo "  3. フロントエンド起動: npm run dev"
echo "  4. エージェント起動（オプション）: docker compose --profile agent up -d"
echo ""
echo "詳細は README_INTEGRATED.md を参照してください。"
