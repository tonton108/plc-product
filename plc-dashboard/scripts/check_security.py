#!/usr/bin/env python3
"""
セキュリティ設定チェックスクリプト

本番環境でデフォルトパスワードが使用されていないか確認します。
サーバー起動前に必ず実行してください。

使用方法:
    python scripts/check_security.py

終了コード:
    0: すべての検証に合格
    1: セキュリティ上の問題が検出された
"""

import os
import sys
from dotenv import load_dotenv
import hashlib

# 環境変数を読み込み
load_dotenv()

# デフォルト値（本番環境で使用してはいけない値）
INSECURE_DEFAULTS = {
    'SECRET_KEY': [
        'your-secure-secret-key-change-in-production',
        'dev-secret-key',
        'your-secret-key',
    ],
    'POSTGRES_PASSWORD': [
        'plc_pass',
        'password',
        'admin',
    ],
    'ADMIN_PASSWORD_HASH': [
        # admin123のハッシュ値
        'e2c6ed4d94bc3d1b605cb5fe7e92e48546b26e0f1e30f97e8151af9f9abb0844',
    ],
}

# 最小パスワード強度
MIN_PASSWORD_LENGTH = 12

def check_env_variable(var_name, current_value, insecure_values):
    """環境変数がデフォルト値でないか確認"""
    if not current_value:
        print(f"⚠️  警告: {var_name} が設定されていません")
        return False

    if current_value in insecure_values:
        print(f"🚨 危険: {var_name} にデフォルト値が使用されています！")
        print(f"   現在値: {current_value[:20]}...")
        print(f"   対策: 強力なランダム文字列に変更してください")
        return False

    return True

def check_password_strength(var_name, password):
    """パスワード強度をチェック"""
    if not password:
        return True  # 未設定はcheck_env_variableで検出

    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"⚠️  警告: {var_name} が短すぎます（最低{MIN_PASSWORD_LENGTH}文字推奨）")
        return False

    return True

def check_cors_settings():
    """CORS設定をチェック"""
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000')

    if cors_origins == '*':
        print(f"⚠️  警告: CORS_ORIGINS が '*' に設定されています")
        print(f"   イントラネット環境であっても、具体的なオリジンを指定することを推奨します")
        print(f"   例: CORS_ORIGINS=http://192.168.1.10:3000,http://192.168.1.11:3000")
        return False

    return True

def check_flask_env():
    """Flask環境設定をチェック"""
    flask_env = os.getenv('FLASK_ENV', 'development')

    if flask_env == 'development':
        print(f"⚠️  警告: FLASK_ENV が 'development' に設定されています")
        print(f"   本番環境では 'production' に変更してください")
        return False

    return True

def generate_secure_secret():
    """セキュアなシークレットキーを生成"""
    import secrets
    return secrets.token_hex(32)

def main():
    print("=" * 60)
    print("🔒 セキュリティ設定チェックを開始します")
    print("=" * 60)
    print()

    issues_found = 0

    # 1. SECRET_KEYのチェック
    secret_key = os.getenv('SECRET_KEY')
    if not check_env_variable('SECRET_KEY', secret_key, INSECURE_DEFAULTS['SECRET_KEY']):
        issues_found += 1
        print(f"   💡 推奨: export SECRET_KEY={generate_secure_secret()}")
    else:
        print(f"✅ SECRET_KEY: 安全")
    print()

    # 2. POSTGRES_PASSWORDのチェック
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    if not check_env_variable('POSTGRES_PASSWORD', postgres_password, INSECURE_DEFAULTS['POSTGRES_PASSWORD']):
        issues_found += 1
    elif not check_password_strength('POSTGRES_PASSWORD', postgres_password):
        issues_found += 1
    else:
        print(f"✅ POSTGRES_PASSWORD: 安全")
    print()

    # 3. ADMIN_PASSWORD_HASHのチェック（Raspberry Piエージェント用）
    admin_password_hash = os.getenv('ADMIN_PASSWORD_HASH')
    if admin_password_hash and not check_env_variable('ADMIN_PASSWORD_HASH', admin_password_hash, INSECURE_DEFAULTS['ADMIN_PASSWORD_HASH']):
        issues_found += 1
    else:
        print(f"✅ ADMIN_PASSWORD_HASH: 安全")
    print()

    # 4. CORS設定のチェック
    if not check_cors_settings():
        print(f"   本番環境では具体的なオリジンを指定してください")
    else:
        print(f"✅ CORS_ORIGINS: 安全")
    print()

    # 5. FLASK_ENV設定のチェック
    if not check_flask_env():
        print(f"   本番環境では FLASK_ENV=production を設定してください")
    else:
        print(f"✅ FLASK_ENV: 安全")
    print()

    # 6. データベースURL確認
    database_url = os.getenv('DATABASE_URL')
    if database_url and 'localhost' in database_url:
        print(f"⚠️  情報: DATABASE_URL に 'localhost' が含まれています")
        print(f"   本番環境では実際のホスト名またはIPアドレスを指定してください")
    elif database_url:
        print(f"✅ DATABASE_URL: 設定済み")
    print()

    # 結果サマリー
    print("=" * 60)
    if issues_found == 0:
        print("✅ すべてのセキュリティチェックに合格しました")
        print("=" * 60)
        return 0
    else:
        print(f"🚨 {issues_found} 件のセキュリティ上の問題が検出されました")
        print("=" * 60)
        print()
        print("対策:")
        print("1. .envファイルを編集してデフォルト値を変更してください")
        print("2. パスワードは最低12文字以上、英数字+記号を組み合わせてください")
        print("3. 変更後、再度このスクリプトを実行して確認してください")
        print()
        return 1

if __name__ == '__main__':
    sys.exit(main())
