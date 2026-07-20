"""
Siemens S7 Rack/Slot 設定の永続化・検証テスト（Issue #58）

- 登録/更新APIで rack/slot が保存され、シリアライザが返すこと
- 範囲外の rack(0-7)/slot(0-31) は400になること
- 未指定時は既定 rack=0 / slot=1（S7-1200/1500）になること
"""

import json


def _register_payload(**overrides):
    """Siemens設備の登録ペイロード雛形"""
    payload = {
        "equipment_id": "S7_REG_001",
        "manufacturer": "シーメンス",
        "series": "S7-300",
        "ip": "192.168.1.20",
        "plc_ip": "192.168.1.206",
        "mac_address": "00:AA:BB:CC:DD:58",
        "cpu_serial_number": "CPU_S7_REG_001",
        "hostname": "s7-raspi",
        "port": 102,
        "interval": 1000,
    }
    payload.update(overrides)
    return payload


def _post_register(client, payload):
    return client.post(
        "/api/register", data=json.dumps(payload), content_type="application/json"
    )


def _get_equipment(client, equipment_id):
    return client.get(f"/api/equipment/{equipment_id}")


def _put_equipment(client, equipment_id, payload):
    return client.put(
        f"/api/equipment/{equipment_id}",
        data=json.dumps(payload),
        content_type="application/json",
    )


class TestRackSlotPersistence:
    def test_register_persists_rack_slot(self, client, session):
        """S7-300想定: rack=0/slot=2 が保存され、GETで返ること"""
        resp = _post_register(client, _register_payload(rack=0, slot=2))
        assert resp.status_code == 200

        got = _get_equipment(client, "S7_REG_001")
        assert got.status_code == 200
        body = got.get_json()
        assert body["rack"] == 0
        assert body["slot"] == 2

    def test_default_rack_slot_when_absent(self, client, session):
        """rack/slot未指定なら既定 rack=0 / slot=1（S7-1200/1500）"""
        resp = _post_register(
            client,
            _register_payload(
                equipment_id="S7_REG_002", cpu_serial_number="CPU_S7_REG_002"
            ),
        )
        assert resp.status_code == 200

        body = _get_equipment(client, "S7_REG_002").get_json()
        assert body["rack"] == 0
        assert body["slot"] == 1

    def test_put_updates_rack_slot(self, client, session, sample_equipment):
        """既存設備をPUTで slot=2 に更新できること（エージェント保存経路）"""
        resp = _put_equipment(
            client,
            sample_equipment.equipment_id,
            {
                "cpu_serial_number": sample_equipment.cpu_serial_number,
                "rack": 0,
                "slot": 2,
            },
        )
        assert resp.status_code == 200

        body = _get_equipment(client, sample_equipment.equipment_id).get_json()
        assert body["slot"] == 2


class TestRackSlotValidation:
    def test_invalid_slot_returns_400(self, client, session):
        """slotが範囲外(0-31超)は400"""
        resp = _post_register(client, _register_payload(slot=99))
        assert resp.status_code == 400
        assert "slot" in resp.get_json()["error"].lower()

    def test_invalid_rack_returns_400(self, client, session):
        """rackが範囲外(0-7超)は400"""
        resp = _post_register(client, _register_payload(rack=8))
        assert resp.status_code == 400
        assert "rack" in resp.get_json()["error"].lower()

    def test_negative_slot_returns_400(self, client, session):
        """負のslotは400"""
        resp = _post_register(client, _register_payload(slot=-1))
        assert resp.status_code == 400
        assert "slot" in resp.get_json()["error"].lower()
