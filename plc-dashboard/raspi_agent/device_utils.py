"""
デバイス識別ユーティリティモジュール

Phase 19: api_client.py, agent_app.pyから統合

このモジュールはRaspberry Piのデバイス識別情報を取得する
共通関数を提供します：
- CPUシリアル番号（不変識別子）
- MACアドレス
- IPアドレス
- ホスト名
"""

import socket
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_cpu_serial_number() -> str:
    """
    Raspberry PiのCPUシリアル番号を取得（不変識別子）

    Returns:
        str: CPUシリアル番号、または取得できない場合はフォールバックID

    Note:
        - Raspberry Piでは/proc/cpuinfoからSerial行を読み取る
        - 非Raspberry Pi環境ではフォールバックIDを返す
    """
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    serial = line.split(':')[1].strip()
                    if serial and serial != "0000000000000000":
                        return serial
        logger.warning("CPU Serial情報が見つからないため、フォールバックIDを使用")
        return _generate_fallback_serial()
    except FileNotFoundError:
        # 非Linux環境（Windows等）
        logger.debug("非Linux環境: フォールバックIDを使用")
        return _generate_fallback_serial()
    except Exception as e:
        logger.error(f"CPUシリアル番号取得エラー: {e}")
        return _generate_fallback_serial()


def _generate_fallback_serial() -> str:
    """
    CPUシリアル番号が取得できない場合のフォールバックIDを生成

    Returns:
        str: 固定のフォールバックID
    """
    fallback_id = "FALLBACK_FIXED_ID"
    logger.debug(f"フォールバックID使用: {fallback_id}")
    return fallback_id


def get_mac_address() -> str:
    """
    デバイスのMACアドレスを取得

    Returns:
        str: XX:XX:XX:XX:XX:XX形式のMACアドレス
    """
    mac = uuid.getnode()
    # バイト順序を正しく処理してXX:XX:XX:XX:XX:XX形式に変換
    return ':'.join(['{:02x}'.format((mac >> i) & 0xff) for i in range(0, 48, 8)][::-1])


def get_ip_address() -> str:
    """
    デバイスのIPアドレスを取得

    外部への接続を試みることで、実際に使用されているIPアドレスを取得します。

    Returns:
        str: IPアドレス、接続できない場合は127.0.0.1
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # 実際には接続せず、ルーティングテーブルから適切なIPを取得
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except OSError:
        logger.debug("ネットワーク接続なし: ローカルホストIPを返す")
        return '127.0.0.1'


def get_hostname() -> str:
    """
    デバイスのホスト名を取得

    Returns:
        str: ホスト名
    """
    return socket.gethostname()


def get_device_info() -> dict:
    """
    デバイスの全識別情報を一括取得

    Returns:
        dict: デバイス情報を含む辞書
            - cpu_serial_number: CPUシリアル番号
            - mac_address: MACアドレス
            - ip_address: IPアドレス
            - hostname: ホスト名
    """
    return {
        "cpu_serial_number": get_cpu_serial_number(),
        "mac_address": get_mac_address(),
        "ip_address": get_ip_address(),
        "hostname": get_hostname(),
    }
