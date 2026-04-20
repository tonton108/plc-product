# Python 3.11をベースイメージとして使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージを更新
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtをコピーして依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート5000を公開
EXPOSE 5000

# 環境変数を設定
ENV PYTHONPATH=/app
ENV FLASK_ENV=${FLASK_ENV:-development}
ENV FLASK_DEBUG=${FLASK_DEBUG:-1}

# アプリケーションを起動（manage.pyが内部でDB接続確認とテーブル作成を行う）
CMD ["python", "manage.py"] 