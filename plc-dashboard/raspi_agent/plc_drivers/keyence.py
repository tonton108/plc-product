"""
キーエンスPLC用ドライバー

Modbus TCP を使用したキーエンスPLCとの通信を提供します。
- ポート: 502
- エンディアン: Big-Endian
- ライブラリ: pymodbus

CLAUDE.md参照: PLCプロトコル基礎知識 - Modbus TCP

Phase 4リファクタリング: データ型変換を共通関数に置き換え
"""
import logging
from .base import (
    validate_plc_ip,
    update_error_stats,
    retry_on_failure,
    safe_plc_read,
    group_continuous_word_addresses,
    convert_words_to_value,
    CONNECTION_TIMEOUT
)
from ..config.constants import DEFAULT_MODBUS_PORT

logger = logging.getLogger(__name__)


def connect_keyence_plc(ip, port=DEFAULT_MODBUS_PORT, timeout=CONNECTION_TIMEOUT):
    """
    キーエンスPLC接続（Modbus/TCP）
    CLAUDE.md参照: Modbus TCP, ポート502, Big-Endian

    Args:
        ip: PLCのIPアドレス
        port: Modbusポート（デフォルト502）
        timeout: タイムアウト時間（秒）

    Returns:
        ModbusTcpClient: Modbus接続オブジェクト、失敗時はNone
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        logger.error("pymodbusライブラリがインストールされていません: pip install pymodbus")
        return None

    def _connect():
        client = ModbusTcpClient(ip, port=port, timeout=timeout)
        if client.connect():
            logger.info(f"✅ キーエンスPLC接続成功: {ip}:{port}")
            return client
        else:
            raise Exception("Modbus接続に失敗しました")

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"キーエンスPLC接続失敗: {ip}:{port} - {e}")
        return None


def keyence_address_to_modbus(address, data_type="word"):
    """
    キーエンスアドレスをModbusアドレスに変換

    Args:
        address: キーエンスアドレス（例: DM100, R100.1, MR200）
        data_type: データ型（word, bit等）

    Returns:
        tuple: (register_type, modbus_addr)
    """
    address_upper = address.upper()

    if address_upper.startswith('DM'):
        # データメモリ → Holding Registers
        addr_num = int(address[2:])
        if data_type == "bit":
            raise ValueError("DMアドレスではビット指定はできません")
        return ("holding", addr_num)

    elif address_upper.startswith('R'):
        # リレー → Coils
        if '.' in address:
            # ビット指定 (例: R100.1)
            base_addr, bit_pos = address.split('.')
            addr_num = int(base_addr[1:])
            bit_pos = int(bit_pos)
            # キーエンスでは1リレー = 16ビット
            modbus_addr = addr_num * 16 + bit_pos
        else:
            addr_num = int(address[1:])
            if data_type == "bit":
                modbus_addr = addr_num * 16  # R100 = ビット1600
            else:
                modbus_addr = addr_num
        return ("coil", modbus_addr)

    elif address_upper.startswith('MR'):
        # 内部リレー → Coils (オフセット付き)
        if '.' in address:
            base_addr, bit_pos = address.split('.')
            addr_num = int(base_addr[2:])
            bit_pos = int(bit_pos)
            modbus_addr = 10000 + addr_num * 16 + bit_pos  # オフセット
        else:
            addr_num = int(address[2:])
            if data_type == "bit":
                modbus_addr = 10000 + addr_num * 16
            else:
                modbus_addr = 10000 + addr_num
        return ("coil", modbus_addr)

    else:
        raise ValueError(f"不明なキーエンスアドレス形式: {address}")


def read_keyence_modbus(client, address, data_type="word", scale=1):
    """
    キーエンスPLCからModbus経由でデータ読み取り

    Args:
        client: Modbusクライアント
        address: キーエンスアドレス
        data_type: データ型
        scale: スケール係数

    Returns:
        読み取った値、エラー時はNone
    """
    try:
        from pymodbus.exceptions import ModbusException
        register_type, modbus_addr = keyence_address_to_modbus(address, data_type)

        if data_type == "bit":
            # ビット読み取り
            if register_type == "coil":
                result = client.read_coils(modbus_addr, 1)
                if not result.isError():
                    return 1 if result.bits[0] else 0
                else:
                    raise Exception(f"Coil読み取りエラー: {result}")
            else:
                raise ValueError("ビット読み取りはCoilのみ対応")

        elif data_type in ("float32", "dword"):
            # 32bitデータ (2レジスタ) - float32またはdword
            if register_type == "holding":
                result = client.read_holding_registers(modbus_addr, 2)
                if not result.isError():
                    # 共通関数でfloat32/dwordに変換（Big-Endian）
                    return convert_words_to_value(
                        result.registers[0], result.registers[1], data_type
                    )
                else:
                    raise Exception(f"Holding Register読み取りエラー: {result}")
            else:
                raise ValueError(f"{data_type}はHolding Registerのみ対応")

        else:
            # 16bit word
            if register_type == "holding":
                result = client.read_holding_registers(modbus_addr, 1)
                if not result.isError():
                    return result.registers[0]
                else:
                    raise Exception(f"Holding Register読み取りエラー: {result}")
            elif register_type == "coil":
                result = client.read_coils(modbus_addr, 16)  # 16ビット分
                if not result.isError():
                    # 16ビットを整数に変換
                    value = 0
                    for i in range(16):
                        if i < len(result.bits) and result.bits[i]:
                            value |= (1 << i)
                    return value
                else:
                    raise Exception(f"Coil読み取りエラー: {result}")

    except (ModbusException, Exception) as e:
        logger.error(f"キーエンスModbus読み取りエラー({address}): {e}")
        return None


def read_keyence_plc(client, data_points, modbus_port=DEFAULT_MODBUS_PORT):
    """
    キーエンスPLCからデータを読み取り

    Args:
        client: Modbusクライアント
        data_points: データ項目の辞書
        modbus_port: Modbusポート

    Returns:
        dict: 読み取ったデータ
    """
    data = {}

    # バッチ読み取り最適化: 連続したwordアドレスをグループ化（DMアドレスのみ）
    word_groups = group_continuous_word_addresses(data_points, device_type='DM')

    # グループ化されたwordアドレスを一括読み取り
    for group in word_groups:
        try:
            start_addr = group['start_address']
            count = group['count']

            if count == 1:
                # 単独アドレス → 個別読み取り
                logger.debug(f"📖 単独読み取り: DM{start_addr}")
                result = client.read_holding_registers(address=start_addr, count=1, unit=1)
            else:
                # 連続アドレス → バッチ読み取り（最適化）
                logger.info(f"🚀 バッチ読み取り: DM{start_addr}-DM{start_addr + count - 1} ({count}ワード)")
                result = client.read_holding_registers(address=start_addr, count=count, unit=1)

            # 読み取った値を各項目に割り当て
            if not result.isError():
                for i, key in enumerate(group['keys']):
                    setting = group['settings'][i]
                    scale = setting.get("scale", 1)
                    raw_value = result.registers[i]

                    # スケール適用
                    if scale > 1:
                        data[key] = raw_value / scale
                    else:
                        data[key] = raw_value

                    logger.debug(f"  ✅ {key} = {data[key]} (raw: {raw_value}, scale: {scale})")
            else:
                raise Exception(f"Modbus読み取りエラー: {result}")

        except Exception as e:
            logger.error(f"❌ バッチ読み取りエラー (DM{group['start_address']}): {e}")
            # エラー時は個別に再試行
            for i, key in enumerate(group['keys']):
                setting = group['settings'][i]
                addr_num = group['start_address'] + i
                try:
                    result = client.read_holding_registers(address=addr_num, count=1, unit=1)
                    if not result.isError():
                        raw_value = result.registers[0]
                        scale = setting.get("scale", 1)
                        data[key] = raw_value / scale if scale > 1 else raw_value
                except Exception:
                    logger.warning(f"⚠️ {key}(DM{addr_num})の個別再試行も失敗")

    # bit, dword, float32は個別処理（従来通り）
    # ※既にバッチ読み取りで取得したwordデータはスキップ
    for key, setting in data_points.items():
        if setting.get("enabled", False):
            address = setting.get("address")
            scale = setting.get("scale", 1)
            data_type = setting.get("data_type", "word")  # デフォルト: word

            # バッチ読み取り済みのデータはスキップ
            if key in data:
                continue

            if address:
                raw_value = read_keyence_modbus(client, address, data_type, scale)
                if raw_value is not None:
                    if data_type == "bit":
                        data[key] = int(raw_value)
                    elif scale > 1:
                        data[key] = raw_value / scale
                    else:
                        data[key] = raw_value
                else:
                    logger.warning(f"⚠️ {key}({address})のデータ取得に失敗")

    # 接続を閉じる
    try:
        client.close()
    except Exception:
        pass

    if data:
        update_error_stats(True)
        logger.info(f"✅ キーエンスPLC データ取得成功: {len(data)}項目")

    return data
