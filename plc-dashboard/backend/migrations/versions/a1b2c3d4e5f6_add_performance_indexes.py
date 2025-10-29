"""Add performance indexes

Revision ID: a1b2c3d4e5f6
Revises: 27e1e8566303
Create Date: 2025-10-29 21:30:00.000000

このマイグレーションは、クエリパフォーマンスを大幅に向上させるための
インデックスを追加します。

参考: _docs/analysis/db-design-review.md
参考: _docs/decisions/query-optimization.md
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '27e1e8566303'
branch_labels = None
depends_on = None


def upgrade():
    # logs テーブルにインデックスを追加
    # タイムスタンプ検索の高速化
    op.create_index('idx_logs_timestamp', 'logs', ['timestamp'], unique=False)

    # 設備別 + 期間検索の高速化（複合インデックス）
    # 典型的なクエリ: WHERE equipment_id = X AND timestamp BETWEEN Y AND Z
    op.create_index('idx_logs_equipment_timestamp', 'logs',
                    ['equipment_id', 'timestamp'], unique=False)

    # daily_log_summaries テーブルにインデックスを追加
    # 設備別 + 日付検索の高速化（複合インデックス）
    # 典型的なクエリ: WHERE equipment_id = X AND date BETWEEN Y AND Z
    op.create_index('idx_daily_summary_equipment_date', 'daily_log_summaries',
                    ['equipment_id', 'date'], unique=False)

    # monthly_log_summaries テーブルにインデックスを追加
    # 設備別 + 年月検索の高速化（複合インデックス）
    # 典型的なクエリ: WHERE equipment_id = X AND year = Y AND month = Z
    op.create_index('idx_monthly_summary_equipment_year_month',
                    'monthly_log_summaries',
                    ['equipment_id', 'year', 'month'], unique=False)


def downgrade():
    # インデックスを削除
    op.drop_index('idx_monthly_summary_equipment_year_month',
                  table_name='monthly_log_summaries')
    op.drop_index('idx_daily_summary_equipment_date',
                  table_name='daily_log_summaries')
    op.drop_index('idx_logs_equipment_timestamp', table_name='logs')
    op.drop_index('idx_logs_timestamp', table_name='logs')
