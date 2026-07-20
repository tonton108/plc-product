"""
オムロンPLC用ドライバー

FINS Protocol を使用したオムロンPLCとの通信を提供します。
- ポート: 9600 (UDP/TCP)
- エンディアン: Big-Endian
- ライブラリ: fins

CLAUDE.md参照: PLCプロトコル基礎知識 - FINS Protocol

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
    CONNECTION_TIMEOUT,
)

logger = logging.getLogger(__name__)


def connect_omron_plc(ip, timeout=CONNECTION_TIMEOUT):
    """
    オムロンPLC接続（タイムアウト付き）
    CLAUDE.md参照: FINS Protocol, ポート9600, Big-Endian

    Args:
        ip: PLCのIPアドレス
        timeout: タイムアウト時間（秒）

    Returns:
        fins.udp.UDPFinsConnection: FINS接続オブジェクト、失敗時はNone
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    import fins.udp

    def _connect():
        fins_client = fins.udp.UDPFinsConnection()
        fins_client.connect(ip)
        # CLAUDE.md ルール4: finsライブラリのconnect()はソケットタイムアウトを
        # 1.0秒固定で設定するため、受け取ったtimeout(秒)で上書きする。
        # これを怠ると通信断時に1秒でしか待たず、逆に設定値が無視される。
        fins_client.fins_socket.settimeout(timeout)
        fins_client.dest_node_add = 1
        fins_client.srce_node_add = 25
        logger.info(f"✅ オムロンPLC接続成功: {ip}")
        return fins_client

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"オムロンPLC接続失敗: {ip} - {e}")
        return None


def read_omron_plc(fins_client, data_points):
    """
    オムロンPLCからデータを読み取り

    Args:
        fins_client: FINS接続オブジェクト
        data_points: データ項目の辞書

    Returns:
        dict: 読み取ったデータ
    """
    data = {}

    # バッチ読み取り最適化: 連続したwordアドレスをグループ化
    # device_type="D" とすることで "D100"（既定設定）も "DM100" も対象になる
    # （"DM100".startswith("D") は真。"DM"限定だと既定の"D"始まりアドレスで
    # バッチが一切発動せず個別読みに退化していた）。番号抽出はプレフィックス非依存。
    word_groups = group_continuous_word_addresses(data_points, device_type="D")

    # グループ化されたwordアドレスを一括読み取り
    for group in word_groups:
        try:
            start_addr = group["start_address"]
            count = group["count"]

            if count == 1:
                # 単独アドレス → 個別読み取り
                logger.debug(f"📖 単独読み取り: DM{start_addr}")
                addr_bytes = start_addr.to_bytes(2, byteorder="big") + b"\x00"
                mem_area = fins_client.memory_area_read(b"\x82", addr_bytes, 1)
            else:
                # 連続アドレス → バッチ読み取り（最適化）
                logger.info(
                    f"🚀 バッチ読み取り: DM{start_addr}-DM{start_addr + count - 1} ({count}ワード)"
                )
                addr_bytes = start_addr.to_bytes(2, byteorder="big") + b"\x00"
                mem_area = fins_client.memory_area_read(b"\x82", addr_bytes, count)

            # 読み取った値を各項目に割り当て
            if mem_area and len(mem_area) >= count * 2:
                for i, key in enumerate(group["keys"]):
                    setting = group["settings"][i]
                    scale = setting.get("scale", 1)
                    # 2バイトずつ読み取り（Big-Endian）
                    offset = i * 2
                    raw_value = int.from_bytes(
                        mem_area[offset : offset + 2], byteorder="big"
                    )

                    # スケール適用
                    if scale > 1:
                        data[key] = raw_value / scale
                    else:
                        data[key] = raw_value

                    logger.debug(
                        f"  ✅ {key} = {data[key]} (raw: {raw_value}, scale: {scale})"
                    )

        except Exception as e:
            logger.error(f"❌ バッチ読み取りエラー (DM{group['start_address']}): {e}")
            # エラー時は個別に再試行
            for i, key in enumerate(group["keys"]):
                setting = group["settings"][i]
                addr_num = group["start_address"] + i
                try:
                    addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"
                    mem_area = fins_client.memory_area_read(b"\x82", addr_bytes, 1)
                    if mem_area and len(mem_area) >= 2:
                        raw_value = int.from_bytes(mem_area[0:2], byteorder="big")
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
            # 32bitワード順序（Phase 2）。実機確認まではオムロンも low_first を既定とする
            word_order = setting.get("word_order", "low_first")

            # バッチ読み取り済みのデータはスキップ
            if key in data:
                continue

            if address:

                def read_omron_data():
                    """オムロンPLCデータ読み取り関数（safe_plc_read用）"""
                    raw_value = None

                    # データ型別の処理
                    if data_type == "bit":
                        # ビットアドレス処理 (CIO100.01等)
                        if "." in address:
                            # ビット指定あり (例: CIO100.01)
                            base_addr, bit_pos = address.split(".")
                            bit_pos = int(bit_pos)

                            if base_addr.upper().startswith("CIO"):
                                addr_num = int(base_addr[3:])
                                # CIOエリア (0x30)
                                addr_bytes = addr_num.to_bytes(
                                    2, byteorder="big"
                                ) + bit_pos.to_bytes(1, byteorder="big")
                                mem_area = fins_client.memory_area_read(
                                    b"\x30", addr_bytes, 1
                                )
                                raw_value = mem_area[0] if mem_area else 0
                            elif base_addr.upper().startswith("WR"):
                                addr_num = int(base_addr[2:])
                                # WRエリア (0x31)
                                addr_bytes = addr_num.to_bytes(
                                    2, byteorder="big"
                                ) + bit_pos.to_bytes(1, byteorder="big")
                                mem_area = fins_client.memory_area_read(
                                    b"\x31", addr_bytes, 1
                                )
                                raw_value = mem_area[0] if mem_area else 0
                        else:
                            raise ValueError(
                                f"オムロンビットアドレスには.XX指定が必要: {address}"
                            )

                    elif data_type in ("float32", "dword"):
                        # 32bitデータ (2ワード) - float32またはdword
                        if address.upper().startswith("DM"):
                            addr_num = int(address[2:])
                        elif address.upper().startswith("D"):
                            addr_num = int(address[1:])
                        else:
                            raise ValueError(f"不明なアドレス形式: {address}")

                        # 2ワード読み取り
                        addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"
                        mem_area = fins_client.memory_area_read(b"\x82", addr_bytes, 2)

                        # 共通関数でfloat32/dwordに変換（Big-Endian）
                        if mem_area and len(mem_area) >= 4:
                            word1 = int.from_bytes(mem_area[0:2], byteorder="big")
                            word2 = int.from_bytes(mem_area[2:4], byteorder="big")
                            raw_value = convert_words_to_value(
                                word1, word2, data_type, word_order
                            )

                    else:
                        # 従来の16bitワード読み取り（DM エリア: 0x82）
                        if address.upper().startswith("DM"):
                            addr_num = int(address[2:])
                        elif address.upper().startswith("D"):
                            addr_num = int(address[1:])
                        else:
                            # D/DM以外（CIO/WR/HR等）はword直読み未対応。
                            # 未定義のaddr_numを参照する前にここで弾く
                            # （従来は UnboundLocalError が safe_plc_read に握りつぶされ、
                            #   紛らわしいエラーで静かに欠落していた）。
                            raise ValueError(f"不明なアドレス形式: {address}")

                        # アドレスをバイト形式に変換
                        addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"

                        # PLCからデータを読み取り（DM エリア: 0x82）
                        mem_area = fins_client.memory_area_read(b"\x82", addr_bytes, 1)

                        if mem_area and len(mem_area) >= 2:
                            raw_value = int.from_bytes(mem_area[0:2], byteorder="big")
                        else:
                            raise ValueError(f"不明なアドレス形式: {address}")

                    return raw_value

                # 安全な読み取り実行
                raw_value = safe_plc_read(read_omron_data, f"{key}({address})読み取り")

                # スケール適用 (ビット以外)
                if raw_value is not None:
                    if data_type == "bit":
                        data[key] = int(raw_value)  # ビットは0/1
                    elif scale > 1:
                        data[key] = raw_value / scale
                    else:
                        data[key] = raw_value
                else:
                    logger.warning(f"⚠️ {key}({address})のデータ取得に失敗")

    # 接続は自動でクローズされるため明示的な切断処理は不要

    if data:
        update_error_stats(True)
        logger.info(f"✅ オムロンPLC データ取得成功: {len(data)}項目")

    return data
