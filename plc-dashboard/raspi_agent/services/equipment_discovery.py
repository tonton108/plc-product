"""
設備検索サービス

Phase 9リファクタリング: 設備検索ロジックを統一
Phase 19: デバイス識別関数をdevice_utils.pyからインポート

このモジュールは設備の検索・識別ロジックを提供します：
- 優先度付き設備検索（CPUシリアル番号 → MACアドレス → IPアドレス）
- デバイス識別子の取得
"""

import logging
from device_utils import get_cpu_serial_number, get_mac_address, get_ip_address

# モジュール用ロガー
logger = logging.getLogger(__name__)


def get_device_identifiers():
    """デバイス識別子を取得

    Returns:
        dict: {
            'cpu_serial_number': str,
            'mac_address': str,
            'ip_address': str
        }
    """
    return {
        'cpu_serial_number': get_cpu_serial_number(),
        'mac_address': get_mac_address(),
        'ip_address': get_ip_address()
    }


def search_equipment_by_priority(db_api, cpu_serial_number=None, mac_address=None, ip_address=None, verbose=False):
    """優先度順に設備を検索

    検索優先順位：
    1. CPUシリアル番号（最優先・不変識別子）
    2. MACアドレス（準不変）
    3. IPアドレス（可変・最後の手段）

    Args:
        db_api: DatabaseAPIインスタンス
        cpu_serial_number: CPUシリアル番号（オプション）
        mac_address: MACアドレス（オプション）
        ip_address: IPアドレス（オプション）
        verbose: 詳細ログを出力するか（デフォルト: False）

    Returns:
        tuple: (equipment_info, search_method)
            - equipment_info: 設備情報辞書（見つからない場合はNone）
            - search_method: 検索成功した方法（"CPUシリアル番号", "MACアドレス", "IPアドレス", None）
    """
    # 検索優先順位の定義
    search_order = [
        ('cpu_serial_number', cpu_serial_number, 'CPUシリアル番号'),
        ('mac_address', mac_address, 'MACアドレス'),
        ('ip_address', ip_address, 'IPアドレス'),
    ]

    for param_name, param_value, method_name in search_order:
        if param_value:
            if verbose:
                logger.debug(f"{method_name} '{param_value}' で設備検索中...")

            # 動的にキーワード引数を作成
            search_params = {param_name: param_value}
            equipment_info = db_api.get_equipment_by_device_info(**search_params)

            if equipment_info:
                if verbose:
                    equipment_id = equipment_info.get('equipment_id', '不明')
                    logger.info(f"{method_name}で設備発見: {equipment_id}")
                return equipment_info, method_name

    # 見つからなかった場合
    if verbose:
        logger.warning("設備が見つかりませんでした")

    return None, None


def search_equipment_with_device_info(db_api, verbose=False):
    """現在のデバイス情報を使用して設備を検索

    get_device_identifiers()でデバイス情報を取得し、
    search_equipment_by_priority()で検索を実行する便利関数。

    Args:
        db_api: DatabaseAPIインスタンス
        verbose: 詳細ログを出力するか（デフォルト: False）

    Returns:
        tuple: (equipment_info, search_method, device_info)
            - equipment_info: 設備情報辞書（見つからない場合はNone）
            - search_method: 検索成功した方法
            - device_info: デバイス識別子辞書
    """
    device_info = get_device_identifiers()

    if verbose:
        logger.debug("デバイス情報取得完了")
        logger.debug(f"  CPUシリアル番号: {device_info['cpu_serial_number']}")
        logger.debug(f"  MACアドレス: {device_info['mac_address']}")
        logger.debug(f"  IPアドレス: {device_info['ip_address']}")

    equipment_info, search_method = search_equipment_by_priority(
        db_api,
        cpu_serial_number=device_info['cpu_serial_number'],
        mac_address=device_info['mac_address'],
        ip_address=device_info['ip_address'],
        verbose=verbose
    )

    return equipment_info, search_method, device_info
