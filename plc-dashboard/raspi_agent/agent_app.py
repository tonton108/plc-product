from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
from flask_socketio import SocketIO
from flask_babel import Babel, gettext as _
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
import logging
# ラズパイではローカルDBを使用しない
# from backend.db import init_db
# from backend.api.routes import register_routes
# PLCエージェント関連インポート
from plc_agent import main_loop as plc_main_loop

load_dotenv()

# Windows環境でのUnicodeEncodeError回避用ヘルパー関数
def safe_print(*args, **kwargs):
    """Windows環境でemojiを含むprint文のエンコードエラーを回避"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # emojiと特殊文字を削除してから出力
        import re
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # Unicode emoji・記号文字を削除（広範囲をカバー）
                # U+1F000-U+1FFFF: 絵文字
                # U+2000-U+2BFF: 各種記号
                safe_arg = re.sub(r'[\U0001F000-\U0001FFFF\u2000-\u2BFF\uFE00-\uFE0F]', '', arg)
                safe_args.append(safe_arg)
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)

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

# Babel（多言語対応）設定
app.config['BABEL_DEFAULT_LOCALE'] = 'ja'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['LANGUAGES'] = {
    'ja': '日本語',
    'en': 'English',
    'zh': '中文'
}
babel = Babel(app)

def get_locale():
    """現在の言語を取得（クッキー > ブラウザ設定）"""
    # クッキーから言語を取得
    lang = request.cookies.get('lang')
    if lang in app.config['LANGUAGES']:
        return lang
    # ブラウザの言語設定から最適な言語を選択
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'ja'

babel.init_app(app, locale_selector=get_locale)

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

@app.route("/change_language/<lang>")
def change_language(lang):
    """言語を切り替え"""
    if lang in app.config['LANGUAGES']:
        response = make_response(redirect(request.referrer or url_for('index')))
        response.set_cookie('lang', lang, max_age=60*60*24*365)  # 1年間有効
        return response
    return redirect(request.referrer or url_for('index'))

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
        
        safe_print(f"🔍 [自動分岐] デバイス情報取得完了")
        safe_print(f"   CPUシリアル番号: {cpu_serial_number}")
        safe_print(f"   MACアドレス: {mac_address}")
        safe_print(f"   IPアドレス: {ip_address}")
        
        # DB APIで設備検索（CPUシリアル番号最優先）
        db_api = config.config_manager.db_api
        equipment_info = None
        search_method = "なし"
        
        # 1. CPUシリアル番号で検索（最優先・最も確実）
        if cpu_serial_number:
            safe_print(f"🔍 [自動分岐] CPUシリアル番号 '{cpu_serial_number}' で設備検索中...")
            equipment_info = db_api.get_equipment_by_device_info(cpu_serial_number=cpu_serial_number)
            if equipment_info:
                search_method = "CPUシリアル番号"
                safe_print(f"✅ [自動分岐] CPUシリアル番号で設備発見: {equipment_info.get('equipment_id')}")
        
        # 2. CPUシリアル番号で見つからない場合、MACアドレスで検索
        if not equipment_info and mac_address:
            safe_print(f"🔍 [自動分岐] MACアドレス '{mac_address}' で設備検索中...")
            equipment_info = db_api.get_equipment_by_device_info(mac_address=mac_address)
            if equipment_info:
                search_method = "MACアドレス"
                safe_print(f"✅ [自動分岐] MACアドレスで設備発見: {equipment_info.get('equipment_id')}")
        
        # 3. MACアドレスでも見つからない場合、IPアドレスで検索
        if not equipment_info and ip_address:
            safe_print(f"🔍 [自動分岐] IPアドレス '{ip_address}' で設備検索中...")
            equipment_info = db_api.get_equipment_by_device_info(ip_address=ip_address)
            if equipment_info:
                search_method = "IPアドレス"
                safe_print(f"✅ [自動分岐] IPアドレスで設備発見: {equipment_info.get('equipment_id')}")
        
        # 分岐判定
        if equipment_info:
            equipment_id = equipment_info.get('equipment_id')
            safe_print(f"🎯 [自動分岐] 設備発見 → モニタリング画面へ遷移")
            safe_print(f"   設備ID: {equipment_id}")
            safe_print(f"   検索方法: {search_method}")
            safe_print(f"   製造元: {equipment_info.get('manufacturer', '未設定')}")
            safe_print(f"   シリーズ: {equipment_info.get('series', '未設定')}")
            
            # 設備IDをローカル設定に保存（plc_agent用）
            config.config_manager.save_equipment_id(equipment_id)
            safe_print(f"📝 [自動分岐] 設備ID '{equipment_id}' をローカル設定に保存しました")
            
            return redirect(url_for("monitoring"))
        else:
            safe_print(f"❌ [自動分岐] 設備未発見 → 初期設定画面へ遷移")
            safe_print(f"💡 [自動分岐] 設備登録が必要です")
            return redirect(url_for("initial_setup"))
            
    except Exception as e:
        safe_print(f"❌ [自動分岐] エラー発生: {e}")
        safe_print(f"🔄 [自動分岐] エラーのため初期設定画面へ遷移")
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
        
        safe_print(f"[INFO] 設定画面から送信するデータ: {plc_data}")

        # PLCデータ項目設定を追加（動的JSON形式に対応）
        data_points = {}

        # plc_configs_jsonからPLC設定を読み取り（新しい動的フォーマット）
        plc_configs_json = request.form.get("plc_configs_json", "")

        if plc_configs_json:
            try:
                plc_configs = json.loads(plc_configs_json)
                safe_print(f"[INFO] 動的PLC設定を受信: {len(plc_configs)}項目")

                for plc_config in plc_configs:
                    data_type = plc_config.get("data_type")
                    if not data_type:
                        continue

                    data_points[data_type] = {
                        "name": plc_config.get("name", data_type),  # 項目名
                        "icon": plc_config.get("icon", ""),  # アイコン
                        "unit": plc_config.get("unit", ""),  # 単位
                        "address": plc_config.get("address", ""),
                        "data_type": plc_config.get("plc_data_type", "word"),
                        "scale": plc_config.get("scale_factor", 1),
                        "enabled": plc_config.get("enabled", True)
                    }

                safe_print(f"[INFO] 処理したPLC項目: {list(data_points.keys())}")

            except json.JSONDecodeError as e:
                safe_print(f"❌ JSON解析エラー: {e}")
                # JSONエラーの場合は空の設定を使用
                data_points = {}
        else:
            safe_print("⚠️ plc_configs_jsonが見つかりません（古いフォーマットの可能性）")
        
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
            
            safe_print(f"[INFO] API サーバーに設備登録中: {api_url}")
            safe_print(f"[INFO] 送信データ: {api_data}")
            
            response = requests.post(api_url, json=api_data, timeout=10)
            
            if response.status_code == 200:
                safe_print("✅ API サーバーへの設備登録成功")
                
                # PLCデータ設定もAPI サーバーに送信
                try:
                    plc_configs = []
                    for data_type, setting in data_points.items():
                        plc_configs.append({
                            "data_type": data_type,
                            "name": setting.get("name", data_type),  # 項目名
                            "icon": setting.get("icon", ""),  # アイコン
                            "unit": setting.get("unit", ""),  # 単位
                            "enabled": setting.get("enabled", False),
                            "address": setting.get("address", ""),
                            "scale_factor": setting.get("scale", 1),
                            "plc_data_type": setting.get("data_type", "word")
                        })

                    plc_config_url = f"http://{plc_data['central_server_ip']}:{plc_data['central_server_port']}/api/equipment/{plc_data['equipment_id']}/plc_configs"
                    safe_print(f"[INFO] 送信するPLC設定: {plc_configs}")  # デバッグ用
                    plc_response = requests.put(plc_config_url, json=plc_configs, timeout=10)
                    
                    if plc_response.status_code == 200:
                        safe_print("✅ PLCデータ設定も送信成功")
                    else:
                        safe_print(f"⚠️ PLCデータ設定送信失敗: {plc_response.status_code}")
                        
                except Exception as plc_e:
                    safe_print(f"❌ PLCデータ設定送信エラー: {plc_e}")
                
            else:
                safe_print(f"⚠️ API サーバーへの設備登録失敗: {response.status_code}")
                safe_print(f"   レスポンス: {response.text}")
                
        except Exception as e:
            safe_print(f"❌ API サーバーへの設備登録エラー: {e}")
            safe_print("ℹ️ ローカル設定は保存されました")
        
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
            safe_print(f"✅ ローカル設備ID更新成功: {new_equipment_id}")
            return jsonify({"success": True, "message": "ローカル設備IDを更新しました"})
        else:
            return jsonify({"success": False, "error": "ローカル設備IDの更新に失敗しました"}), 500

    except Exception as e:
        safe_print(f"❌ ローカル設備ID更新エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/equipment/<equipment_id>", methods=["PUT"])
@require_auth
def api_update_equipment(equipment_id):
    """設備基本設定を更新（ローカル保存 + 中央サーバー転送）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "無効なリクエストデータ"}), 400

        # 現在の設定を読み込み
        current_config = config.load_plc_config()

        # 基本設定を更新
        updated_config = {
            "equipment_id": data.get("equipment_id", equipment_id),
            "manufacturer": data.get("manufacturer"),
            "series": data.get("series"),
            "plc_ip": data.get("plc_ip"),
            "plc_port": data.get("plc_port"),
            "modbus_port": data.get("modbus_port", 502),
            "interval": data.get("interval"),
            "central_server_ip": data.get("central_server_ip", config.central_server_ip),
            "central_server_port": data.get("central_server_port", config.central_server_port),
            "mac_address": data.get("mac_address"),
            "cpu_serial_number": data.get("cpu_serial_number"),
            "hostname": data.get("hostname"),
            "raspi_ip": data.get("raspi_ip")
        }

        # data_pointsは既存の設定を保持（別のエンドポイントで更新）
        if "data_points" in current_config:
            updated_config["data_points"] = current_config["data_points"]

        # ローカル設定を保存
        config.save_plc_config(updated_config)
        safe_print(f"✅ ローカル設定保存成功: {equipment_id}")

        # 中央サーバーに設備情報を送信
        try:
            import requests
            api_data = {
                "equipment_id": updated_config["equipment_id"],
                "manufacturer": updated_config["manufacturer"],
                "series": updated_config["series"],
                "ip": updated_config["raspi_ip"],
                "plc_ip": updated_config["plc_ip"],
                "mac_address": updated_config["mac_address"],
                "cpu_serial_number": updated_config["cpu_serial_number"],
                "hostname": updated_config["hostname"],
                "port": updated_config["plc_port"],
                "modbus_port": updated_config["modbus_port"],
                "interval": updated_config["interval"]
            }

            api_url = f"http://{updated_config['central_server_ip']}:{updated_config['central_server_port']}/api/register"
            safe_print(f"📡 中央サーバーに設備更新を送信: {api_url}")

            response = requests.post(api_url, json=api_data, timeout=10)

            if response.status_code == 200:
                safe_print(f"✅ 中央サーバーへの設備更新成功")
            else:
                safe_print(f"⚠️ 中央サーバーへの設備更新失敗: {response.status_code}")

        except Exception as e:
            safe_print(f"❌ 中央サーバーへの設備更新エラー: {e}")
            # 中央サーバー転送失敗でもローカル保存は成功しているのでエラーにしない

        # PLCエージェントを再起動して設定を反映
        restart_plc_agent()

        return jsonify({"success": True, "message": "設備設定を更新しました"})

    except Exception as e:
        safe_print(f"❌ 設備設定更新エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/equipment/<equipment_id>/plc_configs", methods=["PUT"])
@require_auth
def api_update_plc_configs(equipment_id):
    """PLCデータ設定を更新（ローカル保存 + 中央サーバー転送）"""
    try:
        plc_configs = request.get_json()
        if not isinstance(plc_configs, list):
            return jsonify({"success": False, "error": "無効なリクエストデータ"}), 400

        # 現在の設定を読み込み
        current_config = config.load_plc_config()

        # PLCデータ設定を辞書形式に変換
        data_points = {}
        for plc_config in plc_configs:
            data_type = plc_config.get("data_type")
            data_points[data_type] = {
                "address": plc_config.get("address"),
                "data_type": plc_config.get("plc_data_type", "word"),
                "scale": plc_config.get("scale_factor", 1),
                "enabled": plc_config.get("enabled", False)
            }

        # data_pointsを設定に追加
        current_config["data_points"] = data_points

        # ローカル設定を保存
        config.save_plc_config(current_config)
        safe_print(f"✅ PLCデータ設定保存成功: {equipment_id}")

        # 中央サーバーにPLCデータ設定を送信
        try:
            import requests
            plc_config_url = f"http://{current_config.get('central_server_ip', config.central_server_ip)}:{current_config.get('central_server_port', config.central_server_port)}/api/equipment/{equipment_id}/plc_configs"
            safe_print(f"📡 中央サーバーにPLCデータ設定を送信: {plc_config_url}")

            response = requests.put(plc_config_url, json=plc_configs, timeout=10)

            if response.status_code == 200:
                safe_print(f"✅ 中央サーバーへのPLCデータ設定送信成功")
            else:
                safe_print(f"⚠️ 中央サーバーへのPLCデータ設定送信失敗: {response.status_code}")

        except Exception as e:
            safe_print(f"❌ 中央サーバーへのPLCデータ設定送信エラー: {e}")
            # 中央サーバー転送失敗でもローカル保存は成功しているのでエラーにしない

        # PLCエージェントを再起動して設定を反映
        restart_plc_agent()

        return jsonify({"success": True, "message": "PLCデータ設定を更新しました"})

    except Exception as e:
        safe_print(f"❌ PLCデータ設定更新エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/equipment/<equipment_id>/plc_configs", methods=["GET"])
@require_auth
def api_get_plc_configs(equipment_id):
    """PLCデータ設定を取得（DB優先、ローカル設定フォールバック）"""
    try:
        # 1. DB APIでPLC設定を取得（優先）
        db_api = config.config_manager.db_api
        plc_configs = db_api.get_plc_data_configs(equipment_id)

        if plc_configs:
            safe_print(f"✅ DBからPLC設定を取得: {equipment_id} - {len(plc_configs)}項目")
            return jsonify(plc_configs), 200

        # 2. DB設定が空の場合、ローカルplc_config.jsonから取得（フォールバック）
        safe_print(f"⚠️ DB設定が空のため、ローカル設定をフォールバック: {equipment_id}")
        local_config = config.load_plc_config()
        data_points = local_config.get("data_points", {})

        # ローカル設定を中央サーバー形式に変換
        configs = []
        for data_type, setting in data_points.items():
            configs.append({
                "data_type": data_type,
                "name": setting.get("name", data_type),  # 項目名（空なら内部キーを使用）
                "icon": setting.get("icon", ""),  # アイコン
                "unit": setting.get("unit", ""),  # 単位
                "enabled": setting.get("enabled", False),
                "address": setting.get("address", ""),
                "scale_factor": setting.get("scale", 1),
                "plc_data_type": setting.get("data_type", "word")
            })

        safe_print(f"✅ ローカル設定からPLC設定を取得: {equipment_id} - {len(configs)}項目")
        return jsonify(configs), 200

    except Exception as e:
        safe_print(f"❌ PLC設定取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

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
        
        safe_print(f"🔍 [DEBUG] デバイス情報 - CPU: {cpu_serial_number}, MAC: {mac_address}, IP: {ip_address}")
        
        # DB APIで設備検索（CPUシリアル番号最優先）
        db_api = config.config_manager.db_api
        equipment_info = None
        
        # CPUシリアル番号で検索（最優先）
        if cpu_serial_number:
            equipment_info = db_api.get_equipment_by_device_info(cpu_serial_number=cpu_serial_number)
            if equipment_info:
                safe_print(f"✅ [DEBUG] CPUシリアル番号で設備発見: {equipment_info.get('equipment_id')}")
        
        # CPUシリアル番号で見つからない場合、MACアドレスで検索
        if not equipment_info and mac_address:
            equipment_info = db_api.get_equipment_by_device_info(mac_address=mac_address)
            if equipment_info:
                safe_print(f"✅ [DEBUG] MACアドレスで設備発見: {equipment_info.get('equipment_id')}")
        
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
                
                safe_print(f"✅ [DEBUG] DB優先の設備情報を返却: {equipment_id}")
                return jsonify(result)
        
        # DB設備情報が見つからない場合、ローカル設定をフォールバック
        safe_print("⚠️ [DEBUG] DB設備情報が見つからず、ローカル設定をフォールバック")
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
        safe_print(f"❌ [DEBUG] 設備情報取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

def restart_plc_agent():
    """PLC Agentを再起動（設定変更時）"""
    global plc_agent_thread, plc_agent_stop_event
    
    # 既存のPLCエージェントを停止
    stop_plc_agent()
    
    # 新しいPLCエージェントを起動
    start_plc_agent()
    safe_print("✅ PLCエージェントを再起動しました")

def start_plc_agent():
    """PLCエージェントをバックグラウンドで起動"""
    global plc_agent_thread, plc_agent_stop_event
    
    if plc_agent_thread and plc_agent_thread.is_alive():
        safe_print("⚠️ PLCエージェントは既に起動中です")
        return
    
    # 停止イベントをリセット
    plc_agent_stop_event.clear()
    
    # PLCエージェントをスレッドで起動
    plc_agent_thread = threading.Thread(target=plc_agent_wrapper, daemon=True)
    plc_agent_thread.start()
    safe_print("🚀 PLCエージェントを起動しました")

def stop_plc_agent():
    """PLCエージェントを停止"""
    global plc_agent_thread, plc_agent_stop_event
    
    if plc_agent_thread and plc_agent_thread.is_alive():
        # 停止イベントを設定
        plc_agent_stop_event.set()
        
        # スレッドの終了を最大5秒待機
        plc_agent_thread.join(timeout=5)
        
        if plc_agent_thread.is_alive():
            safe_print("⚠️ PLCエージェントの停止に時間がかかっています")
        else:
            safe_print("🛑 PLCエージェントを停止しました")
    
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
                safe_print("⚠️ 設備IDが未設定です。10秒後に再試行します。")
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
                    safe_print(f"✅ DB送信成功: {equipment_id} / {values}")
                else:
                    safe_print(f"❌ DB送信エラー: {equipment_id}")
            else:
                safe_print("⚠️ データ取得失敗。")

            # 設定された間隔で待機（停止イベントも監視）
            interval = config.get("interval", 5000)
            plc_agent_stop_event.wait(interval / 1000.0)
            
    except Exception as e:
        safe_print(f"[ERROR] PLCエージェントエラー: {e}")

def cleanup_on_exit():
    """アプリケーション終了時のクリーンアップ"""
    safe_print("[INFO] アプリケーション終了処理...")
    stop_plc_agent()

# 終了時のクリーンアップを登録
atexit.register(cleanup_on_exit)

if __name__ == "__main__":
    safe_print("[INFO] PLC UI システム起動中...")

    # ログローテーション実行（起動時に自動チェック）
    try:
        from log_rotator import rotate_all_logs
        current_dir = os.path.dirname(os.path.abspath(__file__))
        rotate_all_logs(log_dir=current_dir, keep_days=7)
    except Exception as e:
        safe_print(f"[WARNING] ログローテーションスキップ: {e}")

    # PLCエージェントを自動起動
    start_plc_agent()

    # Flaskアプリケーション起動（SocketIO対応）
    port = int(config.raspi_ui_port)
    safe_print(f"[INFO] WebUI起動: http://0.0.0.0:{port}")
    safe_print("[INFO] WebSocket機能が有効化されました")
    socketio.run(app, debug=True, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True) 