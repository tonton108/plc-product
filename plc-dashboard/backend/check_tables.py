import os
import sys
# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.db import db

app = create_app()
with app.app_context():
    # テーブル一覧を表示
    tables = list(db.Model.metadata.tables.keys())
    print('📋 作成されたテーブル一覧:')
    for table in tables:
        print(f'  ✅ {table}')
    
    # equipmentsテーブルのデータ確認
    from backend.db.models import Equipment, PLCDataConfig, Log
    equipments = Equipment.query.all()
    print(f'\n📊 equipmentsテーブルのデータ数: {len(equipments)}')
    for eq in equipments:
        print(f'  - {eq.equipment_id}: {eq.manufacturer} {eq.series} ({eq.ip})')
    
    # plc_data_configsテーブルのデータ確認
    configs = PLCDataConfig.query.all()
    print(f'\n🔧 plc_data_configsテーブルのデータ数: {len(configs)}')
    
    # logsテーブルのデータ確認
    logs = Log.query.all()
    print(f'\n📈 logsテーブルのデータ数: {len(logs)}') 