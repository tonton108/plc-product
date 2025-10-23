import { io } from 'socket.io-client'

export default defineNuxtPlugin((nuxtApp) => {
  // クライアントサイドでのみ実行
  if (import.meta.client) {
    // Socket.IOクライアントの初期化
    const socket = io('http://localhost:5000', {
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