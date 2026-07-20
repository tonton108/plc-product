"""
plc_agent の接続クローズ（リソースリーク）回帰テスト

三菱ドライバの読み取り中に例外が発生しても、PLC接続が確実に閉じられることを
検証する。旧実装は read_mitsubishi_plc の後ろに素で plc.close() を置いており、
read_mitsubishi_plc（内部のアドレスグループ化は try 外）が例外を送出すると
read_from_real_plc の except へ伝播し、close() がスキップされてソケットが
リークしていた。
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
