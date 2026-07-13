import { ref } from 'vue'

/**
 * インシデント文脈（SPEC §5.2）用コンポーザブル
 *
 * エラー/アラーム発生時に保全された「発生前（リードアップ）」および
 * 「発生後（アフターマス）」の生ログスナップショットを取得する。
 * 生ログ本体は30日で消えるが、この文脈は長期保持され後から追跡できる。
 *
 * 使用例:
 *   const {
 *     incidents, loading, contextDialog, selectedContext, contextLoading,
 *     loadIncidents, openIncidentContext
 *   } = useIncidents(equipmentId)
 */
export const useIncidents = (equipmentIdRef) => {
  const { apiFetch } = useApi()

  // 一覧（軽量・context_dataは含まない）
  const incidents = ref([])
  const loading = ref(false)
  // 詳細ダイアログ（生ログ配列を含む）
  const contextDialog = ref(false)
  const selectedContext = ref(null)
  const contextLoading = ref(false)

  const getEquipmentId = () =>
    typeof equipmentIdRef === 'string' ? equipmentIdRef : equipmentIdRef?.value

  // 詳細取得の競合対策。最後に開いたインシデントIDのレスポンスのみ反映し、
  // 連続操作で遅延した先発レスポンスが後発の表示を上書きしないようにする。
  let latestRequestId = 0

  /**
   * インシデント一覧を読み込む（発生時刻の新しい順）
   */
  const loadIncidents = async () => {
    const equipmentId = getEquipmentId()
    if (!equipmentId) return

    loading.value = true
    try {
      incidents.value = await apiFetch(`/api/equipment/${equipmentId}/incidents`)
    } catch (error) {
      // インシデント未発生時などは空配列扱い（正常系）
      console.error('インシデント一覧取得エラー:', error)
      incidents.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 1インシデントの生データ文脈（発生前/発生後の生ログ配列）を取得しダイアログを開く
   * @param {number} incidentId - インシデントID
   */
  const openIncidentContext = async (incidentId) => {
    const equipmentId = getEquipmentId()
    if (!equipmentId) return

    const requestId = ++latestRequestId
    contextDialog.value = true
    contextLoading.value = true
    selectedContext.value = null
    try {
      const data = await apiFetch(
        `/api/equipment/${equipmentId}/incidents/${incidentId}/context`
      )
      // 後発リクエストが発行済みなら、この遅延レスポンスは破棄する
      if (requestId !== latestRequestId) return
      selectedContext.value = data
    } catch (error) {
      console.error('インシデント文脈取得エラー:', error)
      if (requestId === latestRequestId) selectedContext.value = null
    } finally {
      if (requestId === latestRequestId) contextLoading.value = false
    }
  }

  return {
    incidents,
    loading,
    contextDialog,
    selectedContext,
    contextLoading,
    loadIncidents,
    openIncidentContext,
  }
}
