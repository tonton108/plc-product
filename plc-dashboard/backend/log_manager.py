#!/usr/bin/env python3
"""
PLCログデータ管理ツール
クリーンアップ、集計作成、統計表示などの管理機能を提供

Phase 15: 定数化・logger統一
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta, timezone

from api.constants import DEFAULT_DB_URL, BATCH_DELETE_SIZE, DEFAULT_CLEANUP_DAYS

# Phase 15: ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定（Phase 15: 定数を使用）
if not os.getenv('DATABASE_URL'):
    os.environ['DATABASE_URL'] = DEFAULT_DB_URL

from app import create_app
from db import db
from db.models import Equipment, Log, DailyLogSummary, MonthlyLogSummary
from sqlalchemy import text, func

def show_stats():
    """データベース統計を表示"""
    app, socketio = create_app()

    with app.app_context():
        logger.info("=" * 60)
        logger.info("PLCログデータベース統計")
        logger.info("=" * 60)

        # 基本統計
        total_equipments = Equipment.query.count()
        total_logs = Log.query.count()
        total_daily = DailyLogSummary.query.count()
        total_monthly = MonthlyLogSummary.query.count()

        logger.info(f"設備数: {total_equipments}")
        logger.info(f"ログ数: {total_logs:,}")
        logger.info(f"日次集計数: {total_daily:,}")
        logger.info(f"月次集計数: {total_monthly:,}")

        if total_logs > 0:
            # 期間統計
            oldest_log = Log.query.order_by(Log.timestamp.asc()).first()
            newest_log = Log.query.order_by(Log.timestamp.desc()).first()

            logger.info("【データ期間】")
            if oldest_log and newest_log:
                logger.info(f"最古: {oldest_log.timestamp}")
                logger.info(f"最新: {newest_log.timestamp}")
            else:
                logger.info("データがありません")

            # 最近の統計
            recent_1h = Log.query.filter(Log.timestamp >= datetime.now(timezone.utc) - timedelta(hours=1)).count()
            recent_24h = Log.query.filter(Log.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)).count()
            recent_7d = Log.query.filter(Log.timestamp >= datetime.now(timezone.utc) - timedelta(days=7)).count()

            logger.info("【最近のデータ】")
            logger.info(f"1時間以内: {recent_1h:,}件")
            logger.info(f"24時間以内: {recent_24h:,}件")
            logger.info(f"7日以内: {recent_7d:,}件")

            # 設備別統計（Phase 18: N+1クエリ修正 - 1クエリで集計）
            logger.info("【設備別ログ数】")
            log_counts = db.session.query(
                Equipment.equipment_id,
                func.count(Log.id).label('log_count')
            ).outerjoin(Log, Equipment.id == Log.equipment_id)\
             .group_by(Equipment.id, Equipment.equipment_id)\
             .all()
            for equipment_id, log_count in log_counts:
                logger.info(f"  {equipment_id}: {log_count:,}件")

        # データベースサイズ情報（PostgreSQL用）
        try:
            # PostgreSQLのデータベースサイズを取得
            result = db.session.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
            db_size = result.scalar()
            logger.info(f"【データベースサイズ】: {db_size}")
        except Exception:
            logger.info("【データベースサイズ】: 取得できませんでした")

        logger.info("=" * 60)

def cleanup_old_data(days):
    """古いデータを削除"""
    app, socketio = create_app()

    with app.app_context():
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        old_logs = Log.query.filter(Log.timestamp < cutoff_date)
        count = old_logs.count()

        if count == 0:
            logger.info(f"{days}日以上古いログはありません")
            return

        logger.info(f"{days}日以上古いログを削除します: {count:,}件")

        # 確認
        confirm = input("続行しますか？ (y/N): ")
        if confirm.lower() != 'y':
            logger.info("キャンセルしました")
            return

        # バッチ削除（Phase 15: 定数を使用）
        deleted_count = 0

        while True:
            batch = Log.query.filter(Log.timestamp < cutoff_date).limit(BATCH_DELETE_SIZE).all()
            if not batch:
                break

            for log in batch:
                db.session.delete(log)

            db.session.commit()
            deleted_count += len(batch)
            logger.info(f"削除済み: {deleted_count:,}/{count:,}件")

        logger.info(f"削除完了: {deleted_count:,}件")

def create_daily_summary_manual(date_str):
    """指定日の日次集計を手動作成"""
    app, socketio = create_app()

    with app.app_context():
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.error("日付形式が正しくありません (YYYY-MM-DD)")
            return

        logger.info(f"{target_date}の日次集計を作成します")

        # 既存データの確認
        existing = DailyLogSummary.query.filter_by(date=target_date).count()
        if existing > 0:
            logger.warning(f"{target_date}の集計は既に{existing}件存在します")
            confirm = input("上書きしますか？ (y/N): ")
            if confirm.lower() != 'y':
                logger.info("キャンセルしました")
                return

        created_count = 0
        equipments = Equipment.query.all()

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

            # 統計計算
            current_values = [log.current for log in daily_logs if log.current is not None]
            temp_values = [log.temperature for log in daily_logs if log.temperature is not None]
            pressure_values = [log.pressure for log in daily_logs if log.pressure is not None]
            cycle_values = [log.cycle_time for log in daily_logs if log.cycle_time is not None]

            production_total = max([log.production_count for log in daily_logs if log.production_count is not None], default=0)
            error_count = len([log for log in daily_logs if log.error_code and log.error_code > 0])

            # 既存削除
            existing_summary = DailyLogSummary.query.filter_by(
                equipment_id=equipment.id,
                date=target_date
            ).first()
            if existing_summary:
                db.session.delete(existing_summary)

            # 新規作成
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
            logger.info(f"  {equipment.equipment_id}: {len(daily_logs)}件のログから集計作成")

        db.session.commit()
        logger.info(f"日次集計作成完了: {created_count}設備")

def create_monthly_summary_manual(year, month):
    """指定月の月次集計を手動作成"""
    app, socketio = create_app()

    with app.app_context():
        logger.info(f"{year}年{month}月の月次集計を作成します")

        # 既存データの確認
        existing = MonthlyLogSummary.query.filter_by(year=year, month=month).count()
        if existing > 0:
            logger.warning(f"{year}年{month}月の集計は既に{existing}件存在します")
            confirm = input("上書きしますか？ (y/N): ")
            if confirm.lower() != 'y':
                logger.info("キャンセルしました")
                return

        created_count = 0
        equipments = Equipment.query.all()

        for equipment in equipments:
            # 指定月の日次集計を取得
            from calendar import monthrange
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
            error_total = sum([ds.error_count for ds in daily_summaries if ds.error_count])

            # 既存削除
            existing_summary = MonthlyLogSummary.query.filter_by(
                equipment_id=equipment.id,
                year=year,
                month=month
            ).first()
            if existing_summary:
                db.session.delete(existing_summary)

            # 新規作成
            monthly_summary = MonthlyLogSummary(
                equipment_id=equipment.id,
                year=year,
                month=month,
                production_count_total=production_total,
                current_avg=sum(current_avgs) / len(current_avgs) if current_avgs else None,
                error_count_total=error_total,
                operational_days=len(daily_summaries)
            )

            db.session.add(monthly_summary)
            created_count += 1
            logger.info(f"  {equipment.equipment_id}: {len(daily_summaries)}日分から集計作成")

        db.session.commit()
        logger.info(f"月次集計作成完了: {created_count}設備")

def main():
    parser = argparse.ArgumentParser(description='PLCログデータ管理ツール')
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # 統計表示
    subparsers.add_parser('stats', help='データベース統計を表示')
    
    # データクリーンアップ
    cleanup_parser = subparsers.add_parser('cleanup', help='古いデータを削除')
    cleanup_parser.add_argument('--days', type=int, default=90, help='保持期間（日）')
    
    # 日次集計作成
    daily_parser = subparsers.add_parser('daily', help='日次集計を作成')
    daily_parser.add_argument('date', help='対象日（YYYY-MM-DD）')
    
    # 月次集計作成
    monthly_parser = subparsers.add_parser('monthly', help='月次集計を作成')
    monthly_parser.add_argument('year', type=int, help='対象年')
    monthly_parser.add_argument('month', type=int, help='対象月')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'stats':
        show_stats()
    elif args.command == 'cleanup':
        cleanup_old_data(args.days)
    elif args.command == 'daily':
        create_daily_summary_manual(args.date)
    elif args.command == 'monthly':
        create_monthly_summary_manual(args.year, args.month)

if __name__ == "__main__":
    main() 