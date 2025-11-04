"""
Docker再起動から初回アクセスまでの時間を計測
"""
import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess
import time

# Windows環境でのUnicode出力問題を回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def measure_docker_startup():
    """Docker再起動から初回アクセスまでの時間を計測"""
    print("=" * 70)
    print("  Docker Restart → First Access Time Measurement")
    print("=" * 70)

    try:
        # 1. フロントエンドコンテナを再起動
        print("\n[1/5] フロントエンドコンテナを再起動中...")
        restart_start = time.time()

        result = subprocess.run(
            ['docker', 'compose', 'restart', 'frontend'],
            cwd='D:/plc-product/plc-dashboard',
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        restart_end = time.time()
        restart_time = restart_end - restart_start

        print(f"  [OK] コンテナ再起動完了: {restart_time:.2f}秒")

        # 2. Dockerログを監視してビルド完了を待つ
        print("\n[2/5] Nuxtビルド完了を待機中...")
        build_start = time.time()

        max_wait = 60  # 最大60秒待つ
        while time.time() - build_start < max_wait:
            logs_result = subprocess.run(
                ['docker', 'compose', 'logs', '--tail=5', 'frontend'],
                cwd='D:/plc-product/plc-dashboard',
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if logs_result.stdout and 'Vite client built' in logs_result.stdout and 'Vite server built' in logs_result.stdout:
                build_end = time.time()
                build_time = build_end - build_start
                print(f"  [OK] Nuxtビルド完了: {build_time:.2f}秒")
                break

            time.sleep(1)
        else:
            print(f"  [WARNING] ビルド完了を検出できませんでした（{max_wait}秒経過）")
            build_time = max_wait

        # 3. 少し待機（サーバーが完全に起動するまで）
        print("\n[3/5] サーバー起動完了を待機中...")
        time.sleep(3)

        # 4. ブラウザで初回アクセス
        print("\n[4/5] ブラウザで初回アクセス中...")
        access_start = time.time()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # タイムアウトを120秒に設定
            page.goto('http://localhost:3000/', wait_until='networkidle', timeout=120000)

            access_end = time.time()
            access_time = access_end - access_start

            print(f"  [OK] ページ読み込み完了: {access_time:.2f}秒")

            # 5. スクリーンショット撮影
            print("\n[5/5] スクリーンショット撮影中...")
            screenshot_path = Path(__file__).parent / 'docker_startup_screenshot.png'
            page.screenshot(path=str(screenshot_path))
            print(f"  [OK] スクリーンショット保存: {screenshot_path}")

            # 総計時間
            total_time = access_end - restart_start

            print("\n" + "=" * 70)
            print("  Timing Results")
            print("=" * 70)

            print(f"\n⏱️  各ステップの所要時間:")
            print(f"  1️⃣  Docker再起動: {restart_time:.2f}秒")
            print(f"  2️⃣  Nuxtビルド: {build_time:.2f}秒")
            print(f"  3️⃣  初回アクセス: {access_time:.2f}秒")
            print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"  📊 合計時間: {total_time:.2f}秒")

            # 評価
            print(f"\n💡 評価:")
            if total_time < 20:
                print(f"  ✅ 許容範囲内 ({total_time:.2f}秒)")
            elif total_time < 40:
                print(f"  ⚠️  やや遅い ({total_time:.2f}秒)")
            else:
                print(f"  ❌ 遅すぎる！改善が必要 ({total_time:.2f}秒)")

            print(f"\n📝 内訳:")
            print(f"  - Docker再起動は避けられない処理です")
            print(f"  - Nuxtビルドは初回のみ発生します（2回目以降は高速）")
            print(f"  - 初回アクセスは依存関係のダウンロードを含みます")

            print("\nブラウザは5秒後に自動的に閉じます...")
            time.sleep(5)
            browser.close()

            return True

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = measure_docker_startup()
    sys.exit(0 if success else 1)
