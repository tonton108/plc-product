"""
負荷シミュレーション：高頻度データ送信時の影響を検証
"""

import time
from datetime import datetime


def simulate_interval_impact(interval_ms, server_timeout_sec=5):
    """
    データ送信間隔と負荷の関係を計算

    Args:
        interval_ms: データ送信間隔（ミリ秒）
        server_timeout_sec: サーバータイムアウト時間（秒）
    """

    print("=" * 70)
    print(f"  負荷シミュレーション: {interval_ms}ms間隔")
    print("=" * 70)

    interval_sec = interval_ms / 1000.0

    # 1時間あたりの送信回数
    sends_per_hour = int(3600 / interval_sec)
    sends_per_day = sends_per_hour * 24

    print(f"\n[通常時の負荷]")
    print(f"  送信間隔: {interval_ms}ms ({interval_sec}秒)")
    print(f"  1時間あたりの送信回数: {sends_per_hour:,}回")
    print(f"  1日あたりの送信回数: {sends_per_day:,}回")

    # サーバーダウン時の影響
    print(f"\n[サーバーダウン時の影響]")
    print(f"  タイムアウト時間: {server_timeout_sec}秒")

    # 実質的なサイクルタイム（送信失敗時）
    cycle_time_down = interval_sec + server_timeout_sec
    effective_interval = cycle_time_down * 1000  # ミリ秒に変換

    print(f"  実質的なサイクルタイム: {cycle_time_down}秒 ({effective_interval}ms)")
    print(f"  データ取得頻度の低下: {interval_ms}ms → {effective_interval}ms")
    print(f"  低下率: {((effective_interval - interval_ms) / interval_ms * 100):.1f}%")

    # 1時間ダウンした場合のタイムアウト待ち時間
    downtime_hours = 1
    timeout_waits = int(downtime_hours * 3600 / cycle_time_down)
    total_timeout_time = timeout_waits * server_timeout_sec

    print(f"\n[1時間ダウン時の無駄な待ち時間]")
    print(f"  タイムアウト発生回数: {timeout_waits:,}回")
    print(
        f"  総タイムアウト待ち時間: {total_timeout_time:,}秒 ({total_timeout_time/60:.1f}分)"
    )

    # CPU/メモリ影響
    print(f"\n[リソース影響]")
    avg_request_size = 0.5  # KB（推定）
    data_volume_per_day = sends_per_day * avg_request_size / 1024  # MB
    print(f"  1日あたりの送信データ量: {data_volume_per_day:.2f}MB（推定）")

    # バッファに保存されるデータ量（1日ダウンした場合）
    buffer_records_per_day = int(24 * 3600 / cycle_time_down)
    buffer_size_mb = buffer_records_per_day * 0.5 / 1024  # MB
    print(
        f"  1日ダウン時のバッファデータ量: {buffer_size_mb:.2f}MB ({buffer_records_per_day:,}件)"
    )

    # 警告判定
    print(f"\n[総合評価]")
    warnings = []

    if interval_sec < 1:
        warnings.append("[WARNING] 1秒未満の高頻度送信：タイムアウト待ちの影響が大きい")

    if effective_interval > interval_ms * 2:
        warnings.append(
            "[WARNING] サーバーダウン時に実質的なデータ取得頻度が半分以下になる"
        )

    if sends_per_day > 100000:
        warnings.append("[WARNING] 1日10万回以上の送信：サーバー負荷が高い")

    if buffer_records_per_day > 50000:
        warnings.append(
            "[WARNING] 1日ダウン時のバッファ件数が5万件超：再送に時間がかかる"
        )

    if warnings:
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("  [OK] 問題なし：現状の仕組みで十分実用的")

    print("=" * 70 + "\n")

    return {
        "interval_ms": interval_ms,
        "sends_per_day": sends_per_day,
        "effective_interval": effective_interval,
        "buffer_records_per_day": buffer_records_per_day,
        "has_warnings": len(warnings) > 0,
    }


def main():
    """複数の送信間隔でシミュレーション"""

    print("\n" + "=" * 70)
    print("  PLCエージェント 負荷シミュレーション")
    print("=" * 70)
    print(f"  実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    # 各種送信間隔でシミュレーション
    intervals = [
        5000,  # 現在のデフォルト（5秒）
        2000,  # 2秒
        1000,  # 1秒
        500,  # 500ms
        200,  # 200ms
        100,  # 100ms
    ]

    results = []
    for interval in intervals:
        result = simulate_interval_impact(interval)
        results.append(result)
        time.sleep(0.1)

    # 比較表を表示
    print("\n" + "=" * 70)
    print("  送信間隔別の比較表")
    print("=" * 70)
    print(
        f"{'送信間隔':<12} {'1日の送信回数':<15} {'ダウン時の実質間隔':<20} {'1日ダウン時のバッファ件数':<25} {'評価'}"
    )
    print("-" * 70)

    for result in results:
        interval = result["interval_ms"]
        sends = result["sends_per_day"]
        effective = result["effective_interval"]
        buffer = result["buffer_records_per_day"]
        status = "[WARNING] 要対策" if result["has_warnings"] else "[OK]"

        print(
            f"{interval:>6}ms     {sends:>12,}回     {effective:>10.0f}ms          {buffer:>15,}件        {status}"
        )

    print("=" * 70)

    # 推奨事項
    print("\n" + "=" * 70)
    print("  推奨事項")
    print("=" * 70)

    print("\n[短期対策]")
    print("  1. タイムアウト時間を短縮（5秒 → 2秒）")
    print("     - 影響を軽減できるが、根本的な解決にはならない")

    print("\n[中期対策]")
    print("  2. 指数バックオフ方式の導入")
    print("     - 1回目失敗: 2秒タイムアウト")
    print("     - 2回目失敗: 3秒タイムアウト")
    print("     - 3回目以降: タイムアウトなし（即座にバッファ保存）")

    print("\n[長期対策（推奨）]")
    print("  3. WebSocket通知方式の実装")
    print("     - サーバーシャットダウン/起動通知")
    print("     - タイムアウト待ちが完全になくなる")
    print("     - 高頻度システムでも安定動作")

    print("\n[その他の最適化]")
    print("  4. バッチ送信の導入")
    print("     - 複数データをまとめて送信（通信回数を削減）")
    print("  5. データ圧縮")
    print("     - JSONをgzip圧縮して送信（帯域幅を削減）")

    print("\n" + "=" * 70)


# --- pytest テスト ---
# これらは負荷計算ロジック（純粋関数）を検証する。
# 従来このファイルは test_ 関数を持たず、pytestで一切実行されていなかった。


def test_simulate_interval_impact_5000ms():
    """5秒間隔: 計算値が期待通りで警告が立たないこと"""
    result = simulate_interval_impact(5000)
    assert result["interval_ms"] == 5000
    # (3600 / 5) * 24 = 17280回/日
    assert result["sends_per_day"] == 17280
    # (5秒間隔 + 5秒タイムアウト) * 1000 = 10000ms
    assert result["effective_interval"] == 10000
    assert result["has_warnings"] is False


def test_simulate_interval_impact_high_frequency_warns():
    """100ms間隔: 高頻度送信で警告が立つこと"""
    result = simulate_interval_impact(100)
    # 36000回/時 * 24 = 864000回/日
    assert result["sends_per_day"] == 864000
    assert result["has_warnings"] is True


def test_simulate_interval_impact_custom_timeout():
    """タイムアウト時間を変えると実質サイクルタイムに反映されること"""
    result = simulate_interval_impact(1000, server_timeout_sec=2)
    # (1秒 + 2秒) * 1000 = 3000ms
    assert result["effective_interval"] == 3000


def test_main_runs_without_error():
    """main()が全間隔のシミュレーションをエラーなく完走すること（スモーク）"""
    main()


if __name__ == "__main__":
    main()
