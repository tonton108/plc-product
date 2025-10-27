// https://nuxt.com/docs/api/configuration/nuxt-config
import { createVuetify } from 'vuetify'

export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: true },
  css: [
    'vuetify/styles',
    '~/assets/styles/modern.css'
  ],
  build: {
    transpile: ['vuetify'],
  },
  plugins: [
    '~/plugins/vuetify.ts',
    '~/plugins/socket.io.client.ts'
  ],
  ssr: false, // Socket.IOクライアントはクライアントサイドのみで動作

  // 静的生成設定（Electronアプリ用）
  nitro: {
    preset: 'static'
    // デフォルトの出力先(.output/public)を使用し、後でdesktop-app/nuxt-distにコピーする
  },

  // イントラネット環境でアクセスを許可
  devServer: {
    host: '0.0.0.0', // 全ネットワークインターフェースでリッスン
    port: 3000
  },

  // 環境変数設定
  runtimeConfig: {
    public: {
      // 本番環境では中央サーバーのIPを指定
      // 例: NUXT_PUBLIC_API_BASE=http://192.168.1.10:5000
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:5000'
    }
  }
})
