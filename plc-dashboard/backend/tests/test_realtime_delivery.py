"""
リアルタイム配信の設備別room宛て化テスト（Phase 3）

plc_data_update が全体（monitoring）ではなく equipment_{id} room 宛てに
配信されることを検証する。
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import api.routes.logs as logs_module


def _post_log(client, equipment_id, extra=None):
    payload = {
        "equipment_id": equipment_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 25.0,
        **(extra or {}),
    }
    return client.post('/api/logs', data=json.dumps(payload),
                       content_type='application/json')


class TestPerEquipmentRoomDelivery:
    def test_emit_targets_equipment_room(self, client, session, sample_equipment, monkeypatch):
        """plc_data_update が equipment_{id} room 宛てに配信される"""
        mock_socketio = MagicMock()
        monkeypatch.setattr(logs_module, 'get_socketio', lambda: mock_socketio)

        response = _post_log(client, sample_equipment.equipment_id)
        assert response.status_code == 200

        mock_socketio.emit.assert_called_once()
        args, kwargs = mock_socketio.emit.call_args
        assert args[0] == 'plc_data_update'
        # 全体('monitoring')ではなく設備別roomに限定されていること
        assert kwargs.get('to') == f"equipment_{sample_equipment.equipment_id}"

    def test_emit_payload_matches_equipment(self, client, session, sample_equipment, monkeypatch):
        """配信ペイロードのequipment_idが対象設備と一致する"""
        mock_socketio = MagicMock()
        monkeypatch.setattr(logs_module, 'get_socketio', lambda: mock_socketio)

        _post_log(client, sample_equipment.equipment_id, {"temp_a": 30.5})

        args, kwargs = mock_socketio.emit.call_args
        payload = args[1]
        assert payload["equipment_id"] == sample_equipment.equipment_id
        assert payload["temp_a"] == 30.5  # 動的項目も配信に含まれる（Phase 2）
