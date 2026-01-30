"""
設備登録スクリプト

Raspberry Piエージェントを中央サーバーに登録します。

Phase 4リファクタリング: db_utils.pyから共通関数をインポートして重複を排除
Phase 14: print() → logger統一
"""
import requests
import socket
import os
import logging
from dotenv import load_dotenv

# db_utils.pyから共通関数をインポート（重複排除）
from db_utils import get_cpu_serial_number, get_mac_address
from config.constants import DEFAULT_MODBUS_PORT

# Phase 14: ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env読み込み
load_dotenv()

# .envから取得（デフォルト値を設定）
FLASK_SERVER = os.getenv("FLASK_SERVER", "http://localhost:5000")
logger.debug(f"FLASK_SERVER: {FLASK_SERVER}")


def get_ip():
    """ホスト名からIPアドレスを取得"""
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

# 設備IDを自動生成（MACアドレスベース）
mac_address = get_mac_address()
cpu_serial = get_cpu_serial_number()
equipment_id = f"EP_{mac_address.replace(':', '').upper()[:8]}"

data = {
    "equipment_id": equipment_id,  # 設備IDを追加
    "ip": get_ip(),
    "mac_address": mac_address,
    "cpu_serial_number": cpu_serial,  # CPUシリアル番号を追加
    "hostname": socket.gethostname(),
    "manufacturer": "",  # 空文字で初期化
    "series": "",        # 空文字で初期化
    "port": DEFAULT_MODBUS_PORT,  # デフォルトポート
    "interval": 60       # デフォルト間隔（秒）
}

logger.info(f"送信データ: {data}")
logger.info(f"CPUシリアル番号: {cpu_serial}")

try:
    r = requests.post(f"{FLASK_SERVER}/api/register", json=data, timeout=5)
    r.raise_for_status()
    logger.info(f"登録レスポンス: {r.json()}")
except requests.RequestException as e:
    logger.error(f"登録失敗: {e}")
    logger.info("中央サーバーが起動しているか確認してください")
