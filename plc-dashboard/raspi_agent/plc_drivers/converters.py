"""
データ型変換モジュール

Phase 11リファクタリング: base.pyから分割

全メーカー共通のBig-Endianデータ変換機能を提供します：
- 2ワード → float32（IEEE754）
- 2ワード → dword（32bit整数）
- 統一インターフェース
"""

import struct
import logging

logger = logging.getLogger(__name__)


def convert_words_to_float32(word1, word2):
    """
    2ワードをIEEE754 float32に変換（Big-Endian）

    CLAUDE.md参照: PLCプロトコル基礎知識 - エンディアン
    すべてのPLCでBig-Endianを使用します。

    Args:
        word1: 上位ワード（16bit）
        word2: 下位ワード（16bit）

    Returns:
        float: 変換されたfloat32値
    """
    combined = (word1 << 16) | word2
    return struct.unpack('>f', struct.pack('>I', combined))[0]


def convert_words_to_dword(word1, word2):
    """
    2ワードを32bit整数（dword）に変換（Big-Endian）

    CLAUDE.md参照: PLCプロトコル基礎知識 - エンディアン
    すべてのPLCでBig-Endianを使用します。

    Args:
        word1: 上位ワード（16bit）
        word2: 下位ワード（16bit）

    Returns:
        int: 変換された32bit整数
    """
    return (word1 << 16) | word2


def convert_words_to_value(word1, word2, data_type="dword"):
    """
    2ワードを指定データ型に変換（Big-Endian）

    統一的なインターフェースでfloat32とdwordの変換を提供します。

    Args:
        word1: 上位ワード（16bit）
        word2: 下位ワード（16bit）
        data_type: データ型（"float32" または "dword"）

    Returns:
        変換された値（float or int）

    Example:
        # float32変換
        value = convert_words_to_value(0x4120, 0x0000, "float32")  # 10.0

        # dword変換
        value = convert_words_to_value(0x0001, 0x0000, "dword")  # 65536
    """
    combined = (word1 << 16) | word2
    if data_type == "float32":
        return struct.unpack('>f', struct.pack('>I', combined))[0]
    else:  # dword
        return combined
