"""
logsテーブルの月次パーティション管理（Phase 3）

Postgresでは logs を timestamp による月次RANGEパーティションとして運用する。
対応する月のパーティションが存在しない期間へINSERTすると失敗するため、
現在月から数ヶ月先までのパーティションを常に用意しておく必要がある。

この関数は起動時とスケジューラの日次ジョブから呼ばれ、先の月のパーティションを
先回りして作成する（IF NOT EXISTS で冪等）。SQLite（単体テスト）では何もしない。
"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy import text

from db import db

logger = logging.getLogger(__name__)

# 現在月から何ヶ月先まで用意するか（日次ジョブが追従するので数ヶ月あれば十分）
DEFAULT_MONTHS_AHEAD = 3


def _month_start(d: date) -> date:
    """その月の1日を返す"""
    return date(d.year, d.month, 1)


def _add_months(d: date, n: int) -> date:
    """月初dにnヶ月足した月初を返す"""
    total = (d.year * 12 + (d.month - 1)) + n
    return date(total // 12, total % 12 + 1, 1)


def _is_postgres() -> bool:
    return db.session.get_bind().dialect.name == "postgresql"


def ensure_log_partitions(months_ahead: int = DEFAULT_MONTHS_AHEAD) -> int:
    """現在月から months_ahead ヶ月先までの logs 月次パーティションを用意する

    Postgresのみ動作（SQLiteでは0を返して何もしない）。冪等。
    logs がパーティション化されていない場合や個別の作成失敗は握り潰してログに残す
    （スケジューラスレッドを落とさないため）。

    Returns:
        int: 実際に作成・コミットできたパーティション数（既存分・失敗分は数えない）。

    設計注意:
    - 月ごとに個別コミットする。まとめて最後に1回commitすると、途中月の失敗で
      rollbackした際に「直前まで成功していた未コミットのCREATE」も巻き戻り、
      当月分パーティションが欠落しうる（Postgresは同一トランザクションを一括で戻すため）。
    - 全体を try/except で包み、DB接続断等でも例外を外へ伝播させない。伝播すると
      呼び出し元スケジューラの日次ジョブ（集計・他クリーンアップ）が巻き添えで中断する。
    """
    try:
        if not _is_postgres():
            return 0

        # logs がパーティション親でなければ何もしない（マイグレーション未適用のDB等）
        is_partitioned = db.session.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_partitioned_table pt "
                "JOIN pg_class c ON c.oid = pt.partrelid WHERE c.relname = 'logs')"
            )
        ).scalar()
        if not is_partitioned:
            logger.info(
                "logsはパーティション化されていないため、パーティション作成をスキップ"
            )
            return 0

        current = _month_start(datetime.now(timezone.utc).date())
        created = 0
        for i in range(months_ahead + 1):
            start = _add_months(current, i)
            end = _add_months(start, 1)
            pname = f"logs_{start.year:04d}_{start.month:02d}"

            # 既存なら何もしない（新規作成数を正確に数えるため実在チェック）。
            # CREATE側にも IF NOT EXISTS を残し、並行実行時の競合に備える。
            exists = db.session.execute(
                text("SELECT to_regclass(:qname)"), {"qname": f"public.{pname}"}
            ).scalar()
            if exists is not None:
                continue

            try:
                db.session.execute(
                    text(
                        f'CREATE TABLE IF NOT EXISTS "{pname}" '
                        f"PARTITION OF logs FOR VALUES FROM (:start) TO (:end)"
                    ),
                    {"start": start.isoformat(), "end": end.isoformat()},
                )
                db.session.commit()  # 月ごとに独立コミット（失敗の巻き添えを防ぐ）
                created += 1
            except Exception as e:
                db.session.rollback()
                logger.error(f"パーティション {pname} の作成に失敗: {e}", exc_info=True)

        logger.info(
            f"logs月次パーティションを確認しました（現在月+{months_ahead}ヶ月、"
            f"新規作成{created}件）"
        )
        return created
    except Exception as e:
        db.session.rollback()
        logger.error(f"ensure_log_partitions で予期せぬエラー: {e}", exc_info=True)
        return 0
