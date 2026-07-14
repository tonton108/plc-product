# インストーラのランタイム同梱ノウハウ（Postgresポータブル）

**ステータス:** 参考ノウハウ（将来のゼロ前提インストーラ用）。2026-07-14 に `desktop-app/` 廃止時に吸収。
**出典:** 旧 `plc-dashboard/desktop-app/electron/main.js`（廃止済み・git履歴に残存）。
**関連:** SPEC §3.1（配布形態）/ §3.1 L80（initdbフラグ要件）、`windows-service-setup.md`（現行のサービス方式）。

> このドキュメントは、Phase 4 の最終段「PostgreSQL/Python ランタイム同梱によるゼロ前提インストーラ」を
> 実装するときの一次参考。**現行の本番構成（Phase 4）は既存ネイティブPostgres＋Windowsサービス方式**で、
> ここに記す「ポータブルPostgresをアプリが起動する」方式ではない点に注意（下記「却下した方式」参照）。

---

## 却下した方式（なぜ子プロセスspawnをやめたか）

旧 `desktop-app` は Electron が **PostgreSQL / Flask / Nuxt を子プロセスとして spawn** し、
アプリ終了時に停止する構成だった（`startPostgres()` / `startFlaskBackend()` / `startNuxtServer()`）。

**却下理由:** SPEC §3.1 の要件「PC起動と同時に自動開始、**ログオフ・アプリ終了で止まらない**」を満たせない。
アプリ（トレイGUI）と常駐サーバーの寿命が結合してしまう。Phase 4 では
**Windowsサービス方式**（postgres=`postgresql-x64-18` / Memurai / plc-ingest / plc-viewer）を採用し、
トレイアプリ（`electron/`）は「サービスを管理・表示するGUI」に徹する構成へ変更した。

したがって将来ポータブルPostgresを同梱する場合も、**アプリがspawnするのではなく
サービスとして登録**する（`pg_ctl register` もしくは Shawl 経由）。再利用するのは以下の
「initdb・postgresql.conf・停止」のコマンドノウハウであって、子プロセス管理ロジックではない。

---

## ポータブルPostgres配置レイアウト（想定）

```
<server>/backend/postgres-portable/
├── bin/
│   ├── initdb.exe
│   ├── postgres.exe
│   └── pg_ctl.exe
└── data/            … initdb で生成（初回のみ）
```

extraResources で同梱する場合（electron-builder）:

```json
{ "from": "../backend/postgres-portable", "to": "server/backend/postgres-portable", "filter": ["**/*"] }
```

> バイナリ本体（数百MB）はリポジトリに置かず、ビルド前に取得して配置する
> （`prepare-postgres` 相当のステップ。desktop-app では未実装＝スクリプト欠落だった）。

---

## 初期化（initdb）— 初回のみ

`data/` が存在しなければ初期化する。

```
initdb.exe -D <data> -U postgres -E UTF8 --locale=C --auth=<method>
```

- `-E UTF8` … エンコーディング（必須。SPEC §3.1 L80）
- `--locale` … 明示する（SPEC §3.1 L80。`C` もしくは適切なロケール）
- `--auth` … **`trust` を避ける**（SPEC §3.1 L80 の明示要件）。
  - ⚠️ 旧 desktop-app は開発都合で `--auth=trust` にしていた。本番同梱では
    `scram-sha-256` 等にし、superuserパスワードを生成して安全に設定する
    （`reset-postgres-password.ps1` / `setup-all.ps1` のパスワード生成・pg_hba手順を流用）。

initdb 後、`data/postgresql.conf` に追記していた設定（参考値）:

```conf
port = <PORT>
max_connections = 50
shared_buffers = 128MB
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
```

> 200台スケール（Phase 3）を踏まえると `max_connections` / `shared_buffers` は
> 本番想定で再検討する（この値は単機デモ由来）。

---

## 起動・停止（サービス化しない検証時の手動起動コマンド）

```
# 起動（"database system is ready to accept connections" を待つ）
postgres.exe -D <data> -p <PORT>

# グレースフル停止
pg_ctl.exe stop -D <data> -m fast
```

本番はこれを**サービス登録**して常駐させる（依存順: postgres → Memurai → ingest/viewer。
`windows-service-setup.md` §2 の依存順に合わせる）。

---

## ポート衝突回避（参考）

旧実装は `net.createServer().listen()` で空きポートを探索し 5433 から開始していた。
ただし本番は**固定ポート5432のサービス**前提（クライアント・エージェントの接続先が固定であるべき）なので、
同梱時も原則固定ポートとし、衝突時はセットアップで検知して案内する方針が望ましい。

---

## Python ランタイム同梱（未検討事項）

Flask backend は Python 実行環境を要する。ゼロ前提化するには以下のいずれかが必要:

- **埋め込み Python（python-embed）＋ 事前 `pip install -r requirements.txt`** をインストーラに同梱
- もしくは PyInstaller 等で `serve_production.py` を単一exe化

いずれも大バイナリ・ビルド工程が増えるため、採用は別途方針決定が必要（本ドキュメント作成時点で未決）。
現行の段階的アプローチでは Python は**インストール前提**（`setup-all.ps1` が依存確認する）。
