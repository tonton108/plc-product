/**
 * 認証状態管理コンポーザブル（Phase 1）
 *
 * バックエンドの /api/auth/* と連携し、Bearerトークンとユーザー情報を管理する。
 * トークンは localStorage（キー: plc_auth_token）に保持し、
 * ページリロード後も維持される。
 */

interface AuthUser {
  id: number
  username: string
  role: 'admin' | 'operator'
  is_active: boolean
}

// localStorageキー（他ファイルからも必ずこの定数を参照すること。直書き禁止）
export const TOKEN_KEY = 'plc_auth_token'
export const USER_KEY = 'plc_auth_user'

export const useAuth = () => {
  const config = useRuntimeConfig()
  // 空文字は「同一オリジン相対」を意味する（Phase 4: viewer同梱配信）。
  // `??` で未設定時のみ既定へフォールバックし、空文字はそのまま保持する。
  const apiBase = config.public.apiBase ?? 'http://localhost:5000'

  // タブ内で共有するリアクティブ状態（初期値はlocalStorageから復元）
  const user = useState<AuthUser | null>('auth_user', () => {
    if (import.meta.client) {
      try {
        const stored = localStorage.getItem(USER_KEY)
        return stored ? JSON.parse(stored) : null
      } catch {
        return null
      }
    }
    return null
  })

  const getToken = (): string | null => {
    if (!import.meta.client) return null
    return localStorage.getItem(TOKEN_KEY)
  }

  const isAuthenticated = (): boolean => !!getToken()

  const isAdmin = computed(() => user.value?.role === 'admin')

  const login = async (username: string, password: string): Promise<void> => {
    const response = await $fetch<{ token: string; user: AuthUser }>(
      `${apiBase}/api/auth/login`,
      {
        method: 'POST',
        body: { username, password },
      }
    )
    localStorage.setItem(TOKEN_KEY, response.token)
    localStorage.setItem(USER_KEY, JSON.stringify(response.user))
    user.value = response.user
  }

  const clearSession = (): void => {
    if (import.meta.client) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    }
    user.value = null
  }

  const logout = async (): Promise<void> => {
    const token = getToken()
    if (token) {
      try {
        // サーバー側のトークンを失効させる（失敗してもローカルは消す）
        await $fetch(`${apiBase}/api/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        })
      } catch {
        // サーバー到達不能でもログアウト自体は成立させる
      }
    }
    clearSession()
  }

  return {
    user,
    isAdmin,
    getToken,
    isAuthenticated,
    login,
    logout,
    clearSession,
  }
}
