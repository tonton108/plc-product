"""
テーマ切り替えトランジションの簡易テスト（ログイン不要）
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_transition_simple():
    """テーマ切り替えトランジションを計測（簡易版）"""
    print("=" * 70)
    print("  Theme Transition Test (Simple)")
    print("=" * 70)

    with sync_playwright() as p:
        try:
            print("\nブラウザを起動中...")
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            print("ログインページを開く...")
            page.goto('http://localhost:3000/', timeout=60000)

            print("ログイン中...")
            page.fill('input[type="text"]', 'admin')
            page.fill('input[type="password"]', 'plc-monitor-2025')
            page.click('button:has-text("ログイン")')
            page.wait_for_function('window.location.pathname !== "/login"', timeout=10000)
            time.sleep(2)
            print("設備一覧画面が表示されました")

            print("\n📊 トランジション計測開始（5回テスト）...")
            transition_times = []
            fps_values = []
            drop_counts = []

            for i in range(5):
                print(f"\n[テスト {i+1}/5]")

                # トランジション計測
                result = page.evaluate('''() => {
                    return new Promise((resolve) => {
                        const startTime = performance.now();
                        let frameCount = 0;
                        const frameTimes = [];
                        let lastTime = startTime;

                        function measureFrame() {
                            const now = performance.now();
                            const elapsed = now - startTime;
                            const frameDuration = now - lastTime;

                            if (frameDuration > 0) {
                                frameTimes.push(frameDuration);
                            }
                            lastTime = now;
                            frameCount++;

                            if (elapsed < 450) {
                                requestAnimationFrame(measureFrame);
                            } else {
                                const avgFrameTime = frameTimes.reduce((a,b) => a+b, 0) / frameTimes.length;
                                const fps = 1000 / avgFrameTime;
                                const drops = frameTimes.filter(t => t > 16.67).length;

                                resolve({
                                    time: elapsed,
                                    frames: frameCount,
                                    fps: fps,
                                    drops: drops
                                });
                            }
                        }

                        // テーマ切り替えをシミュレート（v-appの背景色を変更）
                        const app = document.querySelector('.v-application');
                        if (app) {
                            const isDark = app.classList.contains('v-theme--dark');
                            app.classList.toggle('v-theme--dark');
                            app.classList.toggle('v-theme--light');
                            requestAnimationFrame(measureFrame);
                        } else {
                            resolve({error: 'v-applicationが見つかりません'});
                        }
                    });
                }''')

                if 'error' not in result:
                    transition_times.append(result['time'])
                    fps_values.append(result['fps'])
                    drop_counts.append(result['drops'])

                    print(f"  所要時間: {result['time']:.0f}ms")
                    print(f"  FPS: {result['fps']:.1f}")
                    print(f"  フレームドロップ: {result['drops']}")

                time.sleep(0.6)

            # 統計計算
            print("\n" + "=" * 70)
            print("  結果")
            print("=" * 70)

            avg_time = sum(transition_times) / len(transition_times)
            avg_fps = sum(fps_values) / len(fps_values)
            avg_drops = sum(drop_counts) / len(drop_counts)

            print(f"\n⏱️  トランジション時間:")
            print(f"  平均: {avg_time:.0f}ms")
            print(f"  目標: 400ms")
            print(f"  差: {avg_time - 400:+.0f}ms")

            print(f"\n🎬 パフォーマンス:")
            print(f"  平均FPS: {avg_fps:.1f}")
            print(f"  平均フレームドロップ: {avg_drops:.1f}")

            # 評価
            print(f"\n💡 評価:")
            if abs(avg_time - 400) < 50:
                print(f"  ✅ 時間: 良好")
            else:
                print(f"  ⚠️  時間: ズレあり")

            if avg_drops < 2:
                print(f"  ✅ スムーズさ: 非常に滑らか")
            elif avg_drops < 5:
                print(f"  ⚠️  スムーズさ: 概ね滑らか")
            else:
                print(f"  ❌ スムーズさ: カクつきあり")

            score = max(0, 100 - (avg_drops * 5) - (abs(avg_time - 400) / 10))
            print(f"\n🌟 スコア: {score:.1f}/100")

            print("\nブラウザは5秒後に閉じます...")
            time.sleep(5)
            browser.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            try:
                browser.close()
            except:
                pass
            return False

if __name__ == '__main__':
    success = test_transition_simple()
    sys.exit(0 if success else 1)
