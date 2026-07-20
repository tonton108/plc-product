"""
設備登録の識別子ロジック検証（乗っ取り防止・equipment_id衝突）。

register は不変識別子（cpu_serial_number > mac_address）で既存設備を特定すべき。
可変の equipment_id で特定してしまうと、別デバイスが同じ equipment_id を使った際に
既存レコードの cpu_serial/mac を上書き＝乗っ取りが起きる。
"""

import json

from db.models import Equipment


def _payload(**over):
    p = {
        "equipment_id": "RID_EQ",
        "manufacturer": "Mitsubishi",
        "series": "iQ-R",
        "ip": "192.168.1.20",
        "plc_ip": "192.168.1.200",
        "mac_address": "00:AA:BB:CC:DD:01",
        "cpu_serial_number": "RID_CPU_A",
        "hostname": "raspi",
        "port": 5000,
        "interval": 5000,
    }
    p.update(over)
    return p


def _register(client, payload):
    return client.post(
        "/api/register", data=json.dumps(payload), content_type="application/json"
    )


class TestRegisterIdentity:
    def test_new_device_cannot_hijack_existing_by_equipment_id(self, client, session):
        """別デバイス（新cpu_serial/mac）が既存のequipment_idで登録しても、
        既存レコードのcpu_serial/macを上書きしてはならない（乗っ取り防止）。"""
        # デバイスA登録
        r1 = _register(client, _payload())
        assert r1.status_code == 200

        # 別デバイスB: cpu_serial/macは別、equipment_idはAと同じ
        r2 = _register(
            client,
            _payload(cpu_serial_number="RID_CPU_B", mac_address="00:AA:BB:CC:DD:02"),
        )

        # Aのレコードが健在で、識別子が上書きされていないこと
        a = Equipment.query.filter_by(cpu_serial_number="RID_CPU_A").first()
        assert a is not None, "デバイスAのcpu_serialが別デバイスに上書きされた（乗っ取り）"
        assert a.mac_address == "00:AA:BB:CC:DD:01", "デバイスAのmacが上書きされた"
        assert a.equipment_id == "RID_EQ"

        # Bはequipment_id衝突として拒否される（409）
        assert r2.status_code == 409, f"equipment_id衝突が拒否されていない: {r2.status_code}"

    def test_reregister_same_cpu_serial_updates_record(self, client, session):
        """同一cpu_serialの再登録は同じレコードを更新（equipment_id変更も可）。"""
        r1 = _register(client, _payload(equipment_id="RID_EQ1"))
        assert r1.status_code == 200

        # 同じcpu_serialでequipment_idを変更して再登録
        r2 = _register(client, _payload(equipment_id="RID_EQ2", plc_ip="10.0.0.9"))
        assert r2.status_code == 200

        # レコードは1件のまま、equipment_id/plc_ipが更新される
        rows = Equipment.query.filter_by(cpu_serial_number="RID_CPU_A").all()
        assert len(rows) == 1
        assert rows[0].equipment_id == "RID_EQ2"
        assert rows[0].plc_ip == "10.0.0.9"

    def test_reregister_by_mac_when_cpu_absent(self, client, session):
        """cpu_serialが一致しなくてもmac一致なら同一デバイスとして更新。"""
        r1 = _register(client, _payload())
        assert r1.status_code == 200

        # 同じmac、cpu_serialは（再イメージ等で）別値、equipment_idも同じ
        r2 = _register(client, _payload(cpu_serial_number="RID_CPU_A2"))
        assert r2.status_code == 200

        # macで特定され1件のまま更新（新規作成で2件にならない）
        rows = Equipment.query.filter_by(mac_address="00:AA:BB:CC:DD:01").all()
        assert len(rows) == 1
