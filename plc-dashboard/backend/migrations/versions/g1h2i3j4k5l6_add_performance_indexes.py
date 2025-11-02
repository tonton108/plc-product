"""パフォーマンス最適化インデックスの追加（Phase 3）

Revision ID: g1h2i3j4k5l6
Revises: f1g2h3i4j5k6
Create Date: 2025-11-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g1h2i3j4k5l6'
down_revision = 'f1g2h3i4j5k6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Phase 3: パフォーマンス最適化インデックスを追加

    最適化対象:
    1. logs テーブル: equipment_id + timestamp (最重要)
    2. plc_data_configs テーブル: equipment_id
    3. daily_log_summaries テーブル: date降順最適化
    """

    print("[MIGRATION] Phase 3インデックス作成開始...")

    # 1. logsテーブルの最適化（最重要）
    print("[MIGRATION] logsテーブルにインデックスを作成中...")

    # equipment_id + timestamp DESC の複合インデックス
    # 用途: 設備ごとの最新データ取得、時系列範囲検索
    op.create_index(
        'idx_logs_equipment_timestamp',
        'logs',
        ['equipment_id', sa.text('timestamp DESC')],
        postgresql_ops={'timestamp': 'DESC'}
    )
    print("[MIGRATION] ✅ idx_logs_equipment_timestamp 作成完了")

    # timestamp のみのインデックス（全設備の時系列検索用）
    op.create_index(
        'idx_logs_timestamp',
        'logs',
        [sa.text('timestamp DESC')],
        postgresql_ops={'timestamp': 'DESC'}
    )
    print("[MIGRATION] ✅ idx_logs_timestamp 作成完了")

    # 2. plc_data_configsテーブルの最適化
    print("[MIGRATION] plc_data_configsテーブルにインデックスを作成中...")

    # equipment_id のインデックス（JOIN最適化）
    op.create_index(
        'idx_plc_configs_equipment',
        'plc_data_configs',
        ['equipment_id']
    )
    print("[MIGRATION] ✅ idx_plc_configs_equipment 作成完了")

    # enabled フラグのインデックス（有効な設定のみ取得）
    op.create_index(
        'idx_plc_configs_enabled',
        'plc_data_configs',
        ['enabled']
    )
    print("[MIGRATION] ✅ idx_plc_configs_enabled 作成完了")

    # 3. daily_log_summariesテーブルの最適化
    print("[MIGRATION] daily_log_summariesテーブルにインデックスを作成中...")

    # equipment_id + date DESC の複合インデックス
    # 注: UNIQUE制約(uq_equipment_date)が既に存在するが、降順検索に最適化されていない
    op.create_index(
        'idx_daily_summary_equipment_date_desc',
        'daily_log_summaries',
        ['equipment_id', sa.text('date DESC')],
        postgresql_ops={'date': 'DESC'}
    )
    print("[MIGRATION] ✅ idx_daily_summary_equipment_date_desc 作成完了")

    # 4. monthly_log_summariesテーブルの最適化
    print("[MIGRATION] monthly_log_summariesテーブルにインデックスを作成中...")

    # equipment_id + year DESC + month DESC の複合インデックス
    op.create_index(
        'idx_monthly_summary_equipment_year_month_desc',
        'monthly_log_summaries',
        ['equipment_id', sa.text('year DESC'), sa.text('month DESC')],
        postgresql_ops={'year': 'DESC', 'month': 'DESC'}
    )
    print("[MIGRATION] ✅ idx_monthly_summary_equipment_year_month_desc 作成完了")

    # カラムコメント追加
    connection = op.get_bind()

    print("[MIGRATION] カラムコメントを追加中...")
    connection.execute(sa.text("COMMENT ON INDEX idx_logs_equipment_timestamp IS '設備ごとの時系列検索用（最新データ取得、範囲検索）'"))
    connection.execute(sa.text("COMMENT ON INDEX idx_logs_timestamp IS '全設備の時系列検索用（グローバル検索）'"))
    connection.execute(sa.text("COMMENT ON INDEX idx_plc_configs_equipment IS 'PLC設定のJOIN最適化用'"))
    connection.execute(sa.text("COMMENT ON INDEX idx_plc_configs_enabled IS '有効な設定のみ取得用'"))
    connection.execute(sa.text("COMMENT ON INDEX idx_daily_summary_equipment_date_desc IS '日次集計の降順検索最適化用'"))
    connection.execute(sa.text("COMMENT ON INDEX idx_monthly_summary_equipment_year_month_desc IS '月次集計の降順検索最適化用'"))

    print("[MIGRATION] Phase 3インデックス作成完了")
    print("[MIGRATION] 期待される効果:")
    print("[MIGRATION]   - logsテーブル検索: 10倍以上高速化")
    print("[MIGRATION]   - JOIN操作: 3-5倍高速化")
    print("[MIGRATION]   - 最新データ取得: 50倍以上高速化")


def downgrade():
    """
    Phase 3インデックスを削除
    """

    print("[MIGRATION] Phase 3インデックスを削除中...")

    # インデックスコメント削除
    connection = op.get_bind()
    connection.execute(sa.text("COMMENT ON INDEX idx_logs_equipment_timestamp IS NULL"))
    connection.execute(sa.text("COMMENT ON INDEX idx_logs_timestamp IS NULL"))
    connection.execute(sa.text("COMMENT ON INDEX idx_plc_configs_equipment IS NULL"))
    connection.execute(sa.text("COMMENT ON INDEX idx_plc_configs_enabled IS NULL"))
    connection.execute(sa.text("COMMENT ON INDEX idx_daily_summary_equipment_date_desc IS NULL"))
    connection.execute(sa.text("COMMENT ON INDEX idx_monthly_summary_equipment_year_month_desc IS NULL"))

    # インデックス削除
    op.drop_index('idx_monthly_summary_equipment_year_month_desc', table_name='monthly_log_summaries')
    op.drop_index('idx_daily_summary_equipment_date_desc', table_name='daily_log_summaries')
    op.drop_index('idx_plc_configs_enabled', table_name='plc_data_configs')
    op.drop_index('idx_plc_configs_equipment', table_name='plc_data_configs')
    op.drop_index('idx_logs_timestamp', table_name='logs')
    op.drop_index('idx_logs_equipment_timestamp', table_name='logs')

    print("[MIGRATION] Phase 3ダウングレード完了")
