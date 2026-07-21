"""
アラーム重複送信の抑止テスト

PLCが同一エラーコードを出し続けている間、アラームがポーリング毎に再送されず、
状態遷移（新規発生／コード変化／解消後の再発）時のみ送信されることを検証する。

バックエンドはアラームを重複排除せず、POSTごとに新規AlarmHistory行の作成＋
高コストなインシデント文脈保全を行うため、抑止しないと同一アラームの継続中に
それらが際限なく積み上がる。
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plc_agent


class _FakeStopEvent:
    """指定回数のイテレーションだけ回して停止するスタブ停止イベント。

    main_loop は各周回の先頭で is_set() を確認するため、stop_after 回 False を
    返した後 True を返してループを抜ける。wait() は即時に戻す（sleepしない）。
    """

    def __init__(self, stop_after):
        self.stop_after = stop_after
        self.calls = 0

    def is_set(self):
        if self.calls >= self.stop_after:
            return True
        self.calls += 1
        return False

    def wait(self, timeout=None):
        return False


def _run_main_loop_with_values(values_sequence, send_results=None):
    """与えた値列を read_from_plc が順に返すよう差し替えて main_loop を回す。

    Args:
        values_sequence: read_from_plc が順に返す値の列
        send_results: report_alarm の戻り値（送信成否）を順に指定するリスト。
            None の場合は常に True（送信成功）とみなす。

    Returns:
        報告された alarm_code のリスト（report_alarm 呼び出し順）
    """
    reported = []
    results_iter = iter(send_results) if send_results is not None else None

    def fake_report_alarm(alarm_code, **kwargs):
        reported.append(alarm_code)
        if results_iter is None:
            return True
        return next(results_iter)

    stop_event = _FakeStopEvent(stop_after=len(values_sequence))

    with patch.object(plc_agent, "reload_env_vars", lambda: None), patch.object(
        plc_agent,
        "load_plc_config",
        return_value={"equipment_id": "EQ", "interval": 1000},
    ), patch.object(
        plc_agent, "read_from_plc", side_effect=list(values_sequence)
    ), patch.object(
        plc_agent, "report_alarm", side_effect=fake_report_alarm
    ), patch.object(
        plc_agent, "db_api"
    ) as mock_db_api:
        mock_db_api.send_log_data.return_value = True
        plc_agent.main_loop(stop_event=stop_event)

    return reported


class TestAlarmDedup:
    @pytest.mark.unit
    def test_same_alarm_reported_once_while_active(self):
        """同一エラーコードの継続中は1回だけ報告される"""
        reported = _run_main_loop_with_values(
            [
                {"error_code": 5},
                {"error_code": 5},
                {"error_code": 5},
            ]
        )
        assert reported == ["E005"]

    @pytest.mark.unit
    def test_alarm_refires_after_clear(self):
        """一度解消（error_code=0）した後に再発すると再送される"""
        reported = _run_main_loop_with_values(
            [
                {"error_code": 5},
                {"error_code": 0},
                {"error_code": 5},
            ]
        )
        assert reported == ["E005", "E005"]

    @pytest.mark.unit
    def test_code_change_reports_new_alarm(self):
        """継続中でもエラーコードが変われば新しいアラームとして送信される"""
        reported = _run_main_loop_with_values(
            [
                {"error_code": 5},
                {"error_code": 5},
                {"error_code": 6},
            ]
        )
        assert reported == ["E005", "E006"]

    @pytest.mark.unit
    def test_no_alarm_when_error_code_zero(self):
        """error_code が常に0なら一度も送信されない"""
        reported = _run_main_loop_with_values(
            [
                {"error_code": 0},
                {"temperature": 25},
            ]
        )
        assert reported == []

    @pytest.mark.unit
    def test_retries_when_send_fails(self):
        """送信失敗（サーバー到達不能）時は last_alarm_code を据え置き、次周期で再送する。

        送信成否を無視して last_alarm_code を先に更新すると、アラーム継続中の
        一時的なサーバー障害でそのアラームが永久欠落する。1周期目False→2周期目Trueで
        両周期とも report_alarm が呼ばれ、成功後は重複排除されることを検証する。
        """
        reported = _run_main_loop_with_values(
            [
                {"error_code": 5},  # 送信失敗
                {"error_code": 5},  # 再試行して成功
                {"error_code": 5},  # 成功済みなので抑止
            ],
            send_results=[False, True, True],
        )
        assert reported == ["E005", "E005"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
