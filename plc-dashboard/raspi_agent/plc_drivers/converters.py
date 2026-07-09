"""
データ型変換モジュール

Phase 11リファクタリング: base.pyから分割
Phase 2: ワード順序（word_order）をメーカー・機種ごとに指定可能に変更

32bit値（dword/float32）を2ワードから復元する。ワード間の順序は
メーカー・機種依存（詳細は _docs/plc-knowledge/endianness.md）:
- high_first: 先に読んだワードが上位（シーメンスS7等）
- low_first : 先に読んだワードが下位（三菱MELSEC等）★三菱の既定

旧版は全メーカーを high_first 相当（(word1<<16)|word2）で固定していたが、
三菱の公式マニュアルにより「先頭アドレス=下位ワード」が確定したため、
word_order を導入して設備/項目ごとに切り替えられるようにした。
バイト列の組み立ては常に Big-Endian(">") 表記で統一し、順序差は
pack に渡すワードの並びで吸収する。
"""

import struct
import logging

logger = logging.getLogger(__name__)

WORD_ORDER_HIGH_FIRST = "high_first"
WORD_ORDER_LOW_FIRST = "low_first"


def _combine_words(word1, word2, word_order):
    """先に読んだ word1, 次の word2 を word_order に従って32bitに結合する"""
    if word_order == WORD_ORDER_LOW_FIRST:
        # 先頭アドレス側（word1）が下位ワード
        return (word2 << 16) | word1
    # high_first（既定の後方互換）: 先頭アドレス側（word1）が上位ワード
    return (word1 << 16) | word2


def convert_words_to_float32(word1, word2, word_order=WORD_ORDER_HIGH_FIRST):
    """
    2ワードをIEEE754 float32に変換

    Args:
        word1: 先に読んだワード（先頭アドレス側）
        word2: 次に読んだワード
        word_order: ワード間順序（"high_first" / "low_first"）

    Returns:
        float: 変換されたfloat32値
    """
    combined = _combine_words(word1, word2, word_order)
    return struct.unpack(">f", struct.pack(">I", combined))[0]


def convert_words_to_dword(word1, word2, word_order=WORD_ORDER_HIGH_FIRST):
    """
    2ワードを32bit整数（dword）に変換

    Args:
        word1: 先に読んだワード（先頭アドレス側）
        word2: 次に読んだワード
        word_order: ワード間順序（"high_first" / "low_first"）

    Returns:
        int: 変換された32bit整数
    """
    return _combine_words(word1, word2, word_order)


def convert_words_to_value(word1, word2, data_type="dword", word_order=WORD_ORDER_HIGH_FIRST):
    """
    2ワードを指定データ型に変換

    統一的なインターフェースでfloat32とdwordの変換を提供します。

    Args:
        word1: 先に読んだワード（先頭アドレス側）
        word2: 次に読んだワード
        data_type: データ型（"float32" または "dword"）
        word_order: ワード間順序（"high_first" / "low_first"）

    Returns:
        変換された値（float or int）

    Example:
        # 三菱（low_first）でのfloat32変換
        value = convert_words_to_value(0x0000, 0x4120, "float32", "low_first")  # 10.0
    """
    combined = _combine_words(word1, word2, word_order)
    if data_type == "float32":
        return struct.unpack(">f", struct.pack(">I", combined))[0]
    else:  # dword
        return combined
