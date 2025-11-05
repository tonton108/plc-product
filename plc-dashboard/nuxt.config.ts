// https://nuxt.com/docs/api/configuration/nuxt-config
import { createVuetify } from 'vuetify'

export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: false }, // 開発ツールを無効化してパフォーマンス向上
  
  modules: [
    '@nuxtjs/i18n'
  ],

  i18n: {
    locales: [
      { code: 'ja', iso: 'ja-JP', name: '日本語' },
      { code: 'en', iso: 'en-US', name: 'English' },
      { code: 'zh', iso: 'zh-CN', name: '中文' }
    ],
    defaultLocale: 'ja',
    strategy: 'no_prefix',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      redirectOn: 'root'
    },
    compilation: {
      strictMessage: false
    }
  },

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

  // Viteの最適化設定（開発環境のパフォーマンス向上）
  vite: {
    optimizeDeps: {
      include: ['vuetify', 'socket.io-client']
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'vuetify': ['vuetify']
          }
        }
      }
    }
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