import { io } from 'socket.io-client'
import { TOKEN_KEY } from '~/composables/useAuth'

export default defineNuxtPlugin(() => {
  // クライアントサイドでのみ実行
  if (import.meta.client) {
    // runtimeConfigからAPIベースURLを取得
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase || 'http://localhost:5000'

    // Socket.IOクライアントの初期化
    // auth: 接続のたびに最新のログイントークンをハンドシェイクに載せる（Phase 1）
    // バックエンド側は websocket.py の on_connect でこのトークンを検証し、無効なら接続を拒否する
    const socket = io(apiBase, {
      autoConnect: false,
      auth: (cb) => {
        cb({ token: localStorage.getItem(TOKEN_KEY) || '' })
      }
    })

    // グローバルに$socketとしてアクセス可能にする
    return {
      provide: {
        socket
      }
    }
  }
}) 