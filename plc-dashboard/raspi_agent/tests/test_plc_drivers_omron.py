"""
オムロンPLCドライバーのユニットテスト

修正内容:
- FINSプロトコルのアドレスバイト順序の検証
- 修正前後の比較テスト
- 公式仕様書との適合性テスト
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# テスト対象のモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOmronAddressBytes:
    """オムロンFINSアドレスバイト生成のテスト"""

    @pytest.mark.unit
    def test_dm100_address_bytes_correct(self):
        """
        DM100のアドレスバイト生成（修正後）

        FINS仕様: word_address(2 bytes big-endian) + bit_position(1 byte)
        DM100 = 0x0064 → b'\x00\x64\x00'
        """
        addr_num = 100
        addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"

        # 期待値: b'\x00\x64\x00' (FINS公式仕様書と一致)
        expected = b"\x00\x64\x00"
        assert (
            addr_bytes == expected
        ), f"Expected {expected.hex()}, got {addr_bytes.hex()}"

    @pytest.mark.unit
    def test_dm100_address_bytes_wrong(self):
        """
        DM100のアドレスバイト生成（修正前の誤った実装）

        修正前のコードが生成するバイト列を検証
        """
        addr_num = 100
        wrong_bytes = b"\x00" + addr_num.to_bytes(2, byteorder="big")

        # 修正前: b'\x00\x00\x64' → DM0として誤認される
        assert wrong_bytes == b"\x00\x00\x64"

        # 正しいバイト列とは異なることを確認
        correct_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"
        assert wrong_bytes != correct_bytes, "修正前と修正後のバイト列は異なるべき"

    @pytest.mark.unit
    def test_various_dm_addresses(self):
        """様々なDMアドレスのバイト生成テスト"""
        test_cases = [
            (0, b"\x00\x00\x00"),  # DM0
            (1, b"\x00\x01\x00"),  # DM1
            (100, b"\x00\x64\x00"),  # DM100
            (255, b"\x00\xff\x00"),  # DM255
            (256, b"\x01\x00\x00"),  # DM256
            (1000, b"\x03\xe8\x00"),  # DM1000
            (32767, b"\x7f\xff\x00"),  # DM32767 (最大値)
        ]

        for addr_num, expected in test_cases:
            addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"
            assert (
                addr_bytes == expected
            ), f"DM{addr_num}: Expected {expected.hex()}, got {addr_bytes.hex()}"

    @pytest.mark.unit
    def test_address_byte_structure(self):
        """アドレスバイト構造の検証（FINS仕様準拠）"""
        addr_num = 100
        addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"

        # バイト長が3であることを確認
        assert len(addr_bytes) == 3, "FINSアドレスは3バイトである必要がある"

        # 最初の2バイトがアドレス値（Big-Endian）
        word_address = int.from_bytes(addr_bytes[0:2], byteorder="big")
        assert (
            word_address == 100
        ), f"ワードアドレスは100であるべき、実際は{word_address}"

        # 3バイト目がビット位置（通常は0）
        bit_position = addr_bytes[2]
        assert bit_position == 0, f"ビット位置は0であるべき、実際は{bit_position}"

    @pytest.mark.unit
    def test_fins_official_example(self):
        """
        FINS公式仕様書の例との一致確認

        公式マニュアル W227-E1-2 より:
        DM100から150ワード読み取り
        - fins_cmnd[12] = 0x82  (DMエリアコード)
        - fins_cmnd[13] = 0x00  (アドレス高位)
        - fins_cmnd[14] = 0x64  (アドレス中位) = 100
        - fins_cmnd[15] = 0x00  (アドレス低位/ビット位置)
        """
        addr_num = 100
        addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"

        # 公式例と一致することを確認
        assert addr_bytes[0] == 0x00, "アドレス高位バイトが不一致"
        assert addr_bytes[1] == 0x64, "アドレス中位バイトが不一致（公式例: 0x64=100）"
        assert addr_bytes[2] == 0x00, "アドレス低位バイト/ビット位置が不一致"


class TestOmronPLCReadWithMock:
    """モックを使ったオムロンPLC読み取り統合テスト"""

    @pytest.mark.unit
    def test_read_omron_plc_calls_with_correct_address_bytes(self):
        """
        read_omron_plc関数が正しいアドレスバイトでmemory_area_readを呼び出すか検証
        """
        # モックのFINSクライアント作成
        mock_fins = Mock()
        mock_fins.memory_area_read.return_value = b"\x00\x64"  # DM100の値=100

        data_points = {
            "temp": {
                "enabled": True,
                "data_type": "word",
                "address": "D100",
                "scale": 1,
            }
        }

        # 実際の関数をインポートして実行
        from plc_drivers.omron import read_omron_plc

        # ※ 例外をpytest.skipで握りつぶすと不具合を見逃すため、直接検証する
        read_omron_plc(mock_fins, data_points)

        # memory_area_readが正しいパラメータで呼ばれたか検証（最初の呼び出し）
        call_args = mock_fins.memory_area_read.call_args_list[0]
        args, kwargs = call_args
        memory_area_code = args[0]
        addr_bytes = args[1]
        read_count = args[2]

        # DMエリアコード（0x82）の確認
        assert (
            memory_area_code == b"\x82"
        ), f"メモリエリアコードが不正: {memory_area_code.hex()}"

        # アドレスバイト列が正しいことを確認
        expected_addr = b"\x00\x64\x00"  # DM100
        assert (
            addr_bytes == expected_addr
        ), f"アドレスバイトが不正: expected {expected_addr.hex()}, got {addr_bytes.hex()}"

        # 読み取りサイズの確認
        assert read_count == 1, f"読み取りサイズが不正: {read_count}"

    @pytest.mark.unit
    def test_multiple_address_batch_read(self):
        """連続アドレスのバッチ読み取りテスト"""
        mock_fins = Mock()
        # 3ワード分のデータを返す（DM100, DM101, DM102）
        mock_fins.memory_area_read.return_value = b"\x00\x64\x00\x65\x00\x66"

        data_points = {
            "temp1": {
                "enabled": True,
                "data_type": "word",
                "address": "D100",
                "scale": 1,
            },
            "temp2": {
                "enabled": True,
                "data_type": "word",
                "address": "D101",
                "scale": 1,
            },
            "temp3": {
                "enabled": True,
                "data_type": "word",
                "address": "D102",
                "scale": 1,
            },
        }

        from plc_drivers.omron import read_omron_plc

        # ※ 連続する"D100/101/102"は1回のバッチ読み取り（count=3）にまとまるべき。
        #   device_type="DM"のバグ時はグループ化されず個別3回になり、この検証が
        #   pytest.skipで握りつぶされていた（O1修正で解消）。
        read_omron_plc(mock_fins, data_points)

        # バッチ読み取りで正しいアドレスとサイズが指定されているか
        call_args = mock_fins.memory_area_read.call_args_list[0]
        args, kwargs = call_args
        addr_bytes = args[1]
        read_count = args[2]

        # 開始アドレスがDM100（b'\x00\x64\x00'）
        assert (
            addr_bytes == b"\x00\x64\x00"
        ), f"バッチ読み取り開始アドレスが不正: {addr_bytes.hex()}"

        # 読み取りサイズが3ワード（＝バッチが発動している証拠）
        assert read_count == 3, f"バッチ読み取りサイズが不正: {read_count}"
        # 個別3回ではなく1回のバッチ呼び出しであること
        assert (
            mock_fins.memory_area_read.call_count == 1
        ), f"バッチ最適化が効いていない（呼び出し回数={mock_fins.memory_area_read.call_count}）"


class TestOmronFloat32DwordAddressing:
    """float32とdwordの2ワードアドレッシングテスト"""

    @pytest.mark.unit
    def test_float32_address_bytes(self):
        """float32読み取り時のアドレスバイト（2ワード読み取り）"""
        addr_num = 100
        addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"

        # float32でも同じアドレスバイト構造を使用
        assert addr_bytes == b"\x00\x64\x00"
        assert len(addr_bytes) == 3

    @pytest.mark.unit
    def test_dword_address_bytes(self):
        """dword読み取り時のアドレスバイト（2ワード読み取り）"""
        addr_num = 200
        addr_bytes = addr_num.to_bytes(2, byteorder="big") + b"\x00"

        # dwordでも同じアドレスバイト構造を使用
        assert addr_bytes == b"\x00\xc8\x00"  # 0xc8 = 200
        assert len(addr_bytes) == 3


class TestOmronConnectTimeout:
    """接続時のタイムアウト適用（CLAUDE.md ルール4）"""

    @pytest.mark.unit
    def test_connect_overrides_socket_timeout(self):
        # finsライブラリのconnect()は1.0秒固定でsettimeoutするため、
        # 受け取ったtimeoutで上書きすること（未上書きだと設定値が無視される）。
        from plc_drivers.omron import connect_omron_plc

        mock_client = MagicMock()
        with patch("fins.udp.UDPFinsConnection", return_value=mock_client):
            client = connect_omron_plc("192.168.0.10", timeout=5)

        assert client is mock_client
        mock_client.fins_socket.settimeout.assert_called_once_with(5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
