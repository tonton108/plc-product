"""
エラーログ・アラーム報告モジュール

Phase 4: Raspberry Piエージェントと中央サーバーのPhase 2 API連携
"""
import os
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 中央サーバーのURL（環境変数から取得）
CENTRAL_SERVER_URL = os.getenv("CENTRAL_SERVER_URL", "http://localhost:5000")


class ErrorReporter:
    """PLC通信エラーとアラームを中央サーバーに報告するクラス"""

    def __init__(self, equipment_id: str, server_url: str = None):
        """
        Args:
            equipment_id: 設備ID（例: "LINE_A_001"）
            server_url: 中央サーバーのURL（デフォルト: 環境変数から取得）
        """
        self.equipment_id = equipment_id
        self.server_url = server_url or CENTRAL_SERVER_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def send_communication_error(
        self,
        error_type: str,
        error_message: str,
        retry_count: int = 0,
        plc_ip: str = None,
        protocol: str = None,
        error_code: str = None
    ) -> bool:
        """
        PLC通信エラーを中央サーバーに送信

        Args:
            error_type: エラー種別（TIMEOUT, CONNECTION_FAILED, PROTOCOL_ERROR等）
            error_message: エラーメッセージ
            retry_count: リトライ回数
            plc_ip: PLCのIPアドレス
            protocol: 通信プロトコル（MC_PROTOCOL_3E, FINS, MODBUS等）
            error_code: エラーコード（任意）

        Returns:
            bool: 送信成功時True、失敗時False
        """
        try:
            endpoint = f"{self.server_url}/api/equipment/{self.equipment_id}/error_logs"

            payload = {
                "error_type": error_type,
                "error_message": error_message,
                "retry_count": retry_count
            }

            # オプションパラメータを追加
            if plc_ip:
                payload["plc_ip"] = plc_ip
            if protocol:
                payload["protocol"] = protocol
            if error_code:
                payload["error_code"] = error_code

            logger.debug(f"📤 エラーログ送信: {endpoint}")
            logger.debug(f"   Payload: {payload}")

            response = self.session.post(endpoint, json=payload, timeout=5)
            response.raise_for_status()

            logger.info(f"✅ エラーログ送信成功: {error_type} - {error_message}")
            return True

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ エラーログ送信タイムアウト（中央サーバー: {self.server_url}）")
            return False

        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 エラーログ送信失敗: 中央サーバーに接続できません（{self.server_url}）")
            return False

        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ エラーログ送信失敗: HTTP {response.status_code} - {response.text}")
            return False

        except Exception as e:
            logger.error(f"❌ エラーログ送信失敗（予期しないエラー）: {e}")
            return False

    def send_alarm(
        self,
        alarm_code: str,
        alarm_level: str,
        alarm_message: str = "",
        alarm_data: Dict[str, Any] = None
    ) -> bool:
        """
        PLCアラームを中央サーバーに送信

        Args:
            alarm_code: アラームコード（例: "E001", "W123"）
            alarm_level: アラームレベル（WARNING, ERROR, CRITICAL）
            alarm_message: アラームメッセージ
            alarm_data: アラーム詳細データ（JSON）

        Returns:
            bool: 送信成功時True、失敗時False
        """
        try:
            endpoint = f"{self.server_url}/api/equipment/{self.equipment_id}/alarms"

            payload = {
                "alarm_code": alarm_code,
                "alarm_level": alarm_level,
                "alarm_message": alarm_message
            }

            if alarm_data:
                payload["alarm_data"] = alarm_data

            logger.debug(f"📤 アラーム送信: {endpoint}")
            logger.debug(f"   Payload: {payload}")

            response = self.session.post(endpoint, json=payload, timeout=5)
            response.raise_for_status()

            logger.info(f"✅ アラーム送信成功: {alarm_code} ({alarm_level}) - {alarm_message}")
            return True

        except requests.exceptions.Timeout:
            logger.error(f"⏱️ アラーム送信タイムアウト（中央サーバー: {self.server_url}）")
            return False

        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 アラーム送信失敗: 中央サーバーに接続できません（{self.server_url}）")
            return False

        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ アラーム送信失敗: HTTP {response.status_code} - {response.text}")
            return False

        except Exception as e:
            logger.error(f"❌ アラーム送信失敗（予期しないエラー）: {e}")
            return False

    def update_plc_status(self, is_online: bool, last_error_type: str = None) -> bool:
        """
        PLC通信状態を更新（内部使用）

        Note: この関数は現在未実装（Phase 2 APIに対応する更新エンドポイントがないため）
        将来的に実装予定

        Args:
            is_online: PLC通信可能状態
            last_error_type: 最後のエラー種別

        Returns:
            bool: 送信成功時True、失敗時False
        """
        # Phase 2 APIには plc_status の更新エンドポイントがないため、
        # エラーログ送信時に自動的に更新される
        logger.debug(f"PLC状態: {'オンライン' if is_online else 'オフライン'}")
        return True


# グローバルインスタンス（シングルトンパターン）
_global_reporter: Optional[ErrorReporter] = None


def initialize_error_reporter(equipment_id: str, server_url: str = None):
    """
    エラーレポーターを初期化

    Args:
        equipment_id: 設備ID
        server_url: 中央サーバーのURL（オプション）
    """
    global _global_reporter
    _global_reporter = ErrorReporter(equipment_id, server_url)
    logger.info(f"📡 エラーレポーター初期化完了: {equipment_id} -> {server_url or CENTRAL_SERVER_URL}")


def get_error_reporter() -> Optional[ErrorReporter]:
    """
    グローバルエラーレポーターインスタンスを取得

    Returns:
        ErrorReporter: インスタンス（未初期化の場合はNone）
    """
    if _global_reporter is None:
        logger.warning("⚠️ エラーレポーターが初期化されていません")
    return _global_reporter


def report_error(
    error_type: str,
    error_message: str,
    retry_count: int = 0,
    plc_ip: str = None,
    protocol: str = None
) -> bool:
    """
    PLC通信エラーを報告（便利関数）

    Args:
        error_type: エラー種別
        error_message: エラーメッセージ
        retry_count: リトライ回数
        plc_ip: PLCのIPアドレス
        protocol: 通信プロトコル

    Returns:
        bool: 送信成功時True、失敗時False
    """
    reporter = get_error_reporter()
    if reporter:
        return reporter.send_communication_error(
            error_type=error_type,
            error_message=error_message,
            retry_count=retry_count,
            plc_ip=plc_ip,
            protocol=protocol
        )
    return False


def report_alarm(
    alarm_code: str,
    alarm_level: str,
    alarm_message: str = "",
    alarm_data: Dict[str, Any] = None
) -> bool:
    """
    PLCアラームを報告（便利関数）

    Args:
        alarm_code: アラームコード
        alarm_level: アラームレベル
        alarm_message: アラームメッセージ
        alarm_data: アラーム詳細データ

    Returns:
        bool: 送信成功時True、失敗時False
    """
    reporter = get_error_reporter()
    if reporter:
        return reporter.send_alarm(
            alarm_code=alarm_code,
            alarm_level=alarm_level,
            alarm_message=alarm_message,
            alarm_data=alarm_data
        )
    return False
