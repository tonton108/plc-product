import { io } from 'socket.io-client'
import { TOKEN_KEY } from '~/composables/useAuth'

export default defineNuxtPlugin((nuxtApp) => {
  // クライアントサイドでのみ実行
  if (import.meta.client) {
    // runtimeConfigからAPIベースURLを取得。
    // 空文字は「同一オリジン相対」を意味する（Phase 4: viewer同梱配信）。
    // `??` で未設定時のみ既定へフォールバックし、空文字はそのまま保持する。
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase ?? 'http://localhost:5000'

    // Socket.IOクライアントの初期化
    // auth: 接続のたびに最新のログイントークンをハンドシェイクに載せる（Phase 1）
    // バックエンド側は websocket.py の on_connect でこのトークンを検証し、無効なら接続を拒否する
    const socketOptions = {
      autoConnect: false,
      auth: (cb: (data: { token: string }) => void) => {
        cb({ token: localStorage.getItem(TOKEN_KEY) || '' })
      }
    }
    // apiBaseが空なら接続先URLを渡さず、現在のオリジンへ接続する（同一オリジン相対）
    const socket = apiBase ? io(apiBase, socketOptions) : io(socketOptions)

    // グローバルに$socketとしてアクセス可能にする
    return {
      provide: {
        socket
      }
    }
  }
}) 