"""
API エンドポイントのテスト
"""
import pytest
import json
from datetime import datetime, timezone


class TestEquipmentAPI:
    """設備管理APIのテスト"""

    def test_get_all_equipment_empty(self, client):
        """設備一覧取得（空の場合）"""
        response = client.get('/api/equipment')
        assert response.status_code == 200
        assert isinstance(response.json, list)

    def test_get_all_equipment_with_data(self, client, sample_equipment):
        """設備一覧取得（データありの場合）"""
        response = client.get('/api/equipment')
        assert response.status_code == 200
        assert len(response.json) == 1
        assert response.json[0]['equipment_id'] == 'TEST_001'

    def test_register_equipment(self, client):
        """設備登録"""
        data = {
            "equipment_id": "NEW_001",
            "manufacturer": "Mitsubishi",
            "series": "iQ-R",
            "ip": "192.168.1.20",
            "plc_ip": "192.168.1.200",
            "mac_address": "00:AA:BB:CC:DD:EE",
            "cpu_serial_number": "CPU_NEW_001",
            "hostname": "new-raspi",
            "port": 5000,
            "interval": 5000
        }
        response = client.post('/api/register',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        assert response.json['message'] == '登録完了'

    def test_register_equipment_missing_fields(self, client):
        """設備登録（必須フィールド不足）"""
        data = {
            "equipment_id": "INVALID_001"
            # mac_address が不足
        }
        response = client.post('/api/register',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_get_equipment_config(self, client, sample_equipment):
        """設備設定取得"""
        response = client.get(f'/api/equipment/{sample_equipment.equipment_id}')
        assert response.status_code == 200
        assert response.json['equipment_id'] == 'TEST_001'
        assert response.json['manufacturer'] == 'Mitsubishi'

    def test_get_equipment_config_not_found(self, client):
        """設備設定取得（存在しない設備）"""
        response = client.get('/api/equipment/NOTFOUND_001')
        assert response.status_code == 404

    def test_save_equipment_config(self, client, sample_equipment):
        """設備設定保存"""
        data = {
            "manufacturer": "Keyence",
            "series": "KV-8000",
            "plc_ip": "192.168.1.150",
            "interval": 3000,
            "cpu_serial_number": sample_equipment.cpu_serial_number
        }
        response = client.put(f'/api/equipment/{sample_equipment.equipment_id}',
                             data=json.dumps(data),
                             content_type='application/json')
        assert response.status_code == 200

    def test_search_equipment_by_cpu_serial(self, client, sample_equipment):
        """CPUシリアル番号で設備検索"""
        response = client.get(f'/api/equipment/search?cpu_serial_number={sample_equipment.cpu_serial_number}')
        assert response.status_code == 200
        assert response.json['equipment_id'] == 'TEST_001'

    def test_search_equipment_not_found(self, client):
        """設備検索（見つからない場合）"""
        response = client.get('/api/equipment/search?cpu_serial_number=INVALID')
        assert response.status_code == 404


class TestPLCConfigAPI:
    """PLC設定APIのテスト"""

    def test_get_plc_configs(self, client, sample_plc_config):
        """PLC設定取得"""
        equipment_id = sample_plc_config.equipment.equipment_id
        response = client.get(f'/api/equipment/{equipment_id}/plc_configs')
        assert response.status_code == 200
        assert isinstance(response.json, list)
        assert len(response.json) >= 1

    def test_save_plc_configs(self, client, sample_equipment):
        """PLC設定保存"""
        data = [
            {
                "data_type": "production_count",
                "enabled": True,
                "address": "D100",
                "scale_factor": 1,
                "plc_data_type": "word"
            },
            {
                "data_type": "current",
                "enabled": True,
                "address": "D110",
                "scale_factor": 0.1,
                "plc_data_type": "word"
            }
        ]
        response = client.put(f'/api/equipment/{sample_equipment.equipment_id}/plc_configs',
                             data=json.dumps(data),
                             content_type='application/json')
        assert response.status_code == 200

    def test_save_plc_configs_missing_data_type_returns_400(self, client, sample_equipment):
        """data_type欠落のconfigは500ではなく400（NOT NULL違反の事前検知）"""
        data = [{"name": "x", "enabled": True, "address": "D100"}]  # data_type無し
        response = client.put(
            f'/api/equipment/{sample_equipment.equipment_id}/plc_configs',
            data=json.dumps(data), content_type='application/json')
        assert response.status_code == 400
        assert "data_type" in response.get_json().get("error", "")


class TestLogAPI:
    """ログAPIのテスト"""

    def test_save_log_data(self, client, sample_equipment):
        """ログデータ保存"""
        data = {
            "equipment_id": sample_equipment.equipment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "production_count": 100,
            "current": 15.5,
            "temperature": 45.2,
            "pressure": 0.5,
            "cycle_time": 12.3,
            "error_code": 0
        }
        response = client.post('/api/logs',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200
        assert response.json['saved_to_db'] is True

    def test_save_log_data_missing_equipment_id(self, client):
        """ログデータ保存（equipment_id不足）"""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "production_count": 100
        }
        response = client.post('/api/logs',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 400

    def test_get_latest_data(self, client, sample_equipment):
        """最新データ取得"""
        # まずデータを投入
        data = {
            "equipment_id": sample_equipment.equipment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "production_count": 50,
            "current": 12.5
        }
        client.post('/api/logs',
                   data=json.dumps(data),
                   content_type='application/json')

        # 最新データ取得
        response = client.get(f'/api/logs/{sample_equipment.equipment_id}/latest')
        assert response.status_code == 200
        assert response.json['equipment_id'] == sample_equipment.equipment_id

    def test_get_history_data(self, client, sample_equipment):
        """履歴データ取得"""
        # データを複数投入
        for i in range(5):
            data = {
                "equipment_id": sample_equipment.equipment_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "production_count": 100 + i,
                "current": 15.0 + i
            }
            client.post('/api/logs',
                       data=json.dumps(data),
                       content_type='application/json')

        # 履歴データ取得
        response = client.get(f'/api/logs/{sample_equipment.equipment_id}/history?limit=10')
        assert response.status_code == 200
        assert response.json['total_records'] >= 5


class TestAdminAPI:
    """管理APIのテスト"""

    def test_get_database_stats(self, client, sample_equipment):
        """データベース統計取得"""
        response = client.get('/api/admin/stats')
        assert response.status_code == 200
        assert 'total_logs' in response.json
        assert 'total_equipments' in response.json
        assert response.json['total_equipments'] >= 1

    def test_manual_cleanup(self, client):
        """手動クリーンアップ"""
        data = {"days": 90}
        response = client.post('/api/admin/cleanup',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200

    def test_manual_create_daily_summary(self, client):
        """日次集計作成"""
        data = {
            "type": "daily",
            "date": "2025-01-15"
        }
        response = client.post('/api/admin/create_summary',
                              data=json.dumps(data),
                              content_type='application/json')
        assert response.status_code == 200


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_404_not_found(self, client):
        """404エラー"""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        assert 'error' in response.json

    def test_invalid_json(self, client):
        """無効なJSON"""
        response = client.post('/api/register',
                              data='invalid json',
                              content_type='application/json')
        assert response.status_code in [400, 500]  # JSON parse error
