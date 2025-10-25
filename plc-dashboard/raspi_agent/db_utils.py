import os
import requests
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import socket
import uuid
from local_buffer import LocalBuffer

load_dotenv()

def get_cpu_serial_number():
    """ラズパイのCPUシリアル番号を取得（不変識別子）"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    # Serial行から値を抽出
                    serial = line.split(':')[1].strip()
                    if serial and serial != "0000000000000000":
                        return serial
        # SerialがないかデフォルトIDの場合は、fallback
        print("[WARNING] CPU Serial情報が見つからないため、フォールバックIDを使用")
        return _generate_fallback_serial()
    except Exception as e:
        print(f"[ERROR] CPUシリアル番号取得エラー: {e}")
        print("🔄 フォールバックIDを生成します")
        return _generate_fallback_serial()

def _generate_fallback_serial():
    """CPUシリアル番号が取得できない場合の固定フォールバックIDを返す"""
    # 不変の固定値を使用
    fallback_id = "FALLBACK_FIXED_ID"
    print(f"💡 フォールバックID使用: {fallback_id} (固定値)")
    return fallback_id

def get_mac_address():
    """MACアドレスを取得"""
    return ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])

def get_ip_address():
    """IPアドレスを取得"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'

class DatabaseAPI:
    """中央サーバーのデータベースAPIとの通信クラス"""

    def __init__(self):
        self.central_server_ip = os.getenv("CENTRAL_SERVER_IP", "192.168.1.10")
        self.central_server_port = os.getenv("CENTRAL_SERVER_PORT", "5000")
        self.base_url = f"http://{self.central_server_ip}:{self.central_server_port}/api"

        # ローカルバッファ機能を初期化
        self.buffer = LocalBuffer(db_path='config/buffer.db', max_retry=10)
        print("[INFO] ローカルバッファ機能を有効化しました")
        
    def get_equipment_config(self, equipment_id):
        """設備の基本設定を取得"""
        try:
            response = requests.get(f"{self.base_url}/equipment/{equipment_id}", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[ERROR] 設備設定取得エラー: {e}")
            return None
    
    def get_equipment_by_device_info(self, cpu_serial_number=None, mac_address=None, ip_address=None):
        """デバイス情報（CPUシリアル番号、MACアドレス、IPアドレス）で設備を検索"""
        try:
            params = {}
            if cpu_serial_number:
                params['cpu_serial_number'] = cpu_serial_number
            if mac_address:
                params['mac_address'] = mac_address
            if ip_address:
                params['ip_address'] = ip_address
            
            response = requests.get(f"{self.base_url}/equipment/search", params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[ERROR] デバイス情報による設備検索エラー: {e}")
            return None
    
    def check_equipment_setup_completed(self, equipment_id):
        """設備の初回セットアップが完了しているかチェック"""
        try:
            response = requests.get(f"{self.base_url}/equipment/{equipment_id}/setup_status", timeout=5)
            if response.status_code == 200:
                result = response.json()
                return result.get("setup_completed", False)
            return False
        except Exception as e:
            print(f"[ERROR] セットアップ状態確認エラー: {e}")
            return False
    
    def get_plc_data_configs(self, equipment_id):
        """設備のPLCデータ設定を取得"""
        try:
            response = requests.get(f"{self.base_url}/equipment/{equipment_id}/plc_configs", timeout=5)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"[ERROR] PLCデータ設定取得エラー: {e}")
            return []
    
    def save_equipment_config(self, equipment_data):
        """設備の基本設定を保存"""
        try:
            equipment_id = equipment_data.get("equipment_id")
            response = requests.put(f"{self.base_url}/equipment/{equipment_id}", 
                                  json=equipment_data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] 設備設定保存エラー: {e}")
            return False
    
    def save_equipment_config_by_id(self, target_equipment_id, equipment_data):
        """指定された設備IDで設備の基本設定を保存（設備ID変更対応）"""
        try:
            response = requests.put(f"{self.base_url}/equipment/{target_equipment_id}", 
                                  json=equipment_data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] 設備設定保存エラー: {e}")
            return False
    
    def save_plc_data_configs(self, equipment_id, plc_configs):
        """設備のPLCデータ設定を保存"""
        try:
            response = requests.put(f"{self.base_url}/equipment/{equipment_id}/plc_configs", 
                                  json=plc_configs, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] PLCデータ設定保存エラー: {e}")
            return False
    
    def mark_setup_completed(self, equipment_id):
        """設備の初回セットアップ完了をマーク"""
        try:
            response = requests.post(f"{self.base_url}/equipment/{equipment_id}/mark_setup_completed", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] セットアップ完了マークエラー: {e}")
            return False
    
    def send_log_data(self, equipment_id, log_data):
        """ログデータを送信（バッファリング対応）

        1. まずローカルバッファに保存
        2. 中央サーバーへの送信を試行
        3. 送信成功時はバッファから削除、失敗時はバッファに残す
        """
        try:
            payload = {
                "equipment_id": equipment_id,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                **log_data
            }

            # 1. ローカルバッファに保存
            record_id = self.buffer.save(equipment_id, payload)

            # 2. 中央サーバーへの送信を試行
            try:
                response = requests.post(f"{self.base_url}/logs", json=payload, timeout=5)
                if response.status_code == 200:
                    # 送信成功 → バッファから削除
                    self.buffer.mark_as_sent(record_id)
                    return True
                else:
                    # 送信失敗（HTTPエラー） → バッファに残す
                    error_msg = f"HTTP {response.status_code}"
                    self.buffer.increment_retry(record_id, error_msg)
                    print(f"[WARN] サーバーエラー（バッファに保存済み）: {error_msg}")
                    return False
            except requests.exceptions.RequestException as e:
                # 接続エラー → バッファに残す
                error_msg = str(e)
                self.buffer.increment_retry(record_id, error_msg)
                print(f"[WARN] 接続エラー（バッファに保存済み）: {error_msg}")
                return False

        except Exception as e:
            print(f"[ERROR] ログデータ送信エラー: {e}")
            return False

    def retry_pending_data(self, batch_size=100):
        """未送信データを再送信

        Args:
            batch_size: 1回に再送するデータ数（デフォルト100件）

        Returns:
            (成功数, 失敗数, 総数) のタプル
        """
        pending = self.buffer.get_pending(limit=batch_size)

        if not pending:
            return (0, 0, 0)

        success_count = 0
        failure_count = 0

        print(f"\n[RETRY] 未送信データの再送信を開始: {len(pending)}件")

        for record_id, equipment_id, data in pending:
            try:
                # タイムスタンプを再設定せず、元のタイムスタンプを使用
                response = requests.post(f"{self.base_url}/logs", json=data, timeout=5)

                if response.status_code == 200:
                    # 送信成功 → バッファから削除
                    self.buffer.mark_as_sent(record_id)
                    success_count += 1
                    print(f"  [OK] 再送成功: ID={record_id}, 設備={equipment_id}")
                else:
                    # 送信失敗 → 再試行カウント更新
                    error_msg = f"HTTP {response.status_code}"
                    self.buffer.increment_retry(record_id, error_msg)
                    failure_count += 1
                    print(f"  [WARN] 再送失敗（ID={record_id}）: {error_msg}")

            except requests.exceptions.RequestException as e:
                # 接続エラー → 再試行カウント更新
                error_msg = str(e)
                self.buffer.increment_retry(record_id, error_msg)
                failure_count += 1
                print(f"  [WARN] 再送失敗（ID={record_id}）: 接続エラー")
            except Exception as e:
                # その他のエラー
                self.buffer.increment_retry(record_id, str(e))
                failure_count += 1
                print(f"  [ERROR] 再送エラー（ID={record_id}）: {e}")

        print(f"[RESULT] 再送結果: 成功={success_count}, 失敗={failure_count}, 総数={len(pending)}\n")

        return (success_count, failure_count, len(pending))

    def cleanup_buffer(self, days=30):
        """古いバッファデータをクリーンアップ

        Args:
            days: 保存期間（日数、デフォルト30日）

        Returns:
            削除されたレコード数
        """
        # 古いデータを削除
        deleted_old = self.buffer.cleanup_old_data(days=days)

        # 再試行上限を超えたデータを削除
        deleted_max_retry = self.buffer.cleanup_max_retry_exceeded()

        total_deleted = deleted_old + deleted_max_retry

        if total_deleted > 0:
            print(f"[CLEANUP] バッファクリーンアップ完了: {total_deleted}件削除")

        return total_deleted

    def get_buffer_stats(self):
        """バッファの統計情報を取得・表示"""
        self.buffer.print_stats()
        return self.buffer.get_stats()

class ConfigManager:
    """設定管理クラス（DB + JSONフォールバック）"""
    
    def __init__(self):
        self.db_api = DatabaseAPI()
        self.json_config_path = 'config/plc_config.json'
        
    def is_first_run_db(self):
        """データベースベースの初回起動判定"""
        try:
            # デバイス固有の情報を取得
            mac_address = get_mac_address()
            ip_address = get_ip_address()
            
            print(f"🔍 デバイス情報で設備検索: MAC={mac_address}, IP={ip_address}")
            
            # データベースから設備を検索
            equipment_info = self.db_api.get_equipment_by_device_info(
                mac_address=mac_address, 
                ip_address=ip_address
            )
            
            if not equipment_info:
                print("[WARNING] データベースに設備が未登録 → 初回起動")
                return True
            
            equipment_id = equipment_info.get("equipment_id")
            if not equipment_id:
                print("[WARNING] 設備IDが取得できない → 初回起動")
                return True
            
            # 設備の初回セットアップ完了状態をチェック
            setup_completed = self.db_api.check_equipment_setup_completed(equipment_id)
            if not setup_completed:
                print(f"[WARNING] 設備 {equipment_id} のセットアップ未完了 → 初回起動")
                return True
            
            # PLCデータ設定が存在し、有効な項目があるかチェック
            plc_configs = self.db_api.get_plc_data_configs(equipment_id)
            if not plc_configs:
                print(f"[WARNING] 設備 {equipment_id} のPLC設定が存在しない → 初回起動")
                return True
            
            # 有効なPLC設定があるかチェック
            enabled_configs = [config for config in plc_configs if config.get("enabled", False)]
            if not enabled_configs:
                print(f"[WARNING] 設備 {equipment_id} に有効なPLC設定がない → 初回起動")
                return True
            
            print(f"[SUCCESS] 設備 {equipment_id} は設定済み → 通常起動")
            return False
            
        except Exception as e:
            print(f"[ERROR] 初回起動判定エラー: {e} → 初回起動として扱う")
            return True
    
    def load_plc_config(self):
        """PLC設定を読み込み（DB優先、JSONフォールバック）"""
        # まずローカルJSONファイルから設備IDを取得
        local_config = self._load_json_config()
        equipment_id = local_config.get("equipment_id")
        
        if not equipment_id:
            print("[WARNING] 設備IDが未設定です。")
            return local_config
        
        # DBから設備設定を取得
        equipment_config = self.db_api.get_equipment_config(equipment_id)
        plc_data_configs = self.db_api.get_plc_data_configs(equipment_id)
        
        if equipment_config and plc_data_configs is not None:
            # DB設定をローカル形式に変換
            config = {
                "equipment_id": equipment_config.get("equipment_id"),
                "plc_ip": equipment_config.get("ip"),
                "plc_port": equipment_config.get("port"),
                "modbus_port": equipment_config.get("modbus_port", 502),  # Modbusポート追加
                "manufacturer": equipment_config.get("manufacturer"),
                "series": equipment_config.get("series"),
                "interval": equipment_config.get("interval"),
                "central_server_ip": self.db_api.central_server_ip,
                "central_server_port": self.db_api.central_server_port,
                "data_points": {}
            }
            
            # PLCデータ設定を変換
            for plc_config in plc_data_configs:
                data_type = plc_config.get("data_type")
                config["data_points"][data_type] = {
                    "name": plc_config.get("name", data_type),  # 項目名
                    "icon": plc_config.get("icon", ""),  # アイコン
                    "unit": plc_config.get("unit", ""),  # 単位
                    "address": plc_config.get("address"),
                    "data_type": plc_config.get("plc_data_type", "word"),  # 新しいPLCデータ型フィールド
                    "scale": plc_config.get("scale_factor", 1),
                    "enabled": plc_config.get("enabled", False)
                }
            
            print(f"[SUCCESS] DB設定読み込み成功: {equipment_id}")
            return config
        else:
            print("[WARNING] DB設定読み込み失敗、JSONファイルを使用")
            return local_config
    
    def save_plc_config(self, config_data):
        """PLC設定を保存（DB + JSONバックアップ）"""
        # JSONファイルにもバックアップ保存
        self._save_json_config(config_data)
        
        new_equipment_id = config_data.get("equipment_id")
        if not new_equipment_id:
            print("[ERROR] 設備IDが未設定のためDB保存をスキップ")
            return False
        
        # 現在の設備をMACアドレスで特定
        mac_address = config_data.get("mac_address")
        current_equipment = None
        current_equipment_id = None
        
        if mac_address:
            # まず中央サーバーで検索を試行
            current_equipment = self.db_api.get_equipment_by_device_info(mac_address=mac_address)
            if current_equipment:
                current_equipment_id = current_equipment.get("equipment_id")
                print(f"🔍 現在の設備を特定（DB）: {current_equipment_id} → {new_equipment_id}")
            else:
                # 中央サーバーAPIが利用できない場合、JSONファイルから既存設備IDを取得
                try:
                    json_config = self._load_json_config()
                    json_mac = json_config.get("mac_address")
                    json_equipment_id = json_config.get("equipment_id")
                    
                    # MACアドレスが一致し、設備IDが設定されている場合は既存設備として扱う
                    if json_mac == mac_address and json_equipment_id:
                        current_equipment_id = json_equipment_id
                        print(f"🔍 現在の設備を特定（JSON）: {current_equipment_id} → {new_equipment_id}")
                except Exception as e:
                    print(f"[WARNING] JSONファイルから既存設備ID取得に失敗: {e}")
        
        # 追加チェック：新しい設備IDが既存設備として中央サーバーに存在するか確認
        if not current_equipment_id and new_equipment_id:
            try:
                existing_equipment = self.db_api.get_equipment_config(new_equipment_id)
                if existing_equipment:
                    current_equipment_id = new_equipment_id
                    print(f"🔍 設備IDによる既存設備を特定: {new_equipment_id}")
            except Exception as e:
                print(f"[WARNING] 設備ID検索に失敗: {e}")
        
        # 設備基本情報をDB保存
        equipment_data = {
            "equipment_id": new_equipment_id,                 # 新しい設備ID（データ内容）
            "manufacturer": config_data.get("manufacturer"),
            "series": config_data.get("series"),
            "ip": config_data.get("raspi_ip"),                # ラズパイのIPアドレス（DB側のipフィールド）
            "plc_ip": config_data.get("plc_ip"),              # PLCのIPアドレス（新しいplc_ipフィールド）
            "port": config_data.get("plc_port"),              # PLCのポート
            "modbus_port": config_data.get("modbus_port", 502),  # Modbusポート追加
            "interval": config_data.get("interval"),
            # ラズパイのデバイス情報も保存
            "mac_address": config_data.get("mac_address"),
            "hostname": config_data.get("hostname"),
            "raspi_ip": config_data.get("raspi_ip")           # ラズパイのIPアドレス（APIとの互換性用）
        }
        
        # PLCデータ設定をDB形式に変換
        plc_configs = []
        data_points = config_data.get("data_points", {})
        for data_type, setting in data_points.items():
            plc_configs.append({
                "data_type": data_type,
                "name": setting.get("name", data_type),  # 項目名（なければdata_typeをフォールバック）
                "icon": setting.get("icon", ""),  # アイコン
                "unit": setting.get("unit", ""),  # 単位
                "enabled": setting.get("enabled", False),
                "address": setting.get("address", ""),
                "scale_factor": setting.get("scale", 1),
                "plc_data_type": setting.get("data_type", "word")  # PLCデータ型追加
            })
        
        # DB保存実行（現在の設備IDでURL生成、新しい設備IDでデータ更新）
        target_equipment_id = current_equipment_id if current_equipment_id else new_equipment_id
        
        equipment_success = self.db_api.save_equipment_config_by_id(target_equipment_id, equipment_data)
        plc_success = self.db_api.save_plc_data_configs(target_equipment_id, plc_configs)
        
        # 設定保存が成功した場合、セットアップ完了フラグを設定
        if equipment_success and plc_success:
            # セットアップ完了フラグは新しい設備IDで設定
            self.db_api.mark_setup_completed(new_equipment_id)
            print(f"[SUCCESS] DB設定保存成功: {target_equipment_id} → {new_equipment_id}")
            return True
        else:
            print("[ERROR] DB設定保存失敗")
            return False
    
    def _load_json_config(self):
        """JSONファイルから設定を読み込み"""
        try:
            with open(self.json_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "plc_ip": "192.168.1.100",
                "plc_port": 5000,
                "modbus_port": 502,
                "manufacturer": "三菱",
                "series": "FX",
                "equipment_id": "",
                "interval": 1000,
                "data_points": {
                    "production_count": {"address": "D150", "data_type": "word", "scale": 1, "enabled": False},
                    "current": {"address": "D100", "data_type": "word", "scale": 10, "enabled": True},
                    "temperature": {"address": "D101", "data_type": "float32", "scale": 1, "enabled": True},
                    "pressure": {"address": "D102", "data_type": "word", "scale": 100, "enabled": True},
                    "cycle_time": {"address": "D200", "data_type": "dword", "scale": 1, "enabled": False},
                    "error_code": {"address": "D300", "data_type": "word", "scale": 1, "enabled": False}
                }
            }
    
    def _save_json_config(self, config_data):
        """JSONファイルに設定を保存"""
        os.makedirs('config', exist_ok=True)
        with open(self.json_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    def save_equipment_id(self, equipment_id):
        """設備IDを設定に保存"""
        try:
            # 現在の設定を読み込み
            config_data = self._load_json_config()
            
            # 設備IDを更新
            config_data["equipment_id"] = equipment_id
            
            # 設定を保存
            self._save_json_config(config_data)
            print(f"📝 設備ID '{equipment_id}' をローカル設定に保存しました")
            
            return True
        except Exception as e:
            print(f"[ERROR] 設備ID保存エラー: {e}")
            return False
    
    def save_admin_password(self, password_hash):
        """管理者パスワードハッシュをローカル設定に保存"""
        try:
            # 現在の設定を読み込み
            config_data = self._load_json_config()
            
            # パスワードハッシュを更新
            config_data["admin_password_hash"] = password_hash
            
            # 設定を保存
            self._save_json_config(config_data)
            print("📝 管理者パスワードをローカル設定に保存しました")
            
            return True
        except Exception as e:
            print(f"[ERROR] 管理者パスワード保存エラー: {e}")
            return False
    
    def get_admin_password_hash(self):
        """管理者パスワードハッシュを取得（ローカル設定優先）"""
        try:
            config_data = self._load_json_config()
            local_hash = config_data.get("admin_password_hash")
            
            if local_hash:
                print("[SUCCESS] ローカル設定のパスワードハッシュを使用")
                return local_hash
            else:
                print("[WARNING] ローカル設定にパスワードなし、デフォルトを使用")
                return None  # デフォルトまたは環境変数を使用
                
        except Exception as e:
            print(f"[ERROR] パスワードハッシュ取得エラー: {e}")
            return None 