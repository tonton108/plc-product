// https://nuxt.com/docs/api/configuration/nuxt-config
import { createVuetify } from 'vuetify'

export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: true },
  css: ['vuetify/styles'],
  build: {
    transpile: ['vuetify'],
  },
  plugins: [
    '~/plugins/vuetify.ts',
    '~/plugins/socket.io.client.ts'
  ],
  ssr: false, // Socket.IOクライアントはクライアントサイドのみで動作

  // 環境変数設定
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:5000'
    }
  }
})
