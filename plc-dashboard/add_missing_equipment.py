#!/usr/bin/env python3
"""
不足している設備IDをデータベースに追加
"""

import psycopg2
from datetime import datetime

def add_missing_equipment():
    try:
        # PostgreSQL接続
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="plc_monitor",
            user="plc_user",
            password="plc_pass"
        )
        cursor = conn.cursor()
        
        # 不足している設備ID EP_TEST_CONFIG123454 を追加
        insert_query = """
        INSERT INTO equipments 
        (equipment_id, manufacturer, series, ip, plc_ip, mac_address, hostname, port, modbus_port, interval, status, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (equipment_id) DO NOTHING
        """
        
        values = (
            "EP_TEST_CONFIG123454",  # equipment_id
            "三菱",                   # manufacturer
            "Q",                     # series
            "192.168.0.100",         # ip
            "192.168.0.100",         # plc_ip
            "00:11:22:33:44:56",     # mac_address
            "DESKTOP-K88UM9J",       # hostname
            5001,                    # port
            502,                     # modbus_port
            2000,                    # interval
            "設定済み",               # status
            datetime.utcnow()        # updated_at
        )
        
        cursor.execute(insert_query, values)
        conn.commit()
        
        print("✅ 設備 EP_TEST_CONFIG123454 を正常に追加しました")
        
        # 確認のため設備一覧を表示
        cursor.execute("SELECT equipment_id, manufacturer, series, status FROM equipments ORDER BY id")
        equipments = cursor.fetchall()
        
        print("\n📊 現在の設備一覧:")
        for eq in equipments:
            print(f"  - {eq[0]}: {eq[1]} {eq[2]} ({eq[3]})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    add_missing_equipment() 