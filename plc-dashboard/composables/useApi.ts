/**
 * API呼び出し共通コンポーザブル（Phase 1）
 *
 * バックエンドAPIへの全リクエストに Authorization: Bearer ヘッダを自動付与する。
 * 401（トークン失効・無効）を受けたらセッションを破棄してログイン画面へ遷移する。
 *
 * 使い方:
 *   const { apiFetch } = useApi()
 *   const data = await apiFetch('/api/equipment')                     // GET
 *   await apiFetch(`/api/equipment/${id}`, { method: 'PUT', body })   // PUT
 */

export const useApi = () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || 'http://localhost:5000'
  const { getToken, clearSession } = useAuth()

  const apiFetch = async <T = any>(path: string, options: any = {}): Promise<T> => {
    const token = getToken()
    const headers: Record<string, string> = {
      ...(options.headers || {}),
    }
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    try {
      return await $fetch<T>(`${apiBase}${path}`, {
        ...options,
        headers,
      })
    } catch (error: any) {
      if (error?.response?.status === 401 || error?.status === 401) {
        // トークン失効: セッションを破棄してログイン画面へ
        clearSession()
        navigateTo('/login')
      }
      throw error
    }
  }

  return { apiFetch, apiBase }
}
