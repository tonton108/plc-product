"""
設備API（api/routes/equipment.py）の補完テスト

既存テスト（test_api / test_equipment_validation / test_dynamic_data）が
register/一覧/検索/PUT必須キー/plc_configs を覆っていたのに対し、未カバーだった
check-equipment・GET単体成功・setup_status・mark_setup_completed を検証する。

インメモリSQLite（conftest.py）。client は admin Bearer + APIキー付き。
"""
from db.models.constants import SetupStatus

EQ = "TEST_001"


class TestCheckEquipment:
    def test_found_by_mac_and_ip(self, client, sample_equipment):
        """mac_address と ip が一致すれば検索結果を返す"""
        resp = client.post("/api/check-equipment", json={
            "mac_address": sample_equipment.mac_address,
            "ip": sample_equipment.ip,
        })
        assert resp.status_code == 200
        body = resp.get_json()
        # 見つかった場合は to_search_result（found=False を含まない）
        assert body.get("found") is not False

    def test_not_found_returns_found_false(self, client, sample_equipment):
        """一致しなければ found=False"""
        resp = client.post("/api/check-equipment", json={
            "mac_address": "ZZ:ZZ:ZZ:ZZ:ZZ:ZZ", "ip": "10.0.0.254",
        })
        assert resp.status_code == 200
        assert resp.get_json() == {"found": False}

    def test_missing_fields_returns_400(self, client):
        """mac_address / ip 欠落は400"""
        resp = client.post("/api/check-equipment", json={"mac_address": "x"})
        assert resp.status_code == 400


class TestGetEquipmentConfig:
    def test_success(self, client, sample_equipment):
        """存在する設備は200で基本設定を返す"""
        resp = client.get(f"/api/equipment/{EQ}")
        assert resp.status_code == 200
        assert resp.get_json()["equipment_id"] == EQ

    def test_not_found(self, client):
        resp = client.get("/api/equipment/NOPE")
        assert resp.status_code == 404


class TestSetupStatus:
    def test_setup_status_incomplete(self, client, sample_equipment):
        """BASIC_INFO_REGISTERED の設備は setup_completed=False"""
        resp = client.get(f"/api/equipment/{EQ}/setup_status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["setup_completed"] is False
        assert body["setup_status"] == SetupStatus.BASIC_INFO_REGISTERED

    def test_setup_status_not_found(self, client):
        resp = client.get("/api/equipment/NOPE/setup_status")
        assert resp.status_code == 404

    def test_mark_setup_completed(self, client, sample_equipment):
        """mark_setup_completed で SETUP_COMPLETE になり setup_completed=True"""
        resp = client.post(f"/api/equipment/{EQ}/mark_setup_completed")
        assert resp.status_code == 200
        assert resp.get_json()["setup_status"] == SetupStatus.SETUP_COMPLETE
        # 反映確認: setup_status エンドポイントが完了扱いを返す
        after = client.get(f"/api/equipment/{EQ}/setup_status").get_json()
        assert after["setup_completed"] is True

    def test_mark_setup_completed_not_found(self, client):
        resp = client.post("/api/equipment/NOPE/mark_setup_completed")
        assert resp.status_code == 404
