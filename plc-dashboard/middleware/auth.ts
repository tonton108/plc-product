/**
 * 認証ミドルウェア
 *
 * ログインしていないユーザーをログインページにリダイレクトします。
 *
 * 使用方法:
 *   ページコンポーネントで以下を追加:
 *   definePageMeta({
 *     middleware: 'auth'
 *   })
 */

export default defineNuxtRouteMiddleware((to, from) => {
  // サーバーサイドでは実行しない（クライアントサイドのみ）
  if (process.server) {
    return
  }

  // ログインページ自体は認証不要
  if (to.path === '/login') {
    return
  }

  // 認証トークンの確認
  const authToken = localStorage.getItem('plc_auth_token')

  if (!authToken) {
    // 未認証の場合、ログインページにリダイレクト
    return navigateTo('/login')
  }

  // 認証済みの場合は通過
  return
})
