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
})
