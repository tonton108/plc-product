"""i18n辞書統合の多言語スモーク（リポジトリ衛生・ロケール辞書重複解消の回帰確認）

ルート locales/ を廃し i18n/locales/ に一本化した後も、
- ルート限定だったキー（monitoring.realtimeMonitoring 等）が欠落しないこと
- 非デフォルト言語(en/zh)が遅延ロードのみで正しく表示されること（eager import廃止の要確認点）
- 生の i18n キー（"plcConfigEdit." 等）が画面に漏れないこと
をPlaywrightで確認する。

## 前提
- frontend(:3000)/backend(:5000) 起動、設備 TEST_VIEW 登録済み、admin認証シード済み

## 実行
    python scripts/test_i18n_smoke.py
"""
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
API = "http://127.0.0.1:5000"
EQUIP = "TEST_VIEW"

# 言語ごとの期待文字列（左=monitoring.realtimeMonitoring[旧ルート限定], 右=plcConfigEdit.tab[i18n/locales由来]）
EXPECT = {
    "ja": ("リアルタイム監視", "PLC設定"),
    "en": ("Real-time Monitoring", "PLC Config"),
    "zh": ("实时监控", "PLC设置"),
}


def get_token():
    d = json.dumps({"username": "admin", "password": "admin123!"}).encode()
    r = urllib.request.Request(API + "/api/auth/login", data=d,
                               headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(r).read())["token"]


def main():
    token = get_token()
    all_ok = True
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for lang, (btn_text, tab_text) in EXPECT.items():
            ctx = browser.new_context()
            ctx.add_init_script(
                f"localStorage.setItem('plc_auth_token', {json.dumps(token)});"
                "localStorage.setItem('plc_auth_user', '{\"username\":\"admin\",\"role\":\"admin\"}');"
            )
            # 言語切替: i18n cookie（detectBrowserLanguage.useCookie, cookieKey=i18n_redirected）
            ctx.add_cookies([{"name": "i18n_redirected", "value": lang,
                              "url": FRONTEND}])
            page = ctx.new_page()
            page.goto(f"{FRONTEND}/equipment/{EQUIP}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            # inner_textはCSS text-transform適用後（Vuetifyボタンは大文字化）を返すため、
            # 大小文字を無視して比較する
            body = page.inner_text("body")
            lo = body.lower()

            btn_ok = btn_text.lower() in lo      # 旧ルート限定キーが生きているか
            tab_ok = tab_text.lower() in lo      # plcConfigEditキーが出るか
            # 生キー漏れ（未翻訳）チェック
            leak = ("plcconfigedit." in lo) or ("monitoring.realtime" in lo)
            ok = btn_ok and tab_ok and not leak
            all_ok = all_ok and ok
            print(f"[{lang}] btn({btn_text})={btn_ok}  tab({tab_text})={tab_ok}  "
                  f"生キー漏れ={leak}  -> {'PASS' if ok else 'FAIL'}")
            ctx.close()
        browser.close()
    print("RESULT:", "PASS" if all_ok else "FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
