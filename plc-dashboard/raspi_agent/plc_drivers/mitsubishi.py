"""
三菱電機PLC用ドライバー

MC Protocol (SLMP) を使用した三菱PLCとの通信を提供します。
- ポート: 5000/5007
- エンディアン: Big-Endian
- ライブラリ: pymcprotocol

CLAUDE.md参照: PLCプロトコル基礎知識 - MC Protocol

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

logger = logging.getLogger(__name__)


def connect_mitsubishi_plc(ip, port, timeout=CONNECTION_TIMEOUT):
    """
    三菱PLC接続（タイムアウト付き）
    CLAUDE.md参照: MC Protocol (SLMP), ポート5000/5007, Big-Endian

    Args:
        ip: PLCのIPアドレス
        port: PLCのポート番号（通常5000または5007）
        timeout: タイムアウト時間（秒）

    Returns:
        pymcprotocol.Type3E: PLC接続オブジェクト、失敗時はNone
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    from pymcprotocol import Type3E

    def _connect():
        plc = Type3E()
        plc.setaccessopt(commtype="binary")  # バイナリモード（高速）
        plc.connect(ip, port)
        logger.info(f"✅ 三菱PLC接続成功: {ip}:{port}")
        return plc

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"三菱PLC接続失敗: {ip}:{port} - {e}")
        return None


def read_mitsubishi_plc(plc, data_points):
    """
    三菱PLCからデータを読み取り

    Args:
        plc: PLC接続オブジェクト
        data_points: データ項目の辞書

    Returns:
        dict: 読み取ったデータ
    """
    data = {}

    # バッチ読み取り最適化: 連続したwordアドレスをグループ化
    word_groups = group_continuous_word_addresses(data_points, device_type='D')

    # グループ化されたwordアドレスを一括読み取り
    for group in word_groups:
        try:
            if group['count'] == 1:
                # 単独アドレス → 個別読み取り
                logger.debug(f"📖 単独読み取り: D{group['start_address']}")
                raw_values = plc.batchread_wordunits(
                    headdevice=f"D{group['start_address']}",
                    readsize=1
                )
            else:
                # 連続アドレス → バッチ読み取り（最適化）
                logger.info(f"🚀 バッチ読み取り: D{group['start_address']}-D{group['start_address'] + group['count'] - 1} ({group['count']}ワード)")
                raw_values = plc.batchread_wordunits(
                    headdevice=f"D{group['start_address']}",
                    readsize=group['count']
                )

            # 読み取った値を各項目に割り当て
            for i, key in enumerate(group['keys']):
                setting = group['settings'][i]
                scale = setting.get("scale", 1)
                raw_value = raw_values[i]

                # スケール適用
                if scale > 1:
                    data[key] = raw_value / scale
                else:
                    data[key] = raw_value

                logger.debug(f"  ✅ {key} = {data[key]} (raw: {raw_value}, scale: {scale})")

        except Exception as e:
            logger.error(f"❌ バッチ読み取りエラー (D{group['start_address']}): {e}")
            # エラー時は個別に再試行
            for i, key in enumerate(group['keys']):
                setting = group['settings'][i]
                addr_num = group['start_address'] + i
                try:
                    raw_value = plc.batchread_wordunits(f"D{addr_num}", 1)[0]
                    scale = setting.get("scale", 1)
                    data[key] = raw_value / scale if scale > 1 else raw_value
                except Exception:
                    logger.warning(f"⚠️ {key}(D{addr_num})の個別再試行も失敗")

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
                def read_mitsubishi_data():
                    """三菱PLCデータ読み取り関数（safe_plc_read用）"""
                    raw_value = None

                    # データ型別の処理
                    if data_type == "bit":
                        # ビットアドレス処理 (M100.1, X001等)
                        if '.' in address:
                            # ビット指定あり (例: M100.1)
                            base_addr, bit_pos = address.split('.')
                            bit_pos = int(bit_pos)
                            device_type = base_addr[0]
                            addr_num = int(base_addr[1:])

                            # ビット読み取り
                            bit_values = plc.batchread_bitunits(
                                headdevice=f"{device_type}{addr_num}",
                                readsize=1
                            )
                            raw_value = bit_values[0] if bit_values else 0
                        else:
                            # 単体ビットアドレス (例: M100, X001)
                            device_type = address[0]
                            addr_num = int(address[1:])

                            bit_values = plc.batchread_bitunits(
                                headdevice=f"{device_type}{addr_num}",
                                readsize=1
                            )
                            raw_value = bit_values[0] if bit_values else 0

                    elif data_type in ("float32", "dword"):
                        # 32bitデータ (2ワード) - float32またはdword
                        # CLAUDE.md参照: 三菱PLCはBig-Endianで通信
                        if address.upper().startswith('D'):
                            addr_num = int(address[1:])
                        elif address.upper().startswith('DM'):
                            addr_num = int(address[2:])
                        else:
                            raise ValueError(f"不明なアドレス形式: {address}")

                        # 2ワード読み取り (32bit)
                        word_values = plc.batchread_wordunits(
                            headdevice=f"D{addr_num}",
                            readsize=2
                        )

                        # 共通関数でfloat32/dwordに変換（Big-Endian）
                        if len(word_values) >= 2:
                            raw_value = convert_words_to_value(
                                word_values[0], word_values[1], data_type
                            )

                    else:
                        # 従来の16bitワード読み取り
                        if address.upper().startswith('D'):
                            addr_num = int(address[1:])
                        elif address.upper().startswith('DM'):
                            addr_num = int(address[2:])
                        else:
                            raise ValueError(f"不明なアドレス形式: {address}")

                        # PLCからデータを読み取り
                        raw_value = plc.batchread_wordunits(
                            headdevice=f"D{addr_num}",
                            readsize=1
                        )[0]  # リストの最初の要素を取得

                    return raw_value

                # 安全な読み取り実行
                raw_value = safe_plc_read(read_mitsubishi_data, f"{key}({address})読み取り")

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

    if data:
        update_error_stats(True)
        logger.info(f"✅ 三菱PLC データ取得成功: {len(data)}項目")

    return data
