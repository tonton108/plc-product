import os
import time
import random
import json
from datetime import datetime
import requests
from dotenv import load_dotenv
from db_utils import ConfigManager, DatabaseAPI, get_cpu_serial_number, get_mac_address, get_ip_address
import logging

load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('plc_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 環境変数設定
INTERVAL = int(os.getenv("LOG_INTERVAL_MS", 5000))  # ms間隔
PLC_IP = os.getenv("PLC_IP", "192.168.0.10")
PLC_PORT = int(os.getenv("PLC_PORT", "5000"))
PLC_MANUFACTURER = os.getenv("PLC_MANUFACTURER", "Mitsubishi")
USE_DUMMY_PLC = os.getenv("USE_DUMMY_PLC", "false").lower() == "true"

# エラー処理設定
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "5"))
READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "3"))

# セキュリティ設定（CLAUDE.md参照）
# IPホワイトリスト: 許可するPLC IPアドレスのリスト
ALLOWED_PLC_IPS = os.getenv("ALLOWED_PLC_IPS", "").split(",") if os.getenv("ALLOWED_PLC_IPS") else []
# 読み取り専用モード: Trueの場合、PLCへの書き込みを禁止
READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "true").lower() == "true"
logger.info(f"🔒 セキュリティ設定: 読み取り専用モード={'有効' if READ_ONLY_MODE else '無効'}")
if ALLOWED_PLC_IPS:
    logger.info(f"🔒 許可されたPLC IPアドレス: {ALLOWED_PLC_IPS}")

# DB対応の設定管理クラス
config_manager = ConfigManager()
db_api = DatabaseAPI()

# グローバルパフォーマンス統計（CLAUDE.md参照）
# 目標指標: 通信成功率95%以上、平均応答時間100ms以下、エラー率5%以下
error_stats = {
    "connection_errors": 0,
    "read_errors": 0,
    "last_success": None,
    "consecutive_failures": 0,
    # パフォーマンス監視用の追加指標
    "total_attempts": 0,        # 総通信試行回数
    "successful_attempts": 0,   # 成功回数
    "total_response_time": 0.0, # 累積応答時間（ms）
    "max_response_time": 0.0,   # 最大応答時間（ms）
    "min_response_time": float('inf'),  # 最小応答時間（ms）
    "start_time": datetime.now()  # 統計開始時刻
}

def print_error_stats():
    """
    パフォーマンス統計を表示（CLAUDE.md参照）
    目標指標: 通信成功率95%以上、平均応答時間100ms以下、エラー率5%以下
    """
    global error_stats

    # 基本統計
    print("\n" + "="*60)
    print("📊 PLCエージェント パフォーマンス統計")
    print("="*60)

    # エラー統計
    print("\n【エラー統計】")
    print(f"  接続エラー: {error_stats['connection_errors']}回")
    print(f"  読み取りエラー: {error_stats['read_errors']}回")
    print(f"  連続失敗: {error_stats['consecutive_failures']}回")

    # 通信成功率
    total = error_stats['total_attempts']
    success = error_stats['successful_attempts']
    if total > 0:
        success_rate = (success / total) * 100
        error_rate = 100 - success_rate
        print(f"\n【通信統計】")
        print(f"  総試行回数: {total}回")
        print(f"  成功回数: {success}回")
        print(f"  失敗回数: {total - success}回")
        print(f"  通信成功率: {success_rate:.2f}% {'✅' if success_rate >= 95 else '⚠️'}")
        print(f"  エラー率: {error_rate:.2f}% {'✅' if error_rate <= 5 else '⚠️'}")

    # 応答時間統計
    if success > 0:
        avg_response = error_stats['total_response_time'] / success
        print(f"\n【応答時間統計】")
        print(f"  平均応答時間: {avg_response:.2f}ms {'✅' if avg_response <= 100 else '⚠️'}")
        print(f"  最大応答時間: {error_stats['max_response_time']:.2f}ms")
        if error_stats['min_response_time'] != float('inf'):
            print(f"  最小応答時間: {error_stats['min_response_time']:.2f}ms")

    # 稼働時間
    uptime = datetime.now() - error_stats['start_time']
    print(f"\n【稼働時間】")
    print(f"  開始時刻: {error_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  稼働時間: {uptime}")

    if error_stats['last_success']:
        print(f"  最終成功: {error_stats['last_success'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"  最終成功: なし")

    print("="*60 + "\n")

def reload_env_vars():
    """環境変数を強制的に再読み込み"""
    global USE_DUMMY_PLC, PLC_IP, PLC_PORT, PLC_MANUFACTURER, LOG_INTERVAL_MS
    
    # .envファイルを再読み込み
    load_dotenv(override=True)
    
    # 環境変数を再取得
    USE_DUMMY_PLC = os.getenv("USE_DUMMY_PLC", "false").lower() == "true"
    PLC_IP = os.getenv("PLC_IP", "192.168.1.100")
    PLC_PORT = int(os.getenv("PLC_PORT", "5000"))
    PLC_MANUFACTURER = os.getenv("PLC_MANUFACTURER", "Mitsubishi")
    LOG_INTERVAL_MS = int(os.getenv("LOG_INTERVAL_MS", "5000"))
    
    print(f"🔄 環境変数再読み込み完了:")
    print(f"   USE_DUMMY_PLC = {USE_DUMMY_PLC}")
    print(f"   PLC_IP = {PLC_IP}")
    print(f"   PLC_PORT = {PLC_PORT}")
    print(f"   PLC_MANUFACTURER = {PLC_MANUFACTURER}")
    print(f"   LOG_INTERVAL_MS = {LOG_INTERVAL_MS}")

def load_plc_config():
    """PLC設定をDB優先で読み込み（JSONフォールバック）"""
    return config_manager.load_plc_config()

def update_error_stats(success=True, error_type=None, response_time_ms=None):
    """
    パフォーマンス統計を更新（CLAUDE.md参照）

    Args:
        success: 通信が成功した場合True
        error_type: エラータイプ（"connection" or "read"）
        response_time_ms: 応答時間（ミリ秒）
    """
    global error_stats

    # 総試行回数をカウント
    error_stats["total_attempts"] += 1

    if success:
        error_stats["last_success"] = datetime.now()
        error_stats["consecutive_failures"] = 0
        error_stats["successful_attempts"] += 1

        # 応答時間を記録
        if response_time_ms is not None:
            error_stats["total_response_time"] += response_time_ms
            error_stats["max_response_time"] = max(error_stats["max_response_time"], response_time_ms)
            error_stats["min_response_time"] = min(error_stats["min_response_time"], response_time_ms)

            if response_time_ms > 100:
                logger.warning(f"⚠️ 応答時間が遅い: {response_time_ms:.2f}ms (目標: 100ms以下)")
            else:
                logger.info(f"✅ PLC通信成功 (応答時間: {response_time_ms:.2f}ms)")
        else:
            logger.info("✅ PLC通信成功")
    else:
        error_stats["consecutive_failures"] += 1
        if error_type == "connection":
            error_stats["connection_errors"] += 1
        elif error_type == "read":
            error_stats["read_errors"] += 1

        logger.warning(f"❌ PLC通信失敗 (連続失敗: {error_stats['consecutive_failures']}回)")

    # 定期的に統計を表示（100回ごと）
    if error_stats["total_attempts"] % 100 == 0:
        print_error_stats()

def validate_plc_ip(ip_address):
    """
    PLCのIPアドレスをホワイトリストで検証（CLAUDE.md参照）

    Args:
        ip_address: 検証対象のIPアドレス

    Returns:
        bool: ホワイトリストに含まれている場合True、それ以外False
    """
    # ホワイトリストが空の場合はすべて許可
    if not ALLOWED_PLC_IPS or len(ALLOWED_PLC_IPS) == 0:
        return True

    # IPアドレスがホワイトリストに含まれているか確認
    if ip_address in ALLOWED_PLC_IPS:
        logger.info(f"✅ IPアドレス検証成功: {ip_address}")
        return True
    else:
        logger.error(f"🚫 不正なPLC IPアドレス: {ip_address} (ホワイトリスト: {ALLOWED_PLC_IPS})")
        return False

def check_write_permission():
    """
    PLC書き込み権限をチェック（CLAUDE.md参照）

    Returns:
        bool: 書き込み可能な場合True、それ以外False
    """
    if READ_ONLY_MODE:
        logger.warning("🔒 書き込み保護モードが有効です。PLCへの書き込みは禁止されています。")
        return False
    return True

def retry_on_failure(func, max_retries=MAX_RETRY_ATTEMPTS, delay=1):
    """リトライ機構付きの関数実行"""
    for attempt in range(max_retries):
        try:
            result = func()
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"試行 {attempt + 1}/{max_retries} 失敗: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))  # 指数バックオフ
            else:
                logger.error(f"最大リトライ回数に達しました: {e}")
                raise
    return None

def connect_mitsubishi_plc(ip, port, timeout=CONNECTION_TIMEOUT):
    """
    三菱PLC接続（タイムアウト付き）
    CLAUDE.md参照: MC Protocol (SLMP), ポート5000/5007, Big-Endian
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    from pymcprotocol import Type3E

    def _connect():
        plc = Type3E()
        plc.setaccessopt(commtype="binary")  # バイナリモード（高速）
        plc.connect(ip, port)
        logger.info(f"✅ 三菱PLC接続成功: {ip}:{port}")
        return plc

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"三菱PLC接続失敗: {ip}:{port} - {e}")
        return None

def connect_omron_plc(ip, timeout=CONNECTION_TIMEOUT):
    """
    オムロンPLC接続（タイムアウト付き）
    CLAUDE.md参照: FINS Protocol, ポート9600, Big-Endian
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    import fins.udp

    def _connect():
        fins_client = fins.udp.UDPFinsConnection()
        fins_client.connect(ip)
        fins_client.dest_node_add = 1
        fins_client.srce_node_add = 25
        logger.info(f"✅ オムロンPLC接続成功: {ip}")
        return fins_client

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"オムロンPLC接続失敗: {ip} - {e}")
        return None

def connect_siemens_plc(ip, rack=0, slot=1, timeout=CONNECTION_TIMEOUT):
    """
    シーメンスPLC接続（タイムアウト付き）
    CLAUDE.md参照: S7 Protocol, ポート102, Big-Endian
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    try:
        import snap7
    except ImportError:
        logger.error("snap7ライブラリがインストールされていません: pip install python-snap7")
        return None

    def _connect():
        plc = snap7.client.Client()
        plc.set_connection_type(3)  # OP接続
        plc.connect(ip, rack, slot)
        logger.info(f"✅ シーメンスPLC接続成功: {ip} (Rack:{rack}, Slot:{slot})")
        return plc

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"シーメンスPLC接続失敗: {ip} - {e}")
        return None

def connect_keyence_plc(ip, port=502, timeout=CONNECTION_TIMEOUT):
    """
    キーエンスPLC接続（Modbus/TCP）
    CLAUDE.md参照: Modbus TCP, ポート502, Big-Endian
    """
    # セキュリティチェック: IPホワイトリスト
    if not validate_plc_ip(ip):
        logger.error(f"🚫 IPアドレス検証失敗: {ip}")
        return None

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        logger.error("pymodbusライブラリがインストールされていません: pip install pymodbus")
        return None

    def _connect():
        client = ModbusTcpClient(ip, port=port, timeout=timeout)
        if client.connect():
            logger.info(f"✅ キーエンスPLC接続成功: {ip}:{port}")
            return client
        else:
            raise Exception("Modbus接続に失敗しました")

    try:
        return retry_on_failure(_connect, max_retries=3, delay=1)
    except Exception as e:
        update_error_stats(False, "connection")
        logger.error(f"キーエンスPLC接続失敗: {ip}:{port} - {e}")
        return None

def keyence_address_to_modbus(address, data_type="word"):
    """キーエンスアドレスをModbusアドレスに変換"""
    address_upper = address.upper()
    
    if address_upper.startswith('DM'):
        # データメモリ → Holding Registers
        addr_num = int(address[2:])
        if data_type == "bit":
            raise ValueError("DMアドレスではビット指定はできません")
        return ("holding", addr_num)
        
    elif address_upper.startswith('R'):
        # リレー → Coils
        if '.' in address:
            # ビット指定 (例: R100.1)
            base_addr, bit_pos = address.split('.')
            addr_num = int(base_addr[1:])
            bit_pos = int(bit_pos)
            # キーエンスでは1リレー = 16ビット
            modbus_addr = addr_num * 16 + bit_pos
        else:
            addr_num = int(address[1:])
            if data_type == "bit":
                modbus_addr = addr_num * 16  # R100 = ビット1600
            else:
                modbus_addr = addr_num
        return ("coil", modbus_addr)
        
    elif address_upper.startswith('MR'):
        # 内部リレー → Coils (オフセット付き)
        if '.' in address:
            base_addr, bit_pos = address.split('.')
            addr_num = int(base_addr[2:])
            bit_pos = int(bit_pos)
            modbus_addr = 10000 + addr_num * 16 + bit_pos  # オフセット
        else:
            addr_num = int(address[2:])
            if data_type == "bit":
                modbus_addr = 10000 + addr_num * 16
            else:
                modbus_addr = 10000 + addr_num
        return ("coil", modbus_addr)
        
    else:
        raise ValueError(f"不明なキーエンスアドレス形式: {address}")

def read_keyence_modbus(client, address, data_type="word", scale=1):
    """キーエンスPLCからModbus経由でデータ読み取り"""
    try:
        from pymodbus.exceptions import ModbusException
        register_type, modbus_addr = keyence_address_to_modbus(address, data_type)
        
        if data_type == "bit":
            # ビット読み取り
            if register_type == "coil":
                result = client.read_coils(modbus_addr, 1)
                if not result.isError():
                    return 1 if result.bits[0] else 0
                else:
                    raise Exception(f"Coil読み取りエラー: {result}")
            else:
                raise ValueError("ビット読み取りはCoilのみ対応")
                
        elif data_type == "float32":
            # 32bit浮動小数点 (2レジスタ)
            if register_type == "holding":
                result = client.read_holding_registers(modbus_addr, 2)
                if not result.isError():
                    # IEEE754変換 (ビッグエンディアン)
                    import struct
                    word1, word2 = result.registers[0], result.registers[1]
                    combined = (word1 << 16) | word2
                    return struct.unpack('>f', struct.pack('>I', combined))[0]
                else:
                    raise Exception(f"Holding Register読み取りエラー: {result}")
            else:
                raise ValueError("float32はHolding Registerのみ対応")
                
        elif data_type == "dword":
            # 32bit整数 (2レジスタ)
            if register_type == "holding":
                result = client.read_holding_registers(modbus_addr, 2)
                if not result.isError():
                    word1, word2 = result.registers[0], result.registers[1]
                    return (word1 << 16) | word2
                else:
                    raise Exception(f"Holding Register読み取りエラー: {result}")
            else:
                raise ValueError("dwordはHolding Registerのみ対応")
                
        else:
            # 16bit word
            if register_type == "holding":
                result = client.read_holding_registers(modbus_addr, 1)
                if not result.isError():
                    return result.registers[0]
                else:
                    raise Exception(f"Holding Register読み取りエラー: {result}")
            elif register_type == "coil":
                result = client.read_coils(modbus_addr, 16)  # 16ビット分
                if not result.isError():
                    # 16ビットを整数に変換
                    value = 0
                    for i in range(16):
                        if i < len(result.bits) and result.bits[i]:
                            value |= (1 << i)
                    return value
                else:
                    raise Exception(f"Coil読み取りエラー: {result}")
                    
    except (ModbusException, Exception) as e:
        logger.error(f"キーエンスModbus読み取りエラー({address}): {e}")
        return None

def safe_plc_read(plc_func, error_msg="PLC読み取りエラー"):
    """安全なPLC読み取り（タイムアウト・エラー処理付き）"""
    try:
        result = plc_func()
        return result
    except Exception as e:
        update_error_stats(False, "read")
        logger.error(f"{error_msg}: {e}")
        return None

# === PLCから値を取得する関数 ===
def read_from_plc(config):
    """
    設定ファイルに基づいて動的にPLCからデータを読み取り
    CLAUDE.md参照: 応答時間を測定し、パフォーマンス統計を更新
    """
    global USE_DUMMY_PLC
    import time
    start_time = time.time()  # 応答時間測定開始

    ip = config.get("plc_ip", PLC_IP)
    port = config.get("plc_port", PLC_PORT)
    manufacturer = config.get("manufacturer", PLC_MANUFACTURER)
    data_points = config.get("data_points", {})

    # デバッグ情報出力
    logger.debug(f"🔧 DEBUG: USE_DUMMY_PLC = {USE_DUMMY_PLC}")
    logger.debug(f"🔧 DEBUG: PLC_IP = {ip}, PLC_PORT = {port}")
    logger.debug(f"🔧 DEBUG: Manufacturer = {manufacturer}")

    # 環境変数によるダミーモード設定
    if USE_DUMMY_PLC:
        logger.info("⚠️ [DUMMY MODE] ダミーデータを返します。")
        return generate_dummy_data(data_points)

    # 実際のPLC接続を試行
    logger.info(f"🔌 実際のPLC接続を試行中: {ip}:{port} ({manufacturer})")
    try:
        result = read_from_real_plc(config, ip, port, manufacturer, data_points)
        response_time_ms = (time.time() - start_time) * 1000  # ミリ秒に変換

        if result is None:
            logger.error("❌ PLC接続失敗 - ダミーモードにフォールバック")
            update_error_stats(False, "connection", response_time_ms)
            return generate_dummy_data(data_points)
        else:
            logger.info("✅ PLC接続成功")
            update_error_stats(True, response_time_ms=response_time_ms)
            return result
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(f"❌ PLC接続例外: {e}")
        logger.info("🔄 自動的にダミーモードに切り替えます。")
        update_error_stats(False, "connection", response_time_ms)
        return generate_dummy_data(data_points)

def extract_address_number(address):
    """
    アドレス文字列から数値部分を抽出

    Args:
        address: アドレス文字列（例: "D100", "DM200", "D100.5"）

    Returns:
        int: アドレス番号（例: 100, 200, 100）
    """
    import re
    # ビット指定がある場合は除外（D100.5 → D100）
    address_base = address.split('.')[0]
    # 数字部分を抽出
    match = re.search(r'\d+', address_base)
    if match:
        return int(match.group())
    return None

def group_continuous_word_addresses(data_points, device_type='D'):
    """
    連続したワードアドレスをグループ化（バッチ読み取り最適化用）
    CLAUDE.md参照: パフォーマンス最適化 - バッチ読み取りの活用

    Args:
        data_points: データ項目の辞書
        device_type: デバイスタイプ（'D', 'DM'等）

    Returns:
        list: グループ化されたアドレスリスト
        [
            {
                'keys': ['temp1', 'temp2', 'temp3'],  # データキー
                'start_address': 100,  # 開始アドレス
                'count': 3,  # ワード数
                'settings': [{...}, {...}, {...}]  # 各項目の設定
            },
            ...
        ]
    """
    # wordデータ型のみをフィルタ（dword, float32は除外）
    word_items = []
    for key, setting in data_points.items():
        if not setting.get("enabled", False):
            continue

        data_type = setting.get("data_type", "word")
        address = setting.get("address", "")

        # ビット指定やdword/float32は個別処理
        if data_type != "word" or '.' in address:
            continue

        # 指定デバイスタイプのみ
        if not address.upper().startswith(device_type):
            continue

        addr_num = extract_address_number(address)
        if addr_num is not None:
            word_items.append({
                'key': key,
                'setting': setting,
                'address_num': addr_num,
                'address': address
            })

    # アドレス番号でソート
    word_items.sort(key=lambda x: x['address_num'])

    # 連続アドレスをグループ化
    groups = []
    current_group = None

    for item in word_items:
        if current_group is None:
            # 新しいグループ開始
            current_group = {
                'keys': [item['key']],
                'start_address': item['address_num'],
                'count': 1,
                'settings': [item['setting']],
                'addresses': [item['address']]
            }
        elif item['address_num'] == current_group['start_address'] + current_group['count']:
            # 連続している → グループに追加
            current_group['keys'].append(item['key'])
            current_group['count'] += 1
            current_group['settings'].append(item['setting'])
            current_group['addresses'].append(item['address'])
        else:
            # 連続していない → グループ確定して新しいグループ開始
            groups.append(current_group)
            current_group = {
                'keys': [item['key']],
                'start_address': item['address_num'],
                'count': 1,
                'settings': [item['setting']],
                'addresses': [item['address']]
            }

    # 最後のグループを追加
    if current_group:
        groups.append(current_group)

    return groups

def generate_dummy_data(data_points):
    """ダミーデータを生成"""
    dummy_data = {}
    
    # 有効な各データ項目に対してダミーデータを生成
    for key, setting in data_points.items():
        if setting.get("enabled", False):
            data_type = setting.get("data_type", "word")  # デフォルト: word
            
            if key == "production_count":
                dummy_data[key] = random.randint(1000, 9999)
            elif key == "current":
                dummy_data[key] = round(random.uniform(2.0, 5.0), 1)
            elif key == "temperature":
                dummy_data[key] = round(random.uniform(20.0, 40.0), 1)
            elif key == "pressure":
                dummy_data[key] = round(random.uniform(0.1, 0.8), 2)
            elif key == "cycle_time":
                dummy_data[key] = random.randint(800, 1200)
            elif key == "error_code":
                dummy_data[key] = random.choice([0, 0, 0, 1, 2])  # 大部分は正常(0)
            elif data_type == "bit":
                dummy_data[key] = random.choice([0, 1])  # ビット値
            elif data_type == "float32":
                dummy_data[key] = round(random.uniform(0.0, 1000.0), 3)  # 高精度浮動小数点
            elif data_type == "dword":
                dummy_data[key] = random.randint(0, 4294967295)  # 32bit整数
            else:
                dummy_data[key] = round(random.uniform(0.0, 100.0), 1)
                
    return dummy_data

def read_from_real_plc(config, ip, port, manufacturer, data_points):
    """実際のPLCからデータを読み取り"""
    try:
        if manufacturer.lower() in ["mitsubishi", "三菱"]:
            import struct

            # 新しい接続関数を使用
            plc = connect_mitsubishi_plc(ip, port)
            if not plc:
                logger.error("三菱PLC接続に失敗しました")
                return None

            data = {}

            # バッチ読み取り最適化: 連続したwordアドレスをグループ化
            word_groups = group_continuous_word_addresses(data_points, device_type='D')

            # グループ化されたwordアドレスを一括読み取り
            for group in word_groups:
                try:
                    if group['count'] == 1:
                        # 単独アドレス → 個別読み取り
                        logger.debug(f"📖 単独読み取り: D{group['start_address']}")
                        raw_values = plc.batchread_wordunits(
                            headdevice=f"D{group['start_address']}",
                            readsize=1
                        )
                    else:
                        # 連続アドレス → バッチ読み取り（最適化）
                        logger.info(f"🚀 バッチ読み取り: D{group['start_address']}-D{group['start_address'] + group['count'] - 1} ({group['count']}ワード)")
                        raw_values = plc.batchread_wordunits(
                            headdevice=f"D{group['start_address']}",
                            readsize=group['count']
                        )

                    # 読み取った値を各項目に割り当て
                    for i, key in enumerate(group['keys']):
                        setting = group['settings'][i]
                        scale = setting.get("scale", 1)
                        raw_value = raw_values[i]

                        # スケール適用
                        if scale > 1:
                            data[key] = raw_value / scale
                        else:
                            data[key] = raw_value

                        logger.debug(f"  ✅ {key} = {data[key]} (raw: {raw_value}, scale: {scale})")

                except Exception as e:
                    logger.error(f"❌ バッチ読み取りエラー (D{group['start_address']}): {e}")
                    # エラー時は個別に再試行
                    for i, key in enumerate(group['keys']):
                        setting = group['settings'][i]
                        addr_num = group['start_address'] + i
                        try:
                            raw_value = plc.batchread_wordunits(f"D{addr_num}", 1)[0]
                            scale = setting.get("scale", 1)
                            data[key] = raw_value / scale if scale > 1 else raw_value
                        except:
                            logger.warning(f"⚠️ {key}(D{addr_num})の個別再試行も失敗")

            # bit, dword, float32は個別処理（従来通り）
            # ※既にバッチ読み取りで取得したwordデータはスキップ
            for key, setting in data_points.items():
                if setting.get("enabled", False):
                    address = setting.get("address")
                    scale = setting.get("scale", 1)
                    data_type = setting.get("data_type", "word")  # デフォルト: word

                    # バッチ読み取り済みのデータはスキップ
                    if key in data:
                        continue

                    if address:
                        def read_mitsubishi_data():
                            """三菱PLCデータ読み取り関数（safe_plc_read用）"""
                            raw_value = None
                            
                            # データ型別の処理
                            if data_type == "bit":
                                # ビットアドレス処理 (M100.1, X001等)
                                if '.' in address:
                                    # ビット指定あり (例: M100.1)
                                    base_addr, bit_pos = address.split('.')
                                    bit_pos = int(bit_pos)
                                    device_type = base_addr[0]
                                    addr_num = int(base_addr[1:])
                                    
                                    # ビット読み取り
                                    bit_values = plc.batchread_bitunits(
                                        headdevice=f"{device_type}{addr_num:04X}",
                                        readsize=1
                                    )
                                    raw_value = bit_values[0] if bit_values else 0
                                else:
                                    # 単体ビットアドレス (例: M100, X001)
                                    device_type = address[0]
                                    addr_num = int(address[1:])
                                    
                                    bit_values = plc.batchread_bitunits(
                                        headdevice=f"{device_type}{addr_num:04X}",
                                        readsize=1
                                    )
                                    raw_value = bit_values[0] if bit_values else 0
                                    
                            elif data_type == "float32":
                                # 32bit浮動小数点 (2ワード)
                                # CLAUDE.md参照: 三菱PLCはBig-Endianで通信
                                if address.upper().startswith('D'):
                                    addr_num = int(address[1:])
                                elif address.upper().startswith('DM'):
                                    addr_num = int(address[2:])
                                else:
                                    raise ValueError(f"不明なアドレス形式: {address}")

                                # 2ワード読み取り (32bit)
                                word_values = plc.batchread_wordunits(
                                    headdevice=f"D{addr_num}",
                                    readsize=2
                                )

                                # IEEE754 float32に変換（Big-Endian）
                                if len(word_values) >= 2:
                                    # Big-Endian形式で結合（三菱PLCは全てBig-Endian）
                                    word1, word2 = word_values[0], word_values[1]
                                    combined = (word1 << 16) | word2
                                    raw_value = struct.unpack('>f', struct.pack('>I', combined))[0]
                                    
                            elif data_type == "dword":
                                # 32bit整数 (2ワード)
                                # CLAUDE.md参照: 三菱PLCはBig-Endianで通信
                                if address.upper().startswith('D'):
                                    addr_num = int(address[1:])
                                elif address.upper().startswith('DM'):
                                    addr_num = int(address[2:])
                                else:
                                    raise ValueError(f"不明なアドレス形式: {address}")

                                # 2ワード読み取り
                                word_values = plc.batchread_wordunits(
                                    headdevice=f"D{addr_num}",
                                    readsize=2
                                )

                                if len(word_values) >= 2:
                                    # 32bit整数に結合（Big-Endian）
                                    word1, word2 = word_values[0], word_values[1]
                                    raw_value = (word1 << 16) | word2
                                    
                            else:
                                # 従来の16bitワード読み取り
                                if address.upper().startswith('D'):
                                    addr_num = int(address[1:])
                                elif address.upper().startswith('DM'):
                                    addr_num = int(address[2:])
                                else:
                                    raise ValueError(f"不明なアドレス形式: {address}")
                                
                            # PLCからデータを読み取り
                            raw_value = plc.batchread_wordunits(
                                headdevice=f"D{addr_num}", 
                                readsize=1
                            )[0]  # リストの最初の要素を取得
                            
                            return raw_value
                        
                        # 安全な読み取り実行
                        raw_value = safe_plc_read(read_mitsubishi_data, f"{key}({address})読み取り")
                        
                        # スケール適用 (ビット以外)
                        if raw_value is not None:
                            if data_type == "bit":
                                data[key] = int(raw_value)  # ビットは0/1
                            elif scale > 1:
                                data[key] = raw_value / scale
                            else:
                                data[key] = raw_value
                        else:
                            logger.warning(f"⚠️ {key}({address})のデータ取得に失敗")
                            
            plc.close()
            
            if data:
                update_error_stats(True)
                logger.info(f"✅ 三菱PLC データ取得成功: {len(data)}項目")
            
            return data

        elif manufacturer.lower() in ["keyence", "キーエンス"]:
            # キーエンスPLC（Modbus/TCP対応）
            modbus_port = config.get("modbus_port", 502)  # Modbusポート

            # Modbus/TCP接続
            client = connect_keyence_plc(ip, port=modbus_port)
            if not client:
                logger.error("キーエンスPLC（Modbus/TCP）接続に失敗しました")
                return None

            data = {}

            # バッチ読み取り最適化: 連続したwordアドレスをグループ化（DMアドレスのみ）
            word_groups = group_continuous_word_addresses(data_points, device_type='DM')

            # グループ化されたwordアドレスを一括読み取り
            for group in word_groups:
                try:
                    start_addr = group['start_address']
                    count = group['count']

                    if count == 1:
                        # 単独アドレス → 個別読み取り
                        logger.debug(f"📖 単独読み取り: DM{start_addr}")
                        result = client.read_holding_registers(address=start_addr, count=1, unit=1)
                    else:
                        # 連続アドレス → バッチ読み取り（最適化）
                        logger.info(f"🚀 バッチ読み取り: DM{start_addr}-DM{start_addr + count - 1} ({count}ワード)")
                        result = client.read_holding_registers(address=start_addr, count=count, unit=1)

                    # 読み取った値を各項目に割り当て
                    if not result.isError():
                        for i, key in enumerate(group['keys']):
                            setting = group['settings'][i]
                            scale = setting.get("scale", 1)
                            raw_value = result.registers[i]

                            # スケール適用
                            if scale > 1:
                                data[key] = raw_value / scale
                            else:
                                data[key] = raw_value

                            logger.debug(f"  ✅ {key} = {data[key]} (raw: {raw_value}, scale: {scale})")
                    else:
                        raise Exception(f"Modbus読み取りエラー: {result}")

                except Exception as e:
                    logger.error(f"❌ バッチ読み取りエラー (DM{group['start_address']}): {e}")
                    # エラー時は個別に再試行
                    for i, key in enumerate(group['keys']):
                        setting = group['settings'][i]
                        addr_num = group['start_address'] + i
                        try:
                            result = client.read_holding_registers(address=addr_num, count=1, unit=1)
                            if not result.isError():
                                raw_value = result.registers[0]
                                scale = setting.get("scale", 1)
                                data[key] = raw_value / scale if scale > 1 else raw_value
                        except:
                            logger.warning(f"⚠️ {key}(DM{addr_num})の個別再試行も失敗")

            # bit, dword, float32、および非DMアドレスは個別処理（従来通り）
            # ※既にバッチ読み取りで取得したwordデータはスキップ
            for key, setting in data_points.items():
                if setting.get("enabled", False):
                    address = setting.get("address")
                    scale = setting.get("scale", 1)
                    data_type = setting.get("data_type", "word")

                    # バッチ読み取り済みのデータはスキップ
                    if key in data:
                        continue

                    if address:
                        def read_keyence_data():
                            """キーエンスPLCデータ読み取り関数（safe_plc_read用）"""
                            return read_keyence_modbus(client, address, data_type, scale)
                        
                        # 安全な読み取り実行
                        raw_value = safe_plc_read(read_keyence_data, f"{key}({address})読み取り")
                        
                        # スケール適用
                        if raw_value is not None:
                            if data_type == "bit":
                                data[key] = int(raw_value)  # ビットは0/1
                            elif scale > 1:
                                data[key] = raw_value / scale
                            else:
                                data[key] = raw_value
                        else:
                            logger.warning(f"⚠️ {key}({address})のデータ取得に失敗")
                            
            # Modbus接続を閉じる
            try:
                client.close()
            except:
                pass
            
            if data:
                update_error_stats(True)
                logger.info(f"✅ キーエンスPLC データ取得成功: {len(data)}項目")
            
            return data

        elif manufacturer.lower() in ["omron", "オムロン"]:
            import struct

            # 新しい接続関数を使用
            fins_client = connect_omron_plc(ip)
            if not fins_client:
                logger.error("オムロンPLC接続に失敗しました")
                return None

            data = {}

            # バッチ読み取り最適化: 連続したwordアドレスをグループ化
            word_groups = group_continuous_word_addresses(data_points, device_type='DM')

            # グループ化されたwordアドレスを一括読み取り
            for group in word_groups:
                try:
                    start_addr = group['start_address']
                    count = group['count']

                    if count == 1:
                        # 単独アドレス → 個別読み取り
                        logger.debug(f"📖 単独読み取り: DM{start_addr}")
                        addr_bytes = b'\x00' + start_addr.to_bytes(2, byteorder='big')
                        mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, 1)
                    else:
                        # 連続アドレス → バッチ読み取り（最適化）
                        logger.info(f"🚀 バッチ読み取り: DM{start_addr}-DM{start_addr + count - 1} ({count}ワード)")
                        addr_bytes = b'\x00' + start_addr.to_bytes(2, byteorder='big')
                        mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, count)

                    # 読み取った値を各項目に割り当て
                    if mem_area and len(mem_area) >= count * 2:
                        for i, key in enumerate(group['keys']):
                            setting = group['settings'][i]
                            scale = setting.get("scale", 1)
                            # 2バイトずつ読み取り（Big-Endian）
                            offset = i * 2
                            raw_value = int.from_bytes(mem_area[offset:offset+2], byteorder='big')

                            # スケール適用
                            if scale > 1:
                                data[key] = raw_value / scale
                            else:
                                data[key] = raw_value

                            logger.debug(f"  ✅ {key} = {data[key]} (raw: {raw_value}, scale: {scale})")

                except Exception as e:
                    logger.error(f"❌ バッチ読み取りエラー (DM{group['start_address']}): {e}")
                    # エラー時は個別に再試行
                    for i, key in enumerate(group['keys']):
                        setting = group['settings'][i]
                        addr_num = group['start_address'] + i
                        try:
                            addr_bytes = b'\x00' + addr_num.to_bytes(2, byteorder='big')
                            mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, 1)
                            if mem_area and len(mem_area) >= 2:
                                raw_value = int.from_bytes(mem_area[0:2], byteorder='big')
                                scale = setting.get("scale", 1)
                                data[key] = raw_value / scale if scale > 1 else raw_value
                        except:
                            logger.warning(f"⚠️ {key}(DM{addr_num})の個別再試行も失敗")

            # bit, dword, float32は個別処理（従来通り）
            # ※既にバッチ読み取りで取得したwordデータはスキップ
            for key, setting in data_points.items():
                if setting.get("enabled", False):
                    address = setting.get("address")
                    scale = setting.get("scale", 1)
                    data_type = setting.get("data_type", "word")  # デフォルト: word

                    # バッチ読み取り済みのデータはスキップ
                    if key in data:
                        continue

                    if address:
                        def read_omron_data():
                            """オムロンPLCデータ読み取り関数（safe_plc_read用）"""
                            raw_value = None
                            
                            # データ型別の処理
                            if data_type == "bit":
                                # ビットアドレス処理 (CIO100.01等)
                                if '.' in address:
                                    # ビット指定あり (例: CIO100.01)
                                    base_addr, bit_pos = address.split('.')
                                    bit_pos = int(bit_pos)
                                    
                                    if base_addr.upper().startswith('CIO'):
                                        addr_num = int(base_addr[3:])
                                        # CIOエリア (0x30)
                                        addr_bytes = addr_num.to_bytes(2, byteorder='big') + bit_pos.to_bytes(1, byteorder='big')
                                        mem_area = fins_client.memory_area_read(b'\x30', addr_bytes, 1)
                                        raw_value = mem_area[0] if mem_area else 0
                                    elif base_addr.upper().startswith('WR'):
                                        addr_num = int(base_addr[2:])
                                        # WRエリア (0x31)
                                        addr_bytes = addr_num.to_bytes(2, byteorder='big') + bit_pos.to_bytes(1, byteorder='big')
                                        mem_area = fins_client.memory_area_read(b'\x31', addr_bytes, 1)
                                        raw_value = mem_area[0] if mem_area else 0
                                else:
                                    raise ValueError(f"オムロンビットアドレスには.XX指定が必要: {address}")
                                    
                            elif data_type == "float32":
                                # 32bit浮動小数点 (2ワード)
                                if address.upper().startswith('DM'):
                                    addr_num = int(address[2:])
                                elif address.upper().startswith('D'):
                                    addr_num = int(address[1:])
                                else:
                                    raise ValueError(f"不明なアドレス形式: {address}")
                                
                                # 2ワード読み取り
                                addr_bytes = b'\x00' + addr_num.to_bytes(2, byteorder='big')
                                mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, 2)
                                
                                if mem_area and len(mem_area) >= 4:
                                    # IEEE754 float32に変換 (ビッグエンディアン)
                                    word1 = int.from_bytes(mem_area[0:2], byteorder='big')
                                    word2 = int.from_bytes(mem_area[2:4], byteorder='big')
                                    combined = (word1 << 16) | word2
                                    raw_value = struct.unpack('>f', struct.pack('>I', combined))[0]
                                    
                            elif data_type == "dword":
                                # 32bit整数 (2ワード)
                                if address.upper().startswith('DM'):
                                    addr_num = int(address[2:])
                                elif address.upper().startswith('D'):
                                    addr_num = int(address[1:])
                                else:
                                    raise ValueError(f"不明なアドレス形式: {address}")
                                
                                # 2ワード読み取り
                                addr_bytes = b'\x00' + addr_num.to_bytes(2, byteorder='big')
                                mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, 2)
                                
                                if mem_area and len(mem_area) >= 4:
                                    # 32bit整数に結合
                                    word1 = int.from_bytes(mem_area[0:2], byteorder='big')
                                    word2 = int.from_bytes(mem_area[2:4], byteorder='big')
                                    raw_value = (word1 << 16) | word2
                                    
                            else:
                                # 従来の16bitワード読み取り
                                if address.upper().startswith('DM') or address.upper().startswith('D'):
                                    # DM エリア用のメモリエリアコード（0x82）
                                    if address.upper().startswith('DM'):
                                        addr_num = int(address[2:])
                                    else:
                                        addr_num = int(address[1:])
                                    
                                # アドレスをバイト形式に変換
                                addr_bytes = b'\x00' + addr_num.to_bytes(2, byteorder='big')
                                
                                # PLCからデータを読み取り（DM エリア: 0x82）
                                mem_area = fins_client.memory_area_read(b'\x82', addr_bytes, 1)
                                
                                if mem_area and len(mem_area) >= 2:
                                    raw_value = int.from_bytes(mem_area[0:2], byteorder='big')
                                else:
                                    raise ValueError(f"不明なアドレス形式: {address}")
                            
                            return raw_value
                        
                        # 安全な読み取り実行
                        raw_value = safe_plc_read(read_omron_data, f"{key}({address})読み取り")
                        
                        # スケール適用 (ビット以外)
                        if raw_value is not None:
                            if data_type == "bit":
                                data[key] = int(raw_value)  # ビットは0/1
                            elif scale > 1:
                                data[key] = raw_value / scale
                            else:
                                data[key] = raw_value
                        else:
                            logger.warning(f"⚠️ {key}({address})のデータ取得に失敗")
                            
            # 接続は自動でクローズされるため明示的な切断処理は不要
            
            if data:
                update_error_stats(True)
                logger.info(f"✅ オムロンPLC データ取得成功: {len(data)}項目")
            
            return data

        elif manufacturer.lower() in ["siemens", "シーメンス"]:
            import struct
            
            # 新しい接続関数を使用
            plc = connect_siemens_plc(ip)
            if not plc:
                logger.error("シーメンスPLC接続に失敗しました")
                return None

            data = {}
            
            # 有効な各データ項目を設定に基づいて読み取り
            for key, setting in data_points.items():
                if setting.get("enabled", False):
                    address = setting.get("address")
                    scale = setting.get("scale", 1)
                    data_type = setting.get("data_type", "word")  # デフォルト: word
                    
                    if address:
                        def read_siemens_data():
                            """シーメンスPLCデータ読み取り関数（safe_plc_read用）"""
                            # シーメンスPLCは現在未実装（snap7 APIの複雑さのため）
                            logger.warning(f"シーメンスPLCの読み取りは現在未実装です: {address}")
                            return None
                        
                        # 安全な読み取り実行
                        raw_value = safe_plc_read(read_siemens_data, f"{key}({address})読み取り")
                        
                        # スケール適用 (ビット以外)
                        if raw_value is not None:
                            if data_type == "bit":
                                data[key] = int(raw_value)  # ビットは0/1
                            elif scale > 1:
                                data[key] = raw_value / scale
                            else:
                                data[key] = raw_value
                        else:
                            logger.warning(f"⚠️ {key}({address})のデータ取得に失敗")
                             
            plc.disconnect()
            
            if data:
                update_error_stats(True)
                logger.info(f"✅ シーメンスPLC データ取得成功: {len(data)}項目")
                            
            return data

        else:
            raise ValueError(f"❌ 不明なメーカー: {manufacturer}")

    except Exception as e:
        print(f"❌ PLC読取エラー: {e}")
        return None

def auto_identify_equipment():
    """CPUシリアル番号を使用した設備自動識別"""
    try:
        print("🔍 設備自動識別を実行中...")
        
        # デバイス情報を取得
        cpu_serial = get_cpu_serial_number()
        mac_address = get_mac_address()
        ip_address = get_ip_address()
        
        print(f"📊 デバイス情報:")
        print(f"   CPUシリアル番号: {cpu_serial}")
        print(f"   MACアドレス: {mac_address}")
        print(f"   IPアドレス: {ip_address}")
        
        # 設備検索（優先順位: CPU Serial > MAC > IP）
        equipment_config = db_api.get_equipment_by_device_info(
            cpu_serial_number=cpu_serial,
            mac_address=mac_address,
            ip_address=ip_address
        )
        
        if equipment_config:
            equipment_id = equipment_config.get("equipment_id")
            print(f"✅ 設備識別成功: {equipment_id}")
            
            # 設定に保存（設備IDを永続化）
            config_manager.save_equipment_id(equipment_id)
            print(f"📝 設備ID '{equipment_id}' を設定に保存しました")
            
            return equipment_id
        else:
            print("⚠️ 対応する設備が見つかりませんでした")
            if cpu_serial and cpu_serial == "FALLBACK_FIXED_ID":
                print("ℹ️ フォールバック固定IDが使用されています")
            print("💡 設備登録を行ってください: python register_equipment.py")
            return None
            
    except Exception as e:
        print(f"❌ 設備自動識別エラー: {e}")
        return None

# === メインループ ===
def main_loop():
    # 初回起動時に環境変数を再読み込み
    print("🚀 PLCエージェント起動 - 環境変数確認中...")
    reload_env_vars()
    
    while True:
        # 設定をDB優先で読み込み（設定変更に対応）
        config = load_plc_config()
        equipment_id = config.get("equipment_id")
        
        if not equipment_id:
            print("⚠️ 設備IDが未設定です。自動識別を試行します...")
            
            # CPUシリアル番号による自動識別を実行
            equipment_id = auto_identify_equipment()
            
            if not equipment_id:
                print("⚠️ 設備自動識別に失敗しました。10秒後に再試行します。")
                time.sleep(10)
                continue
            
            # 設定を再読み込み（識別結果を反映）
            config = load_plc_config()
        
        # 設定に基づいてPLCからデータを取得
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

        # 設定された間隔で待機
        interval = config.get("interval", INTERVAL)
        time.sleep(interval / 1000.0)

if __name__ == "__main__":
    main_loop()
