"""認証テーブルの追加（Phase 1: users / auth_tokens / agent_api_keys）

Revision ID: i1j2k3l4m5n6
Revises: h1i2j3k4l5m6
Create Date: 2026-07-10 05:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'i1j2k3l4m5n6'
down_revision = 'h1i2j3k4l5m6'
branch_labels = None
depends_on = None


def upgrade():
    """Phase 1: ユーザー・ログイントークン・エージェントAPIキーのテーブルを追加"""

    print("[MIGRATION] 認証テーブル作成開始...")

    # 1. users テーブル
    print("[MIGRATION] usersテーブルを作成中...")
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='operator'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_users_username'),
    )

    # 2. auth_tokens テーブル
    print("[MIGRATION] auth_tokensテーブルを作成中...")
    op.create_table(
        'auth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.UniqueConstraint('token_hash', name='uq_auth_tokens_token_hash'),
    )
    op.create_index('ix_auth_tokens_token_hash', 'auth_tokens', ['token_hash'])

    # 3. agent_api_keys テーブル
    print("[MIGRATION] agent_api_keysテーブルを作成中...")
    op.create_table(
        'agent_api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(64), nullable=False),
        # equipment_id が NULL のキーは全設備共有キー（SPEC.md §4.2）
        sa.Column('equipment_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipments.id']),
        sa.UniqueConstraint('key_hash', name='uq_agent_api_keys_key_hash'),
    )
    op.create_index('ix_agent_api_keys_key_hash', 'agent_api_keys', ['key_hash'])

    print("[MIGRATION] 認証テーブル作成完了")


def downgrade():
    """認証テーブルを削除"""
    op.drop_index('ix_agent_api_keys_key_hash', table_name='agent_api_keys')
    op.drop_table('agent_api_keys')
    op.drop_index('ix_auth_tokens_token_hash', table_name='auth_tokens')
    op.drop_table('auth_tokens')
    op.drop_table('users')
