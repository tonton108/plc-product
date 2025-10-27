"""
LINE_A_001設備を登録
"""
import requests

BASE_URL = "http://localhost:5000"

def register_equipment():
    """LINE_A_001設備を登録"""
    equipment_data = {
        "equipment_id": "LINE_A_001",
        "manufacturer": "三菱",
        "series": "FX",
        "plc_ip": "192.168.0.10",
        "port": 5000,
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "cpu_serial_number": "TEST_LINE_A_CPU_001",
        "hostname": "line-a-raspi",
        "ip": "192.168.1.101",
        "interval": 2000
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/register",
            json=equipment_data,
            timeout=5
        )

        if response.status_code == 200 or response.status_code == 201:
            print(f"[SUCCESS] LINE_A_001を登録しました")
            print(f"  レスポンス: {response.json()}")
        else:
            print(f"[ERROR] 登録失敗: {response.status_code}")
            print(f"  エラー内容: {response.text}")

    except Exception as e:
        print(f"[ERROR] リクエストエラー: {e}")

if __name__ == '__main__':
    register_equipment()
