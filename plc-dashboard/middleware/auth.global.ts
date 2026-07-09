/**
 * 認証ミドルウェア（グローバル・Phase 1で全ページ適用に変更）
 *
 * ログインしていないユーザーを全ページでログインページにリダイレクトします。
 * （旧実装は definePageMeta({ middleware: 'auth' }) を書いた2ページのみ保護で、
 *   errors-alarms / logs / equipment 詳細がURL直打ちで素通しだった）
 */

import { TOKEN_KEY } from '~/composables/useAuth'

export default defineNuxtRouteMiddleware((to) => {
  // サーバーサイドでは実行しない（クライアントサイドのみ）
  if (import.meta.server) {
    return
  }

  // ログインページ自体は認証不要
  if (to.path === '/login') {
    return
  }

  // 認証トークンの確認
  const authToken = localStorage.getItem(TOKEN_KEY)

  if (!authToken) {
    // 未認証の場合、ログインページにリダイレクト
    return navigateTo('/login')
  }

  return
})
