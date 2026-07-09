"""
PLC通信の共通機能モジュール

エラー統計、バリデーション、リトライ処理、アドレス解析、データ型変換など、
全メーカー共通で使用する機能を提供します。

CLAUDE.md参照: パフォーマンス最適化とセキュリティ

Phase 4リファクタリング: データ型変換関数を追加して重複コードを削減
Phase 11リファクタリング: converters.pyとbatch_reader.pyに分割
Phase 16: 型ヒント追加
"""

import os
import time
import random
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable, TypeVar
from dotenv import load_dotenv

T = TypeVar("T")

# Phase 11: 分割されたモジュールからインポート（後方互換性）
from .converters import (
    convert_words_to_float32,
    convert_words_to_dword,
    convert_words_to_value,
)
from .batch_reader import (
    extract_address_number,
    group_continuous_word_addresses,
)

load_dotenv()

logger = logging.getLogger(__name__)

# 環境変数設定
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "5"))
READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "3"))

# セキュリティ設定（CLAUDE.md参照）
ALLOWED_PLC_IPS = (
    os.getenv("ALLOWED_PLC_IPS", "").split(",") if os.getenv("ALLOWED_PLC_IPS") else []
)
READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "true").lower() == "true"

# グローバルパフォーマンス統計（CLAUDE.md参照）
# 目標指標: 通信成功率95%以上、平均応答時間100ms以下、エラー率5%以下
error_stats = {
    "connection_errors": 0,
    "read_errors": 0,
    "last_success": None,
    "consecutive_failures": 0,
    # パフォーマンス監視用の追加指標
    "total_attempts": 0,  # 総通信試行回数
    "successful_attempts": 0,  # 成功回数
    "total_response_time": 0.0,  # 累積応答時間（ms）
    "max_response_time": 0.0,  # 最大応答時間（ms）
    "min_response_time": float("inf"),  # 最小応答時間（ms）
    "start_time": datetime.now(),  # 統計開始時刻
}


def print_error_stats() -> None:
    """
    パフォーマンス統計を表示（CLAUDE.md参照）
    目標指標: 通信成功率95%以上、平均応答時間100ms以下、エラー率5%以下

    Phase 14: print() → logger統一
    """
    global error_stats

    # 基本統計
    logger.info("=" * 60)
    logger.info("PLCエージェント パフォーマンス統計")
    logger.info("=" * 60)

    # エラー統計
    logger.info("【エラー統計】")
    logger.info(f"  接続エラー: {error_stats['connection_errors']}回")
    logger.info(f"  読み取りエラー: {error_stats['read_errors']}回")
    logger.info(f"  連続失敗: {error_stats['consecutive_failures']}回")

    # 通信成功率
    total = error_stats["total_attempts"]
    success = error_stats["successful_attempts"]
    if total > 0:
        success_rate = (success / total) * 100
        error_rate = 100 - success_rate
        logger.info("【通信統計】")
        logger.info(f"  総試行回数: {total}回")
        logger.info(f"  成功回数: {success}回")
        logger.info(f"  失敗回数: {total - success}回")
        logger.info(
            f"  通信成功率: {success_rate:.2f}% {'(達成)' if success_rate >= 95 else '(未達成)'}"
        )
        logger.info(
            f"  エラー率: {error_rate:.2f}% {'(達成)' if error_rate <= 5 else '(未達成)'}"
        )

    # 応答時間統計
    if success > 0:
        avg_response = error_stats["total_response_time"] / success
        logger.info("【応答時間統計】")
        logger.info(
            f"  平均応答時間: {avg_response:.2f}ms {'(達成)' if avg_response <= 100 else '(未達成)'}"
        )
        logger.info(f"  最大応答時間: {error_stats['max_response_time']:.2f}ms")
        if error_stats["min_response_time"] != float("inf"):
            logger.info(f"  最小応答時間: {error_stats['min_response_time']:.2f}ms")

    # 稼働時間
    uptime = datetime.now() - error_stats["start_time"]
    logger.info("【稼働時間】")
    logger.info(
        f"  開始時刻: {error_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}"
    )
    logger.info(f"  稼働時間: {uptime}")

    if error_stats["last_success"]:
        logger.info(
            f"  最終成功: {error_stats['last_success'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        logger.info("  最終成功: なし")

    logger.info("=" * 60)


def update_error_stats(
    success: bool = True,
    error_type: Optional[str] = None,
    response_time_ms: Optional[float] = None,
) -> None:
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
            error_stats["max_response_time"] = max(
                error_stats["max_response_time"], response_time_ms
            )
            error_stats["min_response_time"] = min(
                error_stats["min_response_time"], response_time_ms
            )

            if response_time_ms > 100:
                logger.warning(
                    f"⚠️ 応答時間が遅い: {response_time_ms:.2f}ms (目標: 100ms以下)"
                )
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

        logger.warning(
            f"❌ PLC通信失敗 (連続失敗: {error_stats['consecutive_failures']}回)"
        )

    # 定期的に統計を表示（100回ごと）
    if error_stats["total_attempts"] % 100 == 0:
        print_error_stats()


def validate_plc_ip(ip_address: str) -> bool:
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
        logger.error(
            f"🚫 不正なPLC IPアドレス: {ip_address} (ホワイトリスト: {ALLOWED_PLC_IPS})"
        )
        return False


def check_write_permission() -> bool:
    """
    PLC書き込み権限をチェック（CLAUDE.md参照）

    Returns:
        bool: 書き込み可能な場合True、それ以外False
    """
    if READ_ONLY_MODE:
        logger.warning(
            "🔒 書き込み保護モードが有効です。PLCへの書き込みは禁止されています。"
        )
        return False
    return True


def retry_on_failure(
    func: Callable[[], T], max_retries: int = MAX_RETRY_ATTEMPTS, delay: int = 1
) -> Optional[T]:
    """
    リトライ機構付きの関数実行

    Args:
        func: 実行する関数
        max_retries: 最大リトライ回数
        delay: リトライ間隔（秒）

    Returns:
        関数の実行結果
    """
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


def safe_plc_read(
    plc_func: Callable[[], T], error_msg: str = "PLC読み取りエラー"
) -> Optional[T]:
    """
    安全なPLC読み取り（タイムアウト・エラー処理付き）

    Args:
        plc_func: PLC読み取り関数
        error_msg: エラーメッセージ

    Returns:
        読み取り結果、エラー時はNone
    """
    try:
        result = plc_func()
        return result
    except Exception as e:
        update_error_stats(False, "read")
        logger.error(f"{error_msg}: {e}")
        return None


def generate_dummy_data(data_points: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    ダミーデータを生成

    Args:
        data_points: データ項目の辞書

    Returns:
        dict: ダミーデータ
    """
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
                dummy_data[key] = round(
                    random.uniform(0.0, 1000.0), 3
                )  # 高精度浮動小数点
            elif data_type == "dword":
                dummy_data[key] = random.randint(0, 4294967295)  # 32bit整数
            else:
                dummy_data[key] = round(random.uniform(0.0, 100.0), 1)

    return dummy_data


# ============================================================
# 後方互換性のためのエクスポート（Phase 11）
# ============================================================
# 以下の関数はconverters.pyとbatch_reader.pyに移動されましたが、
# 既存のimport文との互換性を維持するため、このモジュールからも利用可能です。
#
# from plc_drivers.base import convert_words_to_float32  # 引き続き動作
# from plc_drivers.converters import convert_words_to_float32  # 推奨
#
# ============================================================

__all__ = [
    # エラー統計
    "error_stats",
    "print_error_stats",
    "update_error_stats",
    # セキュリティ・バリデーション
    "validate_plc_ip",
    "check_write_permission",
    "retry_on_failure",
    "safe_plc_read",
    # ダミーデータ
    "generate_dummy_data",
    # 環境変数
    "MAX_RETRY_ATTEMPTS",
    "CONNECTION_TIMEOUT",
    "READ_TIMEOUT",
    "ALLOWED_PLC_IPS",
    "READ_ONLY_MODE",
    # converters.pyからの再エクスポート
    "convert_words_to_float32",
    "convert_words_to_dword",
    "convert_words_to_value",
    # batch_reader.pyからの再エクスポート
    "extract_address_number",
    "group_continuous_word_addresses",
]
