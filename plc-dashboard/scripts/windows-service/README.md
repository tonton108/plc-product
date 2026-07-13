# Windowsサービス化 セットアップ手順（Phase 4 Increment 1）

本番サービング（ingest/viewer 2プロセス＋Redis）を**この中央サーバーPCにネイティブ・
サービスとして常駐**させる。設計は `_docs/deployment/windows-service-setup.md`。

構成: `postgres(既存5432) → Memurai(Redis 6379) → plc-ingest(5000) → plc-viewer(5001)`。
フロントSPAは viewer(Flask) が同一オリジンで配信（相対APIベース・LAN IP焼込不要）。

---

## 事前準備（実行者＝あなた）

1. **フロント静的ビルド**（管理者不要・私が実施済みでもOK。再ビルドする場合）:
   ```powershell
   cd <repo>\plc-dashboard
   $env:NUXT_PUBLIC_API_BASE=''      # 相対APIベースで焼く
   npm run generate                  # .output/public を生成
   ```
2. **既存ネイティブPostgresの superuser(postgres) パスワード**を用意する
   （インストール時に設定した値。role/DB作成に使う）。

## 実行（管理者PowerShell）

```powershell
cd <repo>\plc-dashboard\scripts\windows-service
.\setup-all.ps1 -PgSuperPassword '＜postgresのパスワード＞'
```

- 冪等（再実行可）。winget導入でPATHが未反映のときは、**新しい管理者PowerShellを開いて**
  `.\setup-all.ps1 -PgSuperPassword '...' -SkipInstall` で続行できる。
- 完了時に **admin パスワード / エージェントAPIキー / .env パス / ログパス** を表示する。**控えること**。

## 確認

```powershell
.\verify.ps1
```
- サービス状態、6379待受、ingest/viewer の `/api/health`、viewer の UI(`/`) を確認。

## 私に貼り付けてほしい出力

次の2つの**出力全体**を貼ってください（成功/失敗どちらでも）:
1. `.\setup-all.ps1 ...` の出力（末尾の生成情報ブロック含む。※パスワード/APIキーは伏せてOK）
2. `.\verify.ps1` の出力

→ こちらで結果を判定し、詰まりがあれば修正して次の手順を出します。

## うまくいかない時 / ロールバック

- サービスが起動直後に停止する場合、多くは **LocalSystem が python を実行できない/依存が見つからない**。
  `C:\ProgramData\plc-monitor\logs\` の各サービスログを確認。対処はこちらで指示します
  （サービス実行アカウントを現在ユーザーに切替、または Python をマシン全体に導入 等）。
- 撤去:
  ```powershell
  .\uninstall.ps1                                   # サービスのみ削除
  .\uninstall.ps1 -Full -PgSuperPassword '...'      # Memurai/Shawl/DBも撤去
  ```

## 注意

- ローカル接続は必ず `127.0.0.1`（`localhost` はWindowsのIPv6フォールバックで一律2秒遅延する既知の罠）。
- 生成した秘密情報は `C:\ProgramData\plc-monitor\.env`（管理者/SYSTEMのみ読取ACL）に保存される。
- この手順は既存の Docker 開発環境（5433等）とは独立。ネイティブPostgres(5432)に新規DBを立てる。
