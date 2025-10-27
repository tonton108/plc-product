"""
E2Eデプロイメントテスト
ラズパイと中央サーバーのデータフローを統合的にテストします

テストシナリオ:
1. 環境確認（Docker、ポート）
2. Docker Composeで中央サーバー起動（DB + Backend + Frontend）
3. Raspberry Pi Agentを起動（ダミーPLCモード）
4. データフロー確認（Agent → Backend → Frontend）
5. モニタリング画面での表示確認
"""

import os
import sys
import time
import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# カラー出力用のANSIコード
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(message):
    """ヘッダーメッセージを表示"""
    print(f"\n{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 70}{Colors.ENDC}")

def print_step(step_num, message):
    """ステップメッセージを表示"""
    print(f"\n{Colors.OKBLUE}[STEP {step_num}] {message}{Colors.ENDC}")

def print_success(message):
    """成功メッセージを表示"""
    print(f"{Colors.OKGREEN}[OK] {message}{Colors.ENDC}")

def print_error(message):
    """エラーメッセージを表示"""
    print(f"{Colors.FAIL}[ERROR] {message}{Colors.ENDC}")

def print_warning(message):
    """警告メッセージを表示"""
    print(f"{Colors.WARNING}[WARNING] {message}{Colors.ENDC}")

def print_info(message):
    """情報メッセージを表示"""
    print(f"{Colors.OKCYAN}[INFO] {message}{Colors.ENDC}")

def check_docker():
    """Dockerが起動しているか確認"""
    print_step(1, "Docker環境の確認")
    try:
        result = subprocess.run(
            ['docker', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print_success("Dockerが起動しています")
            return True
        else:
            print_error("Dockerが起動していません")
            return False
    except FileNotFoundError:
        print_error("Dockerがインストールされていません")
        return False
    except Exception as e:
        print_error(f"Docker確認エラー: {e}")
        return False

def check_port_available(port, service_name):
    """ポートが使用可能か確認"""
    try:
        # Windowsの場合はnetstatを使用
        result = subprocess.run(
            ['netstat', '-an'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if f":{port}" in result.stdout:
            print_warning(f"ポート{port}は既に使用中です（{service_name}）")
            return False
        else:
            print_success(f"ポート{port}は使用可能です（{service_name}）")
            return True
    except Exception as e:
        print_warning(f"ポート確認エラー: {e}")
        return True  # エラー時は続行

def check_ports():
    """必要なポートが使用可能か確認"""
    print_step(2, "ポートの確認")
    ports = {
        5433: "PostgreSQL",
        5000: "Backend API",
        3000: "Frontend UI",
        5001: "Raspberry Pi Agent"
    }

    all_available = True
    for port, service in ports.items():
        if not check_port_available(port, service):
            all_available = False

    return all_available

def start_docker_services():
    """Docker Composeでサービスを起動"""
    print_step(3, "中央サーバーの起動（Docker Compose）")

    # プロジェクトルートに移動
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print_info("サービスを起動中...")
    print_info("  - PostgreSQL (ポート5433)")
    print_info("  - Flask Backend (ポート5000)")
    print_info("  - Nuxt Frontend (ポート3000)")

    try:
        # サービスを起動（detachedモード）
        result = subprocess.run(
            ['docker', 'compose', 'up', '-d', 'db', 'backend', 'frontend'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print_success("Docker Composeサービスが起動しました")
            print_info("起動完了を待機中... (30秒)")
            time.sleep(30)  # サービスの起動を待機
            return True
        else:
            print_error(f"Docker Compose起動エラー: {result.stderr}")
            return False

    except Exception as e:
        print_error(f"Docker Compose起動エラー: {e}")
        return False

def check_backend_health():
    """Backendのヘルスチェック"""
    print_step(4, "Backend APIのヘルスチェック")

    backend_url = "http://localhost:5000/api/equipment"
    max_retries = 10
    retry_interval = 3

    for i in range(max_retries):
        try:
            print_info(f"接続試行 {i+1}/{max_retries}...")
            response = requests.get(backend_url, timeout=5)
            if response.status_code == 200:
                print_success("Backend APIが正常に応答しています")
                return True
        except requests.exceptions.RequestException as e:
            if i < max_retries - 1:
                print_warning(f"接続失敗、{retry_interval}秒後に再試行...")
                time.sleep(retry_interval)
            else:
                print_error(f"Backend APIに接続できません: {e}")
                return False

    return False

def check_frontend_health():
    """Frontendのヘルスチェック"""
    print_step(5, "Frontend UIのヘルスチェック")

    frontend_url = "http://localhost:3000"
    max_retries = 10
    retry_interval = 3

    for i in range(max_retries):
        try:
            print_info(f"接続試行 {i+1}/{max_retries}...")
            response = requests.get(frontend_url, timeout=5)
            if response.status_code == 200:
                print_success("Frontend UIが正常に応答しています")
                return True
        except requests.exceptions.RequestException as e:
            if i < max_retries - 1:
                print_warning(f"接続失敗、{retry_interval}秒後に再試行...")
                time.sleep(retry_interval)
            else:
                print_error(f"Frontend UIに接続できません: {e}")
                return False

    return False

def test_frontend_rendering():
    """Playwrightでフロントエンドの実レンダリングをテスト"""
    print_step(5.5, "Frontend UI の実レンダリングテスト（Playwright）")

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        print_warning("Playwright未インストール。実レンダリングテストをスキップします。")
        print_info("インストール方法:")
        print_info("  pip install playwright")
        print_info("  playwright install chromium")
        return True  # スキップしてもテスト続行

    print_info("ヘッドレスブラウザでページを開いています...")

    with sync_playwright() as p:
        try:
            # Chromiumをヘッドレスモードで起動
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # JavaScriptエラーを記録
            js_errors = []
            console_errors = []

            def handle_console(msg):
                if msg.type == 'error':
                    console_errors.append(msg.text)
                    print_warning(f"JS Console Error: {msg.text}")

            def handle_page_error(error):
                js_errors.append(str(error))
                print_error(f"Page Error: {error}")

            page.on('console', handle_console)
            page.on('pageerror', handle_page_error)

            # ページを開く
            print_info("http://localhost:3000/ にアクセス中...")
            page.goto('http://localhost:3000/', wait_until='networkidle', timeout=15000)

            # ログインページの要素が表示されるまで待つ（最大10秒）
            print_info("ページのレンダリングを待機中...")
            try:
                # ログインページの特徴的な要素を待つ
                page.wait_for_selector('input[type="password"], .v-card', timeout=10000)
                print_success("ページが正しくレンダリングされました")

                # スクリーンショットを保存
                screenshot_path = Path(__file__).parent / 'frontend_test_screenshot.png'
                page.screenshot(path=str(screenshot_path))
                print_info(f"スクリーンショット保存: {screenshot_path}")

            except PlaywrightTimeout:
                print_error("ページのレンダリングがタイムアウトしました")
                # エラー時もスクリーンショットを保存
                screenshot_path = Path(__file__).parent / 'frontend_error_screenshot.png'
                page.screenshot(path=str(screenshot_path))
                print_info(f"エラースクリーンショット保存: {screenshot_path}")
                browser.close()
                return False

            # JavaScriptエラーチェック
            if js_errors or console_errors:
                print_error(f"JavaScriptエラーが検出されました:")
                for error in js_errors:
                    print_error(f"  - Page Error: {error}")
                for error in console_errors:
                    print_error(f"  - Console Error: {error}")
                browser.close()
                return False

            print_success("JavaScriptエラーなし")
            browser.close()
            return True

        except Exception as e:
            print_error(f"フロントエンドレンダリングテストエラー: {e}")
            try:
                screenshot_path = Path(__file__).parent / 'frontend_exception_screenshot.png'
                page.screenshot(path=str(screenshot_path))
                print_info(f"例外発生時スクリーンショット保存: {screenshot_path}")
            except:
                pass
            try:
                browser.close()
            except:
                pass
            return False

def start_raspi_agent():
    """Raspberry Pi Agentを起動"""
    print_step(6, "Raspberry Pi Agent の起動")

    # プロジェクトルートに移動
    project_root = Path(__file__).parent.parent
    agent_dir = project_root / "raspi_agent"

    print_info("ダミーPLCモードでエージェントを起動中...")
    print_info(f"作業ディレクトリ: {agent_dir}")

    try:
        # 環境変数を設定
        env = os.environ.copy()
        env['USE_DUMMY_PLC'] = 'true'
        env['CENTRAL_SERVER_IP'] = 'localhost'
        env['CENTRAL_SERVER_PORT'] = '5000'
        env['RASPI_UI_PORT'] = '5001'

        # agent_app.pyをバックグラウンドで起動
        # Note: 実際の環境ではsystemdやsupervisorを使用することを推奨
        print_info("エージェントプロセスを起動...")
        print_warning("このテストでは、エージェントを手動で起動してください:")
        print_info(f"  cd {agent_dir}")
        print_info("  set USE_DUMMY_PLC=true")
        print_info("  set CENTRAL_SERVER_IP=localhost")
        print_info("  set CENTRAL_SERVER_PORT=5000")
        print_info("  python agent_app.py")

        # ユーザーに起動を促す
        input("\nエージェントを起動したら、Enterキーを押してください...")

        return True

    except Exception as e:
        print_error(f"Raspberry Pi Agent起動エラー: {e}")
        return False

def check_raspi_agent_health():
    """Raspberry Pi Agentのヘルスチェック"""
    print_step(7, "Raspberry Pi Agent のヘルスチェック")

    agent_url = "http://localhost:5001"
    max_retries = 5
    retry_interval = 2

    for i in range(max_retries):
        try:
            print_info(f"接続試行 {i+1}/{max_retries}...")
            response = requests.get(agent_url, timeout=5)
            if response.status_code == 200 or response.status_code == 302:
                print_success("Raspberry Pi Agentが正常に応答しています")
                return True
        except requests.exceptions.RequestException as e:
            if i < max_retries - 1:
                print_warning(f"接続失敗、{retry_interval}秒後に再試行...")
                time.sleep(retry_interval)
            else:
                print_error(f"Raspberry Pi Agentに接続できません: {e}")
                return False

    return False

def test_data_flow():
    """データフローのテスト"""
    print_step(8, "データフローのテスト")

    # 設備一覧を取得
    print_info("設備一覧を取得中...")
    try:
        response = requests.get("http://localhost:5000/api/equipment", timeout=10)
        if response.status_code == 200:
            equipment_list = response.json()
            print_success(f"設備一覧取得成功: {len(equipment_list)}件")

            if len(equipment_list) > 0:
                # 最初の設備の最新ログを取得
                equipment_id = equipment_list[0].get('equipment_id', 'UNKNOWN')
                print_info(f"設備 '{equipment_id}' の最新ログを取得中...")

                log_response = requests.get(
                    f"http://localhost:5000/api/logs/{equipment_id}/latest",
                    timeout=10
                )

                if log_response.status_code == 200:
                    latest_log = log_response.json()
                    print_success("最新ログ取得成功:")
                    print_info(f"  設備ID: {latest_log.get('equipment_id', 'N/A')}")
                    print_info(f"  タイムスタンプ: {latest_log.get('timestamp', 'N/A')}")

                    # データ項目を表示
                    data = latest_log.get('data', {})
                    if data:
                        print_info("  データ項目:")
                        for key, value in data.items():
                            print_info(f"    - {key}: {value}")

                    return True, equipment_id
                else:
                    print_warning(f"最新ログ取得失敗: HTTP {log_response.status_code}")
                    return False, equipment_id
            else:
                print_warning("設備が登録されていません")
                print_info("Raspberry Pi Agentから初回データを送信してください")
                return False, None
        else:
            print_error(f"設備一覧取得失敗: HTTP {response.status_code}")
            return False, None

    except Exception as e:
        print_error(f"データフロー確認エラー: {e}")
        return False, None

def show_monitoring_instructions(equipment_id):
    """モニタリング画面の表示手順を案内"""
    print_step(9, "モニタリング画面の確認")

    if equipment_id:
        monitoring_url = f"http://localhost:3000/monitoring/{equipment_id}"
        print_success("以下のURLでモニタリング画面を確認できます:")
        print_info(f"  {monitoring_url}")
    else:
        print_warning("設備IDが不明なため、トップページを確認してください:")
        print_info("  http://localhost:3000")

    print_info("\nモニタリング画面で以下を確認してください:")
    print_info("  1. リアルタイムデータがグラフに表示されている")
    print_info("  2. データが定期的に更新されている（2-5秒間隔）")
    print_info("  3. WebSocket接続が確立されている（画面右上に接続ステータス表示）")

def cleanup_services():
    """サービスをクリーンアップ"""
    print_header("クリーンアップ")

    response = input("\nDocker Composeサービスを停止しますか？ (y/n): ")
    if response.lower() == 'y':
        print_info("サービスを停止中...")
        try:
            subprocess.run(
                ['docker', 'compose', 'down'],
                capture_output=True,
                timeout=30
            )
            print_success("サービスを停止しました")
        except Exception as e:
            print_error(f"サービス停止エラー: {e}")

    print_warning("Raspberry Pi Agentは手動で停止してください（Ctrl+C）")

def main():
    """メイン関数"""
    print_header("E2Eデプロイメントテスト開始")
    print_info(f"テスト開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_results = {
        'docker_check': False,
        'port_check': False,
        'docker_services': False,
        'backend_health': False,
        'frontend_health': False,
        'frontend_rendering': False,
        'raspi_agent': False,
        'data_flow': False
    }

    try:
        # STEP 1-2: 環境確認
        test_results['docker_check'] = check_docker()
        if not test_results['docker_check']:
            print_error("Dockerが利用できません。テストを中止します。")
            return False

        test_results['port_check'] = check_ports()
        if not test_results['port_check']:
            print_warning("一部のポートが使用中です。続行しますか？")
            response = input("続行する場合は 'y' を入力してください: ")
            if response.lower() != 'y':
                print_info("テストを中止しました。")
                return False

        # STEP 3: Docker Composeでサービス起動
        test_results['docker_services'] = start_docker_services()
        if not test_results['docker_services']:
            print_error("Docker Composeサービスの起動に失敗しました。")
            return False

        # STEP 4-5: ヘルスチェック
        test_results['backend_health'] = check_backend_health()
        test_results['frontend_health'] = check_frontend_health()

        if not test_results['backend_health'] or not test_results['frontend_health']:
            print_error("サービスのヘルスチェックに失敗しました。")
            print_info("Docker Composeログを確認してください:")
            print_info("  docker compose logs -f backend")
            print_info("  docker compose logs -f frontend")
            return False

        # STEP 5.5: フロントエンド実レンダリングテスト（Playwright）
        test_results['frontend_rendering'] = test_frontend_rendering()
        if not test_results['frontend_rendering']:
            print_warning("フロントエンド実レンダリングテストに失敗しました。")
            print_info("スクリーンショットを確認してください。")
            print_info("続行しますか？ (y/n)")
            response = input()
            if response.lower() != 'y':
                return False

        # STEP 6-7: Raspberry Pi Agent起動とヘルスチェック
        test_results['raspi_agent'] = start_raspi_agent()
        if test_results['raspi_agent']:
            test_results['raspi_agent'] = check_raspi_agent_health()

        if not test_results['raspi_agent']:
            print_warning("Raspberry Pi Agentの起動に失敗しました。")
            print_info("手動で起動してから、データフローテストを続行できます。")

        # STEP 8: データフローテスト
        data_flow_success, equipment_id = test_data_flow()
        test_results['data_flow'] = data_flow_success

        # STEP 9: モニタリング画面の案内
        show_monitoring_instructions(equipment_id)

        # テスト結果のサマリー
        print_header("テスト結果サマリー")

        print(f"  Docker環境: {'✓' if test_results['docker_check'] else '✗'}")
        print(f"  ポート確認: {'✓' if test_results['port_check'] else '✗'}")
        print(f"  Docker起動: {'✓' if test_results['docker_services'] else '✗'}")
        print(f"  Backend API: {'✓' if test_results['backend_health'] else '✗'}")
        print(f"  Frontend UI: {'✓' if test_results['frontend_health'] else '✗'}")
        print(f"  Frontend Rendering: {'✓' if test_results['frontend_rendering'] else '✗'}")
        print(f"  Raspberry Pi Agent: {'✓' if test_results['raspi_agent'] else '✗'}")
        print(f"  データフロー: {'✓' if test_results['data_flow'] else '✗'}")

        all_success = all(test_results.values())

        if all_success:
            print_header("テスト成功")
            print_success("すべてのテストが正常に完了しました")
            print_info("\n次のステップ:")
            print_info("  1. モニタリング画面でリアルタイムデータを確認")
            print_info("  2. 設備設定画面でPLCデータ項目を設定")
            print_info("  3. 履歴データを確認")
        else:
            print_header("テスト一部失敗")
            print_warning("一部のテストが失敗しました。上記の結果を確認してください。")

        return all_success

    except KeyboardInterrupt:
        print_warning("\n\nテストが中断されました（Ctrl+C）")
        return False

    except Exception as e:
        print_error(f"\nテスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print_info(f"\nテスト終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        cleanup_services()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
