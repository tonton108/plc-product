#!/bin/bash
set -e

echo "========================================="
echo "PLC Monitoring System - Starting Backend"
echo "========================================="

# データベース接続待機
echo "Waiting for database connection..."
python -c "
import time
import sys
from sqlalchemy import create_engine, text
import os

database_url = os.getenv('DATABASE_URL')
if not database_url:
    print('DATABASE_URL not set, using SQLite')
    sys.exit(0)

engine = create_engine(database_url)
max_retries = 30
for i in range(max_retries):
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('✅ Database connection successful!')
        break
    except Exception as e:
        if i < max_retries - 1:
            print(f'Waiting for database... ({i+1}/{max_retries})')
            time.sleep(1)
        else:
            print(f'❌ Failed to connect to database: {e}')
            sys.exit(1)
"

# テーブル作成（マイグレーションの代替）
echo "Creating database tables..."
python -c "
from app import create_app, db
app, _ = create_app()
with app.app_context():
    db.create_all()
    print('✅ Database tables created/verified')
"

echo "========================================="
echo "Starting application..."
echo "========================================="

# アプリケーション起動
exec "$@"
