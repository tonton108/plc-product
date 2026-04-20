"""scale_factorカラムをInteger→Floatに変更

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-04-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h1i2j3k4l5m6'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('plc_data_configs', schema=None) as batch_op:
        batch_op.alter_column('scale_factor',
                              existing_type=sa.Integer(),
                              type_=sa.Float(),
                              existing_nullable=True)


def downgrade():
    with op.batch_alter_table('plc_data_configs', schema=None) as batch_op:
        batch_op.alter_column('scale_factor',
                              existing_type=sa.Float(),
                              type_=sa.Integer(),
                              existing_nullable=True)
