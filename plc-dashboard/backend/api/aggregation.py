"""
動的データ項目の集計ヘルパー（Phase 2）

Log.data（生ログの動的JSON項目）や、日次集計の data_summary を
横断して avg/max/min を算出する共通ロジック。

scheduler.py（自動スケジューラ）と log_manager.py（手動CLI）の両方から
呼ばれ、集計ロジックの重複と乖離（旧Issue #10）を防ぐ。
"""

from collections import defaultdict


def summarize_dynamic_from_logs(logs):
    """生ログのリストから、動的項目（Log.data）ごとの avg/max/min を算出する

    Args:
        logs: Logモデルのリスト（各 log.data は dict or None）

    Returns:
        dict: {"<項目名>_avg": x, "<項目名>_max": y, "<項目名>_min": z, ...}
              数値項目のみ対象。データが無ければ空dict
    """
    values_by_key = defaultdict(list)
    for log in logs:
        if not log.data:
            continue
        for key, value in log.data.items():
            if isinstance(value, bool):
                # boolはintのサブクラスだが集計対象にしない
                continue
            if isinstance(value, (int, float)):
                values_by_key[key].append(value)

    return _avg_max_min(values_by_key)


def summarize_dynamic_from_daily(daily_summaries):
    """日次集計のリストから、動的項目の月次 avg/max/min を算出する

    日次の data_summary（"<key>_avg"/"_max"/"_min"）を月次に集約する:
    - 月次avg = 日次avgの平均
    - 月次max = 日次maxの最大
    - 月次min = 日次minの最小

    Args:
        daily_summaries: DailyLogSummaryのリスト（各 .data_summary は dict or None）

    Returns:
        dict: {"<項目名>_avg": x, "<項目名>_max": y, "<項目名>_min": z, ...}
    """
    avg_values = defaultdict(list)
    max_values = defaultdict(list)
    min_values = defaultdict(list)

    for summary in daily_summaries:
        ds = summary.data_summary
        if not ds:
            continue
        for stat_key, value in ds.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            if stat_key.endswith("_avg"):
                avg_values[stat_key[:-4]].append(value)
            elif stat_key.endswith("_max"):
                max_values[stat_key[:-4]].append(value)
            elif stat_key.endswith("_min"):
                min_values[stat_key[:-4]].append(value)

    result = {}
    for key, vals in avg_values.items():
        if vals:
            result[f"{key}_avg"] = sum(vals) / len(vals)
    for key, vals in max_values.items():
        if vals:
            result[f"{key}_max"] = max(vals)
    for key, vals in min_values.items():
        if vals:
            result[f"{key}_min"] = min(vals)
    return result


def _avg_max_min(values_by_key):
    """項目名→数値リストの辞書から avg/max/min を展開する"""
    result = {}
    for key, vals in values_by_key.items():
        if not vals:
            continue
        result[f"{key}_avg"] = sum(vals) / len(vals)
        result[f"{key}_max"] = max(vals)
        result[f"{key}_min"] = min(vals)
    return result
