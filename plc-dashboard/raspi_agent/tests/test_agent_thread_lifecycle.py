"""
PLCエージェントのスレッド起動/停止ライフサイクルの回帰テスト

restart（stop→start）で、停止処理の join がタイムアウトしても旧スレッドが
確実に終了できることを検証する。

旧実装は共有の停止イベントを start 時に clear() で使い回していたため、
join(5秒) がタイムアウトした後（旧スレッドが PLC接続リトライ中など、最悪
18秒程度 停止フラグを見ない区間にいるケース）に start が同じイベントを
clear() すると、旧スレッドが停止信号を見失って永久に動き続け、新旧2スレッドが
同一設備を並行ポーリングしていた。スレッドごとに独立したイベントを持たせる
ことで、旧スレッドは自身のイベント（set済み）を見て次チェックで終了できる。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_app


class _DummyThread:
    """実スレッドを起動しないスタブ。

    join してもタイムアウトを模して is_alive() は True のまま（＝旧スレッドが
    まだ生きている状況を再現する）。
    """

    def __init__(self, target=None, args=(), daemon=None, **kwargs):
        self.args = args
        self._alive = False

    def start(self):
        self._alive = True

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        # 停止しきらずタイムアウトした状況を模す（is_alive は True のまま）
        return None


@pytest.fixture
def stubbed(monkeypatch):
    monkeypatch.setattr(agent_app.threading, "Thread", _DummyThread)
    monkeypatch.setattr(agent_app, "plc_main_loop", lambda *a, **k: None)
    monkeypatch.setattr(agent_app, "safe_print", lambda *a, **k: None)
    # クリーンな初期状態
    agent_app.plc_agent_thread = None
    agent_app.plc_agent_stop_event = agent_app.threading.Event()
    yield
    agent_app.plc_agent_thread = None


class TestThreadLifecycle:
    @pytest.mark.unit
    def test_restart_does_not_orphan_old_thread(self, stubbed):
        """stop→start で旧イベントは set のまま・新イベントは別オブジェクトでクリア"""
        agent_app.start_plc_agent()
        e1 = agent_app.plc_agent_stop_event

        # 旧スレッドが join タイムアウトで生き残る状況
        agent_app.stop_plc_agent()
        assert e1.is_set(), "停止要求で旧イベントは set されるべき"
        assert agent_app.plc_agent_thread is None

        agent_app.start_plc_agent()
        e2 = agent_app.plc_agent_stop_event

        # 新スレッドは独立した未セットのイベントを持つ
        assert e2 is not e1, "start はスレッドごとに新しいイベントを生成すべき"
        assert not e2.is_set()
        # ★ 旧イベントは依然 set → 旧スレッドは次チェックで正常終了できる
        assert e1.is_set(), "旧イベントが clear されると旧スレッドが停止信号を見失う"

    @pytest.mark.unit
    def test_start_is_idempotent_when_alive(self, stubbed):
        """既に生存中なら二重起動しない（イベントも維持）"""
        agent_app.start_plc_agent()
        e1 = agent_app.plc_agent_stop_event
        t1 = agent_app.plc_agent_thread

        agent_app.start_plc_agent()  # 生存中なので何もしない
        assert agent_app.plc_agent_thread is t1
        assert agent_app.plc_agent_stop_event is e1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
