// https://nuxt.com/docs/api/configuration/nuxt-config
import { createVuetify } from 'vuetify'

export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: false }, // 開発ツールを無効化してパフォーマンス向上

  // コンポーネント自動インポートはディレクトリ名プレフィックスを付けない。
  // 既定では components/common/ErrorLogTable.vue が CommonErrorLogTable として
  // 登録され、テンプレートの <ErrorLogTable> では解決できず空表示になる
  // （エラー・アラーム/インシデント各タブで実際に描画されない不具合の原因）。
  // pathPrefix:false でファイル名基準の名前に統一する（ファイル名の重複なしを確認済み）。
  components: [
    { path: '~/components', pathPrefix: false }
  ],

  // Google Fonts（ガイドライン準拠フォント）
  app: {
    head: {
      link: [
        {
          rel: 'preconnect',
          href: 'https://fonts.googleapis.com'
        },
        {
          rel: 'preconnect',
          href: 'https://fonts.gstatic.com',
          crossorigin: 'anonymous'
        },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap'
        }
      ]
    }
  },

  modules: [
    '@nuxtjs/i18n'
  ],

  i18n: {
    locales: [
      { code: 'ja', iso: 'ja-JP', name: '日本語', file: 'ja.json' },
      { code: 'en', iso: 'en-US', name: 'English', file: 'en.json' },
      { code: 'zh', iso: 'zh-CN', name: '中文', file: 'zh.json' }
    ],
    defaultLocale: 'ja',
    lazy: true,
    langDir: 'locales/',
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