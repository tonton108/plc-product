"""
データクリーンアップと集計作成のスケジューラー

Phase 5リファクタリング: N+1クエリ問題の解消とバッチDELETE最適化
Phase 10リファクタリング: クリーンアップロジック統一、logger使用
"""
import logging
from flask import current_app
from db import db
from db.models import (
    Equipment, Log, DailyLogSummary, MonthlyLogSummary,
    CommunicationErrorLog, AlarmHistory, PLCStatus
)
from sqlalchemy import func
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from calendar import monthrange
import threading
import time

from api.aggregation import summarize_dynamic_from_logs, summarize_dynamic_from_daily

# モジュール用ロガー
logger = logging.getLogger(__name__)


# データ保存期間設定
DATA_RETENTION_CONFIG = {
    'raw_data_days': 30,              # 詳細データ保持期間（日）- SPEC §5.2（旧90日）
    'daily_data_days': 365,           # 日次集計データ保持期間（日）
    'error_log_days': 30,             # エラーログ保持期間（日）- Phase 2
    'alarm_history_days': 30,         # アラーム履歴保持期間（日、解除済みのみ）- Phase 2
    'cleanup_interval_hours': 24      # クリーンアップ実行間隔（時間）
}


# ==========================================
# Phase 10: 汎用クリーンアップ関数
# ==========================================

def batch_cleanup(model, date_column, retention_days, extra_filter=None, data_name="データ", batch_size=10000, cutoff_date=None):
    """汎用バッチクリーンアップ関数

    Phase 10で導入: 3つのクリーンアップ関数の共通ロジックを統一

    Args:
        model: SQLAlchemyモデルクラス（Log, CommunicationErrorLog, AlarmHistory等）
        date_column: 日付カラム（model.timestamp, model.occurred_at等）
        retention_days: 保持日数（cutoff_date省略時のカットオフ計算とログ表示に使用）
        extra_filter: 追加のフィルタ条件（オプション）- 例: AlarmHistory.cleared_at.isnot(None)
        data_name: ログ出力用のデータ名
        batch_size: バッチサイズ（デフォルト10000）
        cutoff_date: カットオフ日時の明示指定（オプション）。呼び出し側で
            事前に件数表示した際のカットオフを固定して渡すことで、対話確認等の
            待ち時間中に基準がずれる（表示件数と実削除件数の乖離）のを防ぐ。
            省略時は `now - retention_days` を都度計算する。

    Returns:
        int: 削除された件数
    """
    try:
        logger.info(f"クリーンアップ開始: {retention_days}日以上古い{data_name}を削除")

        if cutoff_date is None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # 基本クエリを構築
        base_query = model.query.filter(date_column < cutoff_date)

        # 追加フィルタがある場合は適用
        if extra_filter is not None:
            base_query = base_query.filter(extra_filter)

        # 削除対象件数を確認
        target_count = base_query.count()

        if target_count == 0:
            logger.info(f"削除対象の{data_name}はありません")
            return 0

        logger.info(f"削除対象: {target_count}件の{data_name}")

        total_deleted = 0

        while total_deleted < target_count:
            # サブクエリでIDを取得してバッチ削除
            id_column = getattr(model, 'id')
            subquery_base = db.session.query(id_column).filter(date_column < cutoff_date)

            if extra_filter is not None:
                subquery_base = subquery_base.filter(extra_filter)

            subquery = subquery_base.limit(batch_size).subquery()

            deleted_count = db.session.query(model).filter(
                id_column.in_(subquery)
            ).delete(synchronize_session=False)

            db.session.commit()

            if deleted_count == 0:
                break

            total_deleted += deleted_count
            logger.debug(f"削除進行中: {total_deleted}/{target_count}件")

            # CPU負荷軽減
            time.sleep(0.1)

        logger.info(f"クリーンアップ完了: {total_deleted}件の{data_name}を削除しました")
        return total_deleted

    except Exception as e:
        logger.error(f"クリーンアップエラー ({data_name}): {e}", exc_info=True)
        db.session.rollback()
        return 0


# ==========================================
# クリーンアップ関数（汎用関数を使用）
# ==========================================

def cleanup_old_logs(retention_days=None):
    """古いログデータのクリーンアップ（app_context内で実行すること）

    Phase 10: batch_cleanup()を使用してシンプル化
    Phase 3: 保持日数を任意で上書き可能にし、CLI(log_manager)・管理API(admin)の
    削除本体をこの関数（batch_cleanup）に一本化した。retention_days省略時は
    DATA_RETENTION_CONFIG['raw_data_days']（既定30日）を使用する。

    Args:
        retention_days: 保持日数の上書き（Noneなら設定値を使用）

    Returns:
        int: 削除された件数
    """
    if retention_days is None:
        retention_days = DATA_RETENTION_CONFIG['raw_data_days']
    return batch_cleanup(
        model=Log,
        date_column=Log.timestamp,
        retention_days=retention_days,
        data_name="ログ"
    )


def cleanup_old_error_logs():
    """古いエラーログのクリーンアップ（Phase 2）

    Phase 10: batch_cleanup()を使用してシンプル化
    """
    return batch_cleanup(
        model=CommunicationErrorLog,
        date_column=CommunicationErrorLog.occurred_at,
        retention_days=DATA_RETENTION_CONFIG['error_log_days'],
        data_name="エラーログ"
    )


def cleanup_old_alarm_history():
    """古いアラーム履歴のクリーンアップ（Phase 2）

    注意: 解除済み（cleared_at IS NOT NULL）のアラームのみ削除
    未解除のアラームは保持（長期間継続する問題を見逃さないため）

    Phase 10: batch_cleanup()を使用してシンプル化
    """
    deleted = batch_cleanup(
        model=AlarmHistory,
        date_column=AlarmHistory.occurred_at,
        retention_days=DATA_RETENTION_CONFIG['alarm_history_days'],
        extra_filter=AlarmHistory.cleared_at.isnot(None),  # 解除済みのみ
        data_name="アラーム履歴（解除済み）"
    )

    # 未解除アラームの件数を確認（情報提供）
    try:
        uncleared_count = AlarmHistory.query.filter(
            AlarmHistory.cleared_at.is_(None)
        ).count()
        if uncleared_count > 0:
            logger.warning(f"未解除アラーム: {uncleared_count}件（削除せずに保持）")
    except Exception as e:
        logger.error(f"未解除アラーム件数取得エラー: {e}")

    return deleted


# ==========================================
# 集計作成関数
# ==========================================

def create_daily_summary(target_date):
    """指定日の日次集計を作成（app_context内で実行すること）

    Phase 5最適化: N+1クエリ問題の解消
    - 旧方式: 設備ごとにログをクエリ → 1 + N クエリ
    - 新方式: 全設備のログを1クエリで取得 → Python側でグループ化 → 2クエリのみ
    """
    try:
        logger.info(f"日次集計作成開始: {target_date}")

        # 日付範囲を計算
        start_date = datetime.combine(target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)

        # 全設備のIDマップを取得（1クエリ）
        equipments = {eq.id: eq for eq in Equipment.query.all()}

        if not equipments:
            logger.info("設備が登録されていません")
            return

        # 全設備の対象日ログを1クエリで取得（N+1解消）
        all_logs = Log.query.filter(
            Log.equipment_id.in_(equipments.keys()),
            Log.timestamp >= start_date,
            Log.timestamp < end_date
        ).all()

        # Python側で設備ごとにグループ化
        logs_by_equipment = defaultdict(list)
        for log in all_logs:
            logs_by_equipment[log.equipment_id].append(log)

        logger.debug(f"取得ログ数: {len(all_logs)}件 ({len(logs_by_equipment)}設備)")

        # 既存の日次集計を一括削除（1クエリ）
        DailyLogSummary.query.filter(
            DailyLogSummary.equipment_id.in_(equipments.keys()),
            DailyLogSummary.date == target_date
        ).delete(synchronize_session=False)

        created_count = 0

        for equipment_id, daily_logs in logs_by_equipment.items():
            if not daily_logs:
                continue

            # 集計計算
            current_values = [log.current for log in daily_logs if log.current is not None]
            temp_values = [log.temperature for log in daily_logs if log.temperature is not None]
            pressure_values = [log.pressure for log in daily_logs if log.pressure is not None]
            cycle_values = [log.cycle_time for log in daily_logs if log.cycle_time is not None]

            # 最新の生産数量（累積値）
            production_total = max([log.production_count for log in daily_logs if log.production_count is not None], default=0)

            # エラー件数
            error_count = len([log for log in daily_logs if log.error_code and log.error_code > 0])

            # 動的項目（Log.data）の集計（Phase 2）
            dynamic_summary = summarize_dynamic_from_logs(daily_logs)

            # 新しい日次集計を作成
            daily_summary = DailyLogSummary(
                equipment_id=equipment_id,
                date=target_date,
                production_count_total=production_total,
                current_avg=sum(current_values) / len(current_values) if current_values else None,
                current_max=max(current_values) if current_values else None,
                current_min=min(current_values) if current_values else None,
                temperature_avg=sum(temp_values) / len(temp_values) if temp_values else None,
                temperature_max=max(temp_values) if temp_values else None,
                temperature_min=min(temp_values) if temp_values else None,
                pressure_avg=sum(pressure_values) / len(pressure_values) if pressure_values else None,
                pressure_max=max(pressure_values) if pressure_values else None,
                pressure_min=min(pressure_values) if pressure_values else None,
                cycle_time_avg=sum(cycle_values) / len(cycle_values) if cycle_values else None,
                error_count=error_count,
                data_count=len(daily_logs),
                data_summary=dynamic_summary or None
            )

            db.session.add(daily_summary)
            created_count += 1

        db.session.commit()
        logger.info(f"{target_date}の日次集計を作成しました: {created_count}設備")

    except Exception as e:
        logger.error(f"日次集計作成エラー: {e}", exc_info=True)
        db.session.rollback()


def create_monthly_summary(year, month):
    """指定月の月次集計を作成（app_context内で実行すること）

    Phase 5最適化: N+1クエリ問題の解消
    - 旧方式: 設備ごとに日次集計をクエリ → 1 + N クエリ
    - 新方式: 全設備の日次集計を1クエリで取得 → Python側でグループ化 → 2クエリのみ
    """
    try:
        logger.info(f"月次集計作成開始: {year}年{month}月")

        # 日付範囲を計算
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, monthrange(year, month)[1]).date()

        # 全設備のIDマップを取得（1クエリ）
        equipments = {eq.id: eq for eq in Equipment.query.all()}

        if not equipments:
            logger.info("設備が登録されていません")
            return

        # 全設備の対象月日次集計を1クエリで取得（N+1解消）
        all_summaries = DailyLogSummary.query.filter(
            DailyLogSummary.equipment_id.in_(equipments.keys()),
            DailyLogSummary.date >= start_date,
            DailyLogSummary.date <= end_date
        ).all()

        # Python側で設備ごとにグループ化
        summaries_by_equipment = defaultdict(list)
        for summary in all_summaries:
            summaries_by_equipment[summary.equipment_id].append(summary)

        logger.debug(f"取得日次集計数: {len(all_summaries)}件 ({len(summaries_by_equipment)}設備)")

        # 既存の月次集計を一括削除（1クエリ）
        MonthlyLogSummary.query.filter(
            MonthlyLogSummary.equipment_id.in_(equipments.keys()),
            MonthlyLogSummary.year == year,
            MonthlyLogSummary.month == month
        ).delete(synchronize_session=False)

        created_count = 0

        for equipment_id, daily_summaries in summaries_by_equipment.items():
            if not daily_summaries:
                continue

            # 月次集計の計算
            production_total = max([ds.production_count_total for ds in daily_summaries if ds.production_count_total], default=0)
            current_avgs = [ds.current_avg for ds in daily_summaries if ds.current_avg is not None]
            temp_avgs = [ds.temperature_avg for ds in daily_summaries if ds.temperature_avg is not None]
            pressure_avgs = [ds.pressure_avg for ds in daily_summaries if ds.pressure_avg is not None]
            cycle_avgs = [ds.cycle_time_avg for ds in daily_summaries if ds.cycle_time_avg is not None]
            error_total = sum([ds.error_count for ds in daily_summaries if ds.error_count])

            # 動的項目（日次data_summary）の月次集約（Phase 2）
            dynamic_summary = summarize_dynamic_from_daily(daily_summaries)

            # 新しい月次集計を作成
            monthly_summary = MonthlyLogSummary(
                equipment_id=equipment_id,
                year=year,
                month=month,
                production_count_total=production_total,
                current_avg=sum(current_avgs) / len(current_avgs) if current_avgs else None,
                current_max=max([ds.current_max for ds in daily_summaries if ds.current_max is not None], default=None),
                current_min=min([ds.current_min for ds in daily_summaries if ds.current_min is not None], default=None),
                temperature_avg=sum(temp_avgs) / len(temp_avgs) if temp_avgs else None,
                temperature_max=max([ds.temperature_max for ds in daily_summaries if ds.temperature_max is not None], default=None),
                temperature_min=min([ds.temperature_min for ds in daily_summaries if ds.temperature_min is not None], default=None),
                pressure_avg=sum(pressure_avgs) / len(pressure_avgs) if pressure_avgs else None,
                pressure_max=max([ds.pressure_max for ds in daily_summaries if ds.pressure_max is not None], default=None),
                pressure_min=min([ds.pressure_min for ds in daily_summaries if ds.pressure_min is not None], default=None),
                cycle_time_avg=sum(cycle_avgs) / len(cycle_avgs) if cycle_avgs else None,
                error_count_total=error_total,
                operational_days=len(daily_summaries),
                data_summary=dynamic_summary or None
            )

            db.session.add(monthly_summary)
            created_count += 1

        db.session.commit()
        logger.info(f"{year}年{month}月の月次集計を作成しました: {created_count}設備")

    except Exception as e:
        logger.error(f"月次集計作成エラー: {e}", exc_info=True)
        db.session.rollback()


# ==========================================
# スケジューラー
# ==========================================

def start_cleanup_scheduler(app):
    """クリーンアップスケジューラーを開始

    Args:
        app: Flaskアプリケーションオブジェクト
    """

    def cleanup_job():
        while True:
            try:
                # 24時間待機
                time.sleep(DATA_RETENTION_CONFIG['cleanup_interval_hours'] * 3600)

                logger.info("定期クリーンアップを開始します")

                # Flaskアプリケーションコンテキストを設定
                with app.app_context():
                    # 前日の日次集計を作成
                    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
                    create_daily_summary(yesterday)

                    # 前月の月次集計を作成（月初のみ）
                    if datetime.now(timezone.utc).day == 1:
                        last_month = datetime.now(timezone.utc) - timedelta(days=1)
                        create_monthly_summary(last_month.year, last_month.month)

                    # 古いデータのクリーンアップ
                    cleanup_old_logs()
                    cleanup_old_error_logs()
                    cleanup_old_alarm_history()

            except Exception as e:
                logger.error(f"スケジューラーエラー: {e}", exc_info=True)

    # バックグラウンドスレッドで実行
    cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
    cleanup_thread.start()
    logger.info("クリーンアップスケジューラーを開始しました")
