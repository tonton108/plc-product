/**
 * 管理者ガードミドルウェア（Phase 4: ユーザー管理画面）
 *
 * `definePageMeta({ middleware: 'admin' })` を指定したページを admin ロール限定にする。
 * グローバルの auth.global.ts でログイン自体は担保されるので、ここではロールのみ確認する。
 * 非adminはトップへリダイレクトする（URL直打ち対策）。
 */

import { USER_KEY } from '~/composables/useAuth'

export default defineNuxtRouteMiddleware(() => {
  // クライアントサイドのみ（localStorage参照のため）
  if (import.meta.server) return

  try {
    const stored = localStorage.getItem(USER_KEY)
    const user = stored ? JSON.parse(stored) : null
    if (!user || user.role !== 'admin') {
      return navigateTo('/')
    }
  } catch {
    return navigateTo('/')
  }
})
