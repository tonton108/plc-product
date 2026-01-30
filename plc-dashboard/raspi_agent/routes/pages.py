"""
ページルート

Phase 7リファクタリング: agent_app.pyから分割

注意: 主要なページルート（index, initial_setup, monitoring）は
agent_app.pyに残しています。これは以下の理由からです：
- グローバル変数（config, series_list）への依存
- 複雑なテンプレートレンダリング
- 認証フローとの密接な結合

このファイルは将来的なBlueprint完全移行の基盤として存在します。
"""

from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


# 注意: 以下のルートはagent_app.pyに残しています
# - / (index) - 複雑な認証フロー、設備検索ロジック
# - /initial_setup - PLCConfig設定フォーム処理
# - /monitoring - モニタリング画面
# - /login, /logout - セッション管理

# これらは将来的に依存性注入パターンを使用してBlueprintに移行予定
# 現時点では、agent_app.pyからこのモジュールの関数をインポートする形で
# コードの整理を進めています
