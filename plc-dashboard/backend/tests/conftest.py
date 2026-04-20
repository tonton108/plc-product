"""
Pytest設定とフィクスチャ定義
"""
import pytest
import os
from app import create_app, db as _db
from db.models import Equipment, PLCDataConfig, Log


@pytest.fixture(scope='session')
def app():
    """テスト用Flaskアプリケーションを作成"""
    # テスト環境を明示的に設定
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['TESTING'] = '1'

    app, socketio = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # インメモリDB
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='function', autouse=True)
def session(app):
    """各テストケースごとにデータベーストランザクションをクリーンアップ"""
    with app.app_context():
        yield _db.session

        # テスト後に全データを削除
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture(scope='function')
def client(app, session):
    """テスト用Flaskクライアントを作成"""
    return app.test_client()


@pytest.fixture(scope='function')
def sample_equipment(session):
    """サンプル設備を作成"""
    equipment = Equipment(
        equipment_id="TEST_001",
        manufacturer="Mitsubishi",
        series="iQ-R",
        ip="192.168.1.10",
        plc_ip="192.168.1.100",
        mac_address="00:11:22:33:44:55",
        cpu_serial_number="CPU_TEST_001",
        hostname="test-raspi",
        port=5000,
        modbus_port=502,
        interval=5000,
        setup_status="基本情報登録済み",
        operational_status="未稼働"
    )
    session.add(equipment)
    session.commit()
    return equipment


@pytest.fixture(scope='function')
def sample_plc_config(session, sample_equipment):
    """サンプルPLC設定を作成"""
    config = PLCDataConfig(
        equipment_id=sample_equipment.id,
        data_type="production_count",
        enabled=True,
        address="D100",
        scale_factor=1,
        plc_data_type="word"
    )
    session.add(config)
    session.commit()
    return config
