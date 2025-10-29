"""Add pressure_min and pressure_max to monthly_log_summaries

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-29 21:35:00.000000

monthly_log_summariesテーブルにpressure_maxとpressure_minカラムを追加し、
daily_log_summariesとのデータ粒度を統一します。

参考: _docs/analysis/db-design-review.md
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # monthly_log_summaries テーブルに pressure_max と pressure_min を追加
    with op.batch_alter_table('monthly_log_summaries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pressure_max', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('pressure_min', sa.Float(), nullable=True))


def downgrade():
    # カラムを削除
    with op.batch_alter_table('monthly_log_summaries', schema=None) as batch_op:
        batch_op.drop_column('pressure_min')
        batch_op.drop_column('pressure_max')
