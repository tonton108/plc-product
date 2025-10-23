#!/usr/bin/env python3
"""
複数のダミー設備を登録するスクリプト
"""
import requests
import random

# 中央サーバーのURL
API_BASE = "http://localhost:5000/api"

# ダミー設備データ
dummy_equipments = [
    {
        "equipment_id": "LINE_A_001",
        "manufacturer": "三菱",
        "series": "Q",
        "ip": "192.168.1.101",
        "plc_ip": "192.168.10.101",
        "port": 5000,
        "interval": 1000,
        "mac_address": "00:1A:2B:3C:4D:01",
        "cpu_serial_number": "DUMMY_CPU_001",
        "hostname": "LINE_A_PLC",
        "modbus_port": 502,
        "status": "設定済み"
    },
    {
        "equipment_id": "LINE_B_002",
        "manufacturer": "オムロン",
        "series": "CJ",
        "ip": "192.168.1.102",
        "plc_ip": "192.168.10.102",
        "port": 5001,
        "interval": 2000,
        "mac_address": "00:1A:2B:3C:4D:02",
        "cpu_serial_number": "DUMMY_CPU_002",
        "hostname": "LINE_B_PLC",
        "modbus_port": 502,
        "status": "設定済み"
    },
    {
        "equipment_id": "LINE_C_003",
        "manufacturer": "キーエンス",
        "series": "KV-7000",
        "ip": "192.168.1.103",
        "plc_ip": "192.168.10.103",
        "port": 5002,
        "interval": 1500,
        "mac_address": "00:1A:2B:3C:4D:03",
        "cpu_serial_number": "DUMMY_CPU_003",
        "hostname": "LINE_C_PLC",
        "modbus_port": 502,
        "status": "登録済み"
    },
    {
        "equipment_id": "LINE_D_004",
        "manufacturer": "三菱",
        "series": "FX",
        "ip": "192.168.1.104",
        "plc_ip": "192.168.10.104",
        "port": 5003,
        "interval": 1000,
        "mac_address": "00:1A:2B:3C:4D:04",
        "cpu_serial_number": "DUMMY_CPU_004",
        "hostname": "LINE_D_PLC",
        "modbus_port": 502,
        "status": "設定済み"
    },
    {
        "equipment_id": "LINE_E_005",
        "manufacturer": "オムロン",
        "series": "NJ",
        "ip": "192.168.1.105",
        "plc_ip": "192.168.10.105",
        "port": 5004,
        "interval": 3000,
        "mac_address": "00:1A:2B:3C:4D:05",
        "cpu_serial_number": "DUMMY_CPU_005",
        "hostname": "LINE_E_PLC",
        "modbus_port": 502,
        "status": "設定済み"
    },
    {
        "equipment_id": "ROBOT_A_006",
        "manufacturer": "三菱",
        "series": "L",
        "ip": "192.168.1.106",
        "plc_ip": "192.168.10.106",
        "port": 5005,
        "interval": 500,
        "mac_address": "00:1A:2B:3C:4D:06",
        "cpu_serial_number": "DUMMY_CPU_006",
        "hostname": "ROBOT_A_PLC",
        "modbus_port": 502,
        "status": "設定済み"
    },
    {
        "equipment_id": "ROBOT_B_007",
        "manufacturer": "キーエンス",
        "series": "KV-8000",
        "ip": "192.168.1.107",
        "plc_ip": "192.168.10.107",
        "port": 5006,
        "interval": 500,
        "mac_address": "00:1A:2B:3C:4D:07",
        "cpu_serial_number": "DUMMY_CPU_007",
        "hostname": "ROBOT_B_PLC",
        "modbus_port": 502,
        "status": "登録済み"
    },
    {
        "equipment_id": "PRESS_001",
        "manufacturer": "オムロン",
        "series": "CP",
        "ip": "192.168.1.108",
        "plc_ip": "192.168.10.108",
        "port": 5007,
        "interval": 2000,
        "mac_address": "00:1A:2B:3C:4D:08",
        "cpu_serial_number": "DUMMY_CPU_008",
        "hostname": "PRESS_PLC",
        "modbus_port": 502,
        "status": "設定済み"
    },
    {
        "equipment_id": "CONVEYOR_A",
        "manufacturer": "三菱",
        "series": "Q",
        "ip": "192.168.1.109",
        "plc_ip": "192.168.10.109",
        "port": 5008,
        "interval": 1000,
        "mac_address": "00:1A:2B:3C:4D:09",
        "cpu_serial_number": "DUMMY_CPU_009",
        "hostname": "CONVEYOR_A_PLC",
        "modbus_port": 502,
        "status": "設定済み"
    },
    {
        "equipment_id": "INSPECTION_001",
        "manufacturer": "キーエンス",
        "series": "KV-7500",
        "ip": "192.168.1.110",
        "plc_ip": "192.168.10.110",
        "port": 5009,
        "interval": 1000,
        "mac_address": "00:1A:2B:3C:4D:10",
        "cpu_serial_number": "DUMMY_CPU_010",
        "hostname": "INSPECTION_PLC",
        "modbus_port": 502,
        "status": "登録済み"
    }
]

def register_equipment(equipment_data):
    """設備を登録"""
    try:
        # 既存設備の確認
        check_url = f"{API_BASE}/equipment/search"
        params = {"cpu_serial_number": equipment_data["cpu_serial_number"]}
        response = requests.get(check_url, params=params)

        if response.status_code == 200 and response.json():
            print(f"⚠️  {equipment_data['equipment_id']} は既に登録されています（スキップ）")
            return False

        # 設備登録
        register_url = f"{API_BASE}/register"
        response = requests.post(register_url, json=equipment_data)

        if response.status_code == 200 or response.status_code == 201:
            print(f"✅ {equipment_data['equipment_id']} を登録しました")
            return True
        else:
            print(f"❌ {equipment_data['equipment_id']} の登録に失敗: {response.status_code}")
            print(f"   エラー内容: {response.text}")
            return False

    except Exception as e:
        print(f"❌ {equipment_data['equipment_id']} の登録エラー: {e}")
        return False

def add_plc_configs(equipment_id):
    """PLCデータ設定を追加"""
    plc_configs = [
        {
            "data_type": "production_count",
            "address": "D1000",
            "scale_factor": 1,
            "plc_data_type": "word",
            "enabled": True
        },
        {
            "data_type": "current",
            "address": "D100",
            "scale_factor": 10,
            "plc_data_type": "word",
            "enabled": True
        },
        {
            "data_type": "temperature",
            "address": "D101",
            "scale_factor": 1,
            "plc_data_type": "float32",
            "enabled": True
        },
        {
            "data_type": "pressure",
            "address": "D102",
            "scale_factor": 100,
            "plc_data_type": "word",
            "enabled": True
        }
    ]

    try:
        url = f"{API_BASE}/equipment/{equipment_id}/plc_configs"
        response = requests.put(url, json=plc_configs)

        if response.status_code == 200:
            print(f"   📋 {equipment_id} のPLC設定を追加しました")
            return True
        else:
            print(f"   ⚠️  {equipment_id} のPLC設定追加に失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ {equipment_id} のPLC設定追加エラー: {e}")
        return False

def main():
    print("=" * 60)
    print("ダミー設備データ登録スクリプト")
    print("=" * 60)
    print()

    registered_count = 0
    skipped_count = 0

    for equipment in dummy_equipments:
        result = register_equipment(equipment)
        if result:
            registered_count += 1
            # 設定済みステータスの設備にはPLC設定を追加
            if equipment["status"] == "設定済み":
                add_plc_configs(equipment["equipment_id"])
        else:
            skipped_count += 1
        print()

    print("=" * 60)
    print(f"登録完了: {registered_count}件")
    print(f"スキップ: {skipped_count}件")
    print("=" * 60)
    print()
    print("✅ ブラウザで http://localhost:3000 にアクセスして確認してください")

if __name__ == "__main__":
    main()
