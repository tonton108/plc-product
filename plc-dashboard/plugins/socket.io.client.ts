import { io } from 'socket.io-client'

export default defineNuxtPlugin((nuxtApp) => {
  // クライアントサイドでのみ実行
  if (import.meta.client) {
    // runtimeConfigからAPIベースURLを取得
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase || 'http://localhost:5000'

    // Socket.IOクライアントの初期化
    const socket = io(apiBase, {
      autoConnect: false
    })

    // グローバルに$socketとしてアクセス可能にする
    return {
      provide: {
        socket
      }
    }
  }
}) 