<template>
  <v-container>
    <!-- ヘッダーボタン群 -->
    <div class="d-flex align-center mb-6">
      <v-btn
        color="primary"
        variant="elevated"
        size="large"
        @click="goBack"
      >
        <template v-slot:prepend>
          <v-icon>mdi-arrow-left</v-icon>
        </template>
        {{ $t('common.back') }}
      </v-btn>
      <v-spacer></v-spacer>
      <v-btn
        color="success"
        variant="elevated"
        size="large"
        class="mr-3"
        @click="$router.push(`/monitoring/${$route.params.id}`)"
      >
        <template v-slot:prepend>
          <v-icon>mdi-monitor-dashboard</v-icon>
        </template>
        {{ $t('monitoring.realtimeMonitoring') }}
      </v-btn>
      <LanguageSwitch />
      <ThemeToggle />
    </div>

    <v-card class="pa-6 glass-card" elevation="0">
      <v-card-title class="text-h4 mb-4 d-flex align-center font-weight-bold">
        <v-icon size="large" class="mr-3" color="primary">mdi-chart-box-outline</v-icon>
        {{ $t('equipmentDetail.logGraph', { name: equipment?.name || '', manufacturer: equipment?.manufacturer || '' }) }}
      </v-card-title>
      <v-divider class="mb-6"></v-divider>

      <v-tabs v-model="tab" color="primary" class="mb-4" height="60">
        <v-tab value="0" class="text-h6">
          <v-icon class="mr-2">mdi-chart-line</v-icon>
          {{ $t('equipmentDetail.tabs.graph') }}
        </v-tab>
        <v-tab value="1" class="text-h6">
          <v-icon class="mr-2">mdi-table</v-icon>
          {{ $t('equipmentDetail.tabs.table') }}
        </v-tab>
        <v-tab value="2" class="text-h6">
          <v-icon class="mr-2">mdi-alert-circle</v-icon>
          {{ $t('equipmentDetail.tabs.errorsAlarms') }}
        </v-tab>
      </v-tabs>

      <v-card-text class="pa-6">
        <v-window v-model="tab">
          <v-window-item value="0">
            <v-card variant="outlined" class="pa-4">
              <div style="height: 500px">
                <div v-if="filteredLogs.length === 0" class="d-flex align-center justify-center" style="height: 100%;">
                  <div class="text-center">
                    <v-icon size="80" color="grey-lighten-1">mdi-chart-line-variant</v-icon>
                    <div class="text-h6 text-grey mt-4">{{ $t('common.noData') }}</div>
                  </div>
                </div>
                <Chart
                  v-else
                  :data="chartData"
                  :options="chartOptions"
                  type="line"
                />
              </div>
            </v-card>
          </v-window-item>

          <v-window-item value="1">
            <v-card variant="outlined">
              <v-data-table
                :headers="headers"
                :items="filteredLogs"
                density="comfortable"
                :items-per-page="15"
                class="elevation-0"
              />
            </v-card>
          </v-window-item>

          <v-window-item value="2">
            <!-- PLC状態カード -->
            <v-row class="mb-6">
              <v-col cols="12" md="4">
                <v-card :color="plcStatus.is_online ? 'success' : 'error'" dark elevation="4">
                  <v-card-text>
                    <div class="text-h6">{{ $t('plcStatus.title') }}</div>
                    <div class="text-h3 mt-2">
                      <v-icon size="x-large" class="mr-2">
                        {{ plcStatus.is_online ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                      </v-icon>
                      {{ plcStatus.is_online ? $t('plcStatus.online') : $t('plcStatus.offline') }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card color="warning" dark elevation="4">
                  <v-card-text>
                    <div class="text-h6">{{ $t('plcStatus.consecutiveErrors') }}</div>
                    <div class="text-h3 mt-2">{{ $t('plcStatus.consecutiveErrorsValue', { count: plcStatus.consecutive_errors || 0 }) }}</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card color="info" dark elevation="4">
                  <v-card-text>
                    <div class="text-h6">{{ $t('plcStatus.lastCommunication') }}</div>
                    <div class="text-body-1 mt-2">
                      {{ formatDateTime(plcStatus.last_communication_at) || $t('plcStatus.notConnected') }}
                    </div>
                    <div v-if="plcStatus.last_error_type" class="text-body-2 mt-1">
                      {{ $t('plcStatus.lastError', { error: plcStatus.last_error_type }) }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <!-- アラーム履歴 -->
            <v-row class="mb-6">
              <v-col cols="12">
                <v-card elevation="6">
                  <v-card-title class="bg-error text-white">
                    <v-icon class="mr-2">mdi-alarm-light</v-icon>
                    {{ $t('alarms.title') }}
                    <v-spacer></v-spacer>
                    <v-chip color="white" variant="outlined" size="small">
                      {{ $t('alarms.count', { count: alarms.length }) }}
                    </v-chip>
                  </v-card-title>
                  <v-card-text>
                    <v-data-table
                      :headers="alarmHeaders"
                      :items="alarms"
                      :loading="loadingErrors"
                      class="elevation-1"
                      :items-per-page="10"
                    >
                      <template v-slot:item.alarm_level="{ item }">
                        <v-chip
                          :color="getAlarmLevelColor(item.alarm_level)"
                          size="small"
                          variant="flat"
                        >
                          {{ item.alarm_level }}
                        </v-chip>
                      </template>
                      <template v-slot:item.occurred_at="{ item }">
                        {{ formatDateTime(item.occurred_at) }}
                      </template>
                      <template v-slot:item.cleared_at="{ item }">
                        <v-chip
                          v-if="item.cleared_at"
                          color="success"
                          size="small"
                          variant="outlined"
                        >
                          {{ $t('alarms.cleared') }}
                        </v-chip>
                        <v-chip
                          v-else
                          color="error"
                          size="small"
                          variant="flat"
                        >
                          {{ $t('alarms.notCleared') }}
                        </v-chip>
                      </template>
                      <template v-slot:item.acknowledged="{ item }">
                        <v-icon v-if="item.acknowledged" color="success">
                          mdi-check-circle
                        </v-icon>
                        <v-icon v-else color="grey">
                          mdi-circle-outline
                        </v-icon>
                      </template>
                      <template v-slot:item.actions="{ item }">
                        <v-btn
                          v-if="!item.acknowledged"
                          color="primary"
                          size="small"
                          @click="acknowledgeAlarm(item.id)"
                          class="mr-2"
                        >
                          {{ $t('alarms.acknowledge') }}
                        </v-btn>
                        <v-btn
                          v-if="!item.cleared_at"
                          color="success"
                          size="small"
                          @click="clearAlarm(item.id)"
                        >
                          {{ $t('alarms.clear') }}
                        </v-btn>
                      </template>
                    </v-data-table>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <!-- エラーログ -->
            <v-row>
              <v-col cols="12">
                <v-card elevation="6">
                  <v-card-title class="bg-warning text-white">
                    <v-icon class="mr-2">mdi-alert</v-icon>
                    {{ $t('errorLogs.title') }}
                    <v-spacer></v-spacer>
                    <v-chip color="white" variant="outlined" size="small">
                      {{ $t('errorLogs.count', { count: errorLogs.length }) }}
                    </v-chip>
                  </v-card-title>
                  <v-card-text>
                    <v-data-table
                      :headers="errorLogHeaders"
                      :items="errorLogs"
                      :loading="loadingErrors"
                      class="elevation-1"
                      :items-per-page="10"
                    >
                      <template v-slot:item.error_type="{ item }">
                        <v-chip
                          :color="getErrorTypeColor(item.error_type)"
                          size="small"
                          variant="flat"
                        >
                          {{ item.error_type }}
                        </v-chip>
                      </template>
                      <template v-slot:item.occurred_at="{ item }">
                        {{ formatDateTime(item.occurred_at) }}
                      </template>
                      <template v-slot:item.resolved_at="{ item }">
                        <v-chip
                          v-if="item.resolved_at"
                          color="success"
                          size="small"
                          variant="outlined"
                        >
                          {{ $t('errorLogs.resolved') }}
                        </v-chip>
                        <v-chip
                          v-else
                          color="warning"
                          size="small"
                          variant="flat"
                        >
                          {{ $t('errorLogs.notResolved') }}
                        </v-chip>
                      </template>
                      <template v-slot:item.retry_count="{ item }">
                        {{ item.retry_count || 0 }}
                      </template>
                      <template v-slot:item.actions="{ item }">
                        <v-btn
                          v-if="!item.resolved_at"
                          color="success"
                          size="small"
                          @click="resolveErrorLog(item.id)"
                        >
                          {{ $t('errorLogs.resolve') }}
                        </v-btn>
                      </template>
                    </v-data-table>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-window-item>
        </v-window>

        <!-- ✅ 異常値検出は将来的に設定可能にする予定（現在は無効化） -->
        <!-- <v-alert
          v-if="hasAbnormalValue"
          type="error"
          variant="tonal"
          class="mt-6"
          prominent
          border="start"
        >
          <v-alert-title class="text-h6">異常値検出</v-alert-title>
          異常値が検出されました（110以下 または 130以上）
        </v-alert> -->

        <v-btn
          class="mt-6"
          color="primary"
          variant="elevated"
          size="large"
          @click="downloadCSV"
        >
          <template v-slot:prepend>
            <v-icon>mdi-download</v-icon>
          </template>
          {{ $t('equipmentDetail.csvDownload') }}
        </v-btn>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
} from 'chart.js'
import { Chart } from 'vue-chartjs'
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '~/composables/useToast'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement
)

const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()
const apiBase = config.public.apiBase
const equipmentId = route.params.id
const toast = useToast()
const { t } = useI18n()
const { formatDateTime } = useDateTime()

// 戻るボタンのハンドラー
const goBack = () => {
  // ブラウザ履歴があれば戻る、なければトップページへ
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

const tab = ref(0)
const chartData = ref(null)
const chartOptions = ref({})
const logsRaw = ref([])
const selectedPeriod = ref('24h')
const periodOptions = ['1h', '6h', '24h', '7d', '30d']
const equipment = ref(null)

// エラー・アラーム関連の状態
const loadingErrors = ref(false)
const plcStatus = ref({})
const alarms = ref([])
const errorLogs = ref([])

// ✅ PLC設定情報（動的生成用）
const plcConfigs = ref([])
const headers = ref([
  { title: t('equipmentDetail.timestamp'), value: 'timestamp' }
])

// アラーム履歴のヘッダー
const alarmHeaders = computed(() => [
  { title: t('alarms.code'), key: 'alarm_code', sortable: true },
  { title: t('alarms.level'), key: 'alarm_level', sortable: true },
  { title: t('alarms.message'), key: 'alarm_message', sortable: false },
  { title: t('alarms.occurredAt'), key: 'occurred_at', sortable: true },
  { title: t('alarms.state'), key: 'cleared_at', sortable: true },
  { title: t('alarms.acknowledged'), key: 'acknowledged', sortable: true },
  { title: t('common.actions'), key: 'actions', sortable: false },
])

// エラーログのヘッダー
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

// 設備情報を取得
const fetchEquipmentInfo = async () => {
  try {
    const response = await fetch(`${apiBase}/api/equipment/${equipmentId}`)
    if (response.ok) {
      equipment.value = await response.json()
    }
  } catch (error) {
    console.error('設備情報取得エラー:', error)
  }
}

// ✅ PLC設定を取得
const fetchPLCConfigs = async () => {
  try {
    const response = await fetch(`${apiBase}/api/equipment/${equipmentId}/plc_configs`)
    if (response.ok) {
      plcConfigs.value = await response.json()
      console.log('📋 PLC設定取得成功:', plcConfigs.value)
      initializeDynamicHeaders()
    } else {
      console.error('PLC設定取得失敗:', response.status)
    }
  } catch (error) {
    console.error('PLC設定取得エラー:', error)
  }
}

// ✅ 動的テーブルヘッダーを初期化
const initializeDynamicHeaders = () => {
  const newHeaders = [{ title: t('equipmentDetail.timestamp'), value: 'timestamp' }]
  plcConfigs.value.forEach(config => {
    if (config.enabled) {
      newHeaders.push({
        title: `${config.name}${config.unit ? '(' + config.unit + ')' : ''}`,
        value: config.data_type,
        align: 'center'
      })
    }
  })
  headers.value = newHeaders
  console.log('✅ 動的ヘッダー生成完了:', headers.value)
}

const filteredLogs = computed(() => {
  const now = new Date()
  const rangeMs = {
    '1h': 60 * 60 * 1000,
    '6h': 6 * 60 * 60 * 1000,
    '24h': 24 * 60 * 60 * 1000,
  }[selectedPeriod.value]
  return logsRaw.value.filter(log => now - new Date(log.timestamp) <= rangeMs)
})

// ✅ 動的チャートデータ生成
const updateChart = () => {
  // ラベル（時刻）を生成（多言語対応）
  const labels = filteredLogs.value.map(log =>
    formatDateTime(log.timestamp, {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    })
  )

  // データセットを動的生成（PLC設定に基づく）
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

  const datasets = []
  plcConfigs.value.forEach((config, index) => {
    if (config.enabled) {
      datasets.push({
        label: `${config.name}${config.unit ? '(' + config.unit + ')' : ''}`,
        data: filteredLogs.value.map(log => log[config.data_type] ?? null),
        borderColor: colors[index % colors.length],
        backgroundColor: 'transparent',
        tension: 0.2,
        pointRadius: 3,
        pointHoverRadius: 5
      })
    }
  })

  chartData.value = {
    labels,
    datasets
  }
}

// ✅ 異常値検出は将来的に設定可能にする予定（現在は無効化）
// const hasAbnormalValue = computed(() => {
//   return logsRaw.value.some(log => log.value >= 130 || log.value <= 110)
// })

// ✅ 動的CSVダウンロード
const downloadCSV = () => {
  try {
    if (logsRaw.value.length === 0) {
      toast.warning(t('equipmentDetail.noExportData'))
      return
    }

    // ヘッダー行を動的生成
    const headerFields = ['timestamp']
    plcConfigs.value.forEach(config => {
      if (config.enabled) {
        headerFields.push(config.data_type)
      }
    })
    const header = headerFields.join(',') + '\n'

    // データ行を動的生成
    const rows = logsRaw.value.map(log => {
      const values = [log.timestamp]
      plcConfigs.value.forEach(config => {
        if (config.enabled) {
          values.push(log[config.data_type] ?? '')
        }
      })
      return values.join(',')
    })

    const csvContent = header + rows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    a.download = `${equipmentId}_logs_${timestamp}.csv`
    a.click()
    URL.revokeObjectURL(url)

    toast.success(t('equipmentDetail.csvDownloaded', { count: logsRaw.value.length }))
  } catch (error) {
    console.error('CSVダウンロードエラー:', error)
    toast.error(t('equipmentDetail.csvDownloadError'))
  }
}

let intervalId = null

const fetchLogs = async () => {
  try {
    const res = await fetch(`${apiBase}/api/logs/${equipmentId}/history_optimized?period=${selectedPeriod.value}`)
    if (res.ok) {
      const data = await res.json()
      logsRaw.value = data.logs || []
      updateChart()
    }
  } catch (err) {
    console.error('ログ取得失敗:', err)
  }
}

// エラー・アラームデータを読み込み
const loadErrorsAndAlarms = async () => {
  if (!equipmentId) return

  loadingErrors.value = true
  try {
    // 並列でデータ取得
    const [plcStatusRes, alarmsRes, errorLogsRes] = await Promise.all([
      fetch(`${apiBase}/api/equipment/${equipmentId}/plc_status`),
      fetch(`${apiBase}/api/equipment/${equipmentId}/alarms`),
      fetch(`${apiBase}/api/equipment/${equipmentId}/error_logs`)
    ])

    plcStatus.value = await plcStatusRes.json()
    alarms.value = await alarmsRes.json()
    errorLogs.value = await errorLogsRes.json()
  } catch (error) {
    console.error('エラー・アラームデータ読み込みエラー:', error)
  } finally {
    loadingErrors.value = false
  }
}

// アラームレベルの色
const getAlarmLevelColor = (level) => {
  const colors = {
    'WARNING': 'warning',
    'ERROR': 'error',
    'CRITICAL': 'purple'
  }
  return colors[level] || 'grey'
}

// エラー種別の色
const getErrorTypeColor = (type) => {
  const colors = {
    'CONNECTION_FAILED': 'error',
    'CONNECTION_EXCEPTION': 'error',
    'PROTOCOL_ERROR': 'warning',
    'READ_ERROR': 'orange',
    'TIMEOUT': 'warning',
    'CONFIGURATION_ERROR': 'info'
  }
  return colors[type] || 'grey'
}

// アラーム確認機能
const acknowledgeAlarm = async (alarmId) => {
  try {
    const response = await fetch(
      `${apiBase}/api/equipment/${equipmentId}/alarms/${alarmId}/acknowledge`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          acknowledged_by: 'Web UI User'
        })
      }
    )

    if (response.ok) {
      toast.success(t('alarms.acknowledgeSuccess'))
      await loadErrorsAndAlarms()
    } else {
      toast.error(t('alarms.acknowledgeFailed'))
    }
  } catch (error) {
    console.error('アラーム確認エラー:', error)
    toast.error(t('alarms.acknowledgeFailed'))
  }
}

// アラーム解除機能
const clearAlarm = async (alarmId) => {
  try {
    const response = await fetch(
      `${apiBase}/api/equipment/${equipmentId}/alarms/${alarmId}/clear`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    )

    if (response.ok) {
      toast.success(t('alarms.clearSuccess'))
      await loadErrorsAndAlarms()
    } else {
      toast.error(t('alarms.clearFailed'))
    }
  } catch (error) {
    console.error('アラーム解除エラー:', error)
    toast.error(t('alarms.clearFailed'))
  }
}

// エラーログ解決機能
const resolveErrorLog = async (errorLogId) => {
  try {
    const response = await fetch(
      `${apiBase}/api/equipment/${equipmentId}/error_logs/${errorLogId}/resolve`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    )

    if (response.ok) {
      toast.success(t('errorLogs.resolveSuccess'))
      await loadErrorsAndAlarms()
    } else {
      toast.error(t('errorLogs.resolveFailed'))
    }
  } catch (error) {
    console.error('エラーログ解決エラー:', error)
    toast.error(t('errorLogs.resolveFailed'))
  }
}

onMounted(async () => {
  const { default: zoomPlugin } = await import('chartjs-plugin-zoom')
  ChartJS.register(zoomPlugin)

  chartOptions.value = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500, easing: 'easeInOutQuad' },
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: t('chart.title') },
      zoom: {
        zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' },
        pan: { enabled: true, mode: 'x' },
      },
    },
  }

  // ✅ 初期化順序を最適化
  console.log('🚀 ログ履歴ページの初期化開始')

  // 1. 設備情報取得
  await fetchEquipmentInfo()

  // 2. PLC設定取得（動的データ構造の初期化に必要）
  await fetchPLCConfigs()

  // 3. ログデータ取得（PLC設定取得後に実行）
  await fetchLogs()

  // 4. 定期的なログ更新を開始
  intervalId = setInterval(fetchLogs, 10000)

  // 5. エラー・アラームデータを読み込み（初回のみ）
  await loadErrorsAndAlarms()

  console.log('✅ ログ履歴ページの初期化完了')
})

onBeforeUnmount(() => {
  clearInterval(intervalId)
})

// タブが切り替わったときにエラー・アラームデータを再読み込み
watch(tab, (newTab) => {
  if (newTab === '2') {
    loadErrorsAndAlarms()
  }
})

watch([selectedPeriod], updateChart)
</script>

<style scoped>
canvas {
  max-width: 100%;
  height: auto !important;
  display: block;
}
</style>