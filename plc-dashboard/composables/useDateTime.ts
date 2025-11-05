/**
 * 日付フォーマットの国際化対応
 * ロケールに応じた日付・時刻のフォーマットを提供
 */

export const useDateTime = () => {
  const { locale } = useI18n()
  
  /**
   * 日付時刻を現在のロケールに合わせてフォーマット
   * @param dateString - ISO 8601形式の日付文字列
   * @param options - Intl.DateTimeFormatのオプション
   * @returns フォーマット済みの日付文字列
   */
  const formatDateTime = (
    dateString: string | null | undefined,
    options?: Intl.DateTimeFormatOptions
  ): string => {
    if (!dateString) return '-'
    
    try {
      const date = new Date(dateString)
      
      // 無効な日付の場合
      if (isNaN(date.getTime())) {
        console.warn('[useDateTime] 無効な日付:', dateString)
        return '-'
      }
      
      // デフォルトのフォーマットオプション
      const defaultOptions: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false // 24時間表記
      }
      
      // ロケールに応じたフォーマット
      return new Intl.DateTimeFormat(
        locale.value,
        { ...defaultOptions, ...options }
      ).format(date)
    } catch (error) {
      console.error('[useDateTime] フォーマットエラー:', error)
      return '-'
    }
  }
  
  /**
   * 日付のみをフォーマット（時刻なし）
   * @param dateString - ISO 8601形式の日付文字列
   * @returns フォーマット済みの日付文字列
   */
  const formatDate = (dateString: string | null | undefined): string => {
    return formatDateTime(dateString, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  }
  
  /**
   * 時刻のみをフォーマット（日付なし）
   * @param dateString - ISO 8601形式の日付文字列
   * @returns フォーマット済みの時刻文字列
   */
  const formatTime = (dateString: string | null | undefined): string => {
    return formatDateTime(dateString, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }
  
  /**
   * 相対時刻をフォーマット（例: "3分前"、"2時間前"）
   * @param dateString - ISO 8601形式の日付文字列
   * @returns 相対時刻の文字列
   */
  const formatRelativeTime = (dateString: string | null | undefined): string => {
    if (!dateString) return '-'
    
    try {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return '-'
      
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffSeconds = Math.floor(diffMs / 1000)
      const diffMinutes = Math.floor(diffSeconds / 60)
      const diffHours = Math.floor(diffMinutes / 60)
      const diffDays = Math.floor(diffHours / 24)
      
      // 1分未満
      if (diffSeconds < 60) {
        return locale.value === 'ja' ? `${diffSeconds}秒前` :
               locale.value === 'zh' ? `${diffSeconds}秒前` :
               `${diffSeconds}s ago`
      }
      
      // 1時間未満
      if (diffMinutes < 60) {
        return locale.value === 'ja' ? `${diffMinutes}分前` :
               locale.value === 'zh' ? `${diffMinutes}分钟前` :
               `${diffMinutes}m ago`
      }
      
      // 1日未満
      if (diffHours < 24) {
        return locale.value === 'ja' ? `${diffHours}時間前` :
               locale.value === 'zh' ? `${diffHours}小时前` :
               `${diffHours}h ago`
      }
      
      // 1日以上
      return locale.value === 'ja' ? `${diffDays}日前` :
             locale.value === 'zh' ? `${diffDays}天前` :
             `${diffDays}d ago`
    } catch (error) {
      console.error('[useDateTime] 相対時刻フォーマットエラー:', error)
      return '-'
    }
  }
  
  /**
   * ISO 8601形式の日付文字列を生成
   * @param date - Dateオブジェクト（省略時は現在時刻）
   * @returns ISO 8601形式の文字列
   */
  const toISOString = (date: Date = new Date()): string => {
    return date.toISOString()
  }
  
  return {
    formatDateTime,
    formatDate,
    formatTime,
    formatRelativeTime,
    toISOString
  }
}
