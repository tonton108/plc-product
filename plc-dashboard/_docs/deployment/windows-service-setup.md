# Windowsサービス化 設計（Phase 4 Increment 1）

**ステータス:** 設計確定（2026-07-13レビュー承認済み）・実装着手
**確定した決定（§11 A〜E）:** A=viewer(Flask)が静的SPAも配信しAPIベースは相対パス /
B=相対パス化でLAN IP焼込不要 / C=Shawl / D=`C:\ProgramData\plc-monitor\.env`(ACL) /
E=既存ネイティブPostgres(5432)に新規`plc_monitor`を立て migrate+seed（devデータ移行なし）
**対象:** 中央サーバーPC 1台に、本番サービング（ingest/viewer 2プロセス＋Redis）を
**Dockerなし**でWindowsサービスとして常駐させる。SPEC §3.1 の実体化の第一歩。
**関連:** `SPEC.md` §3.1/§10、`backend/serve_production.py`、
`_docs/decisions/wsgi-serving-load-verification.md`（負荷検証でingest分離を確定）

> このIncrementのゴールは「**一番不確実なサービス常駐＋配信をこの実機で通す**」こと。
> ここを通せば、残りのPhase 4（インストーラ.exe化・Electronトレイアプリ・desktop-app廃止）は
> 部品の組み立て作業になる。

---

## 1. スコープ

### やる（Increment 1）
- ネイティブ資産の利用: **PostgreSQL 18**（既にサービス稼働中・5432）
- **Memurai Developer**（Redis 7互換・ネイティブWindows）の導入とサービス化
- **Shawl**（サービスラッパー）で `serve_production.py` を ingest/viewer 2サービス登録
- 起動順・自動再起動・ログ出力・接続経路の確立
- セットアップPowerShell群と本ドキュメントを成果物として残す（＝将来インストーラの部品）

### やらない（後続Increment）
- インストーラ `.exe` 化（Inno Setup / WiX）
- Electronトレイアプリ（サービス管理＋admin画面）
- `desktop-app/` 廃止
- Postgres/Memuraiの**同梱**（今回は既存インストールを使う。同梱＝インストーラ工程で対応）

---

## 2. サービス構成と依存順

```
[Windows起動]
   │
   ▼
(1) postgresql-x64-18   … 既存。Automatic。DB本体（5432）
   │  depends
   ▼
(2) Memurai (Redis)     … 新規。Automatic。SocketIO message_queue（6379）
   │  depends
   ▼
(3) plc-ingest          … 新規(Shawl)。エージェントのPOST受け口（5000）
(4) plc-viewer          … 新規(Shawl)。閲覧のSocket.IO＋読み取りAPI（5001）
   │  depends（フロントの静的ファイルはviewerが配信する案＝§4）
   ▼
(5) plc-frontend        … 【要決定】静的SPA配信（§4で方式を選ぶ）
```

**依存順の担保:** Shawlはネイティブに依存関係を持たないため、Windowsサービスの
`depend`（`sc.exe config <svc> depend= <other>`）で (1)→(2)→(3)(4) を宣言する。
加えて各プロセスは起動時にDB/Redis未達なら**リトライして待つ**か、Shawlの
自動再起動（失敗→再起動）で吸収する。※起動直後のDB/Redis未応答は再起動で回復させる方針。

---

## 3. 各サービス定義（案）

| サービス | 起動コマンド（概念） | ポート/バインド | 主要env | 依存 |
|---|---|---|---|---|
| Memurai | Memuraiインストーラがサービス登録 | `127.0.0.1:6379`（LAN公開不要） | — | postgres |
| plc-ingest | `python serve_production.py` | `0.0.0.0:5000` | `ROLE=ingest` `PORT=5000` `DATABASE_URL` `SECRET_KEY` `SOCKETIO_MESSAGE_QUEUE` | memurai |
| plc-viewer | `python serve_production.py` | `0.0.0.0:5001` | `ROLE=viewer` `PORT=5001` `DATABASE_URL` `SECRET_KEY` `SOCKETIO_MESSAGE_QUEUE` `CORS_ORIGINS` | memurai |
| plc-frontend | §4で決定 | `0.0.0.0:3000` | （静的・APIベースはビルド時に焼込） | viewer |

- **バインドは `0.0.0.0`**（工場内LANの他端末＝ブラウザ/ラズパイからアクセスするため）。
- **Redisは `127.0.0.1` バインド**（同一PC内のプロセス間共有のみ。外部公開しない）。
- `serve_production.py` は既に `HOST`/`PORT`/`ROLE`/`WAITRESS_THREADS`/`SOCKETIO_MESSAGE_QUEUE` をenv読み取り済み。**コード改修は原則不要**。

---

## 4. 接続経路（データフロー）と【要決定：フロント配信】

```
ラズパイagent ──POST /api/logs────────────▶ plc-ingest(5000)
                                              │ emit（Redis message_queue経由）
                                              ▼
ブラウザ ──Socket.IO(long-poll)/読み取りAPI──▶ plc-viewer(5001)
ブラウザ ──GET / (UI本体)──────────────────▶ plc-frontend(3000, 静的SPA)
```

- エージェント: `CENTRAL_SERVER_PORT=5000`（ingest）へ送信。
- ブラウザ: UIを 3000 から取得し、API/Socket.IO は 5001（viewer）へ。
- **リバースプロキシは今回は置かない**（ポート直指定でシンプルに。将来80番集約が要れば別途）。

### 【決定 A（確定）】フロントSPAは viewer(Flask) が配信
Nuxtは `ssr:false`＋nitro static（`.output/public` に静的出力）。
**viewer(Flask)が `.output/public` を静的配信する**（追加の静的サービスを立てない）。
- 実装: viewer起動時、Flaskの静的配信 or catch-allルートで `.output/public/index.html` を返す
  （SPAなので未知パスは `index.html` にフォールバック）。ビルド成果物のパスは設定で渡す。
- UIとAPI/Socket.IOが**同一オリジン(5001)** になる。

### 【決定 B（確定）】APIベースは相対パス（IP焼込不要）
UIとAPIが同一オリジンになるため、`NUXT_PUBLIC_API_BASE=''`（相対）でビルドする。
- `composables/useApi.ts`: `apiBase` が空なら**同一オリジン相対**でfetch（現状は空だと
  `'http://localhost:5000'` にフォールバックするので、空文字を許容するよう調整が要る）。
- `plugins/socket.io.client.ts`: Socket.IO接続先も空なら**現在のオリジン**へ（同5001）。
- 結果、中央サーバーのLAN IPをビルドに焼き込む必要が消える（どの端末からでも自分が開いた
  オリジンにAPIを打つ）。→ **コード改修が必要**（§1の「原則不要」に対する例外）。

---

## 5. Redis（Memurai）配線

- `SOCKETIO_MESSAGE_QUEUE=redis://127.0.0.1:6379/0` を ingest/viewer 両サービスに設定。
- ingest側の `emit`（新ログの配信）が Redis 経由で viewer 側の設備別roomへ届く
  （`_docs/decisions/wsgi-serving-load-verification.md` で実測済み: ingest 279req/s・配信100%）。
- 未設定なら単一プロセス動作にフォールバック（小規模用）。本構成では**必須**。

---

## 6. PostgreSQL（今回は既存ネイティブを利用）

- 既存 `postgresql-x64-18`（5432）を使う。将来インストーラは Postgres を**同梱**し
  `initdb` 時に `--auth`（trust回避）・`--encoding=UTF8`・`--locale` を明示（SPEC §10）。
- Increment 1のセットアップ手順（＝将来インストーラが自動化する予行）:
  1. ロール/DB作成: `plc_user` / `plc_monitor`（パスワードは生成。弱いデフォルト禁止）
  2. `DATABASE_URL=postgresql+psycopg2://plc_user:<pw>@127.0.0.1:5432/plc_monitor`
  3. `flask --app manage.py db upgrade`（マイグレーション適用）
  4. `flask --app manage.py auth seed --admin-password <生成> --api-key <生成>`
- ※現状のDocker Postgres(5433)とはポートが別。データ移行は本Incrementの対象外
  （新規DBを立てて検証する。既存devデータは移さない）。

---

## 7. Shawl によるサービス登録（方針）

Shawlは「任意のコマンドをWindowsサービス化」するラッパー。登録の骨子:

```
shawl add --name plc-ingest ^
  --cwd "C:\path\to\backend" ^
  --log-dir "C:\ProgramData\plc-monitor\logs" ^
  --restart ^                # 失敗時に自動再起動
  -- python serve_production.py
# 環境変数はサービスのレジストリEnvironment、または .env ローダで注入
```

- **自動再起動:** Shawlの再起動ポリシーで、DB/Redis起動前に立ち上がった場合も回復。
- **ログ:** Shawlの `--log-dir` でstdout/stderrをファイル出力（ローテーションは
  Shawl設定 or 別途。NSSMのログローテ相当をどう満たすか要確認）。
- **依存:** `sc.exe config plc-ingest depend= Memurai/postgresql-x64-18`。
- **環境変数の渡し方（要確認）:** サービス実行時のenv注入は
  (a) Shawlの `--env`/環境変数、(b) サービスのレジストリ、(c) backend側で`.env`を読む、の
  いずれか。秘密情報（SECRET_KEY/DBパス）を平文でどこに置くかは§9で扱う。

**代替:** NSSM（SPEC第一候補・2017最終リリースだが実績豊富）。Shawlで詰まればNSSMに切替。

---

## 8. localhost / IPv6 の罠（既知・必ず守る）

`_docs/decisions/wsgi-serving-load-verification.md` の教訓:
- **Windowsで接続先に `localhost` を使うと IPv6 `::1` を先に試み、Waitressが一律2秒遅延する。**
  → プロセス間・ローカル接続は必ず **`127.0.0.1`** を使う（`DATABASE_URL`・`SOCKETIO_MESSAGE_QUEUE`とも）。
- Windowsでのプロセス掃除は `pkill` 不可 → `Get-NetTCPConnection` → `Stop-Process`。

---

## 9. セキュリティ

- **SECRET_KEY・DBパスワードは生成**（`.env.example` の弱いデフォルトは本番で使わない。SPEC §10）。
- 秘密情報の保管: サービス環境変数 or `C:\ProgramData\plc-monitor\.env`（ACLで管理者のみ読取）。
  平文レジストリ露出を避ける方法を実装時に確定。
- `CORS_ORIGINS`: viewerは中央サーバーのオリジンのみ許可（`*`にしない）。
- Redisは `127.0.0.1` バインドで外部遮断。

---

## 10. 検証計画（実装後に実施）

1. **起動順**: PC再起動 → postgres→memurai→ingest→viewer→frontend が自動起動。
2. **配信到達**: `127.0.0.1:5000` にエージェント風POST（APIキー付）→ ブラウザ（別端末 or 同PC）が
   `:3000` でUIを開き `:5001` のSocket.IOで**リアルタイム反映**を確認。
3. **ingest分離の効果**: 閲覧接続がある状態でingestのスループットが崩れないこと（小負荷でスモーク）。
4. **再起動耐性**: 各サービスを `Restart-Service` → 自動回復。ingest/viewerをkill → Shawlが再起動。
5. **依存順**: postgres/memuraiを止めた状態でingest/viewerを起動 → リトライ/再起動で回復。
6. **描画健全性**: 既存の `scripts/test_render_health.py` を viewer/frontend 構成に向けて実行。

---

## 11. 決定事項（2026-07-13 承認済み）

- **【A】✅ viewer(Flask)が静的SPAを配信**（専用静的サービスは立てない）
- **【B】✅ APIベースは相対パス**（`NUXT_PUBLIC_API_BASE=''`。LAN IP焼込不要。useApi/socketの空文字対応が要）
- **【C】✅ Shawl**（winget・保守中。詰まればNSSM）
- **【D】✅ `C:\ProgramData\plc-monitor\.env`（ACLで管理者のみ読取）**
- **【E】✅ 既存ネイティブPostgres(5432)に新規`plc_monitor`**（migrate+seed、devデータ移行なし）

## 11b. 実装ステップ（決定を反映）

- **Step 1（システム非変更・先行）**: viewerの静的配信＋相対APIベース化のコード改修。
  ローカルで `nuxt generate`→Flask単体起動→ブラウザでUI取得＋API相対アクセスを検証。
- **Step 2（システム変更）**: Memurai/Shawl導入、native Postgresに`plc_monitor`作成＋migrate+seed、
  ingest/viewerをShawlでサービス登録、依存順・再起動・配信到達を実機検証。

---

## 12. ロールバック手順

- サービス削除: `shawl remove --name plc-ingest` / `plc-viewer`（or `sc.exe delete`）
- Memurai撤去: `winget uninstall Memurai.MemuraiDeveloper`
- Shawl撤去: `winget uninstall mtkennerly.shawl`
- ネイティブPostgresの `plc_monitor` DBは `DROP DATABASE` で除去可能（既存の他DBには影響しない）
- コード変更は原則なし（`serve_production.py` は既存）。設定スクリプトのみ追加のため影響は限定的。
