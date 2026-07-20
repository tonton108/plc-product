"""
設備登録・更新APIの必須キー検証テスト（Issue #11）

必須キー欠落時に IntegrityError 経由の500ではなく、400と欠落キー名を返すことを検証する。
"""

import json


def _register_payload(**overrides):
    """有効な登録ペイロードの雛形（overridesで一部を差し替え/削除）"""
    payload = {
        "equipment_id": "REG_001",
        "manufacturer": "Mitsubishi",
        "series": "iQ-R",
        "ip": "192.168.1.20",
        "plc_ip": "192.168.1.200",
        "mac_address": "00:AA:BB:CC:DD:01",
        "cpu_serial_number": "CPU_REG_001",
        "hostname": "reg-raspi",
        "port": 5000,
        "interval": 5000,
    }
    for key, value in overrides.items():
        if value is _DELETE:
            payload.pop(key, None)
        else:
            payload[key] = value
    return payload


_DELETE = object()  # ペイロードからキー自体を削除するマーカー


def _post_register(client, payload):
    return client.post(
        "/api/register", data=json.dumps(payload), content_type="application/json"
    )


def _put_equipment(client, equipment_id, payload):
    return client.put(
        f"/api/equipment/{equipment_id}",
        data=json.dumps(payload),
        content_type="application/json",
    )


class TestRegisterRequiredKeys:
    def test_missing_series_returns_400(self, client, session):
        """seriesキー欠落は500ではなく400（欠落キー名を含む）"""
        resp = _post_register(client, _register_payload(series=_DELETE))
        assert resp.status_code == 400
        assert "series" in resp.get_json()["error"]

    def test_null_plc_ip_returns_400(self, client, session):
        """plc_ipがnullでも400（Noneは欠落扱い）"""
        resp = _post_register(client, _register_payload(plc_ip=None))
        assert resp.status_code == 400
        assert "plc_ip" in resp.get_json()["error"]

    def test_null_manufacturer_returns_400(self, client, session):
        """manufacturerがnullでも400（agent_app.py がNoneを転送する経路の500を防ぐ）"""
        resp = _post_register(client, _register_payload(manufacturer=None))
        assert resp.status_code == 400
        assert "manufacturer" in resp.get_json()["error"]

    def test_empty_string_placeholders_accepted(self, client, session):
        """空文字プレースホルダは許容（register_equipment.py の自己登録運用）。

        manufacturer/series/plc_ip を "" で送る自己登録は、NOT NULL制約を
        満たすため200で通り、後からUIで実値を設定できる。
        """
        resp = _post_register(
            client, _register_payload(manufacturer="", series="", plc_ip="")
        )
        assert resp.status_code == 200

    def test_multiple_missing_keys_listed(self, client, session):
        """複数欠落時は欠落キーが全て列挙される"""
        resp = _post_register(client, _register_payload(port=_DELETE, interval=_DELETE))
        assert resp.status_code == 400
        error = resp.get_json()["error"]
        assert "port" in error and "interval" in error

    def test_complete_payload_succeeds(self, client, session):
        """必須キーが揃っていれば200"""
        resp = _post_register(client, _register_payload())
        assert resp.status_code == 200


class TestPutEquipmentRequiredKeys:
    def test_new_equipment_missing_key_returns_400(self, client, session):
        """新規作成分岐で必須キー欠落は400（既存のcpu_serialに一致しない=新規）"""
        payload = {
            "manufacturer": "Keyence",
            "series": "KV-8000",
            "plc_ip": "192.168.1.150",
            "cpu_serial_number": "CPU_PUT_NEW_001",
            "interval": 3000,
            # plc_port が欠落 → port(NOT NULL)がNoneになり従来は500
        }
        resp = _put_equipment(client, "PUT_NEW_001", payload)
        assert resp.status_code == 400
        assert "plc_port" in resp.get_json()["error"]

    def test_new_equipment_complete_succeeds(self, client, session):
        """新規作成分岐で必須キーが揃えば200"""
        payload = {
            "manufacturer": "Keyence",
            "series": "KV-8000",
            "plc_ip": "192.168.1.150",
            "cpu_serial_number": "CPU_PUT_NEW_002",
            "plc_port": 5000,
            "interval": 3000,
        }
        resp = _put_equipment(client, "PUT_NEW_002", payload)
        assert resp.status_code == 200

    def test_update_existing_partial_succeeds(self, client, session, sample_equipment):
        """既存設備の部分更新は必須キー検証の対象外（欠落キーは既存値を保持）"""
        payload = {
            "cpu_serial_number": sample_equipment.cpu_serial_number,
            "manufacturer": "UpdatedMaker",
            # series/plc_ip/plc_port/interval を送らなくても既存値保持で200
        }
        resp = _put_equipment(client, sample_equipment.equipment_id, payload)
        assert resp.status_code == 200

    def test_update_existing_explicit_null_returns_400(self, client, session, sample_equipment):
        """既存設備の更新でNOT NULL列に明示nullを送ると500ではなく400。

        キー省略（既存値保持）は許容されるが、明示的なnullはNoneが代入され
        IntegrityError→500になっていた。事前に400で弾く。
        """
        resp = _put_equipment(
            client,
            sample_equipment.equipment_id,
            {"cpu_serial_number": sample_equipment.cpu_serial_number, "plc_ip": None},
        )
        assert resp.status_code == 400
        assert "plc_ip" in resp.get_json()["error"]
