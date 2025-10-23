"""
PLC通信の共通機能モジュール

エラー統計、バリデーション、リトライ処理、アドレス解析など、
全メーカー共通で使用する機能を提供します。

CLAUDE.md参照: パフォーマンス最適化とセキュリティ
"""
import os
import time
import random
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 環境変数設定
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "5"))
READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "3"))

# セキュリティ設定（CLAUDE.md参照）
ALLOWED_PLC_IPS = os.getenv("ALLOWED_PLC_IPS", "").split(",") if os.getenv("ALLOWED_PLC_IPS") else []
READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "true").lower() == "true"

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


def safe_plc_read(plc_func, error_msg="PLC読み取りエラー"):
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
                dummy_data[key] = round(random.uniform(0.0, 1000.0), 3)  # 高精度浮動小数点
            elif data_type == "dword":
                dummy_data[key] = random.randint(0, 4294967295)  # 32bit整数
            else:
                dummy_data[key] = round(random.uniform(0.0, 100.0), 1)

    return dummy_data
