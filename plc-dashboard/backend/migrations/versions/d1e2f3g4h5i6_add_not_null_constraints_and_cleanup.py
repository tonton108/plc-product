"""NULL制約追加とデータクリーンアップ

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2025-11-02 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3g4h5i6'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


def upgrade():
    """
    1. 古いデータをクリーンアップ（NULL値を持つレコード）
    2. NOT NULL制約を追加
    3. カラムにコメントを追加
    """

    connection = op.get_bind()

    # 1. cpu_serial_numberがNULLのレコードにダミー値を設定
    print("[MIGRATION] cpu_serial_numberがNULLのレコードを修正中...")
    result = connection.execute(sa.text("""
        UPDATE equipments
        SET cpu_serial_number = 'LEGACY_' || id::text
        WHERE cpu_serial_number IS NULL OR cpu_serial_number = ''
    """))
    print(f"[MIGRATION] {result.rowcount}件のcpu_serial_numberを修正しました")

    # 2. plc_ipがNULLのレコードにデフォルト値を設定
    print("[MIGRATION] plc_ipがNULLのレコードを修正中...")
    result = connection.execute(sa.text("""
        UPDATE equipments
        SET plc_ip = ip
        WHERE plc_ip IS NULL OR plc_ip = ''
    """))
    print(f"[MIGRATION] {result.rowcount}件のplc_ipを修正しました")

    # 3. portがNULLのレコードにデフォルト値（502）を設定
    print("[MIGRATION] portがNULLのレコードを修正中...")
    result = connection.execute(sa.text("""
        UPDATE equipments
        SET port = 502
        WHERE port IS NULL
    """))
    print(f"[MIGRATION] {result.rowcount}件のportを修正しました")

    # 4. manufacturerがNULLのレコードにデフォルト値を設定
    print("[MIGRATION] manufacturerがNULLのレコードを修正中...")
    result = connection.execute(sa.text("""
        UPDATE equipments
        SET manufacturer = 'Unknown'
        WHERE manufacturer IS NULL OR manufacturer = ''
    """))
    print(f"[MIGRATION] {result.rowcount}件のmanufacturerを修正しました")

    # 5. seriesがNULLのレコードにデフォルト値を設定
    print("[MIGRATION] seriesがNULLのレコードを修正中...")
    result = connection.execute(sa.text("""
        UPDATE equipments
        SET series = 'Unknown'
        WHERE series IS NULL OR series = ''
    """))
    print(f"[MIGRATION] {result.rowcount}件のseriesを修正しました")

    # 6. intervalがNULLのレコードにデフォルト値（1000ms）を設定
    print("[MIGRATION] intervalがNULLのレコードを修正中...")
    result = connection.execute(sa.text("""
        UPDATE equipments
        SET interval = 1000
        WHERE interval IS NULL
    """))
    print(f"[MIGRATION] {result.rowcount}件のintervalを修正しました")

    # 7. NOT NULL制約を追加
    print("[MIGRATION] NOT NULL制約を追加中...")

    # cpu_serial_numberにNOT NULL制約を追加（UNIQUE制約は既にある）
    op.alter_column('equipments', 'cpu_serial_number',
                    existing_type=sa.String(50),
                    nullable=False)

    # plc_ipにNOT NULL制約を追加
    op.alter_column('equipments', 'plc_ip',
                    existing_type=sa.String(100),
                    nullable=False)

    # portにNOT NULL制約を追加
    op.alter_column('equipments', 'port',
                    existing_type=sa.Integer(),
                    nullable=False)

    # manufacturerにNOT NULL制約を追加
    op.alter_column('equipments', 'manufacturer',
                    existing_type=sa.String(50),
                    nullable=False)

    # seriesにNOT NULL制約を追加
    op.alter_column('equipments', 'series',
                    existing_type=sa.String(50),
                    nullable=False)

    # intervalにNOT NULL制約を追加
    op.alter_column('equipments', 'interval',
                    existing_type=sa.Integer(),
                    nullable=False)

    print("[MIGRATION] NOT NULL制約の追加が完了しました")

    # 8. カラムにコメントを追加（PostgreSQL用）
    print("[MIGRATION] カラムコメントを追加中...")

    connection.execute(sa.text("COMMENT ON COLUMN equipments.id IS '内部ID（主キー）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.equipment_id IS 'ユーザー定義の設備識別子（表示用）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.cpu_serial_number IS 'Raspberry PiのCPUシリアル番号（最優先識別子、不変）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.mac_address IS 'Raspberry PiのMACアドレス（準不変識別子、フォールバック用）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.ip IS 'Raspberry PiのIPアドレス（履歴・トラブルシューティング用、通信には不使用）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.plc_ip IS 'PLCのIPアドレス（通信に使用）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.port IS 'PLCの通信ポート'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.modbus_port IS 'Modbusポート（キーエンスKV用、デフォルト502）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.manufacturer IS 'PLCメーカー（プロトコル選択に使用）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.series IS 'PLCシリーズ（プロトコル詳細設定に使用）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.hostname IS 'Raspberry Piのホスト名（システム管理者向け識別子）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.interval IS 'データ収集間隔（ミリ秒）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.setup_status IS 'セットアップ状態（未登録/基本情報登録済み/PLC設定済み/セットアップ完了）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.operational_status IS '運用状態（未稼働/稼働中/警告/エラー/停止中/メンテナンス中）'"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.updated_at IS '最終更新日時（デバッグ・監査用）'"))

    print("[MIGRATION] カラムコメントの追加が完了しました")
    print("[MIGRATION] マイグレーション完了")


def downgrade():
    """
    NOT NULL制約を削除（元に戻す）
    """

    print("[MIGRATION] NOT NULL制約を削除中...")

    # NOT NULL制約を削除
    op.alter_column('equipments', 'cpu_serial_number',
                    existing_type=sa.String(50),
                    nullable=True)

    op.alter_column('equipments', 'plc_ip',
                    existing_type=sa.String(100),
                    nullable=True)

    op.alter_column('equipments', 'port',
                    existing_type=sa.Integer(),
                    nullable=True)

    op.alter_column('equipments', 'manufacturer',
                    existing_type=sa.String(50),
                    nullable=True)

    op.alter_column('equipments', 'series',
                    existing_type=sa.String(50),
                    nullable=True)

    op.alter_column('equipments', 'interval',
                    existing_type=sa.Integer(),
                    nullable=True)

    # コメントを削除
    connection = op.get_bind()
    connection.execute(sa.text("COMMENT ON COLUMN equipments.id IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.equipment_id IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.cpu_serial_number IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.mac_address IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.ip IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.plc_ip IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.port IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.modbus_port IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.manufacturer IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.series IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.hostname IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.interval IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.setup_status IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.operational_status IS NULL"))
    connection.execute(sa.text("COMMENT ON COLUMN equipments.updated_at IS NULL"))

    print("[MIGRATION] ダウングレード完了")
