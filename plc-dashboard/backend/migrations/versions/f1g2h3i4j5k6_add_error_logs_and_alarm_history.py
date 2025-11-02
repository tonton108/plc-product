"""エラーログとアラーム履歴テーブルの追加（Phase 2）

Revision ID: f1g2h3i4j5k6
Revises: e1f2g3h4i5j6
Create Date: 2025-11-03 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1g2h3i4j5k6'
down_revision = 'e1f2g3h4i5j6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Phase 2: エラーログ・アラーム履歴・PLC状態テーブルを追加
    """

    print("[MIGRATION] Phase 2テーブル作成開始...")

    # 1. communication_error_logs テーブル
    print("[MIGRATION] communication_error_logsテーブルを作成中...")
    op.create_table(
        'communication_error_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('error_type', sa.String(50), nullable=False),
        sa.Column('error_code', sa.String(20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('plc_ip', sa.String(100), nullable=True),
        sa.Column('protocol', sa.String(20), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_method', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipments.id'])
    )

    # インデックス作成
    op.create_index('idx_error_equipment_occurred', 'communication_error_logs',
                    ['equipment_id', 'occurred_at'])
    op.create_index('idx_error_type', 'communication_error_logs', ['error_type'])
    op.create_index('idx_error_unresolved', 'communication_error_logs', ['resolved_at'],
                    postgresql_where=sa.text('resolved_at IS NULL'))

    # カラムコメント追加
    connection = op.get_bind()
    connection.execute(sa.text("COMMENT ON TABLE communication_error_logs IS 'PLC通信エラーログ（タイムアウト・接続失敗等）'"))
    connection.execute(sa.text("COMMENT ON COLUMN communication_error_logs.error_type IS 'エラー種別（TIMEOUT/CONNECTION_FAILED/PROTOCOL_ERROR等）'"))
    connection.execute(sa.text("COMMENT ON COLUMN communication_error_logs.retry_count IS 'リトライ回数（何回目のリトライで発生したか）'"))
    connection.execute(sa.text("COMMENT ON COLUMN communication_error_logs.occurred_at IS 'エラー発生日時（トラブルシューティングの起点）'"))
    connection.execute(sa.text("COMMENT ON COLUMN communication_error_logs.resolved_at IS 'エラー解決日時（NULL=未解決）'"))
    connection.execute(sa.text("COMMENT ON COLUMN communication_error_logs.resolution_method IS '解決方法（AUTO_RETRY/MANUAL_FIX等）'"))

    # 2. alarm_history テーブル
    print("[MIGRATION] alarm_historyテーブルを作成中...")
    op.create_table(
        'alarm_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('alarm_code', sa.String(20), nullable=False),
        sa.Column('alarm_level', sa.String(20), nullable=False),
        sa.Column('alarm_message', sa.Text(), nullable=True),
        sa.Column('alarm_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('cleared_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_by', sa.String(50), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipments.id'])
    )

    # インデックス作成
    op.create_index('idx_alarm_equipment_occurred', 'alarm_history',
                    ['equipment_id', 'occurred_at'], postgresql_ops={'occurred_at': 'DESC'})
    op.create_index('idx_alarm_code', 'alarm_history', ['alarm_code'])
    op.create_index('idx_alarm_level', 'alarm_history', ['alarm_level'])
    op.create_index('idx_alarm_uncleared', 'alarm_history', ['cleared_at'],
                    postgresql_where=sa.text('cleared_at IS NULL'))
    op.create_index('idx_alarm_unacknowledged', 'alarm_history', ['acknowledged'],
                    postgresql_where=sa.text('acknowledged = false'))

    # カラムコメント追加
    connection.execute(sa.text("COMMENT ON TABLE alarm_history IS 'PLCアラーム履歴（警告・エラー・致命的）'"))
    connection.execute(sa.text("COMMENT ON COLUMN alarm_history.alarm_code IS 'PLCから送信されるアラームコード（E001, W123等）'"))
    connection.execute(sa.text("COMMENT ON COLUMN alarm_history.alarm_level IS 'アラームレベル（WARNING/ERROR/CRITICAL）'"))
    connection.execute(sa.text("COMMENT ON COLUMN alarm_history.occurred_at IS 'アラーム発生日時'"))
    connection.execute(sa.text("COMMENT ON COLUMN alarm_history.cleared_at IS 'アラーム解除日時（NULL=継続中）'"))
    connection.execute(sa.text("COMMENT ON COLUMN alarm_history.acknowledged IS 'オペレーター確認済みフラグ'"))

    # 3. plc_status テーブル
    print("[MIGRATION] plc_statusテーブルを作成中...")
    op.create_table(
        'plc_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('last_communication_at', sa.DateTime(), nullable=True),
        sa.Column('is_online', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('consecutive_errors', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error_type', sa.String(50), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_status_change_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('equipment_id'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipments.id'])
    )

    # インデックス作成
    op.create_index('idx_plc_status_online', 'plc_status', ['is_online'])
    op.create_index('idx_plc_status_last_comm', 'plc_status', ['last_communication_at'])

    # カラムコメント追加
    connection.execute(sa.text("COMMENT ON TABLE plc_status IS 'PLC通信状態のリアルタイム監視'"))
    connection.execute(sa.text("COMMENT ON COLUMN plc_status.is_online IS 'PLC通信可能状態（5分以上通信なし→FALSE）'"))
    connection.execute(sa.text("COMMENT ON COLUMN plc_status.consecutive_errors IS '連続エラー回数（3回以上で警告、10回以上でアラート）'"))
    connection.execute(sa.text("COMMENT ON COLUMN plc_status.uptime_seconds IS '累積稼働時間（メンテナンス計画に使用）'"))

    # 4. 既存設備に対してplc_statusレコードを初期化
    print("[MIGRATION] 既存設備のplc_statusを初期化中...")
    connection.execute(sa.text("""
        INSERT INTO plc_status (equipment_id, is_online, consecutive_errors, uptime_seconds)
        SELECT id, false, 0, 0 FROM equipments
    """))

    print("[MIGRATION] Phase 2テーブル作成完了")


def downgrade():
    """
    Phase 2テーブルを削除
    """

    print("[MIGRATION] Phase 2テーブルを削除中...")

    # カラムコメント削除
    connection = op.get_bind()
    connection.execute(sa.text("COMMENT ON TABLE plc_status IS NULL"))
    connection.execute(sa.text("COMMENT ON TABLE alarm_history IS NULL"))
    connection.execute(sa.text("COMMENT ON TABLE communication_error_logs IS NULL"))

    # インデックス削除（テーブル削除時に自動削除されるが、明示的に記載）
    op.drop_index('idx_plc_status_last_comm', table_name='plc_status')
    op.drop_index('idx_plc_status_online', table_name='plc_status')

    op.drop_index('idx_alarm_unacknowledged', table_name='alarm_history')
    op.drop_index('idx_alarm_uncleared', table_name='alarm_history')
    op.drop_index('idx_alarm_level', table_name='alarm_history')
    op.drop_index('idx_alarm_code', table_name='alarm_history')
    op.drop_index('idx_alarm_equipment_occurred', table_name='alarm_history')

    op.drop_index('idx_error_unresolved', table_name='communication_error_logs')
    op.drop_index('idx_error_type', table_name='communication_error_logs')
    op.drop_index('idx_error_equipment_occurred', table_name='communication_error_logs')

    # テーブル削除
    op.drop_table('plc_status')
    op.drop_table('alarm_history')
    op.drop_table('communication_error_logs')

    print("[MIGRATION] Phase 2ダウングレード完了")
