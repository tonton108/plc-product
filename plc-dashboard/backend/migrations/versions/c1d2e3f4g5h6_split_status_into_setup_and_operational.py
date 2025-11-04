"""ステータスをsetup_statusとoperational_statusに分離

Revision ID: c1d2e3f4g5h6
Revises: b2c3d4e5f6a7
Create Date: 2025-11-02 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    """
    既存のstatusフィールドをsetup_statusとoperational_statusに分離

    変換ルール:
    - "登録済み" → setup_status="基本情報登録済み", operational_status="未稼働"
    - "設定済み" → setup_status="PLC設定済み", operational_status="未稼働"
    - "正常" → setup_status="セットアップ完了", operational_status="稼働中"
    - その他 → setup_status="セットアップ完了", operational_status=元の値
    """

    # 1. 新しいカラムを追加
    op.add_column('equipments', sa.Column('setup_status', sa.String(50), nullable=True))
    op.add_column('equipments', sa.Column('operational_status', sa.String(50), nullable=True))

    # 2. 既存データを変換
    connection = op.get_bind()

    # 「登録済み」の設備
    connection.execute(sa.text("""
        UPDATE equipments
        SET setup_status = '基本情報登録済み',
            operational_status = '未稼働'
        WHERE status = '登録済み'
    """))

    # 「設定済み」の設備
    connection.execute(sa.text("""
        UPDATE equipments
        SET setup_status = 'PLC設定済み',
            operational_status = '未稼働'
        WHERE status = '設定済み'
    """))

    # 「正常」の設備
    connection.execute(sa.text("""
        UPDATE equipments
        SET setup_status = 'セットアップ完了',
            operational_status = '稼働中'
        WHERE status = '正常'
    """))

    # その他のステータス（異常、警告、エラーなど）
    connection.execute(sa.text("""
        UPDATE equipments
        SET setup_status = 'セットアップ完了',
            operational_status = status
        WHERE status NOT IN ('登録済み', '設定済み', '正常')
        AND setup_status IS NULL
    """))

    # NULLが残っている場合（念のため）
    connection.execute(sa.text("""
        UPDATE equipments
        SET setup_status = 'セットアップ完了',
            operational_status = '未稼働'
        WHERE setup_status IS NULL
    """))

    # 3. NOT NULL制約を追加
    op.alter_column('equipments', 'setup_status', nullable=False)
    op.alter_column('equipments', 'operational_status', nullable=False)

    # 4. 古いstatusカラムを削除
    op.drop_column('equipments', 'status')


def downgrade():
    """
    setup_statusとoperational_statusを元のstatusに戻す
    """

    # 1. 古いstatusカラムを追加
    op.add_column('equipments', sa.Column('status', sa.String(50), nullable=True))

    # 2. データを逆変換
    connection = op.get_bind()

    # セットアップ状態に応じて変換
    connection.execute(sa.text("""
        UPDATE equipments
        SET status = '登録済み'
        WHERE setup_status = '基本情報登録済み'
    """))

    connection.execute(sa.text("""
        UPDATE equipments
        SET status = '設定済み'
        WHERE setup_status = 'PLC設定済み'
    """))

    # セットアップ完了済みの場合は運用ステータスを採用
    connection.execute(sa.text("""
        UPDATE equipments
        SET status = CASE
            WHEN operational_status = '稼働中' THEN '正常'
            ELSE operational_status
        END
        WHERE setup_status = 'セットアップ完了'
    """))

    # NULLが残っている場合
    connection.execute(sa.text("""
        UPDATE equipments
        SET status = '正常'
        WHERE status IS NULL
    """))

    # 3. NOT NULL制約を追加
    op.alter_column('equipments', 'status', nullable=False)

    # 4. 新しいカラムを削除
    op.drop_column('equipments', 'operational_status')
    op.drop_column('equipments', 'setup_status')
