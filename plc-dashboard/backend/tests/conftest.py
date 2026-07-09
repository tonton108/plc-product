"""
Pytest設定とフィクスチャ定義
"""
import pytest
import os
from app import create_app, db as _db
from db.models import Equipment, PLCDataConfig, Log
from db.models import User, AuthToken, AgentApiKey, UserRoles


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


def _make_authed_client(app, headers):
    """指定ヘッダを全リクエストに自動付与するテストクライアントを作る"""
    test_client = app.test_client()
    original_open = test_client.open

    def open_with_auth(*args, **kwargs):
        request_headers = kwargs.setdefault('headers', {})
        if isinstance(request_headers, dict):
            for key, value in headers.items():
                request_headers.setdefault(key, value)
        return original_open(*args, **kwargs)

    test_client.open = open_with_auth
    return test_client


@pytest.fixture(scope='function')
def admin_user(session):
    """テスト用adminユーザー"""
    user = User(username='test_admin', password='test-admin-password', role=UserRoles.ADMIN)
    session.add(user)
    session.commit()
    return user


@pytest.fixture(scope='function')
def admin_token(session, admin_user):
    """adminユーザーのBearerトークン（平文）"""
    token, raw_token = AuthToken.issue(admin_user)
    session.add(token)
    session.commit()
    return raw_token


@pytest.fixture(scope='function')
def agent_api_key(session):
    """テスト用エージェントAPIキー（平文）"""
    record, raw_key = AgentApiKey.issue(name='test-shared-key')
    session.add(record)
    session.commit()
    return raw_key


@pytest.fixture(scope='function')
def client(app, session, admin_token, agent_api_key):
    """認証済みテストクライアント（adminトークン＋APIキーを自動付与）

    既存の機能テストが認証必須化後もそのまま通るように、
    人間用トークンとエージェント用APIキーの両方を付与する。
    認証自体の検証（401/403）は test_auth.py の unauth_client 等で行う。
    """
    return _make_authed_client(app, {
        'Authorization': f'Bearer {admin_token}',
        'X-API-Key': agent_api_key,
    })


@pytest.fixture(scope='function')
def unauth_client(app, session):
    """無認証のテストクライアント（401検証用）"""
    return app.test_client()


@pytest.fixture(scope='function')
def operator_client(app, session):
    """operatorロールのテストクライアント（403検証用）"""
    user = User(username='test_operator', password='test-operator-password', role=UserRoles.OPERATOR)
    session.add(user)
    session.commit()
    token, raw_token = AuthToken.issue(user)
    session.add(token)
    session.commit()
    return _make_authed_client(app, {'Authorization': f'Bearer {raw_token}'})


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
