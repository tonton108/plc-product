"""
plc_agent のエラー報告回数テスト

1回の物理的な通信失敗に対して report_error が「ちょうど1回」呼ばれることを検証する。
旧実装では read_from_real_plc（内側）と read_from_plc（外側）が両方 report_error を
呼び、1失敗が2件のエラーログ・2回分の consecutive_errors 増分になっていた
（不明メーカー経路は CONFIGURATION_ERROR + READ_ERROR + CONNECTION_FAILED で3重）。
サーバー側 errors_alarms は POST 1件ごとに consecutive_errors を +1 するため、
連続エラー回数のカウント（CLAUDE.md）が実際の2〜3倍に膨れる回帰を防ぐ。
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestErrorReportedOnce:
    """1失敗 = report_error 1回"""

    def _config(self, manufacturer, **extra):
        config = {
            "equipment_id": "TEST_EQ",
            "plc_ip": "192.168.1.100",
            "plc_port": 5000,
            "manufacturer": manufacturer,
            "data_points": {},
        }
        config.update(extra)
        return config

    @pytest.mark.unit
    def test_connection_failure_reports_once(self):
        """三菱の接続失敗（read_from_plc経由）で report_error は1回だけ"""
        from plc_agent import read_from_plc

        config = self._config("三菱")

        # 実PLCモードに固定し、接続失敗（connect が None）を模擬する
        with patch("plc_agent.USE_DUMMY_PLC", False), patch(
            "plc_agent.connect_mitsubishi_plc", return_value=None
        ), patch("plc_agent.report_error") as mock_report, patch(
            "plc_agent.generate_dummy_data", return_value={"dummy": 1}
        ):
            result = read_from_plc(config)

        # ダミーへフォールバックしつつ、報告は内側の PROTOCOL_ERROR 1回のみ
        assert result == {"dummy": 1}
        assert mock_report.call_count == 1
        _, kwargs = mock_report.call_args
        assert kwargs["error_type"] == "PROTOCOL_ERROR"

    @pytest.mark.unit
    def test_unknown_manufacturer_reports_once(self):
        """不明メーカーでは CONFIGURATION_ERROR 1回のみ（READ_ERROR で二重報告しない）"""
        from plc_agent import read_from_real_plc

        config = self._config("未知メーカー")

        with patch("plc_agent.report_error") as mock_report:
            result = read_from_real_plc(
                config, "192.168.1.100", 5000, "未知メーカー", config["data_points"]
            )

        assert result is None
        assert mock_report.call_count == 1
        _, kwargs = mock_report.call_args
        assert kwargs["error_type"] == "CONFIGURATION_ERROR"

    @pytest.mark.unit
    def test_read_exception_reports_once(self):
        """読取中の例外は READ_ERROR 1回のみ（接続成功後に read が例外）"""
        from plc_agent import read_from_real_plc

        config = self._config("三菱")
        mock_plc = MagicMock()

        with patch("plc_agent.connect_mitsubishi_plc", return_value=mock_plc), patch(
            "plc_agent.read_mitsubishi_plc", side_effect=RuntimeError("読取失敗")
        ), patch("plc_agent.report_error") as mock_report:
            result = read_from_real_plc(
                config, "192.168.1.100", 5000, "三菱", config["data_points"]
            )

        assert result is None
        assert mock_report.call_count == 1
        _, kwargs = mock_report.call_args
        assert kwargs["error_type"] == "READ_ERROR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
