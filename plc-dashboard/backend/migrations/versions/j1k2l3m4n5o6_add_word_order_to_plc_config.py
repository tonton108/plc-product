"""PLCDataConfigにword_order列を追加（Phase 2: 32bitワード順序のメーカー別対応）

Revision ID: j1k2l3m4n5o6
Revises: i1j2k3l4m5n6
Create Date: 2026-07-10 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'j1k2l3m4n5o6'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade():
    """plc_data_configs に word_order 列を追加

    既定は 'low_first'（三菱MELSECの32bit値は先頭アドレス=下位ワード）。
    既存行にも server_default で 'low_first' が入る。
    """
    op.add_column(
        'plc_data_configs',
        sa.Column('word_order', sa.String(20), nullable=False, server_default='low_first')
    )


def downgrade():
    op.drop_column('plc_data_configs', 'word_order')
