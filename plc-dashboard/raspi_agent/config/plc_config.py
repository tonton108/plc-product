"""
PLCメーカー・シリーズ定義

Phase 7リファクタリング: agent_app.pyから分割

PLCメーカーとサポートされるシリーズの定義を提供します。
"""

# PLCメーカー・シリーズマッピング
SERIES_LIST = {
    "三菱": ["FX", "Q", "iQ-R", "iQ-F"],
    "キーエンス": ["KV-8000 (Modbus)", "KV-5000 (Modbus)", "KV Nano (Modbus)"],
    "オムロン": ["CJ", "CP", "NX", "NJ"],
    "シーメンス": ["S7-1200 (未実装)", "S7-1500 (未実装)"]
}

# メーカー一覧
MANUFACTURERS = list(SERIES_LIST.keys())

# プロトコルマッピング（将来的な拡張用）
PROTOCOL_MAP = {
    "三菱": "MC Protocol",
    "キーエンス": "Modbus TCP",
    "オムロン": "FINS",
    "シーメンス": "S7"
}


def get_series_for_manufacturer(manufacturer):
    """メーカーのシリーズ一覧を取得

    Args:
        manufacturer: メーカー名

    Returns:
        list: シリーズ一覧、メーカーが存在しない場合は空リスト
    """
    return SERIES_LIST.get(manufacturer, [])


def get_protocol_for_manufacturer(manufacturer):
    """メーカーの通信プロトコルを取得

    Args:
        manufacturer: メーカー名

    Returns:
        str: プロトコル名、存在しない場合は"Unknown"
    """
    return PROTOCOL_MAP.get(manufacturer, "Unknown")
