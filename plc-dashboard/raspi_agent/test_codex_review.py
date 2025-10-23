"""
Codex自動レビューのテスト用ファイル

このファイルには意図的に以下の問題を含めています：
1. セキュリティ問題：ハードコードされたパスワード
2. エンディアン問題：PLCプロトコルでのバイトオーダー間違い
3. タイムアウト設定なし：無限待機のリスク
4. エラーハンドリング不足：例外処理がない
"""

import pymcprotocol
import struct


# ❌ 問題1: ハードコードされたパスワード（セキュリティリスク）
PLC_PASSWORD = "admin123"
DATABASE_PASSWORD = "plc_pass"


def read_float_wrong_endian(plc, address):
    """
    ❌ 問題2: エンディアン問題

    PLCはBig-Endianだが、ここではLittle-Endianで結合している。
    正しい値が取得できない。
    """
    word_values = plc.batchread_wordunits(address, 2)

    # 間違い: Little-Endianで結合（PLCはBig-Endian）
    word1, word2 = word_values[0], word_values[1]
    combined = (word2 << 16) | word1  # 逆！

    # Little-Endianとして解釈（間違い）
    float_value = struct.unpack('<f', struct.pack('<I', combined))[0]

    return float_value


def connect_plc_no_timeout(ip, port):
    """
    ❌ 問題3: タイムアウト設定なし

    タイムアウトを設定していないため、接続が永遠に待機する可能性がある。
    ネットワーク障害時にプログラムがハングする。
    """
    plc = pymcprotocol.Type3E()
    plc.connect(ip, port)  # タイムアウトなし！
    return plc


def read_data_no_error_handling(plc, address, count):
    """
    ❌ 問題4: エラーハンドリングなし

    例外処理がないため、通信エラー時にプログラムがクラッシュする。
    PLC接続が切れた場合の対処がない。
    """
    # 例外処理なし
    data = plc.batchread_wordunits(address, count)
    return data


def save_credentials_to_file():
    """
    ❌ 問題5: 認証情報の平文保存

    パスワードを平文でファイルに保存している。
    """
    with open("config.txt", "w") as f:
        f.write(f"password={PLC_PASSWORD}\n")
        f.write(f"db_password={DATABASE_PASSWORD}\n")


def process_plc_data_unsafe(ip, port):
    """
    ❌ 問題6: 複数の問題が組み合わさっている

    - タイムアウトなし
    - エラーハンドリングなし
    - エンディアン問題
    """
    plc = connect_plc_no_timeout(ip, port)
    data = read_data_no_error_handling(plc, "D100", 10)
    temperature = read_float_wrong_endian(plc, "D200")

    return {
        "data": data,
        "temperature": temperature
    }
