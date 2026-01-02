FROM python:3.10-slim

WORKDIR /app

# システム依存パッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# requirements_agent.txtをコピー
COPY requirements_agent.txt .

# Python依存関係をインストール
RUN pip install --no-cache-dir -r requirements_agent.txt

# アプリケーションのソースをコピー
COPY . .

# 翻訳ファイルをコンパイル
RUN pybabel compile -d translations

# ポート5001を公開
EXPOSE 5001

# Flaskアプリケーションを起動
CMD ["python", "agent_app.py"]
