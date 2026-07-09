import os
import time
import logging
import threading
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

# Phase 4: エラー報告モジュール
from error_reporter import initialize_error_reporter, report_error, report_alarm

# Phase 12: 定数
from config.constants import DEFAULT_MODBUS_PORT, DEFAULT_PLC_IP, DEFAULT_PLC_PORT, DEFAULT_INTERVAL_MS

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

# 環境変数設定（Phase 12: 定数を使用）
INTERVAL = int(os.getenv("LOG_INTERVAL_MS", str(DEFAULT_INTERVAL_MS)))  # ms間隔
PLC_IP = os.getenv("PLC_IP", DEFAULT_PLC_IP)
PLC_PORT = int(os.getenv("PLC_PORT", str(DEFAULT_PLC_PORT)))
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

    # 環境変数を再取得（Phase 12: 定数を使用）
    USE_DUMMY_PLC = os.getenv("USE_DUMMY_PLC", "false").lower() == "true"
    PLC_IP = os.getenv("PLC_IP", DEFAULT_PLC_IP)
    PLC_PORT = int(os.getenv("PLC_PORT", str(DEFAULT_PLC_PORT)))
    PLC_MANUFACTURER = os.getenv("PLC_MANUFACTURER", "Mitsubishi")
    LOG_INTERVAL_MS = int(os.getenv("LOG_INTERVAL_MS", str(DEFAULT_INTERVAL_MS)))

    logger.info("🔄 環境変数再読み込み完了:")
    logger.info(f"   USE_DUMMY_PLC = {USE_DUMMY_PLC}")
    logger.info(f"   PLC_IP = {PLC_IP}")
    logger.info(f"   PLC_PORT = {PLC_PORT}")
    logger.info(f"   PLC_MANUFACTURER = {PLC_MANUFACTURER}")
    logger.info(f"   LOG_INTERVAL_MS = {LOG_INTERVAL_MS}")


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

            # Phase 4: エラーを中央サーバーに報告
            report_error(
                error_type="CONNECTION_FAILED",
                error_message=f"PLC接続失敗: {ip}:{port} ({manufacturer})",
                retry_count=0,
                plc_ip=ip,
                protocol=manufacturer
            )

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

        # Phase 4: 例外をエラーとして報告
        report_error(
            error_type="CONNECTION_EXCEPTION",
            error_message=f"PLC接続例外: {str(e)}",
            retry_count=0,
            plc_ip=ip,
            protocol=manufacturer
        )

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
                report_error(
                    error_type="PROTOCOL_ERROR",
                    error_message=f"三菱PLC接続失敗: {ip}:{port}",
                    plc_ip=ip,
                    protocol="MC_PROTOCOL_3E"
                )
                return None
            data = read_mitsubishi_plc(plc, data_points)
            plc.close()
            return data

        elif manufacturer.lower() in ["omron", "オムロン"]:
            fins_client = connect_omron_plc(ip)
            if not fins_client:
                logger.error("オムロンPLC接続に失敗しました")
                report_error(
                    error_type="PROTOCOL_ERROR",
                    error_message=f"オムロンPLC接続失敗: {ip}",
                    plc_ip=ip,
                    protocol="FINS"
                )
                return None
            return read_omron_plc(fins_client, data_points)

        elif manufacturer.lower() in ["keyence", "キーエンス"]:
            modbus_port = config.get("modbus_port", DEFAULT_MODBUS_PORT)
            client = connect_keyence_plc(ip, port=modbus_port)
            if not client:
                logger.error("キーエンスPLC接続に失敗しました")
                report_error(
                    error_type="PROTOCOL_ERROR",
                    error_message=f"キーエンスPLC接続失敗: {ip}:{modbus_port}",
                    plc_ip=ip,
                    protocol="MODBUS"
                )
                return None
            return read_keyence_plc(client, data_points, modbus_port)

        elif manufacturer.lower() in ["siemens", "シーメンス"]:
            plc = connect_siemens_plc(ip)
            if not plc:
                logger.error("シーメンスPLC接続に失敗しました")
                report_error(
                    error_type="PROTOCOL_ERROR",
                    error_message=f"シーメンスPLC接続失敗: {ip}",
                    plc_ip=ip,
                    protocol="S7"
                )
                return None
            return read_siemens_plc(plc, data_points)

        else:
            error_msg = f"不明なメーカー: {manufacturer}"
            logger.error(f"[ERROR] {error_msg}")
            report_error(
                error_type="CONFIGURATION_ERROR",
                error_message=error_msg,
                plc_ip=ip,
                protocol=manufacturer
            )
            raise ValueError(f"[ERROR] {error_msg}")

    except Exception as e:
        logger.error(f"[ERROR] PLC読取エラー: {e}")
        report_error(
            error_type="READ_ERROR",
            error_message=f"PLC読取エラー: {str(e)}",
            plc_ip=ip,
            protocol=manufacturer
        )
        return None


def auto_identify_equipment():
    """CPUシリアル番号を使用した設備自動識別"""
    try:
        logger.info("🔍 設備自動識別を実行中...")

        # デバイス情報を取得
        cpu_serial = get_cpu_serial_number()
        mac_address = get_mac_address()
        ip_address = get_ip_address()

        logger.info("📊 デバイス情報:")
        logger.info(f"   CPUシリアル番号: {cpu_serial}")
        logger.info(f"   MACアドレス: {mac_address}")
        logger.info(f"   IPアドレス: {ip_address}")

        # 設備検索（優先順位: CPU Serial > MAC > IP）
        equipment_config = db_api.get_equipment_by_device_info(
            cpu_serial_number=cpu_serial,
            mac_address=mac_address,
            ip_address=ip_address
        )

        if equipment_config:
            equipment_id = equipment_config.get("equipment_id")
            logger.info(f"✅ 設備識別成功: {equipment_id}")

            # 設定に保存（設備IDを永続化）
            config_manager.save_equipment_id(equipment_id)
            logger.info(f"📝 設備ID '{equipment_id}' を設定に保存しました")

            # Phase 4: エラーレポーター初期化
            central_server_url = os.getenv("CENTRAL_SERVER_URL", "http://localhost:5000")
            initialize_error_reporter(equipment_id, central_server_url)
            logger.info(f"📡 エラーレポーター初期化完了: {central_server_url}")

            return equipment_id
        else:
            logger.warning("対応する設備が見つかりませんでした")
            if cpu_serial and cpu_serial == "FALLBACK_FIXED_ID":
                logger.info("ℹ️ フォールバック固定IDが使用されています")
            logger.info("💡 設備登録を行ってください: python register_equipment.py")
            return None

    except Exception as e:
        logger.error(f"設備自動識別エラー: {e}")
        return None


# === メインループ ===
def main_loop(stop_event=None):
    """PLCデータ収集のメインループ（送信・再送・バッファクリーンアップを含む）

    Args:
        stop_event: threading.Event。セットされるとループを安全に終了する。
                    WebUI（agent_app.py）からスレッドとして起動する場合に渡す。
                    None の場合は無限ループ（単体起動時）。
    """
    # 単体起動時は誰もセットしないEventに正規化し、以降のNone分岐を不要にする
    if stop_event is None:
        stop_event = threading.Event()

    # 初回起動時に環境変数を再読み込み
    logger.info("🚀 PLCエージェント起動 - 環境変数確認中...")
    reload_env_vars()

    # バッファリング機能のカウンター
    retry_counter = 0  # 再送信のカウンター
    cleanup_counter = 0  # クリーンアップのカウンター
    retry_interval = 60  # 再送信間隔（秒）: 60秒ごと
    cleanup_interval = 3600  # クリーンアップ間隔（秒）: 1時間ごと

    logger.info("📦 バッファリング機能有効:")
    logger.info(f"  - 再送信間隔: {retry_interval}秒ごと")
    logger.info(f"  - クリーンアップ間隔: {cleanup_interval}秒ごと（7日以上前のデータを削除）")

    while not stop_event.is_set():
        # ループ全体を保護し、想定外の例外でも収集スレッドを止めない
        # （スレッド実行時の未捕捉例外はstderrにしか出ず、ログに残らず無音で死ぬため）
        try:
            # 設定をDB優先で読み込み（設定変更に対応）
            config = load_plc_config()
            equipment_id = config.get("equipment_id")

            if not equipment_id:
                logger.warning("設備IDが未設定です。自動識別を試行します...")

                # CPUシリアル番号による自動識別を実行
                equipment_id = auto_identify_equipment()

                if not equipment_id:
                    logger.warning("設備自動識別に失敗しました。10秒後に再試行します。")
                    stop_event.wait(10)
                    continue

                # 設定を再読み込み（識別結果を反映）
                config = load_plc_config()

            # 設定に基づいてPLCからデータを取得
            values = read_from_plc(config)

            if values:
                # Phase 4: アラーム検出とAPI送信
                error_code = values.get("error_code")
                if error_code and error_code > 0:
                    # スケール適用でfloatになり得るため書式化前にintへ正規化
                    error_code = int(error_code)
                    # エラーコードが0以外の場合、アラームとして報告
                    alarm_level = "WARNING" if error_code == 1 else "ERROR"
                    report_alarm(
                        alarm_code=f"E{error_code:03d}",
                        alarm_level=alarm_level,
                        alarm_message=f"PLCアラーム検出: エラーコード {error_code}",
                        alarm_data={
                            "error_code": error_code,
                            "plc_values": values
                        }
                    )
                    logger.warning(f"⚠️ アラーム検出: E{error_code:03d} ({alarm_level})")

                # DB APIを使用してログデータを送信（バッファリング対応）
                success = db_api.send_log_data(equipment_id, values)

                if success:
                    logger.info(f"✅ DB送信成功: {equipment_id} / {values}")
                else:
                    logger.warning(f"DB送信失敗（バッファに保存済み）: {equipment_id}")
            else:
                logger.warning("データ取得失敗。")

            # 設定された間隔で待機
            interval = config.get("interval", INTERVAL)
            stop_event.wait(interval / 1000.0)

            # カウンター更新
            retry_counter += interval / 1000.0
            cleanup_counter += interval / 1000.0

            # 定期的に未送信データを再送信
            if retry_counter >= retry_interval:
                try:
                    success, failure, total = db_api.retry_pending_data(batch_size=100)
                    if total > 0:
                        logger.info(f"🔄 未送信データ再送完了: 成功={success}, 失敗={failure}")
                except Exception as e:
                    logger.error(f"未送信データ再送エラー: {e}")
                finally:
                    retry_counter = 0

            # 定期的に古いバッファデータをクリーンアップ
            if cleanup_counter >= cleanup_interval:
                try:
                    deleted = db_api.cleanup_buffer(days=7)
                    if deleted > 0:
                        logger.info(f"🗑️ 古いバッファデータを削除: {deleted}件")
                except Exception as e:
                    logger.error(f"バッファクリーンアップエラー: {e}")
                finally:
                    cleanup_counter = 0

        except Exception:
            logger.exception("main_loopで未捕捉の例外が発生しました。5秒後に継続します")
            stop_event.wait(5)


if __name__ == "__main__":
    main_loop()
