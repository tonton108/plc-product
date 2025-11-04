"""
テーマ切り替えトランジションのスムーズさをテスト
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_theme_transition():
    """テーマ切り替えトランジションを計測"""
    print("=" * 70)
    print("  Theme Transition Smoothness Test")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            # ブラウザを起動
            print("\n[1/6] ブラウザを起動中...")
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # ログインページを開く
            print("\n[2/6] ログインページを開く...")
            page.goto('http://localhost:3000/', timeout=15000)

            # ログイン
            print("\n[3/6] ログイン中...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            page.wait_for_function('window.location.pathname !== "/login"', timeout=10000)
            time.sleep(2)
            print(f"  [OK] ログイン成功")

            # テーマ切り替えボタンを取得
            theme_button = page.locator('button[aria-describedby*="tooltip"]').first

            # トランジション時間を計測（複数回）
            print("\n[4/6] トランジション時間を計測中...")
            transition_times = []
            frame_drops = []

            for i in range(5):
                print(f"\n  テスト {i+1}/5:")

                # トランジション開始前のスクリーンショット
                if i == 0:
                    screenshot_before = Path(__file__).parent / 'transition_before.png'
                    page.screenshot(path=str(screenshot_before))

                # Performance APIでトランジション計測
                result = page.evaluate('''() => {
                    return new Promise((resolve) => {
                        const startTime = performance.now();
                        let frameCount = 0;
                        let lastFrameTime = startTime;
                        const frameTimes = [];

                        // トランジション開始
                        const themeButton = document.querySelector('button[aria-describedby*="tooltip"]');

                        // アニメーションフレームをカウント
                        function checkFrame() {
                            const currentTime = performance.now();
                            const frameDuration = currentTime - lastFrameTime;
                            frameTimes.push(frameDuration);
                            lastFrameTime = currentTime;
                            frameCount++;

                            // 400ms経過したか確認
                            if (currentTime - startTime < 450) {
                                requestAnimationFrame(checkFrame);
                            } else {
                                const endTime = performance.now();
                                const totalTime = endTime - startTime;

                                // フレームレート計算
                                const avgFrameTime = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
                                const fps = 1000 / avgFrameTime;

                                // フレームドロップ検出（16.67ms = 60fps超過したフレーム）
                                const droppedFrames = frameTimes.filter(t => t > 16.67).length;

                                resolve({
                                    totalTime: totalTime,
                                    frameCount: frameCount,
                                    fps: fps,
                                    droppedFrames: droppedFrames,
                                    avgFrameTime: avgFrameTime
                                });
                            }
                        }

                        // ボタンをクリック
                        if (themeButton) {
                            themeButton.click();
                            requestAnimationFrame(checkFrame);
                        } else {
                            resolve({error: 'ボタンが見つかりません'});
                        }
                    });
                }''')

                if 'error' in result:
                    print(f"    [ERROR] {result['error']}")
                    continue

                transition_times.append(result['totalTime'])
                frame_drops.append(result['droppedFrames'])

                print(f"    所要時間: {result['totalTime']:.0f}ms")
                print(f"    フレーム数: {result['frameCount']}")
                print(f"    平均FPS: {result['fps']:.1f}")
                print(f"    フレームドロップ: {result['droppedFrames']}")
                print(f"    平均フレーム時間: {result['avgFrameTime']:.2f}ms")

                # トランジション完了後のスクリーンショット
                if i == 0:
                    time.sleep(0.5)
                    screenshot_after = Path(__file__).parent / 'transition_after.png'
                    page.screenshot(path=str(screenshot_after))

                # 次のテストのために少し待機
                time.sleep(0.5)

            # 統計情報を計算
            print("\n[5/6] 統計情報を計算中...")
            avg_time = sum(transition_times) / len(transition_times)
            min_time = min(transition_times)
            max_time = max(transition_times)
            avg_drops = sum(frame_drops) / len(frame_drops)

            # 最終スクリーンショット
            print("\n[6/6] スクリーンショット撮影中...")
            screenshot_final = Path(__file__).parent / 'transition_final.png'
            page.screenshot(path=str(screenshot_final))
            print(f"  [OK] スクリーンショット保存")

            print("\n" + "=" * 70)
            print("  Test Results")
            print("=" * 70)

            print(f"\n📊 トランジション時間:")
            print(f"  平均: {avg_time:.0f}ms")
            print(f"  最速: {min_time:.0f}ms")
            print(f"  最遅: {max_time:.0f}ms")
            print(f"  設定値: 400ms")

            print(f"\n🎬 フレームドロップ:")
            print(f"  平均: {avg_drops:.1f}フレーム")

            print(f"\n💡 評価:")

            # 時間の評価
            if abs(avg_time - 400) < 50:
                print(f"  ✅ トランジション時間: 良好（設定値に近い）")
            else:
                print(f"  ⚠️  トランジション時間: ズレあり（{avg_time - 400:.0f}ms差）")

            # フレームドロップの評価
            if avg_drops < 2:
                print(f"  ✅ フレームドロップ: ほぼなし（滑らか）")
            elif avg_drops < 5:
                print(f"  ⚠️  フレームドロップ: 少しあり")
            else:
                print(f"  ❌ フレームドロップ: 多い（カクカクする可能性）")

            # スムーズさの総合評価
            smoothness_score = 100 - (avg_drops * 5) - (abs(avg_time - 400) / 10)
            print(f"\n🌟 スムーズさスコア: {smoothness_score:.1f}/100")

            if smoothness_score >= 90:
                print(f"  ✅ 非常にスムーズ！")
            elif smoothness_score >= 70:
                print(f"  ⚠️  概ねスムーズ")
            else:
                print(f"  ❌ 改善が必要")

            print(f"\n📸 スクリーンショット:")
            print(f"  1. 切り替え前: {screenshot_before if 'screenshot_before' in locals() else 'N/A'}")
            print(f"  2. 切り替え後: {screenshot_after if 'screenshot_after' in locals() else 'N/A'}")
            print(f"  3. 最終: {screenshot_final}")

            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            try:
                screenshot_path = Path(__file__).parent / 'transition_test_error.png'
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
    success = test_theme_transition()
    sys.exit(0 if success else 1)
