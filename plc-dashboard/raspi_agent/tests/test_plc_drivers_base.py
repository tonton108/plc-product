"""
plc_drivers.baseモジュールのユニットテスト
"""
import pytest
import sys
import os

# テスト対象のモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plc_drivers.base import (
    extract_address_number,
    group_continuous_word_addresses,
    generate_dummy_data,
)


class TestExtractAddressNumber:
    """extract_address_number関数のテスト"""

    def test_d_address(self):
        """Dアドレスの数値抽出"""
        assert extract_address_number("D100") == 100
        assert extract_address_number("D0") == 0
        assert extract_address_number("D9999") == 9999

    def test_dm_address(self):
        """DMアドレスの数値抽出"""
        assert extract_address_number("DM100") == 100
        assert extract_address_number("DM200") == 200

    def test_bit_address(self):
        """ビット指定付きアドレスの数値抽出"""
        assert extract_address_number("D100.5") == 100
        assert extract_address_number("M200.1") == 200

    def test_invalid_address(self):
        """無効なアドレス"""
        assert extract_address_number("INVALID") is None
        assert extract_address_number("") is None


class TestGroupContinuousWordAddresses:
    """group_continuous_word_addresses関数のテスト"""

    def test_continuous_addresses(self):
        """連続したアドレスのグループ化"""
        data_points = {
            "temp1": {"enabled": True, "data_type": "word", "address": "D100"},
            "temp2": {"enabled": True, "data_type": "word", "address": "D101"},
            "temp3": {"enabled": True, "data_type": "word", "address": "D102"},
        }
        groups = group_continuous_word_addresses(data_points, device_type='D')

        assert len(groups) == 1
        assert groups[0]['start_address'] == 100
        assert groups[0]['count'] == 3
        assert groups[0]['keys'] == ['temp1', 'temp2', 'temp3']

    def test_non_continuous_addresses(self):
        """非連続アドレスのグループ化"""
        data_points = {
            "temp1": {"enabled": True, "data_type": "word", "address": "D100"},
            "temp2": {"enabled": True, "data_type": "word", "address": "D105"},
            "temp3": {"enabled": True, "data_type": "word", "address": "D110"},
        }
        groups = group_continuous_word_addresses(data_points, device_type='D')

        assert len(groups) == 3
        assert groups[0]['start_address'] == 100
        assert groups[0]['count'] == 1
        assert groups[1]['start_address'] == 105
        assert groups[1]['count'] == 1

    def test_mixed_data_types(self):
        """異なるデータ型の混在（wordのみ抽出）"""
        data_points = {
            "temp1": {"enabled": True, "data_type": "word", "address": "D100"},
            "temp2": {"enabled": True, "data_type": "float32", "address": "D101"},
            "temp3": {"enabled": True, "data_type": "word", "address": "D103"},
        }
        groups = group_continuous_word_addresses(data_points, device_type='D')

        # float32は除外されるため、D100とD103の2グループ
        assert len(groups) == 2
        assert groups[0]['start_address'] == 100
        assert groups[0]['count'] == 1
        assert groups[1]['start_address'] == 103
        assert groups[1]['count'] == 1

    def test_disabled_items(self):
        """無効な項目の除外"""
        data_points = {
            "temp1": {"enabled": True, "data_type": "word", "address": "D100"},
            "temp2": {"enabled": False, "data_type": "word", "address": "D101"},
            "temp3": {"enabled": True, "data_type": "word", "address": "D102"},
        }
        groups = group_continuous_word_addresses(data_points, device_type='D')

        # D101（無効）は除外されるため、D100とD102の2グループ
        assert len(groups) == 2


class TestGenerateDummyData:
    """generate_dummy_data関数のテスト"""

    def test_word_type(self):
        """wordデータ型のダミー生成"""
        data_points = {
            "test_value": {"enabled": True, "data_type": "word"}
        }
        dummy = generate_dummy_data(data_points)

        assert "test_value" in dummy
        assert isinstance(dummy["test_value"], (int, float))

    def test_bit_type(self):
        """bitデータ型のダミー生成"""
        data_points = {
            "test_flag": {"enabled": True, "data_type": "bit"}
        }
        dummy = generate_dummy_data(data_points)

        assert "test_flag" in dummy
        assert dummy["test_flag"] in [0, 1]

    def test_float32_type(self):
        """float32データ型のダミー生成"""
        data_points = {
            "test_float": {"enabled": True, "data_type": "float32"}
        }
        dummy = generate_dummy_data(data_points)

        assert "test_float" in dummy
        assert isinstance(dummy["test_float"], float)

    def test_dword_type(self):
        """dwordデータ型のダミー生成"""
        data_points = {
            "test_dword": {"enabled": True, "data_type": "dword"}
        }
        dummy = generate_dummy_data(data_points)

        assert "test_dword" in dummy
        assert isinstance(dummy["test_dword"], int)
        assert 0 <= dummy["test_dword"] <= 4294967295

    def test_disabled_items_excluded(self):
        """無効な項目は生成されない"""
        data_points = {
            "enabled_item": {"enabled": True, "data_type": "word"},
            "disabled_item": {"enabled": False, "data_type": "word"}
        }
        dummy = generate_dummy_data(data_points)

        assert "enabled_item" in dummy
        assert "disabled_item" not in dummy

    def test_multiple_items(self):
        """複数項目のダミー生成"""
        data_points = {
            "temperature": {"enabled": True, "data_type": "word"},
            "pressure": {"enabled": True, "data_type": "float32"},
            "count": {"enabled": True, "data_type": "dword"},
            "error": {"enabled": True, "data_type": "bit"},
        }
        dummy = generate_dummy_data(data_points)

        assert len(dummy) == 4
        assert "temperature" in dummy
        assert "pressure" in dummy
        assert "count" in dummy
        assert "error" in dummy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
