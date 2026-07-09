"""
32bitワード順序（word_order）変換のテスト（Phase 2）

三菱の公式マニュアルで確定した「先頭アドレス=下位ワード（low_first）」を
中心に、convert_words_to_value の両順序を検証する。
旧版の (word1<<16)|word2 固定では三菱の32bit値が化けていた既知バグの回帰防止。
"""

import struct

import pytest

from plc_drivers.converters import (
    convert_words_to_value,
    convert_words_to_dword,
    convert_words_to_float32,
)


class TestDwordWordOrder:
    """dword（32bit整数）のワード順序"""

    def test_high_first(self):
        # word1=0x1234（上位）, word2=0x5678（下位） → 0x12345678
        assert (
            convert_words_to_value(0x1234, 0x5678, "dword", "high_first") == 0x12345678
        )

    def test_low_first(self):
        # word1=0x5678（下位）, word2=0x1234（上位） → 0x12345678
        # 三菱: 先頭アドレス side（word1）が下位
        assert (
            convert_words_to_value(0x5678, 0x1234, "dword", "low_first") == 0x12345678
        )

    def test_orders_differ(self):
        """同じ2ワードでも順序指定で結果が変わる（取り違え防止）"""
        high = convert_words_to_value(0x0001, 0x0000, "dword", "high_first")
        low = convert_words_to_value(0x0001, 0x0000, "dword", "low_first")
        assert high == 0x00010000  # 65536
        assert low == 0x00000001  # 1
        assert high != low

    def test_dword_helper_default_low_first(self):
        """convert_words_to_dword の既定はシステム既定の low_first（三菱）"""
        # low_first: word1=下位, word2=上位 → (0x0000<<16)|0x0001 = 1
        assert convert_words_to_dword(0x0001, 0x0000) == 0x00000001


class TestFloat32WordOrder:
    """float32（IEEE754）のワード順序"""

    @staticmethod
    def _split_float(value):
        """floatをIEEE754 Big-Endianの2ワード（上位, 下位）に分解"""
        packed = struct.pack(">f", value)
        upper = (packed[0] << 8) | packed[1]
        lower = (packed[2] << 8) | packed[3]
        return upper, lower

    def test_high_first_roundtrip(self):
        upper, lower = self._split_float(3.14)
        # high_first: 先に読むword1が上位
        value = convert_words_to_value(upper, lower, "float32", "high_first")
        assert abs(value - 3.14) < 0.001

    def test_low_first_roundtrip(self):
        upper, lower = self._split_float(3.14)
        # low_first（三菱）: 先に読むword1が下位。格納順は (下位, 上位)
        value = convert_words_to_value(lower, upper, "float32", "low_first")
        assert abs(value - 3.14) < 0.001

    def test_mitsubishi_075_example(self):
        """三菱公式マニュアルの例: 実数0.75 → D0=0x0000(下位), D1=0x3F40(上位)"""
        # batchread_wordunits はアドレス昇順 [D0, D1] を返す = [0x0000, 0x3F40]
        value = convert_words_to_value(0x0000, 0x3F40, "float32", "low_first")
        assert abs(value - 0.75) < 0.0001

    def test_float32_helper_default_low_first(self):
        """convert_words_to_float32 の既定は low_first（三菱）"""
        upper, lower = self._split_float(100.5)
        # low_first既定なので、先頭に下位(lower)・次に上位(upper)を渡すと復元される
        assert abs(convert_words_to_float32(lower, upper) - 100.5) < 0.001
