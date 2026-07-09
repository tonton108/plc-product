"""
バッチ読み取り最適化モジュール

Phase 11リファクタリング: base.pyから分割

連続アドレスのグループ化によるバッチ読み取り最適化機能を提供します：
- アドレス番号の抽出
- 連続ワードアドレスのグループ化

CLAUDE.md参照: パフォーマンス最適化 - バッチ読み取りの活用
"""

import re
import logging

logger = logging.getLogger(__name__)


def extract_address_number(address):
    """
    アドレス文字列から数値部分を抽出

    Args:
        address: アドレス文字列（例: "D100", "DM200", "D100.5"）

    Returns:
        int: アドレス番号（例: 100, 200, 100）
    """
    # ビット指定がある場合は除外（D100.5 → D100）
    address_base = address.split(".")[0]
    # 数字部分を抽出
    match = re.search(r"\d+", address_base)
    if match:
        return int(match.group())
    return None


def group_continuous_word_addresses(data_points, device_type="D"):
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
        if data_type != "word" or "." in address:
            continue

        # 指定デバイスタイプのみ
        if not address.upper().startswith(device_type):
            continue

        addr_num = extract_address_number(address)
        if addr_num is not None:
            word_items.append(
                {
                    "key": key,
                    "setting": setting,
                    "address_num": addr_num,
                    "address": address,
                }
            )

    # アドレス番号でソート
    word_items.sort(key=lambda x: x["address_num"])

    # 連続アドレスをグループ化
    groups = []
    current_group = None

    for item in word_items:
        if current_group is None:
            # 新しいグループ開始
            current_group = {
                "keys": [item["key"]],
                "start_address": item["address_num"],
                "count": 1,
                "settings": [item["setting"]],
                "addresses": [item["address"]],
            }
        elif (
            item["address_num"]
            == current_group["start_address"] + current_group["count"]
        ):
            # 連続している → グループに追加
            current_group["keys"].append(item["key"])
            current_group["count"] += 1
            current_group["settings"].append(item["setting"])
            current_group["addresses"].append(item["address"])
        else:
            # 連続していない → グループ確定して新しいグループ開始
            groups.append(current_group)
            current_group = {
                "keys": [item["key"]],
                "start_address": item["address_num"],
                "count": 1,
                "settings": [item["setting"]],
                "addresses": [item["address"]],
            }

    # 最後のグループを追加
    if current_group:
        groups.append(current_group)

    return groups
