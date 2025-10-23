#!/usr/bin/env python3
"""
PostgreSQL接続テスト
"""

import psycopg2
from dotenv import load_dotenv
import os

# .envファイルを読み込み
load_dotenv()

def test_connection():
    try:
        database_url = os.getenv("DATABASE_URL")
        print(f"🔗 接続テスト: {database_url}")
        
        # PostgreSQL接続（psycopg2形式のURLをパース）
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="plc_monitor",
            user="plc_user",
            password="plc_pass"
        )
        
        # テストクエリ実行
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        print("✅ PostgreSQL接続成功!")
        if version:
            print(f"📊 バージョン: {version[0]}")
        else:
            print("📊 バージョン情報を取得できませんでした")
        
        # テーブル一覧を取得
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        print(f"📋 テーブル数: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_connection() 