"""
plc_agent の接続クローズ（リソースリーク）回帰テスト

各PLCドライバの読み取り中に例外が発生しても、PLC接続が確実に閉じられることを
検証する。

- 三菱: 旧実装は read_mitsubishi_plc の後ろに素で plc.close() を置いており、
  read_mitsubishi_plc（内部のアドレスグループ化は try 外）が例外を送出すると
  read_from_real_plc の except へ伝播し、close() がスキップされてソケットが
  リークしていた。
- オムロン: UDPFinsConnection に close/disconnect が無く、旧実装は明示クローズが
  皆無で GC(__del__) 頼みだった。read_from_real_plc で fins_socket を明示的に
  閉じる（正常時・例外時とも）。
- キーエンス: 旧実装は関数末尾に素で client.close() を置いており、末尾より前の
  group_continuous_word_addresses が例外を送出すると close がスキップされていた。
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMitsubishiConnectionClosed:
    def _config(self):
        return {
            "equipment_id": "TEST_EQ",
            "plc_ip": "192.168.1.100",
            "plc_port": 5000,
            "manufacturer": "三菱",
            "data_points": {},
        }

    @pytest.mark.unit
    def test_close_called_on_read_success(self):
        """正常読み取り時に close される（従来動作の維持）"""
        from plc_agent import read_from_real_plc

        mock_plc = MagicMock()
        with patch("plc_agent.connect_mitsubishi_plc", return_value=mock_plc), patch(
            "plc_agent.read_mitsubishi_plc", return_value={"temp": 25}
        ):
            result = read_from_real_plc(
                self._config(), "192.168.1.100", 5000, "三菱", {}
            )

        assert result == {"temp": 25}
        mock_plc.close.assert_called_once()

    @pytest.mark.unit
    def test_close_called_when_read_raises(self):
        """読み取りが例外を送出しても close される（リーク防止）"""
        from plc_agent import read_from_real_plc

        mock_plc = MagicMock()
        with patch("plc_agent.connect_mitsubishi_plc", return_value=mock_plc), patch(
            "plc_agent.read_mitsubishi_plc", side_effect=RuntimeError("グループ化失敗")
        ), patch("plc_agent.report_error"):
            result = read_from_real_plc(
                self._config(), "192.168.1.100", 5000, "三菱", {}
            )

        # 例外は read_from_real_plc の except で握られ None が返るが、
        # その前に finally で close されていること
        assert result is None
        mock_plc.close.assert_called_once()


class TestOmronConnectionClosed:
    def _config(self):
        return {
            "equipment_id": "TEST_EQ",
            "plc_ip": "192.168.1.100",
            "plc_port": 9600,
            "manufacturer": "オムロン",
            "data_points": {},
        }

    def _mock_fins(self):
        """fins_socket 属性を持つ UDPFinsConnection 相当のモック"""
        mock_fins = MagicMock()
        mock_fins.fins_socket = MagicMock()
        return mock_fins

    @pytest.mark.unit
    def test_socket_closed_on_read_success(self):
        """正常読み取り時に fins_socket が閉じられる"""
        from plc_agent import read_from_real_plc

        mock_fins = self._mock_fins()
        with patch("plc_agent.connect_omron_plc", return_value=mock_fins), patch(
            "plc_agent.read_omron_plc", return_value={"temp": 25}
        ):
            result = read_from_real_plc(
                self._config(), "192.168.1.100", 9600, "オムロン", {}
            )

        assert result == {"temp": 25}
        mock_fins.fins_socket.close.assert_called_once()

    @pytest.mark.unit
    def test_socket_closed_when_read_raises(self):
        """読み取りが例外を送出しても fins_socket が閉じられる（リーク防止）"""
        from plc_agent import read_from_real_plc

        mock_fins = self._mock_fins()
        with patch("plc_agent.connect_omron_plc", return_value=mock_fins), patch(
            "plc_agent.read_omron_plc", side_effect=RuntimeError("読取失敗")
        ), patch("plc_agent.report_error"):
            result = read_from_real_plc(
                self._config(), "192.168.1.100", 9600, "オムロン", {}
            )

        assert result is None
        mock_fins.fins_socket.close.assert_called_once()


class TestKeyenceConnectionClosed:
    def _config(self):
        return {
            "equipment_id": "TEST_EQ",
            "plc_ip": "192.168.1.100",
            "plc_port": 502,
            "manufacturer": "キーエンス",
            "data_points": {},
        }

    @pytest.mark.unit
    def test_client_closed_when_grouping_raises(self):
        """アドレスのグループ化が例外を送出しても client が閉じられる（リーク防止）"""
        from plc_agent import read_from_real_plc

        mock_client = MagicMock()
        with patch("plc_agent.connect_keyence_plc", return_value=mock_client), patch(
            "plc_drivers.keyence.group_continuous_word_addresses",
            side_effect=RuntimeError("グループ化失敗"),
        ), patch("plc_agent.report_error"):
            result = read_from_real_plc(
                self._config(), "192.168.1.100", 502, "キーエンス", {}
            )

        # 例外は read_from_real_plc の except で握られ None が返るが、
        # その前に close されていること
        assert result is None
        mock_client.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
