import { computed } from 'vue'

/**
 * テーブルヘッダー定義用コンポーザブル
 *
 * アラーム履歴、エラーログなどのテーブルヘッダーを提供します。
 * 多言語対応のために computed を使用しています。
 *
 * 使用例:
 * const { alarmHeaders, errorLogHeaders } = useTableHeaders()
 */
export const useTableHeaders = () => {
  const { t } = useI18n()

  /**
   * アラーム履歴テーブルのヘッダー定義
   */
  const alarmHeaders = computed(() => [
    { title: t('alarms.code'), key: 'alarm_code', sortable: true },
    { title: t('alarms.level'), key: 'alarm_level', sortable: true },
    { title: t('alarms.message'), key: 'alarm_message', sortable: false },
    { title: t('alarms.occurredAt'), key: 'occurred_at', sortable: true },
    { title: t('alarms.state'), key: 'cleared_at', sortable: true },
    { title: t('alarms.acknowledged'), key: 'acknowledged', sortable: true },
    { title: t('common.actions'), key: 'actions', sortable: false },
  ])

  /**
   * エラーログテーブルのヘッダー定義
   */
  const errorLogHeaders = computed(() => [
    { title: t('errorLogs.type'), key: 'error_type', sortable: true },
    { title: t('errorLogs.message'), key: 'error_message', sortable: false },
    { title: t('errorLogs.plcIp'), key: 'plc_ip', sortable: false },
    { title: t('errorLogs.protocol'), key: 'protocol', sortable: false },
    { title: t('errorLogs.retryCount'), key: 'retry_count', sortable: true },
    { title: t('errorLogs.occurredAt'), key: 'occurred_at', sortable: true },
    { title: t('errorLogs.state'), key: 'resolved_at', sortable: true },
    { title: t('common.actions'), key: 'actions', sortable: false },
  ])

  /**
   * アラーム履歴テーブルのヘッダー（アクションなし）
   * 読み取り専用ビュー用
   */
  const alarmHeadersReadOnly = computed(() => [
    { title: t('alarms.code'), key: 'alarm_code', sortable: true },
    { title: t('alarms.level'), key: 'alarm_level', sortable: true },
    { title: t('alarms.message'), key: 'alarm_message', sortable: false },
    { title: t('alarms.occurredAt'), key: 'occurred_at', sortable: true },
    { title: t('alarms.state'), key: 'cleared_at', sortable: true },
    { title: t('alarms.acknowledged'), key: 'acknowledged', sortable: true },
  ])

  /**
   * エラーログテーブルのヘッダー（アクションなし）
   * 読み取り専用ビュー用
   */
  const errorLogHeadersReadOnly = computed(() => [
    { title: t('errorLogs.type'), key: 'error_type', sortable: true },
    { title: t('errorLogs.message'), key: 'error_message', sortable: false },
    { title: t('errorLogs.plcIp'), key: 'plc_ip', sortable: false },
    { title: t('errorLogs.protocol'), key: 'protocol', sortable: false },
    { title: t('errorLogs.retryCount'), key: 'retry_count', sortable: true },
    { title: t('errorLogs.occurredAt'), key: 'occurred_at', sortable: true },
    { title: t('errorLogs.state'), key: 'resolved_at', sortable: true },
  ])

  return {
    alarmHeaders,
    errorLogHeaders,
    alarmHeadersReadOnly,
    errorLogHeadersReadOnly
  }
}
