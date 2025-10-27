"""
LINE_A_001のPLCデータ設定を追加
"""
import requests

BASE_URL = "http://localhost:5000"

def setup_plc_configs():
    """LINE_A_001にPLCデータ設定を追加"""
    plc_configs = [
        {
            "name": "温度",
            "data_type": "temperature",
            "address": "D100",
            "plc_data_type": "word",
            "scale_factor": 10,
            "unit": "℃",
            "enabled": True
        },
        {
            "name": "圧力",
            "data_type": "pressure",
            "address": "D101",
            "plc_data_type": "word",
            "scale_factor": 10,
            "unit": "hPa",
            "enabled": True
        },
        {
            "name": "生産数",
            "data_type": "production_count",
            "address": "D102",
            "plc_data_type": "word",
            "scale_factor": 1,
            "unit": "個",
            "enabled": True
        },
        {
            "name": "電流",
            "data_type": "current",
            "address": "D103",
            "plc_data_type": "word",
            "scale_factor": 10,
            "unit": "A",
            "enabled": True
        },
        {
            "name": "サイクルタイム",
            "data_type": "cycle_time",
            "address": "D104",
            "plc_data_type": "word",
            "scale_factor": 1,
            "unit": "ms",
            "enabled": True
        },
        {
            "name": "エラーコード",
            "data_type": "error_code",
            "address": "D105",
            "plc_data_type": "word",
            "scale_factor": 1,
            "unit": "",
            "enabled": True
        }
    ]

    try:
        response = requests.put(
            f"{BASE_URL}/api/equipment/LINE_A_001/plc_configs",
            json=plc_configs,
            timeout=5
        )

        if response.status_code == 200:
            print(f"[SUCCESS] LINE_A_001のPLCデータ設定を追加しました")
            print(f"  設定項目数: {len(plc_configs)}件")
        else:
            print(f"[ERROR] 設定追加失敗: {response.status_code}")
            print(f"  エラー内容: {response.text}")

    except Exception as e:
        print(f"[ERROR] リクエストエラー: {e}")

if __name__ == '__main__':
    setup_plc_configs()
