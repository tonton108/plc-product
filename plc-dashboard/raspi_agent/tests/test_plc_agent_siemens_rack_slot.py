"""
plc_agent のシーメンス接続における Rack/Slot 配線テスト（Issue #58）

read_from_real_plc が設定の rack/slot を connect_siemens_plc へ渡すことを検証する。
S7-300/400 は slot=2 が必須で、これが配線されていないと接続できない。
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSiemensRackSlotWiring:
    """設定の rack/slot が connect_siemens_plc へ渡るか"""

    def _base_config(self, **extra):
        config = {
            "plc_ip": "192.168.1.106",
            "plc_port": 102,
            "manufacturer": "シーメンス",
            "data_points": {},
        }
        config.update(extra)
        return config

    @pytest.mark.unit
    def test_rack_slot_passed_from_config(self):
        """S7-300/400想定: config の rack=0/slot=2 がそのまま渡ること"""
        from plc_agent import read_from_real_plc

        config = self._base_config(rack=0, slot=2)
        mock_plc = MagicMock()

        with patch(
            "plc_agent.connect_siemens_plc", return_value=mock_plc
        ) as mock_connect, patch(
            "plc_agent.read_siemens_plc", return_value={"temp": 25}
        ):
            result = read_from_real_plc(
                config, "192.168.1.106", 102, "シーメンス", config["data_points"]
            )

        assert result == {"temp": 25}
        mock_connect.assert_called_once_with("192.168.1.106", rack=0, slot=2)

    @pytest.mark.unit
    def test_rack_slot_default_when_absent(self):
        """設定に rack/slot が無ければ既定 rack=0/slot=1（S7-1200/1500）"""
        from plc_agent import read_from_real_plc

        config = self._base_config()  # rack/slot 未指定
        mock_plc = MagicMock()

        with patch(
            "plc_agent.connect_siemens_plc", return_value=mock_plc
        ) as mock_connect, patch("plc_agent.read_siemens_plc", return_value={}):
            read_from_real_plc(
                config, "192.168.1.106", 102, "シーメンス", config["data_points"]
            )

        mock_connect.assert_called_once_with("192.168.1.106", rack=0, slot=1)

    @pytest.mark.unit
    def test_connect_failure_reports_rack_slot(self):
        """接続失敗時、report_error に rack/slot が含まれること（診断用）"""
        from plc_agent import read_from_real_plc

        config = self._base_config(rack=0, slot=2)

        with patch("plc_agent.connect_siemens_plc", return_value=None), patch(
            "plc_agent.report_error"
        ) as mock_report:
            result = read_from_real_plc(
                config, "192.168.1.106", 102, "シーメンス", config["data_points"]
            )

        assert result is None
        _, kwargs = mock_report.call_args
        assert "Slot:2" in kwargs["error_message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
