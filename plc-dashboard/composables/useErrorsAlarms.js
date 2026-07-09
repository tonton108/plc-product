import { ref } from 'vue'

/**
 * エラー・アラーム管理用コンポーザブル
 *
 * PLC状態、アラーム履歴、エラーログのAPI呼び出しとアクションを提供します。
 *
 * 使用例:
 * const {
 *   plcStatus, alarms, errorLogs, loading,
 *   loadErrorsAndAlarms, acknowledgeAlarm, clearAlarm, resolveErrorLog
 * } = useErrorsAlarms(equipmentId)
 */
export const useErrorsAlarms = (equipmentIdRef) => {
  const { apiFetch } = useApi()
  const toast = useToast()
  const { t } = useI18n()

  // 状態
  const loading = ref(false)
  const plcStatus = ref({
    is_online: false,
    consecutive_errors: 0,
    last_communication_at: null,
    last_error_type: null,
    last_error_message: null
  })
  const alarms = ref([])
  const errorLogs = ref([])

  /**
   * 設備IDを取得（ref または 文字列に対応）
   */
  const getEquipmentId = () => {
    return typeof equipmentIdRef === 'string'
      ? equipmentIdRef
      : equipmentIdRef?.value
  }

  /**
   * エラー・アラームデータを読み込み
   */
  const loadErrorsAndAlarms = async () => {
    const equipmentId = getEquipmentId()
    if (!equipmentId) return

    loading.value = true
    try {
      // 並列でデータ取得（個別のエラーは無視し、成功した項目のみ反映する）
      // 例: PLCステータス未登録時は404が返るが、これは正常系（データ未登録）として扱う
      const [plcStatusResult, alarmsResult, errorLogsResult] = await Promise.allSettled([
        apiFetch(`/api/equipment/${equipmentId}/plc_status`),
        apiFetch(`/api/equipment/${equipmentId}/alarms`),
        apiFetch(`/api/equipment/${equipmentId}/error_logs`)
      ])

      if (plcStatusResult.status === 'fulfilled') {
        plcStatus.value = plcStatusResult.value
      }
      if (alarmsResult.status === 'fulfilled') {
        alarms.value = alarmsResult.value
      }
      if (errorLogsResult.status === 'fulfilled') {
        errorLogs.value = errorLogsResult.value
      }
    } catch (error) {
      console.error('エラー・アラームデータ読み込みエラー:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * アラームを確認する
   * @param {number} alarmId - アラームID
   * @param {string} acknowledgedBy - 確認者名（デフォルト: 'Web UI User'）
   */
  const acknowledgeAlarm = async (alarmId, acknowledgedBy = 'Web UI User') => {
    const equipmentId = getEquipmentId()
    if (!equipmentId) return false

    try {
      await apiFetch(`/api/equipment/${equipmentId}/alarms/${alarmId}/acknowledge`, {
        method: 'PATCH',
        body: { acknowledged_by: acknowledgedBy }
      })

      toast.success(t('alarms.acknowledgeSuccess'))
      await loadErrorsAndAlarms()
      return true
    } catch (error) {
      console.error('アラーム確認エラー:', error)
      toast.error(t('alarms.acknowledgeFailed'))
      return false
    }
  }

  /**
   * アラームを解除する
   * @param {number} alarmId - アラームID
   */
  const clearAlarm = async (alarmId) => {
    const equipmentId = getEquipmentId()
    if (!equipmentId) return false

    try {
      await apiFetch(`/api/equipment/${equipmentId}/alarms/${alarmId}/clear`, {
        method: 'PATCH'
      })

      toast.success(t('alarms.clearSuccess'))
      await loadErrorsAndAlarms()
      return true
    } catch (error) {
      console.error('アラーム解除エラー:', error)
      toast.error(t('alarms.clearFailed'))
      return false
    }
  }

  /**
   * エラーログを解決する
   * @param {number} errorLogId - エラーログID
   */
  const resolveErrorLog = async (errorLogId) => {
    const equipmentId = getEquipmentId()
    if (!equipmentId) return false

    try {
      await apiFetch(`/api/equipment/${equipmentId}/error_logs/${errorLogId}/resolve`, {
        method: 'PATCH'
      })

      toast.success(t('errorLogs.resolveSuccess'))
      await loadErrorsAndAlarms()
      return true
    } catch (error) {
      console.error('エラーログ解決エラー:', error)
      toast.error(t('errorLogs.resolveFailed'))
      return false
    }
  }

  /**
   * データをリセットする
   */
  const resetData = () => {
    plcStatus.value = {
      is_online: false,
      consecutive_errors: 0,
      last_communication_at: null,
      last_error_type: null,
      last_error_message: null
    }
    alarms.value = []
    errorLogs.value = []
  }

  return {
    // 状態
    loading,
    plcStatus,
    alarms,
    errorLogs,
    // メソッド
    loadErrorsAndAlarms,
    acknowledgeAlarm,
    clearAlarm,
    resolveErrorLog,
    resetData
  }
}
