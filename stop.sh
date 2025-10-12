#!/bin/bash

echo "=========================================="
echo "PLC監視システム - 停止スクリプト"
echo "=========================================="
echo ""

echo "停止オプションを選択してください:"
echo ""
echo "  1) コンテナ停止（データ保持）"
echo "  2) コンテナ停止 + 削除（データ保持）"
echo "  3) 完全削除（データベースも削除）"
echo ""
read -p "選択 [1-3]: " mode

case $mode in
    1)
        echo ""
        echo "⏹️  コンテナを停止します..."
        docker compose stop
        echo "✅ 停止完了"
        ;;
    2)
        echo ""
        echo "⏹️  コンテナを停止・削除します（データは保持）..."
        docker compose down
        echo "✅ 停止・削除完了"
        ;;
    3)
        echo ""
        echo "⚠️  警告: データベースのデータも削除されます！"
        read -p "本当に削除しますか？ [y/N]: " confirm
        if [ "$confirm" == "y" ] || [ "$confirm" == "Y" ]; then
            echo ""
            echo "🗑️  コンテナとボリュームを完全削除します..."
            docker compose down -v
            echo "✅ 完全削除完了"
        else
            echo "❌ キャンセルされました"
        fi
        ;;
    *)
        echo "❌ 無効な選択です。"
        exit 1
        ;;
esac

echo ""
echo "現在のコンテナ状態:"
docker compose ps -a

echo ""
