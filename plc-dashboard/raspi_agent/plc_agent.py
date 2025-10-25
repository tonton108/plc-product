import os
import time
import logging
from dotenv import load_dotenv
from db_utils import ConfigManager, DatabaseAPI, get_cpu_serial_number, get_mac_address, get_ip_address

# plc_driversモジュールからインポート
from plc_drivers import (
    update_error_stats,
    print_error_stats,
    generate_dummy_data,
    connect_mitsubishi_plc,
    read_mitsubishi_plc,
    connect_omron_plc,
    read_omron_plc,
    connect_keyence_plc,
    read_keyence_plc,
    connect_siemens_plc,
    read_siemens_plc
)

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

# DB対応の設定管理クラス
config_manager = ConfigManager()
db_api = DatabaseAPI()


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


def read_from_plc(config):
    """
    設定ファイルに基づいて動的にPLCからデータを読み取り
    CLAUDE.md参照: 応答時間を測定し、パフォーマンス統計を更新
    """
    global USE_DUMMY_PLC
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
        logger.info("[WARNING] [DUMMY MODE] ダミーデータを返します。")
        return generate_dummy_data(data_points)

    # 実際のPLC接続を試行
    logger.info(f"🔌 実際のPLC接続を試行中: {ip}:{port} ({manufacturer})")
    try:
        result = read_from_real_plc(config, ip, port, manufacturer, data_points)
        response_time_ms = (time.time() - start_time) * 1000  # ミリ秒に変換

        if result is None:
            logger.error("[ERROR] PLC接続失敗 - ダミーモードにフォールバック")
            update_error_stats(False, "connection", response_time_ms)
            return generate_dummy_data(data_points)
        else:
            logger.info("[SUCCESS] PLC接続成功")
            update_error_stats(True, response_time_ms=response_time_ms)
            return result
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(f"[ERROR] PLC接続例外: {e}")
        logger.info("🔄 自動的にダミーモードに切り替えます。")
        update_error_stats(False, "connection", response_time_ms)
        return generate_dummy_data(data_points)


def read_from_real_plc(config, ip, port, manufacturer, data_points):
    """
    実際のPLCからデータを読み取り（メーカー別ドライバー使用）

    Args:
        config: PLC設定
        ip: PLCのIPアドレス
        port: PLCのポート番号
        manufacturer: メーカー名
        data_points: データ項目の辞書

    Returns:
        dict: 読み取ったデータ、失敗時はNone
    """
    try:
        if manufacturer.lower() in ["mitsubishi", "三菱"]:
            plc = connect_mitsubishi_plc(ip, port)
            if not plc:
                logger.error("三菱PLC接続に失敗しました")
                return None
            data = read_mitsubishi_plc(plc, data_points)
            plc.close()
            return data

        elif manufacturer.lower() in ["omron", "オムロン"]:
            fins_client = connect_omron_plc(ip)
            if not fins_client:
                logger.error("オムロンPLC接続に失敗しました")
                return None
            return read_omron_plc(fins_client, data_points)

        elif manufacturer.lower() in ["keyence", "キーエンス"]:
            modbus_port = config.get("modbus_port", 502)
            client = connect_keyence_plc(ip, port=modbus_port)
            if not client:
                logger.error("キーエンスPLC接続に失敗しました")
                return None
            return read_keyence_plc(client, data_points, modbus_port)

        elif manufacturer.lower() in ["siemens", "シーメンス"]:
            plc = connect_siemens_plc(ip)
            if not plc:
                logger.error("シーメンスPLC接続に失敗しました")
                return None
            return read_siemens_plc(plc, data_points)

        else:
            raise ValueError(f"[ERROR] 不明なメーカー: {manufacturer}")

    except Exception as e:
        logger.error(f"[ERROR] PLC読取エラー: {e}")
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
            print(f"[SUCCESS] 設備識別成功: {equipment_id}")

            # 設定に保存（設備IDを永続化）
            config_manager.save_equipment_id(equipment_id)
            print(f"📝 設備ID '{equipment_id}' を設定に保存しました")

            return equipment_id
        else:
            print("[WARNING] 対応する設備が見つかりませんでした")
            if cpu_serial and cpu_serial == "FALLBACK_FIXED_ID":
                print("ℹ️ フォールバック固定IDが使用されています")
            print("💡 設備登録を行ってください: python register_equipment.py")
            return None

    except Exception as e:
        print(f"[ERROR] 設備自動識別エラー: {e}")
        return None


# === メインループ ===
def main_loop():
    # 初回起動時に環境変数を再読み込み
    print("🚀 PLCエージェント起動 - 環境変数確認中...")
    reload_env_vars()

    # バッファリング機能のカウンター
    retry_counter = 0  # 再送信のカウンター
    cleanup_counter = 0  # クリーンアップのカウンター
    retry_interval = 60  # 再送信間隔（秒）: 60秒ごと
    cleanup_interval = 3600  # クリーンアップ間隔（秒）: 1時間ごと

    print(f"📦 バッファリング機能有効:")
    print(f"  - 再送信間隔: {retry_interval}秒ごと")
    print(f"  - クリーンアップ間隔: {cleanup_interval}秒ごと（7日以上前のデータを削除）")

    while True:
        # 設定をDB優先で読み込み（設定変更に対応）
        config = load_plc_config()
        equipment_id = config.get("equipment_id")

        if not equipment_id:
            print("[WARNING] 設備IDが未設定です。自動識別を試行します...")

            # CPUシリアル番号による自動識別を実行
            equipment_id = auto_identify_equipment()

            if not equipment_id:
                print("[WARNING] 設備自動識別に失敗しました。10秒後に再試行します。")
                time.sleep(10)
                continue

            # 設定を再読み込み（識別結果を反映）
            config = load_plc_config()

        # 設定に基づいてPLCからデータを取得
        values = read_from_plc(config)

        if values:
            # DB APIを使用してログデータを送信（バッファリング対応）
            success = db_api.send_log_data(equipment_id, values)

            if success:
                print(f"[SUCCESS] DB送信成功: {equipment_id} / {values}")
            else:
                print(f"[WARNING] DB送信失敗（バッファに保存済み）: {equipment_id}")
        else:
            print("[WARNING] データ取得失敗。")

        # 設定された間隔で待機
        interval = config.get("interval", INTERVAL)
        time.sleep(interval / 1000.0)

        # カウンター更新
        retry_counter += interval / 1000.0
        cleanup_counter += interval / 1000.0

        # 定期的に未送信データを再送信
        if retry_counter >= retry_interval:
            try:
                success, failure, total = db_api.retry_pending_data(batch_size=100)
                if total > 0:
                    print(f"🔄 未送信データ再送完了: 成功={success}, 失敗={failure}")
            except Exception as e:
                print(f"[ERROR] 未送信データ再送エラー: {e}")
            finally:
                retry_counter = 0

        # 定期的に古いバッファデータをクリーンアップ
        if cleanup_counter >= cleanup_interval:
            try:
                deleted = db_api.cleanup_buffer(days=7)
                if deleted > 0:
                    print(f"🗑️ 古いバッファデータを削除: {deleted}件")
            except Exception as e:
                print(f"[ERROR] バッファクリーンアップエラー: {e}")
            finally:
                cleanup_counter = 0


if __name__ == "__main__":
    main_loop()
