"""
データクリーンアップと集計作成のスケジューラー
"""
from flask import current_app
from db import db
from db.models import (
    Equipment, Log, DailyLogSummary, MonthlyLogSummary,
    CommunicationErrorLog, AlarmHistory, PLCStatus
)
from datetime import datetime, timedelta, timezone
from calendar import monthrange
import threading
import time


# データ保存期間設定
DATA_RETENTION_CONFIG = {
    'raw_data_days': 90,              # 詳細データ保持期間（日）
    'daily_data_days': 365,           # 日次集計データ保持期間（日）
    'error_log_days': 30,             # エラーログ保持期間（日）- Phase 2
    'alarm_history_days': 30,         # アラーム履歴保持期間（日、解除済みのみ）- Phase 2
    'cleanup_interval_hours': 24      # クリーンアップ実行間隔（時間）
}


def cleanup_old_logs():
    """古いログデータのクリーンアップ（app_context内で実行すること）"""
    try:
        print(f"🧹 クリーンアップ開始: {DATA_RETENTION_CONFIG['raw_data_days']}日以上古いデータを削除")

        # 90日以上古い詳細データを削除
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_CONFIG['raw_data_days'])

        # 削除対象件数を確認
        old_logs_count = Log.query.filter(Log.timestamp < cutoff_date).count()

        if old_logs_count > 0:
            print(f"📊 削除対象: {old_logs_count}件のログ")

            # バッチ削除（大量データ対応）
            batch_size = 1000
            total_deleted = 0

            while True:
                # 1000件ずつ削除
                old_logs = Log.query.filter(Log.timestamp < cutoff_date).limit(batch_size)
                logs_to_delete = old_logs.all()

                if not logs_to_delete:
                    break

                for log in logs_to_delete:
                    db.session.delete(log)

                db.session.commit()
                total_deleted += len(logs_to_delete)
                print(f"📝 削除進行中: {total_deleted}/{old_logs_count}件")

                # CPU負荷軽減のため少し待機
                time.sleep(0.1)

            print(f" クリーンアップ完了: {total_deleted}件のログを削除しました")
        else:
            print("ℹ️ 削除対象のログはありません")

    except Exception as e:
        print(f" クリーンアップエラー: {e}")
        db.session.rollback()


def create_daily_summary(target_date):
    """指定日の日次集計を作成（app_context内で実行すること）"""
    try:
        print(f"📊 日次集計作成開始: {target_date}")

        # 各設備の日次集計を作成
        equipments = Equipment.query.all()
        created_count = 0

        for equipment in equipments:
            # 指定日のログデータを取得
            start_date = datetime.combine(target_date, datetime.min.time())
            end_date = start_date + timedelta(days=1)

            daily_logs = Log.query.filter(
                Log.equipment_id == equipment.id,
                Log.timestamp >= start_date,
                Log.timestamp < end_date
            ).all()

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

            # 既存の日次集計を削除
            existing = DailyLogSummary.query.filter_by(
                equipment_id=equipment.id,
                date=target_date
            ).first()
            if existing:
                db.session.delete(existing)

            # 新しい日次集計を作成
            daily_summary = DailyLogSummary(
                equipment_id=equipment.id,
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
                data_count=len(daily_logs)
            )

            db.session.add(daily_summary)
            created_count += 1

        db.session.commit()
        print(f" {target_date}の日次集計を作成しました: {created_count}設備")

    except Exception as e:
        print(f" 日次集計作成エラー: {e}")
        db.session.rollback()


def create_monthly_summary(year, month):
    """指定月の月次集計を作成（app_context内で実行すること）"""
    try:
        print(f"📊 月次集計作成開始: {year}年{month}月")

        equipments = Equipment.query.all()
        created_count = 0

        for equipment in equipments:
            # 指定月の日次集計を取得
            start_date = datetime(year, month, 1).date()
            end_date = datetime(year, month, monthrange(year, month)[1]).date()

            daily_summaries = db.session.query(DailyLogSummary)\
                .filter_by(equipment_id=equipment.id)\
                .filter(DailyLogSummary.date >= start_date)\
                .filter(DailyLogSummary.date <= end_date)\
                .all()

            if not daily_summaries:
                continue

            # 月次集計の計算
            production_total = max([ds.production_count_total for ds in daily_summaries if ds.production_count_total], default=0)
            current_avgs = [ds.current_avg for ds in daily_summaries if ds.current_avg is not None]
            temp_avgs = [ds.temperature_avg for ds in daily_summaries if ds.temperature_avg is not None]
            pressure_avgs = [ds.pressure_avg for ds in daily_summaries if ds.pressure_avg is not None]
            cycle_avgs = [ds.cycle_time_avg for ds in daily_summaries if ds.cycle_time_avg is not None]
            error_total = sum([ds.error_count for ds in daily_summaries if ds.error_count])

            # 既存の月次集計を削除
            existing = MonthlyLogSummary.query.filter_by(
                equipment_id=equipment.id,
                year=year,
                month=month
            ).first()
            if existing:
                db.session.delete(existing)

            # 新しい月次集計を作成
            monthly_summary = MonthlyLogSummary(
                equipment_id=equipment.id,
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
                cycle_time_avg=sum(cycle_avgs) / len(cycle_avgs) if cycle_avgs else None,
                error_count_total=error_total,
                operational_days=len(daily_summaries)
            )

            db.session.add(monthly_summary)
            created_count += 1

        db.session.commit()
        print(f" {year}年{month}月の月次集計を作成しました: {created_count}設備")

    except Exception as e:
        print(f" 月次集計作成エラー: {e}")
        db.session.rollback()


def cleanup_old_error_logs():
    """古いエラーログのクリーンアップ（Phase 2）"""
    try:
        print(f"🧹 エラーログクリーンアップ開始: {DATA_RETENTION_CONFIG['error_log_days']}日以上古いデータを削除")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_CONFIG['error_log_days'])

        # 削除対象件数を確認
        old_errors_count = CommunicationErrorLog.query.filter(
            CommunicationErrorLog.occurred_at < cutoff_date
        ).count()

        if old_errors_count > 0:
            print(f"📊 削除対象: {old_errors_count}件のエラーログ")

            # バッチ削除
            batch_size = 1000
            total_deleted = 0

            while True:
                old_errors = CommunicationErrorLog.query.filter(
                    CommunicationErrorLog.occurred_at < cutoff_date
                ).limit(batch_size)
                errors_to_delete = old_errors.all()

                if not errors_to_delete:
                    break

                for error in errors_to_delete:
                    db.session.delete(error)

                db.session.commit()
                total_deleted += len(errors_to_delete)
                print(f"📝 削除進行中: {total_deleted}/{old_errors_count}件")

                time.sleep(0.1)

            print(f"✅ エラーログクリーンアップ完了: {total_deleted}件を削除しました")
        else:
            print("ℹ️ 削除対象のエラーログはありません")

    except Exception as e:
        print(f"❌ エラーログクリーンアップエラー: {e}")
        db.session.rollback()


def cleanup_old_alarm_history():
    """古いアラーム履歴のクリーンアップ（Phase 2）

    注意: 解除済み（cleared_at IS NOT NULL）のアラームのみ削除
    未解除のアラームは保持（長期間継続する問題を見逃さないため）
    """
    try:
        print(f"🧹 アラーム履歴クリーンアップ開始: {DATA_RETENTION_CONFIG['alarm_history_days']}日以上古い解除済みアラームを削除")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_CONFIG['alarm_history_days'])

        # 削除対象件数を確認（解除済みのみ）
        old_alarms_count = AlarmHistory.query.filter(
            AlarmHistory.occurred_at < cutoff_date,
            AlarmHistory.cleared_at.isnot(None)  # 解除済みのみ
        ).count()

        if old_alarms_count > 0:
            print(f"📊 削除対象: {old_alarms_count}件のアラーム履歴（解除済み）")

            # バッチ削除
            batch_size = 1000
            total_deleted = 0

            while True:
                old_alarms = AlarmHistory.query.filter(
                    AlarmHistory.occurred_at < cutoff_date,
                    AlarmHistory.cleared_at.isnot(None)
                ).limit(batch_size)
                alarms_to_delete = old_alarms.all()

                if not alarms_to_delete:
                    break

                for alarm in alarms_to_delete:
                    db.session.delete(alarm)

                db.session.commit()
                total_deleted += len(alarms_to_delete)
                print(f"📝 削除進行中: {total_deleted}/{old_alarms_count}件")

                time.sleep(0.1)

            print(f"✅ アラーム履歴クリーンアップ完了: {total_deleted}件を削除しました")
        else:
            print("ℹ️ 削除対象のアラーム履歴はありません")

        # 未解除アラームの件数を確認（情報提供）
        uncleared_count = AlarmHistory.query.filter(
            AlarmHistory.cleared_at.is_(None)
        ).count()
        if uncleared_count > 0:
            print(f"⚠️ 未解除アラーム: {uncleared_count}件（削除せずに保持）")

    except Exception as e:
        print(f"❌ アラーム履歴クリーンアップエラー: {e}")
        db.session.rollback()


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

                print("🕒 定期クリーンアップを開始します")

                # Flaskアプリケーションコンテキストを設定
                with app.app_context():
                    # 前日の日次集計を作成
                    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
                    create_daily_summary(yesterday)

                    # 前月の月次集計を作成（月初のみ）
                    if datetime.now(timezone.utc).day == 1:
                        last_month = datetime.now(timezone.utc) - timedelta(days=1)
                        create_monthly_summary(last_month.year, last_month.month)

                    # 古いデータのクリーンアップ（既存）
                    cleanup_old_logs()

                    # Phase 2: エラーログとアラーム履歴のクリーンアップ
                    cleanup_old_error_logs()
                    cleanup_old_alarm_history()

            except Exception as e:
                print(f"❌ スケジューラーエラー: {e}")

    # バックグラウンドスレッドで実行
    cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
    cleanup_thread.start()
    print("✅ クリーンアップスケジューラーを開始しました")
