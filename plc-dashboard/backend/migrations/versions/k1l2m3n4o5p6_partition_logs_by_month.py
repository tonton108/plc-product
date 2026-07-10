"""logsテーブルを月次RANGEパーティション化（Phase 3: 200台スケール対応）

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
Create Date: 2026-07-10 11:00:00.000000

Postgresでのみ実行する（SQLiteはパーティション非対応。単体テストは非パーティションの
create_allで動くため、このマイグレーションはSQLiteではスキップする）。

方針:
- logs を timestamp による月次RANGEパーティションに変換する。パーティションキーは
  PKに含める必要があるため、実PKは (id, timestamp) にする（モデル側はSQLite都合で
  id単独のまま）。
- 既存データは新パーティション表へコピーして保全する。timestampがNULLの行は
  NOT NULL制約に合わせて now() で補正する。
- 現在月を中心に固定ウィンドウ（-2〜+3ヶ月）の月次パーティションと、範囲外を
  受けるDEFAULTパーティションを作成する。以降の月は
  api.partitions.ensure_log_partitions がスケジューラ経由で先回り作成する。

注意（本番運用）: 既存データ量が非常に大きい場合、INSERT ... SELECT による
コピーは長時間ロックを伴う。大規模データでの適用手順・停止時間の見積りは
_docs/decisions/logs-partitioning-strategy.md を参照。
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "k1l2m3n4o5p6"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


# 共通のカラム定義（親テーブル・非パーティション表で共有）
_LOG_COLUMNS = """
    id integer NOT NULL DEFAULT nextval('logs_id_seq'::regclass),
    equipment_id integer,
    current double precision,
    temperature double precision,
    pressure double precision,
    timestamp timestamp without time zone {ts_null},
    production_count integer,
    cycle_time double precision,
    error_code integer,
    data json
"""


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade():
    if not _is_postgres():
        # SQLite等では非パーティションのまま（テスト環境）
        return

    # 1. sequenceを旧logsから切り離す（後でlogs_oldをDROPしても消えないように）
    op.execute("ALTER SEQUENCE logs_id_seq OWNED BY NONE")

    # 2. 旧テーブルと、その制約・インデックス名を退避
    op.execute("ALTER TABLE logs RENAME TO logs_old")
    op.execute("ALTER TABLE logs_old RENAME CONSTRAINT logs_pkey TO logs_old_pkey")
    op.execute(
        "ALTER TABLE logs_old RENAME CONSTRAINT logs_equipment_id_fkey "
        "TO logs_old_equipment_id_fkey"
    )
    op.execute("ALTER INDEX idx_logs_timestamp RENAME TO idx_logs_timestamp_old")
    op.execute(
        "ALTER INDEX idx_logs_equipment_timestamp "
        "RENAME TO idx_logs_equipment_timestamp_old"
    )

    # 3. パーティション親テーブルを作成（PK=(id, timestamp), RANGE by timestamp）
    op.execute(f"""
        CREATE TABLE logs (
        {_LOG_COLUMNS.format(ts_null='NOT NULL')},
            CONSTRAINT logs_pkey PRIMARY KEY (id, timestamp),
            CONSTRAINT logs_equipment_id_fkey
                FOREIGN KEY (equipment_id) REFERENCES equipments(id)
        ) PARTITION BY RANGE (timestamp)
        """)
    op.execute("CREATE INDEX idx_logs_timestamp ON logs (timestamp)")
    op.execute(
        "CREATE INDEX idx_logs_equipment_timestamp ON logs (equipment_id, timestamp)"
    )

    # 4. 現在月を中心に固定ウィンドウ（-2〜+3ヶ月）の月次パーティションを作成し、
    #    範囲外を受けるDEFAULTパーティションも用意する。
    #    - 固定ウィンドウにすることで、既存データに異常なtimestamp（PLC時計異常等の
    #      過去/未来日付）が混じっていても大量のパーティションを生成しない。
    #    - DEFAULTを置くことで、ウィンドウ外の行やスケジューラ停止で先の月の
    #      パーティションが未作成の場合でもINSERTが失敗せず取りこぼさない（安全網）。
    #    保持期間は30日（SPEC §5.2）なので、実データは通常この窓に収まる。
    op.execute("""
        DO $$
        DECLARE base date; m date; pname text; i int;
        BEGIN
            base := date_trunc('month', now())::date;
            FOR i IN -2..3 LOOP
                m := (base + (i || ' month')::interval)::date;
                pname := 'logs_' || to_char(m, 'YYYY_MM');
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF logs '
                    'FOR VALUES FROM (%L) TO (%L)',
                    pname, m, (m + interval '1 month')::date);
            END LOOP;
        END $$
        """)
    op.execute("CREATE TABLE IF NOT EXISTS logs_default PARTITION OF logs DEFAULT")

    # 5. データ移行（NULL timestampは now() に補正）
    op.execute("""
        INSERT INTO logs (id, equipment_id, current, temperature, pressure,
                          timestamp, production_count, cycle_time, error_code, data)
        SELECT id, equipment_id, current, temperature, pressure,
               COALESCE(timestamp, now()), production_count, cycle_time, error_code, data
        FROM logs_old
        """)

    # 6. 旧テーブル削除、sequenceを新logs.idへ再アタッチし現在値を合わせる
    op.execute("DROP TABLE logs_old")
    op.execute("ALTER SEQUENCE logs_id_seq OWNED BY logs.id")
    # 3引数setval: データが有ればMAX(id)から採番継続（is_called=true）。
    # 空テーブルならis_called=falseで次のnextvalが1を返す（id=1の永久欠番を防ぐ）。
    op.execute(
        "SELECT setval('logs_id_seq', "
        "COALESCE((SELECT MAX(id) FROM logs), 1), "
        "(SELECT MAX(id) FROM logs) IS NOT NULL)"
    )


def downgrade():
    if not _is_postgres():
        return

    # パーティション表を非パーティションの通常テーブルへ戻す（データ保全）
    op.execute("ALTER SEQUENCE logs_id_seq OWNED BY NONE")

    op.execute("ALTER TABLE logs RENAME TO logs_part")
    op.execute("ALTER TABLE logs_part RENAME CONSTRAINT logs_pkey TO logs_part_pkey")
    op.execute(
        "ALTER TABLE logs_part RENAME CONSTRAINT logs_equipment_id_fkey "
        "TO logs_part_equipment_id_fkey"
    )
    op.execute("ALTER INDEX idx_logs_timestamp RENAME TO idx_logs_timestamp_part")
    op.execute(
        "ALTER INDEX idx_logs_equipment_timestamp "
        "RENAME TO idx_logs_equipment_timestamp_part"
    )

    # 通常テーブル（PK=id単独, timestampはnullable）を再作成
    op.execute(f"""
        CREATE TABLE logs (
        {_LOG_COLUMNS.format(ts_null='')},
            CONSTRAINT logs_pkey PRIMARY KEY (id),
            CONSTRAINT logs_equipment_id_fkey
                FOREIGN KEY (equipment_id) REFERENCES equipments(id)
        )
        """)
    op.execute("CREATE INDEX idx_logs_timestamp ON logs (timestamp)")
    op.execute(
        "CREATE INDEX idx_logs_equipment_timestamp ON logs (equipment_id, timestamp)"
    )

    op.execute("""
        INSERT INTO logs (id, equipment_id, current, temperature, pressure,
                          timestamp, production_count, cycle_time, error_code, data)
        SELECT id, equipment_id, current, temperature, pressure,
               timestamp, production_count, cycle_time, error_code, data
        FROM logs_part
        """)

    # パーティション表（子パーティションごと）を削除
    op.execute("DROP TABLE logs_part CASCADE")
    op.execute("ALTER SEQUENCE logs_id_seq OWNED BY logs.id")
    # 3引数setval: データが有ればMAX(id)から採番継続（is_called=true）。
    # 空テーブルならis_called=falseで次のnextvalが1を返す（id=1の永久欠番を防ぐ）。
    op.execute(
        "SELECT setval('logs_id_seq', "
        "COALESCE((SELECT MAX(id) FROM logs), 1), "
        "(SELECT MAX(id) FROM logs) IS NOT NULL)"
    )
