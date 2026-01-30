/**
 * カラーマッピング用コンポーザブル
 *
 * アラームレベル、エラー種別、PLC状態などの色マッピングを提供します。
 *
 * 使用例:
 * const { getAlarmLevelColor, getErrorTypeColor, getStatusColor } = useColorMapping()
 * const color = getAlarmLevelColor('WARNING') // 'warning'
 */
export const useColorMapping = () => {
  /**
   * アラームレベルに対応するVuetifyカラーを取得
   * @param {string} level - アラームレベル (WARNING, ERROR, CRITICAL)
   * @returns {string} Vuetifyカラー名
   */
  const getAlarmLevelColor = (level) => {
    const colors = {
      'WARNING': 'warning',
      'ERROR': 'error',
      'CRITICAL': 'purple'
    }
    return colors[level] || 'grey'
  }

  /**
   * エラー種別に対応するVuetifyカラーを取得
   * @param {string} type - エラー種別
   * @returns {string} Vuetifyカラー名
   */
  const getErrorTypeColor = (type) => {
    const colors = {
      'CONNECTION_FAILED': 'error',
      'CONNECTION_EXCEPTION': 'error',
      'PROTOCOL_ERROR': 'warning',
      'READ_ERROR': 'orange',
      'TIMEOUT': 'warning',
      'CONFIGURATION_ERROR': 'info',
      'UNKNOWN': 'grey'
    }
    return colors[type] || 'grey'
  }

  /**
   * 設備ステータスに対応するVuetifyカラーを取得
   * @param {string} status - 設備ステータス
   * @returns {string} Vuetifyカラー名
   */
  const getStatusColor = (status) => {
    const colors = {
      'セットアップ待ち': 'info',
      'セットアップ中': 'warning',
      'セットアップ完了': 'success',
      '稼働中': 'success',
      '停止中': 'error',
      'メンテナンス中': 'orange'
    }
    return colors[status] || 'grey'
  }

  /**
   * PLC通信状態に対応するVuetifyカラーを取得
   * @param {boolean} isOnline - オンライン状態
   * @returns {string} Vuetifyカラー名
   */
  const getPLCStatusColor = (isOnline) => {
    return isOnline ? 'success' : 'error'
  }

  /**
   * チャート用のカラーパレットを取得
   * @param {number} index - インデックス
   * @returns {string} カラーコード
   */
  const getChartColor = (index) => {
    const colors = [
      '#2196F3', // Blue
      '#FF5722', // Deep Orange
      '#4CAF50', // Green
      '#FF9800', // Orange
      '#9C27B0', // Purple
      '#00BCD4', // Cyan
      '#FFC107', // Amber
      '#E91E63'  // Pink
    ]
    return colors[index % colors.length]
  }

  return {
    getAlarmLevelColor,
    getErrorTypeColor,
    getStatusColor,
    getPLCStatusColor,
    getChartColor
  }
}
