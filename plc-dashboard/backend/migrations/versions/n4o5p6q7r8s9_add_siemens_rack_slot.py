"""Siemens S7用 Rack/Slot設定の追加（Issue #58）

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-07-20 00:00:00.000000

S7-300/400は slot=2 が必須だが、設定経路が無くドライバ既定の
rack=0/slot=1 に固定されていた。設備ごとに rack/slot を保持できるよう
equipments テーブルへカラムを追加する。既定は S7-1200/1500 の rack=0/slot=1。
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "n4o5p6q7r8s9"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade():
    """rack / slot カラムを追加（既定 rack=0 / slot=1）"""
    print("[MIGRATION] Siemens Rack/Slotカラムを追加中...")

    # nullable=True で追加 → 既存行をデフォルト値で埋める → NOT NULL化
    # （既存のPhase 1通信設定マイグレーションと同じ手順）
    op.add_column("equipments", sa.Column("rack", sa.Integer(), nullable=True))
    op.add_column("equipments", sa.Column("slot", sa.Integer(), nullable=True))

    connection = op.get_bind()

    print("[MIGRATION] 既存データにデフォルト値を設定中...")
    connection.execute(sa.text("UPDATE equipments SET rack = 0 WHERE rack IS NULL"))
    connection.execute(sa.text("UPDATE equipments SET slot = 1 WHERE slot IS NULL"))

    print("[MIGRATION] NOT NULL制約を追加中...")
    op.alter_column("equipments", "rack", existing_type=sa.Integer(), nullable=False)
    op.alter_column("equipments", "slot", existing_type=sa.Integer(), nullable=False)

    # カラムコメント（PostgreSQL用）
    connection.execute(
        sa.text(
            "COMMENT ON COLUMN equipments.rack IS "
            "'Siemens S7のRack番号（通常0。他メーカーでは未使用）'"
        )
    )
    connection.execute(
        sa.text(
            "COMMENT ON COLUMN equipments.slot IS "
            "'Siemens S7のSlot番号（S7-1200/1500=1、S7-300/400=2。他メーカーでは未使用）'"
        )
    )

    print("[MIGRATION] Siemens Rack/Slotマイグレーション完了")


def downgrade():
    """rack / slot カラムを削除"""
    print("[MIGRATION] Siemens Rack/Slotカラムを削除中...")

    connection = op.get_bind()
    connection.execute(sa.text("COMMENT ON COLUMN equipments.rack IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.slot IS NULL"))

    op.drop_column("equipments", "slot")
    op.drop_column("equipments", "rack")

    print("[MIGRATION] ダウングレード完了")
