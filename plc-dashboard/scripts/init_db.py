#!/usr/bin/env python3
"""
データベース初期化スクリプト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# PostgreSQLデータベースを使用
if not os.getenv('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor'

def init_database():
    try:
        print("🗄️ データベース初期化中...")
        
        from backend.app import create_app
        from backend.db import db
        
        # アプリケーション作成
        app, socketio = create_app()
        
        # データベース初期化
        with app.app_context():
            # 既存のテーブルを削除
            db.drop_all()
            print("📝 既存テーブル削除完了")
            
            # 新しいテーブルを作成
            db.create_all()
            print("✅ データベーステーブル作成完了")
            
            # テーブル一覧表示
            tables = list(db.Model.metadata.tables.keys())
            print(f"📋 作成されたテーブル: {tables}")
            
    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🏭 PLCモニタリングシステム - DB初期化")
    print("=" * 50)
    
    if init_database():
        print("✅ データベース初期化完了")
    else:
        print("❌ データベース初期化失敗")
        sys.exit(1) 