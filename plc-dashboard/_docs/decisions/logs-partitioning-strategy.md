# logsテーブルのパーティショニング戦略（Phase 3）

**作成日:** 2026-07-10
**ステータス:** コア実装済み（Phase 3-A1）。Docker/PostgreSQL導入により実機検証が可能になり着手
**関連:** SPEC.md §5.2、`migrations/versions/k1l2m3n4o5p6_partition_logs_by_month.py`、`api/partitions.py`、`api/scheduler.py`、`db/models/logs.py`

## 実装状況（2026-07-10）

**実装済み（PR: logsパーティション化）:**
- マイグレーション `k1l2m3n4o5p6`: logs を月次RANGEパーティション（実PK `(id, timestamp)`）へ変換。既存データ保全（`INSERT ... SELECT`、NULL timestampは`now()`補正）。Postgres限定（dialectガード）。downgradeで非パーティションへ復帰。**実Postgresでupgrade↔downgradeラウンドトリップ・データ保全・pruning・新規INSERT採番を検証済み**
- `api/partitions.ensure_log_partitions()`: 現在月+3ヶ月のパーティションを先回り作成（冪等）。スケジューラ起動時＋日次で実行。SQLiteではno-op
- モデル: `Log.timestamp` を NOT NULL 化。PKはSQLite都合で id単独のまま（複合PK・パーティション化はPostgresマイグレーションのみ）

**未実装（フォローアップ候補・本文書の方針どおり）:**
- クリーンアップの `DELETE`→古いパーティション`DROP`最適化（現状は`batch_cleanup`のDELETEがパーティション表でも正しく動く。DROP化は高速化の追加施策）
- 読み取りパスの`timestamp`基準化（現状`ORDER BY id`。動作はするがpartition pruningは効かない）
- 大規模既存データの無停止移行手順（下記「データ移行」。開発/新規環境ではマイグレーションが直接変換）

**テストの範囲:** パーティションのDDL・pruning・ルーティング・DROP削除はPostgres専用のため、SQLite単体テストでは検証できない。ガードのno-op（`tests/test_partitions.py`）のみ単体化し、実挙動はローカル実Postgres＋CIの空Postgres `flask db upgrade` で確認する。

## 背景と目的

200台規模（SPEC.md §1）で各設備が数秒間隔にデータを送ると、`logs`は
月あたり数千万行のオーダーで増える。単一テーブルのままだと以下が問題になる:

- 保持期間超過データの削除（`DELETE ... WHERE timestamp < cutoff`）が重い。
  行削除＋インデックス更新＋VACUUM対象の肥大が続く
- 履歴クエリのインデックスが巨大化し、プランナのコストが上がる
- テーブル/インデックスの肥大でバックアップ・保守が長時間化する

PostgreSQLネイティブの**timestampによるRANGEパーティショニング（月次）**を導入すれば、
保持期間超過分は該当パーティションの`DROP`/`DETACH`で**即時・低コスト**に落とせる。
これが本施策の主目的。

## なぜ「今は実装しない」のか（保留の理由）

現状把握（2026-07-10調査）で、ブラインドで着手するには影響が広く危険と判断した:

1. **主キー変更が必須**: PostgreSQLのネイティブパーティショニングは、
   パーティションキー（`timestamp`）を**主キーおよび全UNIQUE制約に含める**ことを要求する。
   現在の`logs`のPKは`id`単独。`(id, timestamp)`への変更はテーブル再定義に相当する。
2. **テーブル再構築とデータ移行**: 既存の巨大テーブル（本番では最大〜数億行想定）を
   パーティション親へ移し替える必要がある。無停止でやるなら
   「新パーティション表を作成→バックフィル→切替」の段取りと、その間の二重書き込みが要る。
3. **テスト環境で検証できない**: 単体テストは**インメモリSQLite**（`conftest.py`）で走る。
   SQLiteはPostgreSQLのパーティションDDL（`PARTITION BY RANGE`等）を解釈できないため、
   マイグレーションの正当性は**CIの空PostgreSQL**（`flask db upgrade`）でしか確認できない。
   データを伴う移行の検証は本番相当データが要り、CIだけでは不足。
4. **読み取りパスの劣化リスク**: 現在の主要な読み取りは`Log.id`順で並べており
   （`get_latest_data`・`get_history_data`は`ORDER BY Log.id DESC`、
   `get_realtime_status`も同様）、`timestamp`での枝刈り（partition pruning）が効かない。
   パーティション化の効果を出すには、これらを`timestamp`基準の条件・並び替えに
   作り替える必要があり、APIの挙動（特に`id`との整合）に影響する。
5. **前提だったクリーンアップ統合は完了済み**: 3系統（CLI・管理API・スケジューラ）の
   クリーンアップは`scheduler.batch_cleanup`に一本化済み（Phase 3、本PR）。
   パーティション導入時は、この1系統の削除ロジックを
   「`DELETE`」から「古いパーティションの`DROP`/`DETACH`」へ差し替える形になる。

## 実装方針（着手時の手順案・仮説）

> 以下は着手を確定した時点で再検証する前提の手順案。数値・段取りは本番データ量で見直す。

### 1. スキーマ変更

- PKを`id`単独 →`(id, timestamp)`へ変更（親テーブルは`PARTITION BY RANGE (timestamp)`）
- 既存インデックス（`idx_logs_timestamp`, `idx_logs_equipment_timestamp`）は
  各パーティションに引き継ぐ設計にする
- `equipment_id`のFKはパーティション親に定義

### 2. パーティション運用

- **月次RANGEパーティション**（例: `logs_2026_07`）を採用
- 先行して当月＋翌数か月分を事前作成しておく（挿入時に対象パーティション不在で失敗させない）
- 新規パーティションの自動作成は、既存の日次スケジューラ（`start_cleanup_scheduler`）に
  「Nか月先までのパーティションを用意する」ジョブを追加して担保する

### 3. データ移行（無停止案）

1. 新パーティション親テーブルを別名で作成
2. 既存データを月単位でバックフィル（バッチ、`batch_cleanup`と同様に負荷平準化）
3. バックフィル中は新旧両方に書き込む（アプリ側の二重書き込み、または移行ウィンドウを短く取る）
4. 追いついた時点でテーブル名を切替（`RENAME`）、旧テーブルを保持→問題なければ廃棄

移行が重い場合の代替: **切替時点以降のみパーティション化**し、過去データは
旧テーブルに残して読み取り時にUNIONする（移行コストを避ける代わりに読み取りが複雑化）。

### 4. 読み取りパスの修正

- `get_latest_data` / `get_history_data` / `get_realtime_status` を、
  `timestamp`の範囲条件を伴うクエリへ改修し、partition pruningを効かせる
- `id`順の「最新」取得は`(timestamp DESC, id DESC)`に置き換える（同一timestamp内の順序安定化）

### 5. クリーンアップの差し替え

- `scheduler.cleanup_old_logs`（現在は`batch_cleanup`によるバッチ`DELETE`）を、
  保持期間を過ぎた月次パーティションの`DETACH`＋`DROP`に置き換える
- これによりクリーンアップは行削除ではなくメタデータ操作となり、劇的に軽くなる

## 検証計画（着手時）

- **DDLの正当性**: CIの空PostgreSQLで`flask db upgrade`／`downgrade`が通ること
- **pruning確認**: 代表クエリの`EXPLAIN`で対象パーティションのみscanされること
- **移行の等価性**: 移行前後で件数・代表集計値（日次サマリ）が一致すること
- **クリーンアップ**: パーティション`DROP`で保持期間超過分のみ消え、
  現行データが残ること（統合テストの`test_cleanup.py`をパーティション版に拡張）
- **ダウンタイム**: 切替に要する時間を本番相当データで実測し、許容窓に収まること

## 却下・保留した代替案

- **アプリ側での手動シャーディング（設備別テーブル等）**: 200テーブルの管理・
  マイグレーション・クロス設備集計が煩雑。ネイティブパーティションの方が素直
- **今すぐブラインド実装**: 上記1〜4のリスク（PK変更・データ移行・検証不能・読み取り劣化）が
  同時に効くため却下。まず本ドキュメントで前提を固め、着手はデータ量と移行窓の確認後

## 参照

- SPEC.md §5.2（保持30日・スケジューラ統合・パーティショニング）
- `plc-dashboard/backend/api/scheduler.py`（統合済みクリーンアップ）
- `plc-dashboard/_docs/decisions/data-archiving-strategy.md`（階層化アーカイブ）
