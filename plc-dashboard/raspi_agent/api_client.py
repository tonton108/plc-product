"""
中央サーバーAPIクライアント

Phase 8リファクタリング: db_utils.pyから分割
Phase 9: 定数を使用するように更新
Phase 18: 例外ハンドリング改善
Phase 19: デバイス識別関数をdevice_utils.pyに統合

このモジュールは中央サーバーとの通信を担当します：
- DatabaseAPI: REST API通信、ローカルバッファリング
"""

import os
import logging
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from datetime import datetime, timezone
from functools import wraps
from typing import Optional, Any, Callable, TypeVar
from dotenv import load_dotenv
from local_buffer import LocalBuffer
from config.constants import (
    API_TIMEOUT,
    DEFAULT_CENTRAL_SERVER_IP,
    DEFAULT_CENTRAL_SERVER_PORT,
    MAX_RETRY_COUNT,
)

# Phase 19: デバイス識別関数を統合モジュールからインポート（後方互換性のため再エクスポート）
from device_utils import (
    get_cpu_serial_number,
    get_mac_address,
    get_ip_address,
    get_hostname,
    get_device_info,
)

T = TypeVar('T')

load_dotenv()

# モジュール用ロガー
logger = logging.getLogger(__name__)

# Phase 1: エージェントAPIキー認証（中央サーバー側で X-API-Key ヘッダを検証する）
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")


def agent_api_headers():
    """中央サーバーAPI用の認証ヘッダを返す（未設定時は空dict＝ローカル開発向け）"""
    return {"X-API-Key": AGENT_API_KEY} if AGENT_API_KEY else {}


# ==========================================
# API例外ハンドリングヘルパー（Phase 18追加）
# ==========================================

def handle_api_error(
    operation_name: str,
    default_value: Any = None
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """
    API呼び出しの共通エラーハンドリングデコレータ

    Args:
        operation_name: 操作名（ログ出力用）
        default_value: エラー時のデフォルト戻り値

    Returns:
        デコレータ関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except ConnectionError as e:
                logger.error(f" {operation_name} - 接続エラー: {e}")
                return default_value
            except Timeout as e:
                logger.error(f" {operation_name} - タイムアウト: {e}")
                return default_value
            except RequestException as e:
                logger.error(f" {operation_name} - リクエストエラー: {e}")
                return default_value
            except Exception as e:
                logger.error(f" {operation_name} - 予期せぬエラー: {e}")
                return default_value
        return wrapper
    return decorator


# ==========================================
# DatabaseAPI クラス
# ==========================================

class DatabaseAPI:
    """中央サーバーのデータベースAPIとの通信クラス

    主な機能：
    - 設備設定の取得・保存
    - PLCデータ設定の取得・保存
    - ログデータの送信（ローカルバッファリング対応）
    - 未送信データの再送信
    """

    def __init__(self):
        self.central_server_ip = os.getenv("CENTRAL_SERVER_IP", DEFAULT_CENTRAL_SERVER_IP)
        self.central_server_port = os.getenv("CENTRAL_SERVER_PORT", DEFAULT_CENTRAL_SERVER_PORT)
        self.base_url = f"http://{self.central_server_ip}:{self.central_server_port}/api"

        # ローカルバッファ機能を初期化
        self.buffer = LocalBuffer(db_path='config/buffer.db', max_retry=MAX_RETRY_COUNT)
        logger.info(" ローカルバッファ機能を有効化しました")

    def get_equipment_config(self, equipment_id: str) -> Optional[dict]:
        """設備の基本設定を取得

        Phase 18: 例外ハンドリング改善 - 具体的な例外型を使用
        """
        try:
            response = requests.get(f"{self.base_url}/equipment/{equipment_id}", headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"設備が見つかりません: {equipment_id}")
            else:
                logger.warning(f"設備設定取得 - HTTPエラー {response.status_code}")
            return None
        except (ConnectionError, Timeout) as e:
            logger.error(f" 設備設定取得 - 接続/タイムアウトエラー: {e}")
            return None
        except RequestException as e:
            logger.error(f" 設備設定取得エラー: {e}")
            return None

    def get_equipment_by_device_info(
        self,
        cpu_serial_number: Optional[str] = None,
        mac_address: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[dict]:
        """デバイス情報（CPUシリアル番号、MACアドレス、IPアドレス）で設備を検索

        Phase 18: 例外ハンドリング改善
        """
        try:
            params = {}
            if cpu_serial_number:
                params['cpu_serial_number'] = cpu_serial_number
            if mac_address:
                params['mac_address'] = mac_address
            if ip_address:
                params['ip_address'] = ip_address

            response = requests.get(f"{self.base_url}/equipment/search", params=params, headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug("デバイス情報に一致する設備が見つかりません")
            return None
        except (ConnectionError, Timeout) as e:
            logger.error(f" デバイス情報検索 - 接続/タイムアウトエラー: {e}")
            return None
        except RequestException as e:
            logger.error(f" デバイス情報による設備検索エラー: {e}")
            return None

    def check_equipment_setup_completed(self, equipment_id: str) -> bool:
        """設備の初回セットアップが完了しているかチェック

        Phase 18: 例外ハンドリング改善
        """
        try:
            response = requests.get(f"{self.base_url}/equipment/{equipment_id}/setup_status", headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                result = response.json()
                return result.get("setup_completed", False)
            return False
        except (ConnectionError, Timeout) as e:
            logger.error(f" セットアップ状態確認 - 接続/タイムアウトエラー: {e}")
            return False
        except RequestException as e:
            logger.error(f" セットアップ状態確認エラー: {e}")
            return False

    def get_plc_data_configs(self, equipment_id: str) -> list:
        """設備のPLCデータ設定を取得

        Phase 18: 例外ハンドリング改善
        """
        try:
            response = requests.get(f"{self.base_url}/equipment/{equipment_id}/plc_configs", headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                return response.json()
            return []
        except (ConnectionError, Timeout) as e:
            logger.error(f" PLCデータ設定取得 - 接続/タイムアウトエラー: {e}")
            return []
        except RequestException as e:
            logger.error(f" PLCデータ設定取得エラー: {e}")
            return []

    def save_equipment_config(self, equipment_data: dict) -> bool:
        """設備の基本設定を保存

        Phase 18: 例外ハンドリング改善
        """
        try:
            equipment_id = equipment_data.get("equipment_id")
            response = requests.put(f"{self.base_url}/equipment/{equipment_id}",
                                  json=equipment_data, headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                return True
            logger.warning(f"設備設定保存 - HTTPエラー {response.status_code}")
            return False
        except (ConnectionError, Timeout) as e:
            logger.error(f" 設備設定保存 - 接続/タイムアウトエラー: {e}")
            return False
        except RequestException as e:
            logger.error(f" 設備設定保存エラー: {e}")
            return False

    def save_equipment_config_by_id(self, target_equipment_id: str, equipment_data: dict) -> bool:
        """指定された設備IDで設備の基本設定を保存（設備ID変更対応）

        Phase 18: 例外ハンドリング改善
        """
        try:
            response = requests.put(f"{self.base_url}/equipment/{target_equipment_id}",
                                  json=equipment_data, headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                return True
            logger.warning(f"設備設定保存（ID指定） - HTTPエラー {response.status_code}")
            return False
        except (ConnectionError, Timeout) as e:
            logger.error(f" 設備設定保存（ID指定） - 接続/タイムアウトエラー: {e}")
            return False
        except RequestException as e:
            logger.error(f" 設備設定保存エラー: {e}")
            return False

    def save_plc_data_configs(self, equipment_id: str, plc_configs: list) -> bool:
        """設備のPLCデータ設定を保存

        Phase 18: 例外ハンドリング改善
        """
        try:
            response = requests.put(f"{self.base_url}/equipment/{equipment_id}/plc_configs",
                                  json=plc_configs, headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                return True
            logger.warning(f"PLCデータ設定保存 - HTTPエラー {response.status_code}")
            return False
        except (ConnectionError, Timeout) as e:
            logger.error(f" PLCデータ設定保存 - 接続/タイムアウトエラー: {e}")
            return False
        except RequestException as e:
            logger.error(f" PLCデータ設定保存エラー: {e}")
            return False

    def mark_setup_completed(self, equipment_id: str) -> bool:
        """設備の初回セットアップ完了をマーク

        Phase 18: 例外ハンドリング改善
        """
        try:
            response = requests.post(f"{self.base_url}/equipment/{equipment_id}/mark_setup_completed", headers=agent_api_headers(), timeout=API_TIMEOUT)
            if response.status_code == 200:
                return True
            logger.warning(f"セットアップ完了マーク - HTTPエラー {response.status_code}")
            return False
        except (ConnectionError, Timeout) as e:
            logger.error(f" セットアップ完了マーク - 接続/タイムアウトエラー: {e}")
            return False
        except RequestException as e:
            logger.error(f" セットアップ完了マークエラー: {e}")
            return False

    def send_log_data(self, equipment_id: str, log_data: dict) -> bool:
        """ログデータを送信（バッファリング対応）

        1. まずローカルバッファに保存
        2. 中央サーバーへの送信を試行
        3. 送信成功時はバッファから削除、失敗時はバッファに残す

        Note: 既に適切な例外処理が実装されています（RequestException使用）
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
                response = requests.post(f"{self.base_url}/logs", json=payload, headers=agent_api_headers(), timeout=API_TIMEOUT)
                if response.status_code == 200:
                    # 送信成功 → バッファから削除
                    self.buffer.mark_as_sent(record_id)
                    return True
                else:
                    # 送信失敗（HTTPエラー） → バッファに残す
                    error_msg = f"HTTP {response.status_code}"
                    self.buffer.increment_retry(record_id, error_msg)
                    logger.warning(f" サーバーエラー（バッファに保存済み）: {error_msg}")
                    return False
            except requests.exceptions.RequestException as e:
                # 接続エラー → バッファに残す
                error_msg = str(e)
                self.buffer.increment_retry(record_id, error_msg)
                logger.warning(f" 接続エラー（バッファに保存済み）: {error_msg}")
                return False

        except Exception as e:
            logger.error(f" ログデータ送信エラー: {e}")
            return False

    def retry_pending_data(self, batch_size: int = 100) -> tuple:
        """未送信データを再送信

        Args:
            batch_size: 1回に再送するデータ数（デフォルト100件）

        Returns:
            (成功数, 失敗数, 総数) のタプル

        Note: 既に適切な例外処理が実装されています（RequestException使用）
        """
        pending = self.buffer.get_pending(limit=batch_size)

        if not pending:
            return (0, 0, 0)

        success_count = 0
        failure_count = 0

        logger.info(f"未送信データの再送信を開始: {len(pending)}件")

        for record_id, equipment_id, data in pending:
            try:
                # タイムスタンプを再設定せず、元のタイムスタンプを使用
                response = requests.post(f"{self.base_url}/logs", json=data, headers=agent_api_headers(), timeout=API_TIMEOUT)

                if response.status_code == 200:
                    # 送信成功 → バッファから削除
                    self.buffer.mark_as_sent(record_id)
                    success_count += 1
                    logger.debug(f"再送成功: ID={record_id}, 設備={equipment_id}")
                else:
                    # 送信失敗 → 再試行カウント更新
                    error_msg = f"HTTP {response.status_code}"
                    self.buffer.increment_retry(record_id, error_msg)
                    failure_count += 1
                    logger.warning(f"再送失敗（ID={record_id}）: {error_msg}")

            except requests.exceptions.RequestException as e:
                # 接続エラー → 再試行カウント更新
                error_msg = str(e)
                self.buffer.increment_retry(record_id, error_msg)
                failure_count += 1
                logger.warning(f"再送失敗（ID={record_id}）: 接続エラー")
            except Exception as e:
                # その他のエラー
                self.buffer.increment_retry(record_id, str(e))
                failure_count += 1
                logger.error(f"再送エラー（ID={record_id}）: {e}")

        logger.info(f"再送結果: 成功={success_count}, 失敗={failure_count}, 総数={len(pending)}")

        return (success_count, failure_count, len(pending))

    def cleanup_buffer(self, days: int = 30) -> int:
        """古いバッファデータをクリーンアップ

        保持ポリシーは日数ベースに一本化。未配信データは経過日数（days）を
        超えた場合にのみ削除する。以前は cleanup_max_retry_exceeded も呼んで
        いたが、これは retry_count>=max_retry のデータを配信成否・経過日数を
        問わず削除するため、約10分を超える障害で未配信データが恒久欠損して
        いた。再送は retry_count に関わらず継続される（get_pending 参照）。

        Args:
            days: 保存期間（日数、デフォルト30日）

        Returns:
            削除されたレコード数
        """
        # 古いデータのみを削除（未配信でも days を超えたら破棄）
        deleted_old = self.buffer.cleanup_old_data(days=days)

        if deleted_old > 0:
            logger.info(f"バッファクリーンアップ完了: {deleted_old}件削除")

        return deleted_old

    def get_buffer_stats(self) -> dict:
        """バッファの統計情報を取得・表示"""
        self.buffer.print_stats()
        return self.buffer.get_stats()
