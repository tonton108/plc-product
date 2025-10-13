from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_socketio import SocketIO
import os
import json
import socket
import threading
import time
import uuid
import re
import subprocess
import signal
import atexit
import random  # 追加
from datetime import datetime
from dotenv import load_dotenv
from db_utils import ConfigManager, get_cpu_serial_number
from functools import wraps
import hashlib
# ラズパイではローカルDBを使用しない
# from backend.db import init_db
# from backend.api.routes import register_routes
# PLCエージェント関連インポート
from plc_agent import main_loop as plc_main_loop

load_dotenv()

# PLCエージェントプロセス管理
plc_agent_thread = None
plc_agent_stop_event = threading.Event()

# デバイス情報取得関数
def get_mac_address():
    """MACアドレスを取得"""
    mac = uuid.getnode()
    return ':'.join(re.findall('..', f'{mac:012x}'))

def get_ip_address():
    """IPアドレスを取得"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'

app = Flask(__name__)

# セキュリティ設定
app.secret_key = os.getenv("SECRET_KEY", "default-development-key-change-in-production")
app.config['SESSION_COOKIE_SECURE'] = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# SocketIO初期化
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# 認証設定
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()  # デフォルト: admin123
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"  # デフォルトで認証必須に変更

def get_current_admin_password_hash():
    """現在の管理者パスワードハッシュを取得（ローカル設定優先）"""
    config_manager = ConfigManager()
    local_hash = config_manager.get_admin_password_hash()
    
    if local_hash:
        return local_hash
    
    # ローカル設定がない場合は環境変数またはデフォルトを使用
    return os.getenv("ADMIN_PASSWORD_HASH", DEFAULT_ADMIN_PASSWORD_HASH)

def hash_password(password):
    """パスワードをハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def require_auth(f):
    """認証が必要な機能のデコレータ"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not REQUIRE_AUTH:
            return f(*args, **kwargs)
        
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        
        if (username == ADMIN_USERNAME and 
            hash_password(password) == get_current_admin_password_hash()):
            session['authenticated'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="認証に失敗しました")
    
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

class Config:
    def __init__(self):
        self.central_server_ip = os.getenv("CENTRAL_SERVER_IP", "192.168.1.10")
        self.central_server_port = os.getenv("CENTRAL_SERVER_PORT", "5000")
        self.raspi_ui_port = os.getenv("RASPI_UI_PORT", "5001")
        self.config_manager = ConfigManager()
        
    def load_plc_config(self):
        """PLC設定をDB優先で読み込み（JSONフォールバック）"""
        return self.config_manager.load_plc_config()
    
    def save_plc_config(self, config_data):
        """PLC設定をDB + JSONに保存"""
        return self.config_manager.save_plc_config(config_data)

config = Config()

# PLCメーカー・シリーズ
series_list = {
    "三菱": ["FX", "Q", "iQ-R", "iQ-F"],
    "キーエンス": ["KV-8000 (Modbus)", "KV-5000 (Modbus)", "KV Nano (Modbus)"],
    "オムロン": ["CJ", "CP", "NX", "NJ"],
    "シーメンス": ["S7-1200 (未実装)", "S7-1500 (未実装)"]
}
manufacturers = list(series_list.keys())

@app.route("/")
@require_auth
def index():
    """ログイン後の自動分岐：DB確認 → CPUシリアル番号で設備検索 → 適切な画面へ遷移"""
    try:
        from db_utils import get_cpu_serial_number, get_mac_address, get_ip_address
        
        # デバイス情報を取得
        cpu_serial_number = get_cpu_serial_number()
        mac_address = get_mac_address()
        ip_address = get_ip_address()
        
        print(f"🔍 [自動分岐] デバイス情報取得完了")
        print(f"   CPUシリアル番号: {cpu_serial_number}")
        print(f"   MACアドレス: {mac_address}")
        print(f"   IPアドレス: {ip_address}")
        
        # DB APIで設備検索（CPUシリアル番号最優先）
        db_api = config.config_manager.db_api
        equipment_info = None
        search_method = "なし"
        
        # 1. CPUシリアル番号で検索（最優先・最も確実）
        if cpu_serial_number:
            print(f"🔍 [自動分岐] CPUシリアル番号 '{cpu_serial_number}' で設備検索中...")
            equipment_info = db_api.get_equipment_by_device_info(cpu_serial_number=cpu_serial_number)
            if equipment_info:
                search_method = "CPUシリアル番号"
                print(f"✅ [自動分岐] CPUシリアル番号で設備発見: {equipment_info.get('equipment_id')}")
        
        # 2. CPUシリアル番号で見つからない場合、MACアドレスで検索
        if not equipment_info and mac_address:
            print(f"🔍 [自動分岐] MACアドレス '{mac_address}' で設備検索中...")
            equipment_info = db_api.get_equipment_by_device_info(mac_address=mac_address)
            if equipment_info:
                search_method = "MACアドレス"
                print(f"✅ [自動分岐] MACアドレスで設備発見: {equipment_info.get('equipment_id')}")
        
        # 3. MACアドレスでも見つからない場合、IPアドレスで検索
        if not equipment_info and ip_address:
            print(f"🔍 [自動分岐] IPアドレス '{ip_address}' で設備検索中...")
            equipment_info = db_api.get_equipment_by_device_info(ip_address=ip_address)
            if equipment_info:
                search_method = "IPアドレス"
                print(f"✅ [自動分岐] IPアドレスで設備発見: {equipment_info.get('equipment_id')}")
        
        # 分岐判定
        if equipment_info:
            equipment_id = equipment_info.get('equipment_id')
            print(f"🎯 [自動分岐] 設備発見 → モニタリング画面へ遷移")
            print(f"   設備ID: {equipment_id}")
            print(f"   検索方法: {search_method}")
            print(f"   製造元: {equipment_info.get('manufacturer', '未設定')}")
            print(f"   シリーズ: {equipment_info.get('series', '未設定')}")
            
            # 設備IDをローカル設定に保存（plc_agent用）
            config.config_manager.save_equipment_id(equipment_id)
            print(f"📝 [自動分岐] 設備ID '{equipment_id}' をローカル設定に保存しました")
            
            return redirect(url_for("monitoring"))
        else:
            print(f"❌ [自動分岐] 設備未発見 → 初期設定画面へ遷移")
            print(f"💡 [自動分岐] 設備登録が必要です")
            return redirect(url_for("initial_setup"))
            
    except Exception as e:
        print(f"❌ [自動分岐] エラー発生: {e}")
        print(f"🔄 [自動分岐] エラーのため初期設定画面へ遷移")
        return redirect(url_for("initial_setup"))

@app.route("/initial_setup", methods=["GET", "POST"])
@require_auth
def initial_setup():
    if request.method == "POST":
        # デバイス情報を自動取得
        mac_address = get_mac_address()
        ip_address = get_ip_address()
        cpu_serial_number = get_cpu_serial_number()
        hostname = socket.gethostname()
        

        
        # 基本PLC設定（デバイス情報を追加）
        plc_data = {
            "equipment_id": request.form["equipment_id"],
            "plc_ip": request.form["plc_ip"],
            "plc_port": int(request.form["plc_port"]),
            "modbus_port": int(request.form.get("modbus_port", 502)),  # Modbusポート追加
            "manufacturer": request.form["manufacturer"],
            "series": request.form["series"],
            "interval": int(request.form["interval"]),
            "central_server_ip": request.form["central_server_ip"],
            "central_server_port": int(request.form["central_server_port"]),
            # デバイス情報を追加
            "mac_address": mac_address,
            "cpu_serial_number": cpu_serial_number,  # CPUシリアル番号を追加
            "hostname": hostname,
            "raspi_ip": ip_address  # ラズパイのIPアドレス
        }
        
        print(f"[INFO] 設定画面から送信するデータ: {plc_data}")
        
        # PLCデータ項目設定を追加
        data_points = {}
        
        # 各データ項目の設定を処理
        data_items = [
            "production_count",
            "current", 
            "temperature",
            "pressure",
            "cycle_time",
            "error_code"
        ]
        
        for item in data_items:
            enabled_key = f"{item}_enabled"
            address_key = f"{item}_address"
            scale_key = f"{item}_scale"
            data_type_key = f"{item}_data_type"
            
            # チェックボックスがチェックされている場合のみ設定を保存
            if enabled_key in request.form:
                address = request.form.get(address_key, "").strip()
                scale = request.form.get(scale_key, "1")
                data_type = request.form.get(data_type_key, "word")
                
                # アドレスが入力されている場合のみ有効とする
                if address:
                    try:
                        scale_int = int(scale) if scale else 1
                        data_points[item] = {
                            "address": address,
                            "data_type": data_type,
                            "scale": scale_int,
                            "enabled": True
                        }
                    except ValueError:
                        # スケール値が不正な場合はデフォルト値を使用
                        data_points[item] = {
                            "address": address,
                            "data_type": data_type,
                            "scale": 1,
                            "enabled": True
                        }
            else:
                # チェックボックスが無効の場合は無効として保存
                address = request.form.get(address_key, "").strip()
                scale = request.form.get(scale_key, "1")
                data_type = request.form.get(data_type_key, "word")
                if address:  # アドレスがある場合のみ保存（設定は残す）
                    try:
                        scale_int = int(scale) if scale else 1
                        data_points[item] = {
                            "address": address,
                            "data_type": data_type,
                            "scale": scale_int,
                            "enabled": False
                        }
                    except ValueError:
                        data_points[item] = {
                            "address": address,
                            "data_type": data_type,
                            "scale": 1,
                            "enabled": False
                        }
        
        # data_pointsを基本設定に追加
        plc_data["data_points"] = data_points
        
        # 設定保存（ローカル）
        config.save_plc_config(plc_data)
        
        # API サーバーへの設備登録（データベース）
        try:
            api_data = {
                "equipment_id": plc_data["equipment_id"],
                "manufacturer": plc_data["manufacturer"],
                "series": plc_data["series"],
                "ip": plc_data["raspi_ip"],  # ラズパイのIPアドレス
                "plc_ip": plc_data["plc_ip"],  # PLCのIPアドレス
                "mac_address": plc_data["mac_address"],
                "cpu_serial_number": plc_data["cpu_serial_number"],  # CPUシリアル番号
                "hostname": plc_data["hostname"],
                "port": plc_data["plc_port"],
                "modbus_port": plc_data["modbus_port"],
                "interval": plc_data["interval"]
            }
            
            import requests
            api_url = f"http://{plc_data['central_server_ip']}:{plc_data['central_server_port']}/api/register"
            
            print(f"[INFO] API サーバーに設備登録中: {api_url}")
            print(f"[INFO] 送信データ: {api_data}")
            
            response = requests.post(api_url, json=api_data, timeout=10)
            
            if response.status_code == 200:
                print("✅ API サーバーへの設備登録成功")
                
                # PLCデータ設定もAPI サーバーに送信
                try:
                    plc_configs = []
                    for data_type, setting in data_points.items():
                        plc_configs.append({
                            "data_type": data_type,
                            "enabled": setting.get("enabled", False),
                            "address": setting.get("address", ""),
                            "scale_factor": setting.get("scale", 1),
                            "plc_data_type": setting.get("data_type", "word")
                        })
                    
                    plc_config_url = f"http://{plc_data['central_server_ip']}:{plc_data['central_server_port']}/api/equipment/{plc_data['equipment_id']}/plc_configs"
                    plc_response = requests.put(plc_config_url, json=plc_configs, timeout=10)
                    
                    if plc_response.status_code == 200:
                        print("✅ PLCデータ設定も送信成功")
                    else:
                        print(f"⚠️ PLCデータ設定送信失敗: {plc_response.status_code}")
                        
                except Exception as plc_e:
                    print(f"❌ PLCデータ設定送信エラー: {plc_e}")
                
            else:
                print(f"⚠️ API サーバーへの設備登録失敗: {response.status_code}")
                print(f"   レスポンス: {response.text}")
                
        except Exception as e:
            print(f"❌ API サーバーへの設備登録エラー: {e}")
            print("ℹ️ ローカル設定は保存されました")
        
        # PLC Agentを再起動（設定反映）
        restart_plc_agent()
        
        return redirect(url_for("monitoring"))
    
    # GET: 初期設定画面を表示（設備ID未設定時または初回セットアップ時）
    current = config.load_plc_config()
    current.setdefault("central_server_ip", config.central_server_ip)
    current.setdefault("central_server_port", config.central_server_port)
    current.setdefault("modbus_port", 502)  # Modbusポートのデフォルト値
    
    # data_pointsのデフォルト値を設定（初回アクセス時）
    if "data_points" not in current:
        current["data_points"] = {
            "production_count": {"address": "D150", "scale": 1, "enabled": False},
            "current": {"address": "D100", "scale": 10, "enabled": True},
            "temperature": {"address": "D101", "scale": 10, "enabled": True},
            "pressure": {"address": "D102", "scale": 100, "enabled": True},
            "cycle_time": {"address": "D200", "scale": 1, "enabled": False},
            "error_code": {"address": "D300", "scale": 1, "enabled": False}
        }
    
    return render_template("initial_setup.html", 
                         equipment=current, 
                         series_list=series_list, 
                         manufacturers=manufacturers)

@app.route("/monitoring")
@require_auth
def monitoring():
    current_config = config.load_plc_config()
    
    # 設備IDが未設定の場合は初期設定画面にリダイレクト
    if not current_config.get("equipment_id"):
        return redirect(url_for("initial_setup"))
    
    # data_pointsのデフォルト値を設定（モーダル用）
    if "data_points" not in current_config:
        current_config["data_points"] = {
            "production_count": {"address": "D150", "data_type": "word", "scale": 1, "enabled": False},
            "current": {"address": "D100", "data_type": "word", "scale": 10, "enabled": True},
            "temperature": {"address": "D101", "data_type": "float32", "scale": 1, "enabled": True},
            "pressure": {"address": "D102", "data_type": "word", "scale": 100, "enabled": True},
            "cycle_time": {"address": "D200", "data_type": "dword", "scale": 1, "enabled": False},
            "error_code": {"address": "D300", "data_type": "word", "scale": 1, "enabled": False}
        }
    
    return render_template("monitoring.html", 
                         equipment=current_config, 
                         series_list=series_list, 
                         manufacturers=manufacturers)

@app.route("/api/series")
@require_auth
def api_series():
    manufacturer = request.args.get("manufacturer", "")
    return jsonify(series_list.get(manufacturer, []))

@app.route("/api/logs")
@require_auth
def api_logs():
    """現在のPLCデータを返す（ダミーまたは実データ）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 設定ファイルを読み込み
    current_config = config.load_plc_config()
    data_points = current_config.get("data_points", {})
    
    # 有効なデータ項目のみダミーデータを生成（リアルタイム変動）
    dummy_data = {}
    for key, setting in data_points.items():
        if setting.get("enabled", False):
            if key == "production_count":
                # 1200-1300の間で変動（生産数量は徐々に増加傾向）
                base_count = 1200 + int(time.time()) % 100
                dummy_data[key] = base_count + random.randint(-10, 20)
            elif key == "current":
                # 2.8-3.8Aの間で変動
                dummy_data[key] = round(3.0 + random.uniform(-0.2, 0.8), 1)
            elif key == "temperature":
                # 24-28℃の間で変動
                dummy_data[key] = round(25.5 + random.uniform(-1.5, 2.5), 1)
            elif key == "pressure":
                # 0.4-0.5MPaの間で変動
                dummy_data[key] = round(0.45 + random.uniform(-0.05, 0.05), 2)
            elif key == "cycle_time":
                # 800-900msの間で変動
                dummy_data[key] = 850 + random.randint(-50, 50)
            elif key == "error_code":
                # 通常は0、まれにエラーコード（1-5）
                dummy_data[key] = 0 if random.random() > 0.05 else random.randint(1, 5)
            else:
                dummy_data[key] = round(random.uniform(-10, 10), 1)
    
    return jsonify({
        "timestamp": now,
        "status": "running",
        "data": dummy_data
    })

@app.route("/test-connection", methods=["POST"])
def test_connection():
    """PLC接続テスト"""
    current_config = config.load_plc_config()
    
    # 実際の接続テストロジックを実装
    try:
        # ここで実際のPLC接続テストを行う
        success = True  # 仮の結果
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/verify-password", methods=["POST"])
@require_auth
def verify_password():
    """設定変更時のパスワード確認"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "無効なリクエスト"}), 400
    
    password = data.get("password", "")
    
    # 現在ログインしているユーザーのパスワードと照合
    if hash_password(password) == get_current_admin_password_hash():
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "パスワードが正しくありません"})

@app.route("/api/plc-agent/status")
@require_auth
def api_plc_agent_status():
    """PLCエージェントの状態を取得"""
    global plc_agent_thread
    
    is_running = plc_agent_thread is not None and plc_agent_thread.is_alive()
    
    return jsonify({
        "is_running": is_running,
        "status": "運行中" if is_running else "停止中"
    })

@app.route("/api/plc-agent/restart", methods=["POST"])
@require_auth
def api_restart_plc_agent():
    """PLCエージェントを手動再起動"""
    try:
        restart_plc_agent()
        return jsonify({"success": True, "message": "PLCエージェントを再起動しました"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/plc-agent/start", methods=["POST"])
@require_auth
def api_start_plc_agent():
    """PLCエージェントを手動起動"""
    try:
        start_plc_agent()
        return jsonify({"success": True, "message": "PLCエージェントを起動しました"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/plc-agent/stop", methods=["POST"])
@require_auth
def api_stop_plc_agent():
    """PLCエージェントを手動停止"""
    try:
        stop_plc_agent()
        return jsonify({"success": True, "message": "PLCエージェントを停止しました"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/update-local-equipment-id", methods=["POST"])
@require_auth
def api_update_local_equipment_id():
    """ローカル設定ファイルの設備IDを更新"""
    try:
        data = request.get_json()
        new_equipment_id = data.get("equipment_id")
        
        if not new_equipment_id:
            return jsonify({"success": False, "error": "設備IDが指定されていません"}), 400
        
        # ConfigManagerを使用してローカル設定を更新
        success = config.config_manager.save_equipment_id(new_equipment_id)
        
        if success:
            print(f"✅ ローカル設備ID更新成功: {new_equipment_id}")
            return jsonify({"success": True, "message": "ローカル設備IDを更新しました"})
        else:
            return jsonify({"success": False, "error": "ローカル設備IDの更新に失敗しました"}), 500
            
    except Exception as e:
        print(f"❌ ローカル設備ID更新エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/current-equipment-info")
@require_auth
def api_current_equipment_info():
    """現在のデバイスの設備情報をDB優先で取得"""
    try:
        from db_utils import get_cpu_serial_number, get_mac_address, get_ip_address
        
        # デバイス情報を取得
        cpu_serial_number = get_cpu_serial_number()
        mac_address = get_mac_address()
        ip_address = get_ip_address()
        
        print(f"🔍 [DEBUG] デバイス情報 - CPU: {cpu_serial_number}, MAC: {mac_address}, IP: {ip_address}")
        
        # DB APIで設備検索（CPUシリアル番号最優先）
        db_api = config.config_manager.db_api
        equipment_info = None
        
        # CPUシリアル番号で検索（最優先）
        if cpu_serial_number:
            equipment_info = db_api.get_equipment_by_device_info(cpu_serial_number=cpu_serial_number)
            if equipment_info:
                print(f"✅ [DEBUG] CPUシリアル番号で設備発見: {equipment_info.get('equipment_id')}")
        
        # CPUシリアル番号で見つからない場合、MACアドレスで検索
        if not equipment_info and mac_address:
            equipment_info = db_api.get_equipment_by_device_info(mac_address=mac_address)
            if equipment_info:
                print(f"✅ [DEBUG] MACアドレスで設備発見: {equipment_info.get('equipment_id')}")
        
        if equipment_info:
            # DB設備情報が見つかった場合
            equipment_id = equipment_info.get("equipment_id")
            
            # 詳細な設備設定も取得
            detailed_config = db_api.get_equipment_config(equipment_id)
            plc_configs = db_api.get_plc_data_configs(equipment_id)
            
            if detailed_config:
                # PLC設定を辞書形式に変換
                data_points = {}
                for plc_config in plc_configs:
                    data_type = plc_config.get("data_type")
                    data_points[data_type] = {
                        "address": plc_config.get("address"),
                        "data_type": plc_config.get("plc_data_type", "word"),
                        "scale": plc_config.get("scale_factor", 1),
                        "enabled": plc_config.get("enabled", False)
                    }
                
                result = {
                    "source": "database",
                    "equipment_id": detailed_config.get("equipment_id"),
                    "manufacturer": detailed_config.get("manufacturer"),
                    "series": detailed_config.get("series"),
                    "plc_ip": detailed_config.get("plc_ip"),
                    "plc_port": detailed_config.get("port"),
                    "modbus_port": detailed_config.get("modbus_port", 502),
                    "central_server_ip": config.central_server_ip,
                    "central_server_port": config.central_server_port,
                    "interval": detailed_config.get("interval"),
                    "data_points": data_points,
                    "device_info": {
                        "mac_address": mac_address,
                        "cpu_serial_number": cpu_serial_number,
                        "ip": ip_address,
                        "hostname": detailed_config.get("hostname")
                    }
                }
                
                print(f"✅ [DEBUG] DB優先の設備情報を返却: {equipment_id}")
                return jsonify(result)
        
        # DB設備情報が見つからない場合、ローカル設定をフォールバック
        print("⚠️ [DEBUG] DB設備情報が見つからず、ローカル設定をフォールバック")
        local_config = config.load_plc_config()
        local_config["source"] = "local_config"
        local_config["device_info"] = {
            "mac_address": mac_address,
            "cpu_serial_number": cpu_serial_number,
            "ip": ip_address,
            "hostname": socket.gethostname()
        }
        
        return jsonify(local_config)
        
    except Exception as e:
        print(f"❌ [DEBUG] 設備情報取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

def restart_plc_agent():
    """PLC Agentを再起動（設定変更時）"""
    global plc_agent_thread, plc_agent_stop_event
    
    # 既存のPLCエージェントを停止
    stop_plc_agent()
    
    # 新しいPLCエージェントを起動
    start_plc_agent()
    print("✅ PLCエージェントを再起動しました")

def start_plc_agent():
    """PLCエージェントをバックグラウンドで起動"""
    global plc_agent_thread, plc_agent_stop_event
    
    if plc_agent_thread and plc_agent_thread.is_alive():
        print("⚠️ PLCエージェントは既に起動中です")
        return
    
    # 停止イベントをリセット
    plc_agent_stop_event.clear()
    
    # PLCエージェントをスレッドで起動
    plc_agent_thread = threading.Thread(target=plc_agent_wrapper, daemon=True)
    plc_agent_thread.start()
    print("🚀 PLCエージェントを起動しました")

def stop_plc_agent():
    """PLCエージェントを停止"""
    global plc_agent_thread, plc_agent_stop_event
    
    if plc_agent_thread and plc_agent_thread.is_alive():
        # 停止イベントを設定
        plc_agent_stop_event.set()
        
        # スレッドの終了を最大5秒待機
        plc_agent_thread.join(timeout=5)
        
        if plc_agent_thread.is_alive():
            print("⚠️ PLCエージェントの停止に時間がかかっています")
        else:
            print("🛑 PLCエージェントを停止しました")
    
    plc_agent_thread = None

def plc_agent_wrapper():
    """PLCエージェントのラッパー関数（停止イベント監視付き）"""
    try:
        # plc_agent.pyのmain_loop関数を停止イベント付きで実行
        while not plc_agent_stop_event.is_set():
            # 設定をDB優先で読み込み（設定変更に対応）
            from db_utils import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.load_plc_config()
            equipment_id = config.get("equipment_id")
            
            if not equipment_id:
                print("⚠️ 設備IDが未設定です。10秒後に再試行します。")
                plc_agent_stop_event.wait(10)
                continue
            
            # 設定に基づいてPLCからデータを取得
            from plc_agent import read_from_plc
            from db_utils import DatabaseAPI
            
            db_api = DatabaseAPI()
            values = read_from_plc(config)

            if values:
                # DB APIを使用してログデータを送信
                success = db_api.send_log_data(equipment_id, values)
                
                if success:
                    print(f"✅ DB送信成功: {equipment_id} / {values}")
                else:
                    print(f"❌ DB送信エラー: {equipment_id}")
            else:
                print("⚠️ データ取得失敗。")

            # 設定された間隔で待機（停止イベントも監視）
            interval = config.get("interval", 5000)
            plc_agent_stop_event.wait(interval / 1000.0)
            
    except Exception as e:
        print(f"❌ PLCエージェントエラー: {e}")

def cleanup_on_exit():
    """アプリケーション終了時のクリーンアップ"""
    print("🔄 アプリケーション終了処理...")
    stop_plc_agent()

# 終了時のクリーンアップを登録
atexit.register(cleanup_on_exit)

if __name__ == "__main__":
    print("🚀 PLC UI システム起動中...")
    
    # PLCエージェントを自動起動
    start_plc_agent()
    
    # Flaskアプリケーション起動（SocketIO対応）
    port = int(config.raspi_ui_port)
    print(f"🌐 WebUI起動: http://0.0.0.0:{port}")
    print("📡 WebSocket機能が有効化されました")
    socketio.run(app, debug=True, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True) 