"""PLC通信設定の追加（Phase 1）

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3g4h5i6
Create Date: 2025-11-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2g3h4i5j6'
down_revision = 'd1e2f3g4h5i6'
branch_labels = None
depends_on = None


def upgrade():
    """
    PLC通信設定カラムを追加:
    1. protocol: PLCプロトコル（MC_PROTOCOL_3E, FINS, MODBUSなど）
    2. communication_mode: 通信モード（TCP/UDP）
    3. timeout: タイムアウト時間（ミリ秒）
    4. retry_count: リトライ回数
    5. retry_interval: リトライ間隔（ミリ秒）
    """

    print("[MIGRATION] PLC通信設定カラムを追加中...")

    # 1. protocol カラムを追加
    op.add_column('equipments', sa.Column('protocol', sa.String(20), nullable=True))

    # 2. communication_mode カラムを追加
    op.add_column('equipments', sa.Column('communication_mode', sa.String(20), nullable=True))

    # 3. timeout カラムを追加
    op.add_column('equipments', sa.Column('timeout', sa.Integer(), nullable=True))

    # 4. retry_count カラムを追加
    op.add_column('equipments', sa.Column('retry_count', sa.Integer(), nullable=True))

    # 5. retry_interval カラムを追加
    op.add_column('equipments', sa.Column('retry_interval', sa.Integer(), nullable=True))

    print("[MIGRATION] カラムの追加が完了しました")

    # 既存データにデフォルト値を設定
    connection = op.get_bind()

    print("[MIGRATION] 既存データにデフォルト値を設定中...")

    # manufacturer に応じてプロトコルを推定
    # 三菱 → MC_PROTOCOL_3E
    connection.execute(sa.text("""
        UPDATE equipments
        SET protocol = 'MC_PROTOCOL_3E'
        WHERE manufacturer LIKE '%三菱%' OR manufacturer LIKE '%Mitsubishi%'
    """))

    # オムロン → FINS
    connection.execute(sa.text("""
        UPDATE equipments
        SET protocol = 'FINS'
        WHERE manufacturer LIKE '%オムロン%' OR manufacturer LIKE '%OMRON%'
    """))

    # キーエンス → MODBUS（デフォルトはModbus TCP）
    connection.execute(sa.text("""
        UPDATE equipments
        SET protocol = 'MODBUS'
        WHERE manufacturer LIKE '%キーエンス%' OR manufacturer LIKE '%KEYENCE%'
    """))

    # その他 → MC_PROTOCOL_3E（デフォルト）
    connection.execute(sa.text("""
        UPDATE equipments
        SET protocol = 'MC_PROTOCOL_3E'
        WHERE protocol IS NULL
    """))

    # 通信モードはすべてTCPに設定（一般的なデフォルト）
    connection.execute(sa.text("""
        UPDATE equipments
        SET communication_mode = 'TCP'
        WHERE communication_mode IS NULL
    """))

    # タイムアウト: 5000ms（5秒）
    connection.execute(sa.text("""
        UPDATE equipments
        SET timeout = 5000
        WHERE timeout IS NULL
    """))

    # リトライ回数: 3回
    connection.execute(sa.text("""
        UPDATE equipments
        SET retry_count = 3
        WHERE retry_count IS NULL
    """))

    # リトライ間隔: 1000ms（1秒）
    connection.execute(sa.text("""
        UPDATE equipments
        SET retry_interval = 1000
        WHERE retry_interval IS NULL
    """))

    print("[MIGRATION] デフォルト値の設定が完了しました")

    # NOT NULL制約を追加
    print("[MIGRATION] NOT NULL制約を追加中...")

    op.alter_column('equipments', 'protocol',
                    existing_type=sa.String(20),
                    nullable=False)

    op.alter_column('equipments', 'communication_mode',
                    existing_type=sa.String(20),
                    nullable=False)

    op.alter_column('equipments', 'timeout',
                    existing_type=sa.Integer(),
                    nullable=False)

    op.alter_column('equipments', 'retry_count',
                    existing_type=sa.Integer(),
                    nullable=False)

    op.alter_column('equipments', 'retry_interval',
                    existing_type=sa.Integer(),
                    nullable=False)

    print("[MIGRATION] NOT NULL制約の追加が完了しました")

    # カラムコメントを追加（PostgreSQL用）
    print("[MIGRATION] カラムコメントを追加中...")

    connection.execute(sa.text("COMMENT ON COLUMN equipments.protocol IS 'PLCプロトコル（MC_PROTOCOL_3E/FINS/MODBUSなど、明示的に指定）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.communication_mode IS '通信モード（TCP/UDP、プロトコルによって選択）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.timeout IS 'PLC通信タイムアウト時間（ミリ秒、デフォルト5000ms）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.retry_count IS '通信エラー時のリトライ回数（デフォルト3回）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.retry_interval IS 'リトライ間隔（ミリ秒、デフォルト1000ms）'"))

    print("[MIGRATION] カラムコメントの追加が完了しました")
    print("[MIGRATION] Phase 1マイグレーション完了")


def downgrade():
    """
    PLC通信設定カラムを削除
    """

    print("[MIGRATION] PLC通信設定カラムを削除中...")

    # カラムコメントを削除
    connection = op.get_bind()
    connection.execute(sa.text("COMMENT ON COLUMN equipments.protocol IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.communication_mode IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.timeout IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.retry_count IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.retry_interval IS NULL"))

    # カラムを削除
    op.drop_column('equipments', 'retry_interval')
    op.drop_column('equipments', 'retry_count')
    op.drop_column('equipments', 'timeout')
    op.drop_column('equipments', 'communication_mode')
    op.drop_column('equipments', 'protocol')

    print("[MIGRATION] ダウングレード完了")
