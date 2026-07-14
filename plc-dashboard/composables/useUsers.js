import { ref } from 'vue'

/**
 * ユーザー管理コンポーザブル（Phase 4: admin画面）
 *
 * バックエンドの admin専用API（/api/admin/users）を叩いてユーザーの
 * 一覧・作成・パスワード再設定・有効/無効化を行う。全操作 admin ロール必須。
 *
 * 使用例:
 *   const { users, loading, loadUsers, createUser,
 *           resetPassword, deactivateUser, activateUser } = useUsers()
 */
export const useUsers = () => {
  const { apiFetch } = useApi()

  const users = ref([])
  const loading = ref(false)

  const loadUsers = async () => {
    loading.value = true
    try {
      const data = await apiFetch('/api/admin/users')
      users.value = data.users || []
    } finally {
      loading.value = false
    }
  }

  /**
   * ユーザー作成。passwordを省略するとサーバーが自動生成し、
   * レスポンスの generated_password に平文が入る（発行時のみ）。
   */
  const createUser = async ({ username, role, password }) => {
    const body = { username, role }
    if (password) body.password = password
    return await apiFetch('/api/admin/users', { method: 'POST', body })
  }

  /**
   * パスワード再設定。passwordを省略すると自動生成して generated_password で返る。
   */
  const resetPassword = async (userId, password) => {
    const body = password ? { password } : {}
    return await apiFetch(`/api/admin/users/${userId}/reset-password`, {
      method: 'POST',
      body,
    })
  }

  const deactivateUser = async (userId) =>
    await apiFetch(`/api/admin/users/${userId}/deactivate`, { method: 'POST' })

  const activateUser = async (userId) =>
    await apiFetch(`/api/admin/users/${userId}/activate`, { method: 'POST' })

  return {
    users,
    loading,
    loadUsers,
    createUser,
    resetPassword,
    deactivateUser,
    activateUser,
  }
}
