"""インシデント文脈に発生後ウィンドウ（アフターマス）列を追加（SPEC §5.2）

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-07-13 12:00:00.000000

エラー/アラーム発生時点ではまだ存在しない「発生後」の生ログを、スケジューラの
backfillで後追い保存するための列を追加する。after_captured_at がNULLの間は未捕捉。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'm3n4o5p6q7r8'
down_revision = 'l2m3n4o5p6q7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('incident_context') as batch_op:
        batch_op.add_column(sa.Column('after_window_end', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('after_captured_at', sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column('after_log_count', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(sa.Column('after_context_data', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('incident_context') as batch_op:
        batch_op.drop_column('after_context_data')
        batch_op.drop_column('after_log_count')
        batch_op.drop_column('after_captured_at')
        batch_op.drop_column('after_window_end')
