"""
ユーザー管理API（/api/admin/users）のテスト

admin専用のユーザー一覧・作成・パスワード再設定・有効/無効化と、
権限（401/403）・各種ガード（重複・自己無効化・最後のadmin保護・トークン失効）を検証する。
"""

from db.models import User, AuthToken, UserRoles


def _login_token_works(app, raw_token):
    """発行された平文トークンでBearer認証が通るかを確認するヘルパー"""
    c = app.test_client()
    return c.get('/api/admin/users', headers={'Authorization': f'Bearer {raw_token}'})


# === 一覧 ===

def test_list_users_requires_admin(client, operator_client, unauth_client):
    assert unauth_client.get('/api/admin/users').status_code == 401
    assert operator_client.get('/api/admin/users').status_code == 403
    resp = client.get('/api/admin/users')
    assert resp.status_code == 200
    users = resp.get_json()['users']
    # conftestの test_admin が含まれる
    assert any(u['username'] == 'test_admin' for u in users)
    # password_hash は絶対に返さない
    assert all('password_hash' not in u for u in users)


# === 作成 ===

def test_create_user_generates_password(client, session):
    resp = client.post('/api/admin/users', json={'username': '佐藤', 'role': 'operator'})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['user']['username'] == '佐藤'
    assert body['user']['role'] == 'operator'
    assert body['user']['is_active'] is True
    # 自動生成時のみ平文パスワードを返す
    assert 'generated_password' in body and len(body['generated_password']) > 0
    # 実際にそのパスワードでログインできる
    user = User.query.filter_by(username='佐藤').first()
    assert user is not None and user.check_password(body['generated_password'])


def test_create_user_with_explicit_password_not_returned(client, session):
    resp = client.post('/api/admin/users',
                       json={'username': '鈴木', 'role': 'admin', 'password': 'MyPassw0rd!'})
    assert resp.status_code == 201
    body = resp.get_json()
    # 明示指定時は平文を返さない
    assert 'generated_password' not in body
    user = User.query.filter_by(username='鈴木').first()
    assert user.role == 'admin' and user.check_password('MyPassw0rd!')


def test_create_user_defaults_to_operator(client, session):
    resp = client.post('/api/admin/users', json={'username': '既定ロール'})
    assert resp.status_code == 201
    assert resp.get_json()['user']['role'] == UserRoles.OPERATOR


def test_create_user_validation(client, session):
    assert client.post('/api/admin/users', json={}).status_code == 400
    assert client.post('/api/admin/users', json={'username': '   '}).status_code == 400
    assert client.post('/api/admin/users',
                       json={'username': 'x', 'role': 'superuser'}).status_code == 400
    assert client.post('/api/admin/users',
                       json={'username': 'x', 'password': ''}).status_code == 400


def test_create_user_duplicate(client, session):
    client.post('/api/admin/users', json={'username': '重複太郎'})
    resp = client.post('/api/admin/users', json={'username': '重複太郎'})
    assert resp.status_code == 409


def test_create_user_requires_admin(operator_client, unauth_client):
    assert unauth_client.post('/api/admin/users', json={'username': 'a'}).status_code == 401
    assert operator_client.post('/api/admin/users', json={'username': 'a'}).status_code == 403


# === パスワード再設定 ===

def test_reset_password_generates_and_revokes_tokens(client, app, session):
    # 対象ユーザーとログイントークンを用意
    created = client.post('/api/admin/users',
                          json={'username': 'リセット対象', 'password': 'old-pass'}).get_json()
    user_id = created['user']['id']
    user = User.query.get(user_id)
    token, raw_token = AuthToken.issue(user)
    session.add(token)
    session.commit()
    # リセット前はトークンが有効
    assert _login_token_works(app, raw_token).status_code in (200, 403)  # 少なくとも認証は通る

    resp = client.post(f'/api/admin/users/{user_id}/reset-password', json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert 'generated_password' in body
    # 新パスワードが有効
    assert User.query.get(user_id).check_password(body['generated_password'])
    # 既存トークンは全失効（DBから消える）
    assert AuthToken.query.filter_by(user_id=user_id).count() == 0


def test_reset_password_explicit(client, session):
    created = client.post('/api/admin/users', json={'username': 'pw明示'}).get_json()
    user_id = created['user']['id']
    resp = client.post(f'/api/admin/users/{user_id}/reset-password',
                       json={'password': 'New-Pass-1'})
    assert resp.status_code == 200
    assert 'generated_password' not in resp.get_json()
    assert User.query.get(user_id).check_password('New-Pass-1')


def test_reset_password_empty_rejected(client, session):
    created = client.post('/api/admin/users', json={'username': 'reset空'}).get_json()
    user_id = created['user']['id']
    resp = client.post(f'/api/admin/users/{user_id}/reset-password', json={'password': ''})
    assert resp.status_code == 400


def test_reset_password_not_found(client):
    assert client.post('/api/admin/users/99999/reset-password', json={}).status_code == 404


# === 無効化 / 有効化 ===

def test_deactivate_user_revokes_tokens(client, app, session):
    created = client.post('/api/admin/users', json={'username': '無効化対象'}).get_json()
    user_id = created['user']['id']
    user = User.query.get(user_id)
    token, _ = AuthToken.issue(user)
    session.add(token)
    session.commit()

    resp = client.post(f'/api/admin/users/{user_id}/deactivate')
    assert resp.status_code == 200
    assert resp.get_json()['user']['is_active'] is False
    assert User.query.get(user_id).is_active is False
    assert AuthToken.query.filter_by(user_id=user_id).count() == 0


def test_cannot_deactivate_self(client, admin_user, session):
    # 2人目のadminを作り「最後のadmin」ガードを外した上で、自己無効化が拒否されることを確認
    client.post('/api/admin/users', json={'username': 'admin_other', 'role': 'admin'})
    resp = client.post(f'/api/admin/users/{admin_user.id}/deactivate')
    assert resp.status_code == 400
    assert '自分自身' in resp.get_json()['error']
    assert User.query.get(admin_user.id).is_active is True


def test_cannot_deactivate_last_admin(client, admin_user):
    # test_admin が唯一の有効adminのとき、自分を無効化しようとすると「最後のadmin」で拒否
    resp = client.post(f'/api/admin/users/{admin_user.id}/deactivate')
    assert resp.status_code == 400
    assert '最後の有効なadmin' in resp.get_json()['error']
    assert User.query.get(admin_user.id).is_active is True


def test_deactivate_not_found(client):
    assert client.post('/api/admin/users/99999/deactivate').status_code == 404


def test_can_deactivate_other_admin_when_multiple(client, session):
    # 2人目のadminを作れば、そのadminは無効化できる（最後のadminではない）
    other = client.post('/api/admin/users',
                        json={'username': 'admin2', 'role': 'admin'}).get_json()['user']
    resp = client.post(f'/api/admin/users/{other["id"]}/deactivate')
    assert resp.status_code == 200
    assert User.query.get(other['id']).is_active is False


def test_activate_user(client, session):
    created = client.post('/api/admin/users', json={'username': '再有効化'}).get_json()
    user_id = created['user']['id']
    client.post(f'/api/admin/users/{user_id}/deactivate')
    resp = client.post(f'/api/admin/users/{user_id}/activate')
    assert resp.status_code == 200
    assert resp.get_json()['user']['is_active'] is True
    assert User.query.get(user_id).is_active is True


def test_activate_not_found(client):
    assert client.post('/api/admin/users/99999/activate').status_code == 404


def test_deactivate_requires_admin(operator_client, unauth_client, admin_user):
    assert unauth_client.post(
        f'/api/admin/users/{admin_user.id}/deactivate').status_code == 401
    assert operator_client.post(
        f'/api/admin/users/{admin_user.id}/deactivate').status_code == 403
