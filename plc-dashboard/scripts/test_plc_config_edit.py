"""PLC設定編集UIのE2Eテスト（Issue #15 の確認）

設備詳細ページ（/equipment/<id>）の「PLC設定」タブで、PLCデータ項目を
追加→保存し、APIに永続化されることをPlaywrightで確認する。
併せて word_order（32bitワード順序）が float32 選択時にプルダウン表示されることを見る。

## 前提データ（このスクリプトは検証のみ・データ投入はしない）
1. 認証: `flask auth seed --admin-password admin123! --api-key <key>`
2. 設備 TEST_VIEW を登録（PLC設定は空でも可）

## 実行
    pip install playwright && python -m playwright install chromium
    python scripts/test_plc_config_edit.py

期待: 追加した項目が保存後もAPI GET /plc_configs に含まれ、
      float32選択時にword_orderセレクトが表示される。
"""
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
API = "http://127.0.0.1:5000"
EQUIP = "TEST_VIEW"
# テストで追加する一意な内部キー（既存と衝突しないよう固定文字列）
NEW_KEY = "e2e_probe_x"


def get_token():
    d = json.dumps({"username": "admin", "password": "admin123!"}).encode()
    r = urllib.request.Request(API + "/api/auth/login", data=d,
                               headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(r).read())["token"]


def get_configs(token):
    r = urllib.request.Request(f"{API}/api/equipment/{EQUIP}/plc_configs",
                               headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(r).read())


def main():
    token = get_token()

    # 事前クリーンアップ: 前回のテスト項目が残っていれば除去（全件PUTで置換）
    before = [c for c in get_configs(token) if c.get("data_type") != NEW_KEY]
    req = urllib.request.Request(
        f"{API}/api/equipment/{EQUIP}/plc_configs",
        data=json.dumps(before).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT")
    urllib.request.urlopen(req)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        ctx.add_init_script(
            f"localStorage.setItem('plc_auth_token', {json.dumps(token)});"
            "localStorage.setItem('plc_auth_user', '{\"username\":\"admin\",\"role\":\"admin\"}');"
        )
        page = ctx.new_page()
        page.goto(f"{FRONTEND}/equipment/{EQUIP}", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # PLC設定タブへ
        page.get_by_role("tab", name="PLC設定").click()
        page.wait_for_timeout(500)

        # 「項目を追加」→ ダイアログ入力
        page.get_by_test_id("add-plc-config").click()
        page.wait_for_timeout(300)
        page.get_by_label("項目名").fill("E2Eプローブ")
        page.get_by_label("内部キー").fill(NEW_KEY)
        page.get_by_label("アドレス").fill("D500")

        # データ型を float32 に変更 → word_orderセレクトが出ること
        # Vuetifyのv-selectはget_by_labelだと非表示inputを指しクリック不可なため
        # フィールドコンテナ(.v-select)をhas_textで特定してクリックする
        page.locator(".v-select").filter(has_text="データ型").click()
        page.wait_for_timeout(300)
        page.get_by_role("option", name="float32 (32bit)").click()
        page.wait_for_timeout(400)
        # word_orderは32bit選択時のみ描画される（v-if）。コンテナ有無で判定
        word_order_visible = page.locator(".v-select").filter(has_text="ワード順序").count() >= 1
        print("word_orderセレクト表示(float32時):", word_order_visible)

        # OKでローカル反映 → 保存
        page.get_by_role("button", name="OK").click()
        page.wait_for_timeout(300)
        page.get_by_test_id("save-plc-config").click()
        page.wait_for_timeout(1500)

        # 永続化をAPIで確認
        after = get_configs(token)
        saved = next((c for c in after if c.get("data_type") == NEW_KEY), None)
        persisted = saved is not None
        addr_ok = bool(saved) and saved.get("address") == "D500"
        type_ok = bool(saved) and saved.get("plc_data_type") == "float32"
        print("保存後にAPIへ永続化:", persisted, "  address=D500:", addr_ok, "  float32:", type_ok)

        # 重複する内部キーは弾かれること（ダイアログが閉じない＝反映されない）
        page.get_by_test_id("add-plc-config").click()
        page.wait_for_timeout(300)
        page.get_by_label("内部キー").fill(NEW_KEY)  # 既存キーと重複
        page.get_by_role("button", name="OK").click()
        page.wait_for_timeout(500)
        # 重複時はconfigDialogがtrueのまま＝内部キー入力欄が見えている
        dup_blocked = page.get_by_label("内部キー").is_visible()
        print("重複キーをブロック(ダイアログ継続):", dup_blocked)

        ok = word_order_visible and persisted and addr_ok and type_ok and dup_blocked
        print("RESULT:", "PASS" if ok else "FAIL")
        browser.close()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
