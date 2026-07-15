"""
シーメンスPLCドライバー（S7 Protocol）のユニットテスト

検証内容:
- S7アドレス解析（DB / M / I / Q、bit/word/dword/float32）
- バイト列→値変換（Big-Endian、word_order=high_first）
- モックsnap7クライアントでのdb_read / read_area呼び出し
- スケール適用・エラー処理

実機（S7-1200）はSPEC.md §7に従いリリース判定時に確認する。
本テストはsnap7の有無やネットワークに依存しない（read_areaのArea定数解決も
モックで置換して検証する）。
"""

import struct
import sys
import os
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plc_drivers.siemens import (  # noqa: E402
    parse_s7_address,
    read_s7_value,
    read_siemens_plc,
    SIEMENS_DEFAULT_WORD_ORDER,
)


class TestParseS7Address:
    """S7アドレス解析"""

    @pytest.mark.unit
    def test_db_word(self):
        assert parse_s7_address("DB1.DBW10", "word") == ("DB", 1, 10, None)

    @pytest.mark.unit
    def test_db_dword(self):
        assert parse_s7_address("DB2.DBD20", "dword") == ("DB", 2, 20, None)

    @pytest.mark.unit
    def test_db_real_uses_dbd(self):
        # float32(REAL)はDBD表記
        assert parse_s7_address("DB1.DBD0", "float32") == ("DB", 1, 0, None)

    @pytest.mark.unit
    def test_db_bit(self):
        assert parse_s7_address("DB1.DBX0.3", "bit") == ("DB", 1, 0, 3)

    @pytest.mark.unit
    def test_db_byte(self):
        assert parse_s7_address("DB3.DBB4", "word") == ("DB", 3, 4, None)

    @pytest.mark.unit
    def test_db_bit_without_bit_number_raises(self):
        # DBXなのにビット番号が無い
        with pytest.raises(ValueError, match="ビット番号が必要"):
            parse_s7_address("DB1.DBX0", "bit")

    @pytest.mark.unit
    def test_db_bit_out_of_range_raises(self):
        with pytest.raises(ValueError, match="0〜7"):
            parse_s7_address("DB1.DBX0.8", "bit")

    @pytest.mark.unit
    def test_memory_word(self):
        assert parse_s7_address("MW10", "word") == ("M", 0, 10, None)

    @pytest.mark.unit
    def test_memory_dword(self):
        assert parse_s7_address("MD20", "dword") == ("M", 0, 20, None)

    @pytest.mark.unit
    def test_input_bit(self):
        assert parse_s7_address("I0.1", "bit") == ("I", 0, 0, 1)

    @pytest.mark.unit
    def test_output_bit(self):
        assert parse_s7_address("Q2.0", "bit") == ("Q", 0, 2, 0)

    @pytest.mark.unit
    def test_input_word(self):
        assert parse_s7_address("IW4", "word") == ("I", 0, 4, None)

    @pytest.mark.unit
    def test_lowercase_is_accepted(self):
        assert parse_s7_address("db1.dbw10", "word") == ("DB", 1, 10, None)

    @pytest.mark.unit
    def test_memory_bit_without_bit_number_raises(self):
        with pytest.raises(ValueError, match="ビット番号が必要"):
            parse_s7_address("M10", "bit")

    @pytest.mark.unit
    def test_invalid_address_raises(self):
        with pytest.raises(ValueError, match="不明なS7アドレス形式"):
            parse_s7_address("XYZ100", "word")


class TestReadS7ValueWithMock:
    """モックsnap7クライアントでの読み取り"""

    @staticmethod
    def _mock_plc_db(raw_bytes):
        plc = Mock()
        plc.db_read.return_value = bytearray(raw_bytes)
        return plc

    @pytest.mark.unit
    def test_word_read_big_endian(self):
        # 0x0064 = 100（Big-Endian）
        plc = self._mock_plc_db(b"\x00\x64")
        value = read_s7_value(plc, "DB1.DBW0", "word")
        assert value == 100
        plc.db_read.assert_called_once_with(1, 0, 2)

    @pytest.mark.unit
    def test_dword_read_big_endian(self):
        # 0x00012345 = 74565
        plc = self._mock_plc_db(struct.pack(">I", 74565))
        value = read_s7_value(plc, "DB1.DBD0", "dword")
        assert value == 74565
        plc.db_read.assert_called_once_with(1, 0, 4)

    @pytest.mark.unit
    def test_float32_read(self):
        # REAL 3.14 のBig-Endian 4バイト
        plc = self._mock_plc_db(struct.pack(">f", 3.14))
        value = read_s7_value(plc, "DB1.DBD0", "float32")
        assert abs(value - 3.14) < 0.001

    @pytest.mark.unit
    def test_float32_negative(self):
        plc = self._mock_plc_db(struct.pack(">f", -12.5))
        value = read_s7_value(plc, "DB1.DBD4", "float32")
        assert abs(value - (-12.5)) < 0.001
        plc.db_read.assert_called_once_with(1, 4, 4)

    @pytest.mark.unit
    def test_bit_read_set(self):
        # バイト0b00001000 のビット3は1
        plc = self._mock_plc_db(bytes([0b00001000]))
        value = read_s7_value(plc, "DB1.DBX0.3", "bit")
        assert value == 1
        plc.db_read.assert_called_once_with(1, 0, 1)

    @pytest.mark.unit
    def test_bit_read_clear(self):
        # バイト0b00001000 のビット2は0
        plc = self._mock_plc_db(bytes([0b00001000]))
        value = read_s7_value(plc, "DB1.DBX0.2", "bit")
        assert value == 0

    @pytest.mark.unit
    def test_scale_applied_to_word(self):
        # 250 / 10 = 25.0
        plc = self._mock_plc_db(struct.pack(">H", 250))
        value = read_s7_value(plc, "DB1.DBW0", "word", scale=10)
        assert value == 25.0

    @pytest.mark.unit
    def test_scale_not_applied_to_bit(self):
        plc = self._mock_plc_db(bytes([0b00000001]))
        value = read_s7_value(plc, "DB1.DBX0.0", "bit", scale=10)
        assert value == 1

    @pytest.mark.unit
    def test_default_word_order_is_high_first(self):
        # S7既定はhigh_first。0x4049_0FDB ≈ 3.14159 を先頭バイト=上位で格納
        raw = struct.pack(">I", 0x40490FDB)
        plc = self._mock_plc_db(raw)
        value = read_s7_value(plc, "DB1.DBD0", "float32")
        assert abs(value - 3.14159) < 0.001

    @pytest.mark.unit
    def test_word_order_override_low_first(self):
        # word_orderを明示的にlow_firstにすると結果が変わる（取り違え防止）
        raw = struct.pack(">I", 0x40490FDB)
        plc = self._mock_plc_db(raw)
        high = read_s7_value(plc, "DB1.DBD0", "dword", word_order="high_first")
        low = read_s7_value(plc, "DB1.DBD0", "dword", word_order="low_first")
        assert high == 0x40490FDB
        assert low == 0x0FDB4049
        assert high != low

    @pytest.mark.unit
    def test_read_error_returns_none(self):
        plc = Mock()
        plc.db_read.side_effect = RuntimeError("接続断")
        value = read_s7_value(plc, "DB1.DBW0", "word")
        assert value is None

    @pytest.mark.unit
    def test_insufficient_bytes_returns_none(self):
        # 4バイト要求に対し2バイトしか返らない
        plc = Mock()
        plc.db_read.return_value = bytearray(b"\x00\x01")
        value = read_s7_value(plc, "DB1.DBD0", "dword")
        assert value is None

    @pytest.mark.unit
    def test_memory_area_uses_read_area(self, monkeypatch):
        # M域はread_areaを使う。Area定数解決をモックしsnap7非依存にする
        import plc_drivers.siemens as siemens_mod

        sentinel_area = object()
        monkeypatch.setattr(siemens_mod, "_resolve_area", lambda area: sentinel_area)

        plc = Mock()
        plc.read_area.return_value = bytearray(struct.pack(">H", 42))
        value = read_s7_value(plc, "MW10", "word")

        assert value == 42
        plc.read_area.assert_called_once_with(sentinel_area, 0, 10, 2)
        plc.db_read.assert_not_called()


class TestReadSiemensPLC:
    """read_siemens_plc 統合（複数項目・disconnect）"""

    @pytest.mark.unit
    def test_reads_multiple_enabled_points(self):
        plc = Mock()
        # DBW0=10, DBD4=REAL 1.5
        plc.db_read.side_effect = [
            bytearray(struct.pack(">H", 10)),
            bytearray(struct.pack(">f", 1.5)),
        ]

        data_points = {
            "count": {"enabled": True, "data_type": "word", "address": "DB1.DBW0"},
            "temp": {"enabled": True, "data_type": "float32", "address": "DB1.DBD4"},
            "skip": {"enabled": False, "data_type": "word", "address": "DB1.DBW8"},
        }

        result = read_siemens_plc(plc, data_points)

        assert result["count"] == 10
        assert abs(result["temp"] - 1.5) < 0.001
        assert "skip" not in result
        plc.disconnect.assert_called_once()

    @pytest.mark.unit
    def test_disconnect_called_even_on_empty(self):
        plc = Mock()
        result = read_siemens_plc(plc, {})
        assert result == {}
        plc.disconnect.assert_called_once()

    @pytest.mark.unit
    def test_failed_point_is_skipped_not_fatal(self):
        plc = Mock()
        # 1項目目は成功、2項目目は例外
        plc.db_read.side_effect = [
            bytearray(struct.pack(">H", 7)),
            RuntimeError("読み取り失敗"),
        ]
        data_points = {
            "ok": {"enabled": True, "data_type": "word", "address": "DB1.DBW0"},
            "ng": {"enabled": True, "data_type": "word", "address": "DB1.DBW2"},
        }
        result = read_siemens_plc(plc, data_points)
        assert result["ok"] == 7
        assert "ng" not in result

    @pytest.mark.unit
    def test_default_word_order_constant(self):
        # SPEC.md §7: S7のデータ本体はBig-Endian（high_first）
        assert SIEMENS_DEFAULT_WORD_ORDER == "high_first"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
