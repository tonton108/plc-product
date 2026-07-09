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

from api.constants import DEFAULT_DB_URL, DEFAULT_CLEANUP_DAYS

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
from api.aggregation import summarize_dynamic_from_logs

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
    """古いデータを削除

    Phase 3: 削除本体を scheduler.batch_cleanup に委譲し、3系統
    （CLI・管理API・スケジューラ）のクリーンアップ実装を1系統に統合した。
    以前はここで `.all()` → `for log: db.session.delete(log)` と全件を
    ORM経由でロード・逐次削除しており、大量ログで非効率だった。
    CLI固有の対話確認のみここに残す。
    """
    from api.scheduler import batch_cleanup

    app, socketio = create_app()

    with app.app_context():
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        count = Log.query.filter(Log.timestamp < cutoff_date).count()

        if count == 0:
            logger.info(f"{days}日以上古いログはありません")
            return

        logger.info(f"{days}日以上古いログを削除します: {count:,}件")

        # 確認（CLIのみの対話確認）
        confirm = input("続行しますか？ (y/N): ")
        if confirm.lower() != 'y':
            logger.info("キャンセルしました")
            return

        # 削除本体は共通のバッチDELETE（set-based, IN(サブクエリ)）に委譲。
        # 上で件数表示に使ったcutoff_dateをそのまま渡し、input()確認待ちの間に
        # 基準時刻がずれて表示件数と実削除件数が食い違うのを防ぐ。
        deleted_count = batch_cleanup(
            model=Log,
            date_column=Log.timestamp,
            retention_days=days,
            data_name="ログ",
            cutoff_date=cutoff_date
        )

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

            # 動的項目（Log.data）の集計（Phase 2、scheduler.pyと同じ共通ヘルパー）
            dynamic_summary = summarize_dynamic_from_logs(daily_logs)

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
                data_count=len(daily_logs),
                data_summary=dynamic_summary or None
            )

            db.session.add(daily_summary)
            created_count += 1
            logger.info(f"  {equipment.equipment_id}: {len(daily_logs)}件のログから集計作成")

        db.session.commit()
        logger.info(f"日次集計作成完了: {created_count}設備")

def create_monthly_summary_manual(year, month):
    """指定月の月次集計を手動作成

    集計本体は scheduler.create_monthly_summary に委譲する（Issue #10）。
    以前はこのCLIが独自実装を持ち、temperature/pressure/cycle_time や
    動的項目(data_summary)を欠いてスケジューラ経由の集計と乖離していた。
    共通化により、どちらの経路でも同じ内容の月次集計が作られる。
    """
    from api.scheduler import create_monthly_summary

    app, socketio = create_app()

    with app.app_context():
        logger.info(f"{year}年{month}月の月次集計を作成します")

        # 既存データの確認（CLIのみ対話確認。上書きはscheduler側がDELETE→再作成で行う）
        existing = MonthlyLogSummary.query.filter_by(year=year, month=month).count()
        if existing > 0:
            logger.warning(f"{year}年{month}月の集計は既に{existing}件存在します")
            confirm = input("上書きしますか？ (y/N): ")
            if confirm.lower() != 'y':
                logger.info("キャンセルしました")
                return

        create_monthly_summary(year, month)
        logger.info("月次集計作成完了")

def main():
    parser = argparse.ArgumentParser(description='PLCログデータ管理ツール')
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # 統計表示
    subparsers.add_parser('stats', help='データベース統計を表示')
    
    # データクリーンアップ
    cleanup_parser = subparsers.add_parser('cleanup', help='古いデータを削除')
    cleanup_parser.add_argument('--days', type=int, default=DEFAULT_CLEANUP_DAYS, help='保持期間（日）')
    
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