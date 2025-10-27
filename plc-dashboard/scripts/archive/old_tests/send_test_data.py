"""
複数のテストデータをLINE_A_001に送信
"""
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

def send_test_data():
    """5つのデータポイントを送信"""
    for i in range(1, 6):
        data = {
            "equipment_id": "LINE_A_001",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
            "data": {
                "temperature": 28.0 + i,
                "pressure": 1015.0 + i,
                "production_count": 5700 + i * 100,
                "current": 12.0 + i * 0.1,
                "cycle_time": 4200 - i * 50,
                "error_code": 0
            }
        }

        print(f"[INFO] データポイント {i}/5 を送信中...")
        response = requests.post(f"{BASE_URL}/api/logs", json=data, timeout=5)

        if response.status_code == 200:
            print(f"[OK] データポイント {i} 送信成功: {response.json()}")
        else:
            print(f"[ERROR] データポイント {i} 送信失敗: {response.status_code} {response.text}")

        if i < 5:
            time.sleep(2)  # 2秒間隔で送信

if __name__ == '__main__':
    print("\n[INFO] LINE_A_001にテストデータを送信します...\n")
    send_test_data()
    print("\n[SUCCESS] すべてのデータポイントを送信完了\n")
