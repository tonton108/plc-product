"""
認証管理CLIコマンド（Phase 1）

トレイアプリのadmin画面（Phase 4）が完成するまでの間、ユーザー管理は
中央サーバーPC上でこのCLIを使って行う（SPEC.md §4.1）。

使い方（backend ディレクトリで実行）:
    flask --app manage.py auth create-user 佐藤 --role operator
    flask --app manage.py auth set-password 佐藤
    flask --app manage.py auth deactivate-user 佐藤
    flask --app manage.py auth list-users
    flask --app manage.py auth issue-api-key --name 工場A共有キー
    flask --app manage.py auth revoke-api-key 工場A共有キー
    flask --app manage.py auth seed --admin-password xxxx --api-key yyyy   # CI/E2E用
"""

import secrets

import click
from flask.cli import AppGroup

from db import db
from db.models import AgentApiKey, User, UserRoles

auth_cli = AppGroup('auth', help='認証（ユーザー・APIキー）管理コマンド')


def _generate_password() -> str:
    """初期パスワードを生成（12文字のURL-safe文字列）"""
    return secrets.token_urlsafe(9)


@auth_cli.command('create-user')
@click.argument('username')
@click.option('--role', type=click.Choice(UserRoles.get_all()), default=UserRoles.OPERATOR, help='ユーザーロール')
@click.option('--password', default=None, help='パスワード（省略時は自動生成して表示）')
def create_user(username, role, password):
    """ユーザーを作成する"""
    if User.query.filter_by(username=username).first():
        click.echo(f"エラー: ユーザー '{username}' は既に存在します")
        raise SystemExit(1)

    generated = password is None
    if generated:
        password = _generate_password()

    user = User(username=username, password=password, role=role)
    db.session.add(user)
    db.session.commit()

    click.echo(f"ユーザーを作成しました: {username} (role={role})")
    if generated:
        click.echo(f"初期パスワード: {password}")
        click.echo("※このパスワードは再表示できません。本人に伝えて初回ログイン後に変更してください")


@auth_cli.command('set-password')
@click.argument('username')
@click.option('--password', default=None, help='新しいパスワード（省略時は自動生成して表示）')
def set_password(username, password):
    """ユーザーのパスワードを再設定する"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        click.echo(f"エラー: ユーザー '{username}' が見つかりません")
        raise SystemExit(1)

    generated = password is None
    if generated:
        password = _generate_password()

    user.set_password(password)
    # 既存トークンを全失効（パスワード変更時のセキュリティ原則）
    for token in user.tokens:
        db.session.delete(token)
    db.session.commit()

    click.echo(f"パスワードを再設定しました: {username}")
    if generated:
        click.echo(f"新しいパスワード: {password}")


@auth_cli.command('deactivate-user')
@click.argument('username')
def deactivate_user(username):
    """ユーザーを無効化する（ログイン不可にする。削除はしない）"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        click.echo(f"エラー: ユーザー '{username}' が見つかりません")
        raise SystemExit(1)

    user.is_active = False
    for token in user.tokens:
        db.session.delete(token)
    db.session.commit()
    click.echo(f"ユーザーを無効化しました: {username}")


@auth_cli.command('list-users')
def list_users():
    """ユーザー一覧を表示する"""
    users = User.query.order_by(User.id).all()
    if not users:
        click.echo("ユーザーが登録されていません")
        return
    for user in users:
        status = "有効" if user.is_active else "無効"
        click.echo(f"  {user.id}: {user.username} (role={user.role}, {status})")


@auth_cli.command('issue-api-key')
@click.option('--name', required=True, help='キーの識別名（例: 工場A共有キー）')
@click.option('--equipment-id', type=int, default=None, help='設備ID（省略時は全設備共有キー）')
def issue_api_key(name, equipment_id):
    """エージェントAPIキーを発行する（平文キーは発行時のみ表示）"""
    api_key, raw_key = AgentApiKey.issue(name=name, equipment_id=equipment_id)
    db.session.add(api_key)
    db.session.commit()

    scope = f"設備ID={equipment_id}" if equipment_id else "全設備共有"
    click.echo(f"APIキーを発行しました: {name} ({scope})")
    click.echo(f"APIキー: {raw_key}")
    click.echo("※このキーは再表示できません。ラズパイの環境変数 AGENT_API_KEY に設定してください")


@auth_cli.command('revoke-api-key')
@click.argument('name')
def revoke_api_key(name):
    """エージェントAPIキーを失効させる（識別名で指定）"""
    api_keys = AgentApiKey.query.filter_by(name=name, is_active=True).all()
    if not api_keys:
        click.echo(f"エラー: 有効なAPIキー '{name}' が見つかりません")
        raise SystemExit(1)

    for api_key in api_keys:
        api_key.is_active = False
    db.session.commit()
    click.echo(f"APIキーを失効させました: {name}（{len(api_keys)}件）")


@auth_cli.command('list-api-keys')
def list_api_keys():
    """APIキー一覧を表示する（平文キーは表示されない）"""
    api_keys = AgentApiKey.query.order_by(AgentApiKey.id).all()
    if not api_keys:
        click.echo("APIキーが登録されていません")
        return
    for api_key in api_keys:
        status = "有効" if api_key.is_active else "失効"
        scope = f"設備ID={api_key.equipment_id}" if api_key.equipment_id else "全設備共有"
        last_used = api_key.last_used_at.isoformat() if api_key.last_used_at else "未使用"
        click.echo(f"  {api_key.id}: {api_key.name} ({scope}, {status}, 最終使用: {last_used})")


@auth_cli.command('seed')
@click.option('--admin-password', required=True, help='adminユーザーのパスワード')
@click.option('--api-key', required=True, help='登録するAPIキー（平文）')
def seed(admin_password, api_key):
    """CI/E2E・初期セットアップ用: adminユーザーと共有APIキーを既知の値で作成する（冪等）"""
    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        admin = User(username='admin', password=admin_password, role=UserRoles.ADMIN)
        db.session.add(admin)
        click.echo("adminユーザーを作成しました")
    else:
        admin.set_password(admin_password)
        admin.is_active = True
        click.echo("adminユーザーのパスワードを更新しました")

    from db.models.auth import hash_token
    existing_key = AgentApiKey.query.filter_by(key_hash=hash_token(api_key)).first()
    if existing_key is None:
        record, _ = AgentApiKey.issue(name='seed-shared-key', raw_key=api_key)
        db.session.add(record)
        click.echo("共有APIキーを登録しました")
    else:
        existing_key.is_active = True
        click.echo("共有APIキーは登録済みです（有効化のみ実施）")

    db.session.commit()
    click.echo("シード完了")


def register_cli(app):
    """FlaskアプリにCLIコマンドを登録する"""
    app.cli.add_command(auth_cli)
