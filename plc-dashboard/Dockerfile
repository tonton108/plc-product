# Node.js 20をベースイメージとして使用（Nuxt.js 3.17.6の要件）
FROM node:20-alpine

# 作業ディレクトリを設定
WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# 依存関係をインストール
RUN npm install

# アプリケーションコードをコピー
COPY . .

# ポート3000を公開
EXPOSE 3000

# 環境変数を設定（開発モード）
ENV NODE_ENV=development

# 開発サーバーを起動
CMD ["npm", "run", "dev"] 