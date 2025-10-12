#!/usr/bin/env python3
"""
Docker環境用データベース初期化スクリプト
"""

import os
import sys
sys.path.insert(0, '/app')

from backend.app import create_app
from backend.db import db
from backend.db.models import Equipment, PLCDataConfig, Log

def init_database():
    print("🗄️ Docker環境でのデータベース初期化を開始...")
    
    # データベースディレクトリを確実に作成
    db_dir = '/app/instance'
    os.makedirs(db_dir, exist_ok=True)
    
    # DATABASE_URLを設定
    os.environ['DATABASE_URL'] = 'sqlite:///instance/plc_monitoring.db'
    
    app, socketio = create_app()
    
    with app.app_context():
        try:
            # 既存のテーブルを削除して再作成
            db.drop_all()
            db.create_all()
            
            print("✅ データベーステーブル作成完了")
            
            # テスト用設備データを作成
            test_equipment = Equipment(
                equipment_id='EP_TEST_CONFIG12345',
                manufacturer='テストメーカー',
                series='テストシリーズ',
                ip='192.168.1.50',
                plc_ip='192.168.1.100',
                port=502,
                modbus_port=502
            )
            
            db.session.add(test_equipment)
            db.session.commit()  # 設備IDを取得するためにコミット
            
            # PLC設定データを作成
            plc_configs = [
                PLCDataConfig(
                    equipment_id=test_equipment.id,
                    data_type='production_count',
                    address='D100',
                    scale_factor=1,
                    plc_data_type='word'
                ),
                PLCDataConfig(
                    equipment_id=test_equipment.id,
                    data_type='current',
                    address='D101',
                    scale_factor=10,
                    plc_data_type='word'
                ),
                PLCDataConfig(
                    equipment_id=test_equipment.id,
                    data_type='temperature',
                    address='D102',
                    scale_factor=10,
                    plc_data_type='word'
                )
            ]
            
            for config in plc_configs:
                db.session.add(config)
            
            db.session.commit()
            print("✅ テストデータ挿入完了")
            
            # 権限設定
            db_file = '/app/instance/plc_monitoring.db'
            if os.path.exists(db_file):
                os.chmod(db_file, 0o666)
                print(f"✅ データベースファイル権限設定完了: {db_file}")
            
            print("🎯 データベース初期化が正常に完了しました")
            
        except Exception as e:
            print(f"❌ データベース初期化エラー: {e}")
            raise

if __name__ == "__main__":
    init_database() 