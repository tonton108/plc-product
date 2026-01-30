"""
データベースユーティリティ（後方互換ラッパー）

Phase 8リファクタリング: このファイルは後方互換性のためのラッパーです。
Phase 19: デバイス識別関数をdevice_utils.pyに統合

実際の実装は以下に分割されています：
- api_client.py: DatabaseAPIクラス
- config_manager.py: ConfigManagerクラス
- device_utils.py: デバイス識別ユーティリティ（Phase 19追加）

新しいコードでは直接以下をインポートしてください：
    from api_client import DatabaseAPI
    from config_manager import ConfigManager
    from device_utils import get_cpu_serial_number, get_mac_address, get_ip_address

このファイルは既存コードの互換性維持のために残されています。
"""

# api_client.pyからのエクスポート
from api_client import DatabaseAPI

# Phase 19: デバイス識別関数を統合モジュールから直接インポート
from device_utils import (
    get_cpu_serial_number,
    get_mac_address,
    get_ip_address,
)

# config_manager.pyからのエクスポート
from config_manager import ConfigManager

# 後方互換性のための__all__定義
__all__ = [
    'DatabaseAPI',
    'ConfigManager',
    'get_cpu_serial_number',
    'get_mac_address',
    'get_ip_address',
]
