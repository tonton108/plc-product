"""インシデント文脈保全テーブル incident_context を追加（SPEC §5.2）

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-07-12 12:00:00.000000

エラー/アラーム発生時に、該当設備の直前ウィンドウの生ログをJSONで長期保存する。
生ログ本体(logs)は30日でパーティションDROPされるが、この文脈は長期(既定1年)
保持され、過去インシデントを後から調査できるようにする。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'l2m3n4o5p6q7'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'incident_context',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('event_ref_id', sa.Integer(), nullable=False),
        sa.Column('event_time', sa.DateTime(), nullable=False),
        sa.Column('window_start', sa.DateTime(), nullable=False),
        sa.Column('window_end', sa.DateTime(), nullable=False),
        sa.Column('log_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipments.id']),
    )
    op.create_index('ix_incident_context_equipment_id', 'incident_context', ['equipment_id'])
    op.create_index('ix_incident_context_created_at', 'incident_context', ['created_at'])


def downgrade():
    op.drop_index('ix_incident_context_created_at', table_name='incident_context')
    op.drop_index('ix_incident_context_equipment_id', table_name='incident_context')
    op.drop_table('incident_context')
