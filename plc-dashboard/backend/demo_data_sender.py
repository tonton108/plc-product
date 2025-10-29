#!/usr/bin/env python3
"""
PLCデータ送信デモツール
リアルタイムモニタリング機能のテストのため、
ラズパイからのPLCデータ送信を模擬します。
"""

import requests
import time
import random
import json
from datetime import datetime, timezone
import threading
import argparse

class PLCDataSender:
    def __init__(self, server_url="http://localhost:5000", equipment_id="DEMO_001"):
        self.server_url = server_url
        self.equipment_id = equipment_id
        self.running = False
        
        # ベース値
        self.base_values = {
            "production_count": 0,
            "current": 12.5,
            "temperature": 25.0,
            "pressure": 0.8,
            "cycle_time": 15.0,
            "error_code": 0
        }
        
        # 変動範囲
        self.variations = {
            "current": 2.0,      # ±2.0A
            "temperature": 5.0,   # ±5.0℃
            "pressure": 0.2,      # ±0.2MPa
            "cycle_time": 3.0,    # ±3.0秒
        }
    
    def generate_demo_data(self):
        """デモデータを生成"""
        data = {
            "equipment_id": self.equipment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "production_count": self.base_values["production_count"],
            "current": round(
                self.base_values["current"] + random.uniform(
                    -self.variations["current"], 
                    self.variations["current"]
                ), 2
            ),
            "temperature": round(
                self.base_values["temperature"] + random.uniform(
                    -self.variations["temperature"], 
                    self.variations["temperature"]
                ), 1
            ),
            "pressure": round(
                self.base_values["pressure"] + random.uniform(
                    -self.variations["pressure"], 
                    self.variations["pressure"]
                ), 3
            ),
            "cycle_time": round(
                self.base_values["cycle_time"] + random.uniform(
                    -self.variations["cycle_time"], 
                    self.variations["cycle_time"]
                ), 1
            ),
            "error_code": self.base_values["error_code"]
        }
        
        # 1%の確率でエラーを発生
        if random.random() < 0.01:
            data["error_code"] = random.choice([101, 102, 103, 201, 202])
        
        # 5%の確率で生産数量が増加
        if random.random() < 0.05:
            self.base_values["production_count"] += 1
            data["production_count"] = self.base_values["production_count"]
        
        return data
    
    def send_data(self, data):
        """データをサーバーに送信"""
        try:
            url = f"{self.server_url}/api/logs"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=5)
            
            if response.status_code == 200:
                print(f" データ送信成功: {data['timestamp']} - 生産数: {data['production_count']}, 電流: {data['current']}A, 温度: {data['temperature']}℃")
                return True
            else:
                print(f" データ送信失敗: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f" 通信エラー: {e}")
            return False
    
    def start_continuous_sending(self, interval=2.0):
        """連続データ送信を開始"""
        self.running = True
        print(f"連続データ送信開始: 設備ID={self.equipment_id}, 送信間隔={interval}秒")
        print("停止するには Ctrl+C を押してください")
        
        try:
            while self.running:
                data = self.generate_demo_data()
                self.send_data(data)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n⏹️ ユーザーによる停止")
        except Exception as e:
            print(f" エラー発生: {e}")
        finally:
            self.running = False
            print("データ送信終了")
    
    def stop(self):
        """送信停止"""
        self.running = False
    
    def send_single_data(self):
        """単発データ送信"""
        data = self.generate_demo_data()
        print(f"単発データ送信:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return self.send_data(data)
    
    def register_equipment(self):
        """設備をサーバーに登録"""
        registration_data = {
            "equipment_id": self.equipment_id,
            "manufacturer": "Demo Corporation",
            "series": "DEMO-PLC",
            "ip": "192.168.1.100",
            "mac_address": "00:11:22:33:44:55",
            "hostname": "demo-raspberry-pi",
            "port": 502,
            "interval": 2
        }

        try:
            url = f"{self.server_url}/api/register"
            response = requests.post(url, json=registration_data, timeout=5)

            if response.status_code == 200:
                print(f" 設備登録成功: {self.equipment_id}")

                # PLC設定を登録
                self.register_plc_configs()

                return True
            else:
                print(f" 設備登録失敗: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f" 設備登録エラー: {e}")
            return False

    def register_plc_configs(self):
        """PLC設定を登録"""
        plc_configs = [
            {
                "name": "温度",
                "data_type": "temperature",
                "enabled": True,
                "address": "D100",
                "scale_factor": 10,
                "plc_data_type": "word",
                "icon": "",
                "unit": "°C"
            },
            {
                "name": "電流",
                "data_type": "current",
                "enabled": True,
                "address": "D200",
                "scale_factor": 100,
                "plc_data_type": "word",
                "icon": "",
                "unit": "A"
            },
            {
                "name": "圧力",
                "data_type": "pressure",
                "enabled": True,
                "address": "D300",
                "scale_factor": 10,
                "plc_data_type": "word",
                "icon": "",
                "unit": "MPa"
            },
            {
                "name": "回転数",
                "data_type": "rotation",
                "enabled": True,
                "address": "D400",
                "scale_factor": 1,
                "plc_data_type": "word",
                "icon": "",
                "unit": "rpm"
            },
            {
                "name": "振動",
                "data_type": "vibration",
                "enabled": True,
                "address": "D500",
                "scale_factor": 100,
                "plc_data_type": "word",
                "icon": "",
                "unit": "mm/s"
            }
        ]

        try:
            url = f"{self.server_url}/api/equipment/{self.equipment_id}/plc_configs"
            response = requests.put(url, json={"plc_configs": plc_configs}, timeout=5)

            if response.status_code == 200:
                print(f" PLC設定登録成功: {len(plc_configs)}個の設定を登録しました")
                return True
            else:
                print(f" PLC設定登録失敗: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f" PLC設定登録エラー: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='PLCデータ送信デモツール')
    parser.add_argument('--server', default='http://localhost:5000', 
                       help='サーバーURL (デフォルト: http://localhost:5000)')
    parser.add_argument('--equipment-id', default='DEMO_001', 
                       help='設備ID (デフォルト: DEMO_001)')
    parser.add_argument('--interval', type=float, default=2.0,
                       help='送信間隔（秒） (デフォルト: 2.0)')
    parser.add_argument('--mode', choices=['single', 'continuous', 'register'], 
                       default='continuous',
                       help='動作モード (デフォルト: continuous)')
    
    args = parser.parse_args()
    
    sender = PLCDataSender(args.server, args.equipment_id)
    
    print("=" * 60)
    print("PLCデータ送信デモツール")
    print("=" * 60)
    print(f"サーバー: {args.server}")
    print(f"設備ID: {args.equipment_id}")
    print(f"モード: {args.mode}")
    print("=" * 60)
    
    if args.mode == 'register':
        sender.register_equipment()
    elif args.mode == 'single':
        sender.send_single_data()
    elif args.mode == 'continuous':
        # 設備登録も実行
        print("設備登録中...")
        sender.register_equipment()
        time.sleep(1)
        
        # 連続送信開始
        sender.start_continuous_sending(args.interval)

if __name__ == "__main__":
    main() 