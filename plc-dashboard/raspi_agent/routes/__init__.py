"""
ルートモジュール

Phase 7リファクタリング: agent_app.pyからの分割

このパッケージは以下のBlueprintを提供します:
- pages_bp: ページルート（index, initial_setup, monitoring）
- api_bp: REST APIエンドポイント
- language_bp: 言語切替ルート
"""

from .pages import pages_bp
from .api import api_bp
from .language import language_bp

__all__ = ['pages_bp', 'api_bp', 'language_bp']


def register_all_routes(app):
    """すべてのBlueprintをアプリケーションに登録

    Args:
        app: Flaskアプリケーションインスタンス
    """
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(language_bp)
