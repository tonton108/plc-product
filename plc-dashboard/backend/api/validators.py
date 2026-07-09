"""
入力バリデーションモジュール

このモジュールはAPIリクエストの入力データを検証するための
バリデーション関数とデコレータを提供します。

使用例:
    from api.validators import validate_equipment_id, validate_ip_address, require_json

    @app.route("/api/equipment/<equipment_id>", methods=["GET"])
    def get_equipment(equipment_id):
        if not validate_equipment_id(equipment_id):
            return jsonify({"error": "Invalid equipment_id format"}), 400
        ...

Phase 16: 型ヒント追加
"""

import re
import logging
from functools import wraps
from typing import Union, Tuple, Callable, Any, Dict
from flask import request, jsonify, Response

logger = logging.getLogger(__name__)


def validate_equipment_id(equipment_id: str) -> bool:
    """
    設備IDフォーマットを検証

    Args:
        equipment_id: 検証する設備ID

    Returns:
        bool: 有効な場合はTrue、無効な場合はFalse

    検証ルール:
        - 1〜50文字
        - 英数字、アンダースコア、ハイフンのみ許可
    """
    if not equipment_id:
        return False
    return bool(re.match(r'^[A-Za-z0-9_-]{1,50}$', equipment_id))


def validate_ip_address(ip: str) -> bool:
    """
    IPアドレスフォーマットを検証

    Args:
        ip: 検証するIPアドレス

    Returns:
        bool: 有効な場合はTrue、無効な場合はFalse

    検証ルール:
        - IPv4形式（xxx.xxx.xxx.xxx）
        - 各オクテットは0〜255
    """
    if not ip:
        return False

    pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    match = re.match(pattern, ip)
    if not match:
        return False

    # 各オクテットが0〜255の範囲内か確認
    for octet in match.groups():
        if not 0 <= int(octet) <= 255:
            return False

    return True


def validate_port(port: Union[int, str, None]) -> bool:
    """
    ポート番号を検証

    Args:
        port: 検証するポート番号（int または str）

    Returns:
        bool: 有効な場合はTrue、無効な場合はFalse

    検証ルール:
        - 1〜65535の範囲内
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (TypeError, ValueError):
        return False


def validate_mac_address(mac: str) -> bool:
    """
    MACアドレスフォーマットを検証

    Args:
        mac: 検証するMACアドレス

    Returns:
        bool: 有効な場合はTrue、無効な場合はFalse

    検証ルール:
        - XX:XX:XX:XX:XX:XX または XX-XX-XX-XX-XX-XX 形式
        - 各オクテットは16進数（0-9, A-F, a-f）
    """
    if not mac:
        return False

    # コロン区切りまたはハイフン区切りのMACアドレス
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac))


def validate_protocol(protocol: str) -> bool:
    """
    PLCプロトコルを検証

    Args:
        protocol: 検証するプロトコル名

    Returns:
        bool: 有効な場合はTrue、無効な場合はFalse
    """
    valid_protocols = [
        'MC_PROTOCOL_3E',
        'MC_PROTOCOL_4E',
        'MODBUS_TCP',
        'MODBUS_RTU',
        'FINS_TCP',
        'FINS_UDP'
    ]
    return protocol in valid_protocols


def validate_data_type(data_type: str) -> bool:
    """
    PLCデータ項目名（data_type）を検証

    Phase 2: ホワイトリスト方式（固定6種のみ許可）から形式検証に変更。
    「設備ごとに任意のデータ項目を定義できる」仕様のため、項目名は
    固定リストではなく文字種・長さで検証する。

    Args:
        data_type: 検証するデータ項目名

    Returns:
        bool: 有効な場合はTrue、無効な場合はFalse

    検証ルール:
        - 1〜50文字
        - 英数字、アンダースコア、ハイフンのみ許可
    """
    if not data_type:
        return False
    return bool(re.match(r'^[A-Za-z0-9_-]{1,50}$', data_type))


def require_json(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    JSONリクエスト必須デコレータ

    リクエストのContent-Typeがapplication/jsonでない場合、
    400エラーを返します。

    使用例:
        @app.route("/api/endpoint", methods=["POST"])
        @require_json
        def my_endpoint():
            data = request.get_json()
            ...
    """
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Tuple[Response, int]:
        if not request.is_json:
            logger.warning(f"非JSONリクエストを拒否: {request.endpoint}")
            return jsonify({"error": "Content-Type must be application/json"}), 400
        return f(*args, **kwargs)
    return wrapper


def validate_equipment_config(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    設備設定データを一括検証

    Args:
        data: 検証する設備設定データ

    Returns:
        tuple[bool, str]: (検証結果, エラーメッセージ)
            検証成功時は (True, "")
            検証失敗時は (False, "エラーメッセージ")
    """
    # 必須フィールドのチェック
    if "equipment_id" in data and not validate_equipment_id(data["equipment_id"]):
        return False, "Invalid equipment_id format (1-50 alphanumeric characters, underscores, hyphens)"

    # IPアドレスのチェック（存在する場合のみ）
    if "plc_ip" in data and data["plc_ip"] and not validate_ip_address(data["plc_ip"]):
        return False, "Invalid plc_ip format (must be valid IPv4 address)"

    if "ip" in data and data["ip"] and not validate_ip_address(data["ip"]):
        return False, "Invalid ip format (must be valid IPv4 address)"

    if "raspi_ip" in data and data["raspi_ip"] and not validate_ip_address(data["raspi_ip"]):
        return False, "Invalid raspi_ip format (must be valid IPv4 address)"

    # ポート番号のチェック（存在する場合のみ）
    if "port" in data and data["port"] is not None and not validate_port(data["port"]):
        return False, "Invalid port number (must be 1-65535)"

    if "plc_port" in data and data["plc_port"] is not None and not validate_port(data["plc_port"]):
        return False, "Invalid plc_port number (must be 1-65535)"

    if "modbus_port" in data and data["modbus_port"] is not None and not validate_port(data["modbus_port"]):
        return False, "Invalid modbus_port number (must be 1-65535)"

    # MACアドレスのチェック（存在する場合のみ）
    if "mac_address" in data and data["mac_address"] and not validate_mac_address(data["mac_address"]):
        return False, "Invalid mac_address format (must be XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)"

    # プロトコルのチェック（存在する場合のみ）
    if "protocol" in data and data["protocol"] and not validate_protocol(data["protocol"]):
        return False, "Invalid protocol (must be one of: MC_PROTOCOL_3E, MC_PROTOCOL_4E, MODBUS_TCP, MODBUS_RTU, FINS_TCP, FINS_UDP)"

    return True, ""


def validate_plc_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    PLCデータ設定を検証

    Args:
        config: 検証するPLCデータ設定

    Returns:
        tuple[bool, str]: (検証結果, エラーメッセージ)
    """
    # data_typeのチェック
    if "data_type" in config and config["data_type"] and not validate_data_type(config["data_type"]):
        return False, f"Invalid data_type: {config['data_type']}"

    # addressのチェック（空でないことを確認）
    if "address" in config and config.get("enabled", False):
        if not config["address"] or not isinstance(config["address"], str):
            return False, "Address is required when config is enabled"

    # scale_factorのチェック（数値であることを確認）
    if "scale_factor" in config:
        try:
            float(config["scale_factor"])
        except (TypeError, ValueError):
            return False, "Invalid scale_factor (must be a number)"

    return True, ""
