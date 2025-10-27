#!/usr/bin/env python3
"""
データベーステーブル初期化スクリプト
PostgreSQL Portable用：すべてのテーブルを一度に作成
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def init_database():
    """データベースを初期化してすべてのテーブルを作成"""
    app, _ = create_app()

    with app.app_context():
        try:
            # すべてのテーブルを作成
            db.create_all()
            print("[init_tables] テーブル作成成功")

            # 作成されたテーブルを確認
            tables = db.Model.metadata.tables.keys()
            print(f"[init_tables] 作成されたテーブル: {list(tables)}")

            return 0
        except Exception as e:
            print(f"[init_tables] エラー: {e}")
            return 1

if __name__ == "__main__":
    sys.exit(init_database())
