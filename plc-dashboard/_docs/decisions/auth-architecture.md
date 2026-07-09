# 認証アーキテクチャの設計判断（Phase 1）

**作成日:** 2026-07-10
**ステータス:** 採用・実装済み

## 決定内容

| 項目 | 決定 |
|---|---|
| ユーザー認証（ブラウザ→サーバー） | **Bearerトークン方式**（`Authorization: Bearer <token>`） |
| トークンの実体 | **DB保存の不透明トークン**（`secrets.token_urlsafe(32)`、SHA-256ハッシュのみ保存、24時間期限） |
| エージェント認証（ラズパイ→サーバー） | **APIキー方式**（`X-API-Key`ヘッダ、SHA-256ハッシュ保存、設備紐付けnullable） |
| パスワードハッシュ | Werkzeug `generate_password_hash`（PBKDF2-SHA256） |
| ロール | admin / operator の2つ（SPEC.md §4.1） |
| ユーザー管理 | 当面CLI（`flask auth ...`）、最終形はトレイアプリのadmin画面（SPEC.md §3.1） |

## なぜCookieセッションではなくBearerトークンか

現状把握（2026-07-10調査）で確認した構成が決め手:

1. **フロントはクロスオリジン直叩き**: Nuxtは`ssr:false`の静的SPA でプロキシ機構がなく、ブラウザから `http://<サーバーIP>:5000` へ直接fetchする。Cookie方式だと全fetchに`credentials:'include'`、CORSに`supports_credentials=True`＋具体的origin指定が必要
2. **LAN内HTTP運用**: 閲覧クライアントは工場内の複数端末からHTTPでアクセスする（SPEC.md §1）。クロスサイトCookieに必要な`SameSite=None`は`Secure`属性（=HTTPS）が前提であり、HTTP運用と根本的に相性が悪い
3. **Socket.IOとの整合**: トークンなら`io(url, { auth: { token } })`でハンドシェイクにそのまま載る

## なぜJWTではなくDB保存の不透明トークンか

- **即時失効ができる**: ログアウト・ユーザー無効化・パスワード変更で該当トークンをDBから消すだけ。JWTは失効リスト等の追加機構が要る
- **追加依存なし**: Flask-JWT-Extended等の新規ライブラリが不要
- **規模的に問題ない**: 閲覧クライアントは10〜20台想定（SPEC.md §1）。リクエスト毎のDB照合（インデックス付きハッシュの一意検索）は無視できるコスト

## 認可の3デコレータ（backend/api/auth_service.py）

| デコレータ | 用途 | 対象例 |
|---|---|---|
| `require_user(role=None)` | 人間専用 | 設備一覧・ログ閲覧（全ユーザー）、`/api/admin/*`（admin） |
| `require_api_key` | エージェント専用 | `POST /api/logs`、`POST /api/register`、エラー/アラーム報告 |
| `require_user_or_api_key(role=None)` | 両方が使う | 設備設定のGET/PUT（PUTのユーザー側はadmin限定） |

`/api/health` のみ無認証（死活監視用）。

## セキュリティ上の要点

- トークン・APIキーとも**平文はDBに保存しない**（SHA-256ハッシュ）。平文は発行時のレスポンス/CLI出力でのみ得られる
- ログイン失敗時は「ユーザー不存在」と「パスワード誤り」を同じ401にする（ユーザー名列挙の防止）
- `SECRET_KEY` の弱い固定デフォルト（`dev-secret-key`）を廃止。未設定時は起動ごとのランダム値＋警告ログ（トークンはDB照合方式のためSECRET_KEYに依存しない）
- パスワード変更・ユーザー無効化時は当該ユーザーの全トークンを失効

## 見送ったこと（将来課題）

- ログインAPIのレート制限（ブルートフォース対策）— イントラネット前提で優先度を下げた。Phase 4のインストーラー整備時に再検討
- トークンのスライディング延長（現状は24時間の絶対期限）
- フロントのトークン保存先はlocalStorage（XSS耐性はhttpOnly Cookieに劣るが、クロスオリジンHTTP構成の制約から採用。CSP導入等は将来課題）

## 関連

- `docs/SPEC.md` §4（認証・セキュリティ）
- `backend/db/models/auth.py` / `backend/api/auth_service.py` / `backend/api/routes/auth.py` / `backend/api/cli.py`
- `composables/useAuth.ts` / `composables/useApi.ts` / `middleware/auth.global.ts`
