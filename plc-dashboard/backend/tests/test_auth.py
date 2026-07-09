"""
認証（Phase 1）のテスト

- ログイン/ログアウト/me
- 無認証アクセスの401
- ロール不足の403
- APIキー認証
"""
import json


class TestLogin:
    """ログインAPIのテスト"""

    def test_login_success(self, unauth_client, admin_user):
        """正しい資格情報でログインするとトークンとユーザー情報が返る"""
        response = unauth_client.post('/api/auth/login', json={
            "username": "test_admin",
            "password": "test-admin-password",
        })
        assert response.status_code == 200
        assert response.json['token']
        assert response.json['user']['username'] == 'test_admin'
        assert response.json['user']['role'] == 'admin'
        assert 'password_hash' not in response.json['user']

    def test_login_wrong_password(self, unauth_client, admin_user):
        """誤ったパスワードでは401"""
        response = unauth_client.post('/api/auth/login', json={
            "username": "test_admin",
            "password": "wrong-password",
        })
        assert response.status_code == 401

    def test_login_unknown_user(self, unauth_client):
        """存在しないユーザーでは401（存在有無を漏らさない）"""
        response = unauth_client.post('/api/auth/login', json={
            "username": "nobody",
            "password": "whatever",
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, unauth_client):
        """ユーザー名・パスワード未指定は400"""
        response = unauth_client.post('/api/auth/login', json={})
        assert response.status_code == 400

    def test_login_inactive_user(self, unauth_client, session, admin_user):
        """無効化されたユーザーはログインできない"""
        admin_user.is_active = False
        session.commit()
        response = unauth_client.post('/api/auth/login', json={
            "username": "test_admin",
            "password": "test-admin-password",
        })
        assert response.status_code == 401


class TestTokenLifecycle:
    """トークンのライフサイクルのテスト"""

    def test_me_with_valid_token(self, unauth_client, admin_token):
        """有効なトークンで /api/auth/me が通る"""
        response = unauth_client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {admin_token}',
        })
        assert response.status_code == 200
        assert response.json['user']['username'] == 'test_admin'

    def test_logout_invalidates_token(self, unauth_client, admin_token):
        """ログアウト後は同じトークンが使えない"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        response = unauth_client.post('/api/auth/logout', headers=headers)
        assert response.status_code == 200

        response = unauth_client.get('/api/auth/me', headers=headers)
        assert response.status_code == 401

    def test_invalid_token_rejected(self, unauth_client, admin_user):
        """でたらめなトークンは401"""
        response = unauth_client.get('/api/auth/me', headers={
            'Authorization': 'Bearer not-a-real-token',
        })
        assert response.status_code == 401


class TestEndpointProtection:
    """エンドポイント保護のテスト"""

    def test_equipment_list_requires_auth(self, unauth_client):
        """設備一覧は無認証で401"""
        response = unauth_client.get('/api/equipment')
        assert response.status_code == 401

    def test_logs_history_requires_auth(self, unauth_client, sample_equipment):
        """ログ履歴は無認証で401"""
        response = unauth_client.get(f'/api/logs/{sample_equipment.equipment_id}/history')
        assert response.status_code == 401

    def test_admin_stats_requires_admin_role(self, operator_client):
        """operatorロールでは管理APIは403"""
        response = operator_client.get('/api/admin/stats')
        assert response.status_code == 403

    def test_operator_can_read_equipment(self, operator_client, sample_equipment):
        """operatorロールでも閲覧系は許可"""
        response = operator_client.get('/api/equipment')
        assert response.status_code == 200

    def test_operator_cannot_save_equipment_config(self, operator_client, sample_equipment):
        """operatorロールでは設備設定の変更は403"""
        response = operator_client.put(
            f'/api/equipment/{sample_equipment.equipment_id}',
            json={"manufacturer": "Keyence"},
        )
        assert response.status_code == 403

    def test_health_is_public(self, unauth_client):
        """ヘルスチェックは無認証で通る"""
        response = unauth_client.get('/api/health')
        assert response.status_code == 200


class TestApiKeyAuth:
    """エージェントAPIキー認証のテスト"""

    def test_logs_post_requires_api_key(self, unauth_client, sample_equipment):
        """/api/logs はAPIキーなしで401"""
        response = unauth_client.post('/api/logs', json={
            "equipment_id": sample_equipment.equipment_id,
            "production_count": 1,
        })
        assert response.status_code == 401

    def test_logs_post_with_api_key(self, unauth_client, agent_api_key, sample_equipment):
        """有効なAPIキーで /api/logs が通る"""
        response = unauth_client.post(
            '/api/logs',
            json={
                "equipment_id": sample_equipment.equipment_id,
                "production_count": 1,
                "current": 1.0,
            },
            headers={'X-API-Key': agent_api_key},
        )
        assert response.status_code == 200

    def test_register_with_api_key(self, unauth_client, agent_api_key):
        """有効なAPIキーで /api/register が通る"""
        data = {
            "equipment_id": "KEY_001",
            "manufacturer": "Mitsubishi",
            "series": "iQ-R",
            "ip": "192.168.1.30",
            "plc_ip": "192.168.1.130",
            "mac_address": "00:AA:BB:CC:DD:FF",
            "cpu_serial_number": "CPU_KEY_001",
            "hostname": "key-raspi",
            "port": 5000,
            "interval": 5000,
        }
        response = unauth_client.post(
            '/api/register',
            data=json.dumps(data),
            content_type='application/json',
            headers={'X-API-Key': agent_api_key},
        )
        assert response.status_code == 200

    def test_invalid_api_key_rejected(self, unauth_client, sample_equipment):
        """でたらめなAPIキーは401"""
        response = unauth_client.post(
            '/api/logs',
            json={"equipment_id": sample_equipment.equipment_id},
            headers={'X-API-Key': 'not-a-real-key'},
        )
        assert response.status_code == 401

    def test_revoked_api_key_rejected(self, unauth_client, session, agent_api_key, sample_equipment):
        """失効させたAPIキーは401"""
        from db.models import AgentApiKey
        from db.models.auth import hash_token
        record = AgentApiKey.query.filter_by(key_hash=hash_token(agent_api_key)).first()
        record.is_active = False
        session.commit()

        response = unauth_client.post(
            '/api/logs',
            json={"equipment_id": sample_equipment.equipment_id},
            headers={'X-API-Key': agent_api_key},
        )
        assert response.status_code == 401

    def test_user_token_cannot_post_logs(self, unauth_client, admin_token, sample_equipment):
        """/api/logs はエージェント専用（ユーザートークンでは401）"""
        response = unauth_client.post(
            '/api/logs',
            json={"equipment_id": sample_equipment.equipment_id},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert response.status_code == 401
