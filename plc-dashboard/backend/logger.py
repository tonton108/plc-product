import logging
import os

def setup_logger():
    """
    PLC監視システム用のロガーをセットアップ

    環境変数 LOG_LEVEL でログレベルを制御可能:
    - DEBUG: 詳細なデバッグ情報
    - INFO: 一般的な情報メッセージ（デフォルト）
    - WARNING: 警告メッセージ
    - ERROR: エラーメッセージ
    - CRITICAL: 重大なエラー
    """
    log_level = os.getenv('LOG_LEVEL', 'INFO')

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    return logging.getLogger('plc_monitor')

# グローバルロガーインスタンス
logger = setup_logger()
