"""
シーメンスPLC用ドライバー

S7 Protocol を使用したシーメンスPLCとの通信を提供します。
- ポート: 102
- エンディアン: Big-Endian（S7のデータ本体。word_order=high_first）
- ライブラリ: python-snap7 >=3（Pure Python実装。C共有ライブラリ不要）

CLAUDE.md参照: PLCプロトコル基礎知識 - S7 Protocol
SPEC.md §7 参照: 開発はSnap7 server demoで検証、リリース判定前にS7-1200実機で最終確認
（PUT/GET許可・最適化ブロックアクセス無効化はシミュレータでは再現されないため）

Phase 5: スタブ → 実装。アドレス解析は純粋関数（parse_s7_address）として切り出し、
snap7非依存でユニットテスト可能にしている。32bit値の復元は共通の
convert_words_to_value を再利用し、S7既定の word_order=high_first で吸収する。
"""

import re
import logging

from .base import (
    validate_plc_ip,
    update_error_stats,
    retry_on_failure,
    convert_words_to_value,
    CONNECTION_TIMEOUT,
)

logger = logging.getLogger(__name__)

# S7のデータ本体はBig-Endian（先頭バイト=上位）。32bit結合の既定は high_first。
# SPEC.md §7「S7のデータ本体はBig-Endian（word_order=high_first）」に対応。
SIEMENS_DEFAULT_WORD_ORDER = "high_first"

# data_type → 読み取りバイト数
_DATA_TYPE_SIZE = {
    "bit": 1,
    "byte": 1,
    "word": 2,
    "dword": 4,
    "float32": 4,
}

# アドレス表記のサイズ文字 → 許容するdata_type（DBW/DBD等の幅を検証する）
# X=bit, B=byte(8bit), W=word(16bit), D=dword/float32(32bit)
_SIZE_CHAR_DATA_TYPES = {
    "X": {"bit"},
    "B": {"byte"},
    "W": {"word"},
    "D": {"dword", "float32"},
}

# S7メモリ域の先頭文字 → snap7のArea種別キー（DB以外）
# I(入力)=PE, Q(出力)=PA, M(内部メモリ/フラグ)=MK
_MEMORY_AREAS = {"M", "I", "Q"}


def _validate_size_char(size_char, data_type, address):
    """アドレス表記のサイズ文字とdata_typeの整合を検証する（不一致はValueError）。

    実際の読み取り幅は data_type 側で決まるため、表記の幅（例 DBW=2バイト）と
    data_type（例 float32=4バイト）が食い違うと、隣接領域を巻き込んだ誤値を
    黙って返してしまう。表記にサイズ文字がある場合はここで不一致を弾き、
    read_s7_value 側で None＋エラーログにして設定ミスを表面化させる
    （S7ドライバのコードレビュー指摘: bit/byte/word幅の取り違え）。
    """
    allowed = _SIZE_CHAR_DATA_TYPES.get(size_char)
    if allowed is not None and data_type not in allowed:
        raise ValueError(
            f"アドレス表記({size_char})とdata_type({data_type})が不一致です: {address}"
            f"（{size_char}が許容するのは {'/'.join(sorted(allowed))}）"
        )


def connect_siemens_plc(ip, rack=0, slot=1, timeout=CONNECTION_TIMEOUT):
    """
    シーメンスPLC接続（リトライ付き）
    CLAUDE.md参照: S7 Protocol, ポート102, Big-Endian

    Args:
        ip: PLCのIPアドレス
        rack: Rack番号（S7-300/400/1200/1500 とも通常0）
        slot: Slot番号（S7-1200/1500: 1、S7-300/400: 2）
        timeout: タイムアウト時間（秒）

    Returns:
        snap7.client.Client: S7接続オブジェクト、失敗時はNone
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    try:
        import snap7
    except ImportError:
        logger.error(
            "snap7ライブラリがインストールされていません: pip install 'python-snap7>=3'"
        )
        return None

    # snap7のタイムアウトはミリ秒指定。接続前にクライアントへ設定する必要がある。
    timeout_ms = max(int(timeout * 1000), 1000)

    def _connect():
        from snap7.type import Parameter

        plc = snap7.client.Client()
        plc.set_connection_type(3)  # OP接続（PG=1, OP=2, S7Basic=3。汎用のOP相当）
        # CLAUDE.md ルール4: 受け取ったtimeoutを実際にクライアントへ適用する。
        # Ping/Send/Recvの各タイムアウトを設定しないと、通信断時にsnap7が
        # 既定値までブロックしポーリング周期がストールする。
        plc.set_param(Parameter.PingTimeout, timeout_ms)
        plc.set_param(Parameter.SendTimeout, timeout_ms)
        plc.set_param(Parameter.RecvTimeout, timeout_ms)
        plc.connect(ip, rack, slot)
        if not plc.get_connected():
            raise ConnectionError("S7接続確立に失敗しました")
        logger.info(f"✅ シーメンスPLC接続成功: {ip} (Rack:{rack}, Slot:{slot})")
        return plc

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"シーメンスPLC接続失敗: {ip} - {e}")
        return None


def parse_s7_address(address, data_type="word"):
    """
    S7アドレス文字列を (area, db_number, byte_offset, bit_offset) に解析する（純粋関数）。

    対応表記:
        データブロック:
            DB1.DBX0.3  … DB1のバイト0・ビット3（bit）
            DB1.DBW10   … DB1のバイト10から2バイト（word）
            DB1.DBD20   … DB1のバイト20から4バイト（dword/float32）
            DB1.DBB4    … DB1のバイト4から1バイト（byte）
        メモリ域（M=内部メモリ, I=入力, Q=出力）:
            M10.3 / I0.1 / Q2.0  … ビット
            MW10  / IW0  / QW2   … word（2バイト）
            MD20  / ID0  / QD4   … dword（4バイト）
            MB4   / IB0  / QB2   … byte（1バイト）

    Args:
        address: S7アドレス文字列
        data_type: データ型（bit / word / dword / float32）。ビット要否の判定に使う

    Returns:
        tuple: (area, db_number, byte_offset, bit_offset)
            area       … "DB" / "M" / "I" / "Q"
            db_number  … DB番号（DB以外は0）
            byte_offset… バイトオフセット
            bit_offset … ビット番号（bit以外はNone）

    Raises:
        ValueError: 未知のアドレス形式、ビット読み取りでビット番号が欠落している場合、
            またはアドレス表記の幅（DBW/DBD/DBB/DBX等）とdata_typeが不一致の場合
    """
    addr = address.upper().strip()

    # --- データブロック: DB<n>.DB[X/W/D/B]<byte>[.<bit>] ---
    m = re.match(r"^DB(\d+)\.DB([XWDB])(\d+)(?:\.(\d+))?$", addr)
    if m:
        db_num = int(m.group(1))
        size_char = m.group(2)  # X=bit, W=word, D=dword, B=byte
        byte_offset = int(m.group(3))
        bit_offset = int(m.group(4)) if m.group(4) is not None else None

        # 表記の幅（X/B/W/D）とdata_typeの整合を検証する
        _validate_size_char(size_char, data_type, address)

        if size_char == "X" or data_type == "bit":
            if bit_offset is None:
                raise ValueError(f"ビットアドレスにはビット番号が必要です: {address}")
            if not 0 <= bit_offset <= 7:
                raise ValueError(f"ビット番号は0〜7の範囲です: {address}")
        return ("DB", db_num, byte_offset, bit_offset)

    # --- メモリ域: [M/I/Q][W/D/B?]<byte>[.<bit>] ---
    m = re.match(r"^([MIQ])([WDB]?)(\d+)(?:\.(\d+))?$", addr)
    if m:
        area = m.group(1)
        size_char = m.group(2)  # W/D/B、または空（M10.3のビット表記・裸のM10）
        byte_offset = int(m.group(3))
        bit_offset = int(m.group(4)) if m.group(4) is not None else None

        if size_char:
            # 明示的なサイズ文字（MW/MD/MB）はdata_typeと整合させる
            _validate_size_char(size_char, data_type, address)
        elif bit_offset is not None and data_type != "bit":
            # M10.3 のようなビット表記はdata_type=bitでなければ不一致
            raise ValueError(
                f"ビット表記(.{bit_offset})にはdata_type=bitが必要です: {address}"
            )

        if data_type == "bit":
            if bit_offset is None:
                raise ValueError(f"ビットアドレスにはビット番号が必要です: {address}")
            if not 0 <= bit_offset <= 7:
                raise ValueError(f"ビット番号は0〜7の範囲です: {address}")
        return (area, 0, byte_offset, bit_offset)

    raise ValueError(f"不明なS7アドレス形式: {address}")


def _resolve_area(area):
    """メモリ域の先頭文字を snap7 の Area 定数に変換する（I=PE, Q=PA, M=MK）"""
    from snap7.type import Area

    return {"M": Area.MK, "I": Area.PE, "Q": Area.PA}[area]


def _read_s7_bytes(plc, area, db_number, byte_offset, size):
    """S7から指定バイト数を読み取る（DBは db_read、M/I/Qは read_area）"""
    if area == "DB":
        return plc.db_read(db_number, byte_offset, size)
    return plc.read_area(_resolve_area(area), 0, byte_offset, size)


def _bytes_to_value(raw_bytes, data_type, bit_offset, word_order):
    """読み取ったバイト列を data_type に応じた値へ変換する（S7はBig-Endian）"""
    if data_type == "bit":
        return 1 if (raw_bytes[0] >> bit_offset) & 1 else 0

    if data_type == "byte":
        return raw_bytes[0]

    if data_type in ("dword", "float32"):
        # 4バイトを上位ワード・下位ワードに分割し、共通変換へ委譲する。
        # S7は先頭バイト=上位なので既定 word_order=high_first で元の32bit値を復元する。
        word1 = int.from_bytes(raw_bytes[0:2], "big")
        word2 = int.from_bytes(raw_bytes[2:4], "big")
        return convert_words_to_value(word1, word2, data_type, word_order)

    # word（16bit符号なし整数）
    return int.from_bytes(raw_bytes[0:2], "big")


def read_s7_value(plc, address, data_type="word", scale=1, word_order=None):
    """
    S7から1項目を読み取り、data_type・scaleを適用した値を返す（mockでテスト可能）。

    Args:
        plc: snap7クライアント
        address: S7アドレス（例: DB1.DBD0, MW10, I0.3）
        data_type: word / dword / float32 / bit
        scale: スケール係数（>1のとき除算。ビットには適用しない）
        word_order: 32bitワード順序。Noneのときシーメンス既定（high_first）

    Returns:
        読み取った値、エラー時はNone
    """
    if word_order is None:
        word_order = SIEMENS_DEFAULT_WORD_ORDER

    try:
        area, db_number, byte_offset, bit_offset = parse_s7_address(address, data_type)
        size = _DATA_TYPE_SIZE.get(data_type, 2)
        raw_bytes = _read_s7_bytes(plc, area, db_number, byte_offset, size)

        if raw_bytes is None or len(raw_bytes) < size:
            logger.error(
                f"S7読み取りバイト不足({address}): "
                f"{len(raw_bytes) if raw_bytes is not None else 0}/{size}"
            )
            return None

        value = _bytes_to_value(raw_bytes, data_type, bit_offset, word_order)

        if data_type == "bit":
            return int(value)
        if scale and scale > 1:
            return value / scale
        return value

    except Exception as e:
        logger.error(f"S7読み取りエラー({address}): {e}")
        return None


def read_siemens_plc(plc, data_points):
    """
    シーメンスPLCからデータを読み取る

    Args:
        plc: snap7クライアント（接続済み）
        data_points: データ項目の辞書

    Returns:
        dict: 読み取ったデータ
    """
    data = {}

    for key, setting in data_points.items():
        if not setting.get("enabled", False):
            continue

        address = setting.get("address")
        if not address:
            continue

        data_type = setting.get("data_type", "word")
        scale = setting.get("scale", 1)
        # 32bitワード順序（Phase 2）。シーメンスは先頭バイト=上位のため high_first 既定
        word_order = setting.get("word_order", SIEMENS_DEFAULT_WORD_ORDER)

        # read_s7_value は内部で例外を捕捉しNoneを返す（キーエンスドライバと同方式）
        raw_value = read_s7_value(plc, address, data_type, scale, word_order)

        if raw_value is not None:
            data[key] = raw_value
            logger.debug(f"  ✅ {key} = {raw_value} ({address}, {data_type})")
        else:
            logger.warning(f"⚠️ {key}({address})のデータ取得に失敗")

    # 接続を閉じる
    if plc:
        try:
            plc.disconnect()
        except Exception:
            pass

    if data:
        update_error_stats(True)
        logger.info(f"✅ シーメンスPLC データ取得成功: {len(data)}項目")
    else:
        logger.warning("⚠️ シーメンスPLC: データ取得なし")

    return data
