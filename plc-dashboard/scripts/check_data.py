#!/usr/bin/env python3
"""
PLCデータ確認ツール
データベース内のログデータの状況を確認します
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 環境変数設定
if not os.getenv('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor'

from backend.app import create_app
from backend.db import db
from backend.db.models import Equipment, Log

def main():
    app, socketio = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("🔍 PLCデータ確認ツール")
        print("=" * 60)
        
        # 設備一覧
        equipments = Equipment.query.all()
        print(f"📊 登録設備数: {len(equipments)}")
        for eq in equipments:
            print(f"  - {eq.equipment_id}: {eq.manufacturer} {eq.series}")
        
        print("-" * 40)
        
        # 全ログ数
        total_logs = Log.query.count()
        print(f"📈 総ログ数: {total_logs}")
        
        if total_logs > 0:
            # 最新ログ
            latest_log = Log.query.order_by(Log.id.desc()).first()
            if latest_log:
                print(f"📅 最新ログ: {latest_log.timestamp}")
            
            # 最近1時間のログ数
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_logs = Log.query.filter(Log.timestamp >= one_hour_ago).count()
            print(f"⏰ 最近1時間: {recent_logs}件")
            
            # 設備別ログ数
            print("\n📋 設備別ログ数:")
            for eq in equipments:
                eq_logs = Log.query.filter_by(equipment_id=eq.id).count()
                if eq_logs > 0:
                    latest_eq_log = Log.query.filter_by(equipment_id=eq.id)\
                                           .order_by(Log.id.desc()).first()
                    if latest_eq_log:
                        print(f"  - {eq.equipment_id}: {eq_logs}件 (最新: {latest_eq_log.timestamp})")
                    else:
                        print(f"  - {eq.equipment_id}: {eq_logs}件")
                else:
                    print(f"  - {eq.equipment_id}: 0件 (データなし)")
            
            # 最新5件の詳細表示
            print("\n📝 最新5件のログ詳細:")
            recent_logs = Log.query.order_by(Log.id.desc()).limit(5).all()
            for log in recent_logs:
                eq = Equipment.query.get(log.equipment_id)
                if eq:
                    print(f"  [{log.timestamp}] {eq.equipment_id}: "
                          f"生産数={log.production_count}, 電流={log.current}A, "
                          f"温度={log.temperature}℃, エラー={log.error_code or '正常'}")
                else:
                    print(f"  [{log.timestamp}] 不明な設備: 生産数={log.production_count}, 電流={log.current}A")
        else:
            print("⚠️  ログデータがありません")
            print("   ラズパイからのデータ送信を確認してください")
        
        print("=" * 60)

if __name__ == "__main__":
    main() 