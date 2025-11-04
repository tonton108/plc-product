"""
ページ読み込み時間を正確に計測するスクリプト
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def measure_load_time():
    """ページ読み込み時間を計測"""
    print("=" * 70)
    print("  Page Load Time Measurement")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # ブラウザを起動
            print("\n[1/4] ブラウザを起動中...")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # パフォーマンスタイミングを記録
            print("\n[2/4] ページ読み込み開始...")
            start_time = time.time()

            page.goto('http://localhost:3000/', wait_until='networkidle', timeout=120000)

            end_time = time.time()
            total_time = end_time - start_time

            # ブラウザのパフォーマンスAPIから詳細なタイミングを取得
            print("\n[3/4] パフォーマンス情報を取得中...")
            performance = page.evaluate('''() => {
                const perf = window.performance.timing;
                const navigation = performance.getEntriesByType('navigation')[0];

                return {
                    // 基本タイミング
                    navigationStart: perf.navigationStart,
                    domainLookupStart: perf.domainLookupStart,
                    domainLookupEnd: perf.domainLookupEnd,
                    connectStart: perf.connectStart,
                    connectEnd: perf.connectEnd,
                    requestStart: perf.requestStart,
                    responseStart: perf.responseStart,
                    responseEnd: perf.responseEnd,
                    domLoading: perf.domLoading,
                    domInteractive: perf.domInteractive,
                    domContentLoadedEventStart: perf.domContentLoadedEventStart,
                    domContentLoadedEventEnd: perf.domContentLoadedEventEnd,
                    domComplete: perf.domComplete,
                    loadEventStart: perf.loadEventStart,
                    loadEventEnd: perf.loadEventEnd,

                    // Navigation Timing API v2 (より詳細)
                    navigationTiming: navigation ? {
                        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
                        duration: navigation.duration
                    } : null
                };
            }''')

            # 計算されたタイミング
            dns_time = performance['domainLookupEnd'] - performance['domainLookupStart']
            tcp_time = performance['connectEnd'] - performance['connectStart']
            request_time = performance['responseStart'] - performance['requestStart']
            response_time = performance['responseEnd'] - performance['responseStart']
            dom_loading_time = performance['domInteractive'] - performance['domLoading']
            dom_interactive_time = performance['domContentLoadedEventStart'] - performance['domInteractive']
            dom_content_loaded_time = performance['domContentLoadedEventEnd'] - performance['domContentLoadedEventStart']
            total_page_load = performance['loadEventEnd'] - performance['navigationStart']

            # スクリーンショット撮影
            print("\n[4/4] スクリーンショット撮影中...")
            screenshot_path = Path(__file__).parent / 'load_time_screenshot.png'
            page.screenshot(path=str(screenshot_path))
            print(f"  [OK] スクリーンショット保存: {screenshot_path}")

            print("\n" + "=" * 70)
            print("  Load Time Results")
            print("=" * 70)

            print(f"\n📊 合計読み込み時間:")
            print(f"  ⏱️  Playwright計測: {total_time:.2f}秒")
            print(f"  ⏱️  ブラウザ計測: {total_page_load/1000:.2f}秒")

            print(f"\n🔍 詳細タイミング:")
            print(f"  DNS解決: {dns_time:.0f}ms")
            print(f"  TCP接続: {tcp_time:.0f}ms")
            print(f"  リクエスト待機: {request_time:.0f}ms")
            print(f"  レスポンス受信: {response_time:.0f}ms")
            print(f"  DOM読み込み: {dom_loading_time:.0f}ms")
            print(f"  DOMインタラクティブ: {dom_interactive_time:.0f}ms")
            print(f"  DOMContentLoaded: {dom_content_loaded_time:.0f}ms")

            if performance['navigationTiming']:
                nav = performance['navigationTiming']
                print(f"\n📈 Navigation Timing API v2:")
                print(f"  DOMContentLoaded処理: {nav['domContentLoaded']:.0f}ms")
                print(f"  Load完了: {nav['loadComplete']:.0f}ms")
                print(f"  総所要時間: {nav['duration']:.0f}ms")

            # 評価
            print(f"\n💡 評価:")
            if total_time < 3:
                print(f"  ✅ 素晴らしい！ ({total_time:.2f}秒)")
            elif total_time < 10:
                print(f"  ⚠️  やや遅い ({total_time:.2f}秒)")
            else:
                print(f"  ❌ 遅い！改善が必要 ({total_time:.2f}秒)")

            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] エラーが発生しました: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'load_time_error.png'
                page.screenshot(path=str(screenshot_path))
                print(f"  エラースクリーンショット: {screenshot_path}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    success = measure_load_time()
    sys.exit(0 if success else 1)
