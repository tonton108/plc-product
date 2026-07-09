"""
動的データ項目の一気通貫テスト（Phase 2）

固定6カラム以外の任意項目が、受信→Log.data保存→履歴/最新API→
シリアライザまで通ることを検証する。
"""
import json
from datetime import datetime, timezone


class TestDynamicDataPassthrough:
    """受信APIでの動的項目の保存と取得"""

    def _post_log(self, client, equipment_id, extra):
        payload = {
            "equipment_id": equipment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": 25.0,
            **extra,
        }
        return client.post('/api/logs', data=json.dumps(payload),
                           content_type='application/json')

    def test_dynamic_item_saved_to_data(self, client, session, sample_equipment):
        """固定カラム以外の項目がLog.dataに保存される"""
        from db.models import Log

        response = self._post_log(client, sample_equipment.equipment_id, {
            "temp_a": 30.5,
            "custom_sensor": 42,
        })
        assert response.status_code == 200

        log = Log.query.filter_by(equipment_id=sample_equipment.id).order_by(Log.id.desc()).first()
        assert log.data == {"temp_a": 30.5, "custom_sensor": 42}
        # 固定カラムは従来どおり
        assert log.temperature == 25.0

    def test_no_dynamic_item_leaves_data_none(self, client, session, sample_equipment):
        """固定項目のみの場合 data は None"""
        from db.models import Log

        response = self._post_log(client, sample_equipment.equipment_id, {})
        assert response.status_code == 200

        log = Log.query.filter_by(equipment_id=sample_equipment.id).order_by(Log.id.desc()).first()
        assert log.data is None

    def test_latest_api_includes_dynamic_items(self, client, session, sample_equipment):
        """最新データAPIのレスポンスに動的項目が含まれる"""
        self._post_log(client, sample_equipment.equipment_id, {"temp_a": 30.5})

        response = client.get(f'/api/logs/{sample_equipment.equipment_id}/latest')
        assert response.status_code == 200
        assert response.json["temp_a"] == 30.5
        assert response.json["temperature"] == 25.0

    def test_history_api_includes_dynamic_items(self, client, session, sample_equipment):
        """履歴APIのレスポンスに動的項目が含まれる"""
        self._post_log(client, sample_equipment.equipment_id, {"vibration": 1.2})

        response = client.get(f'/api/logs/{sample_equipment.equipment_id}/history?limit=10')
        assert response.status_code == 200
        assert response.json["data"][0]["vibration"] == 1.2

    def test_fixed_column_not_overwritten_by_data(self, client, session, sample_equipment):
        """固定カラムと同名キーが来ても固定カラム値が優先される"""
        from db.models import Log

        # temperature は固定カラム。dataには入らずカラムに入る
        response = self._post_log(client, sample_equipment.equipment_id, {"temperature": 99.9})
        assert response.status_code == 200

        log = Log.query.filter_by(equipment_id=sample_equipment.id).order_by(Log.id.desc()).first()
        # 後勝ちで99.9（payloadでtemperature=25.0の後にextraで99.9上書き）
        assert log.temperature == 99.9
        assert log.data is None  # temperatureは固定なのでdataに残らない


class TestDynamicDataValidation:
    """動的項目名のバリデーション（形式検証への変更）"""

    def test_custom_data_type_accepted(self, client, sample_equipment):
        """任意の項目名（旧ホワイトリスト外）でPLC設定を保存できる"""
        configs = [{
            "name": "金型温度A",
            "data_type": "mold_temp_a",  # 旧ホワイトリストには無い
            "enabled": True,
            "address": "D100",
            "scale_factor": 1,
            "plc_data_type": "float32",
        }]
        response = client.put(
            f'/api/equipment/{sample_equipment.equipment_id}/plc_configs',
            data=json.dumps(configs), content_type='application/json')
        assert response.status_code == 200

    def test_invalid_data_type_rejected(self, client, sample_equipment):
        """不正な文字を含む項目名は拒否される"""
        configs = [{
            "data_type": "bad name!",  # 空白・記号
            "enabled": True,
            "address": "D100",
            "plc_data_type": "word",
        }]
        response = client.put(
            f'/api/equipment/{sample_equipment.equipment_id}/plc_configs',
            data=json.dumps(configs), content_type='application/json')
        assert response.status_code == 400


class TestWordOrderConfig:
    """word_orderのPLC設定の往復"""

    def test_word_order_persisted_and_returned(self, client, sample_equipment):
        """word_orderが保存され、取得APIで返る"""
        configs = [{
            "data_type": "temp_a",
            "enabled": True,
            "address": "D100",
            "plc_data_type": "float32",
            "word_order": "high_first",
        }]
        put_resp = client.put(
            f'/api/equipment/{sample_equipment.equipment_id}/plc_configs',
            data=json.dumps(configs), content_type='application/json')
        assert put_resp.status_code == 200

        get_resp = client.get(f'/api/equipment/{sample_equipment.equipment_id}/plc_configs')
        assert get_resp.status_code == 200
        assert get_resp.json[0]["word_order"] == "high_first"

    def test_word_order_defaults_low_first(self, client, sample_equipment):
        """word_order未指定時はlow_first（三菱既定）"""
        configs = [{
            "data_type": "temp_b",
            "enabled": True,
            "address": "D102",
            "plc_data_type": "dword",
        }]
        client.put(
            f'/api/equipment/{sample_equipment.equipment_id}/plc_configs',
            data=json.dumps(configs), content_type='application/json')

        get_resp = client.get(f'/api/equipment/{sample_equipment.equipment_id}/plc_configs')
        assert get_resp.json[0]["word_order"] == "low_first"
