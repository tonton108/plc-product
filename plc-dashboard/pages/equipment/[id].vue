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
          <!-- グラフタブ -->
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

          <!-- テーブルタブ -->
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

          <!-- エラー・アラームタブ（共通コンポーネント使用） -->
          <v-window-item value="2">
            <!-- PLC状態カード -->
            <PLCStatusCards :plc-status="plcStatus" />

            <!-- アラーム履歴 -->
            <v-row class="mb-6">
              <v-col cols="12">
                <AlarmHistoryTable
                  :alarms="alarms"
                  :loading="loadingErrors"
                  @acknowledge="acknowledgeAlarm"
                  @clear="clearAlarm"
                />
              </v-col>
            </v-row>

            <!-- エラーログ -->
            <v-row>
              <v-col cols="12">
                <ErrorLogTable
                  :error-logs="errorLogs"
                  :loading="loadingErrors"
                  @resolve="resolveErrorLog"
                />
              </v-col>
            </v-row>
          </v-window-item>
        </v-window>

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
/**
 * 設備詳細ページ
 *
 * ログ履歴のグラフ・テーブル表示、エラー・アラーム管理機能を提供します。
 * Phase 3リファクタリング: 共通コンポーネントとcomposablesを使用。
 */
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
const { getChartColor } = useColorMapping()

// useErrorsAlarms composableを使用（エラー・アラームタブ用）
const {
  loading: loadingErrors,
  plcStatus,
  alarms,
  errorLogs,
  loadErrorsAndAlarms,
  acknowledgeAlarm,
  clearAlarm,
  resolveErrorLog
} = useErrorsAlarms(equipmentId)

// 戻るボタンのハンドラー
const goBack = () => {
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
const equipment = ref(null)

// PLC設定情報（動的生成用）
const plcConfigs = ref([])
const headers = ref([
  { title: t('equipmentDetail.timestamp'), value: 'timestamp' }
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

// PLC設定を取得
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

// 動的テーブルヘッダーを初期化
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

// 動的チャートデータ生成
const updateChart = () => {
  const labels = filteredLogs.value.map(log =>
    formatDateTime(log.timestamp, {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    })
  )

  const datasets = []
  plcConfigs.value.forEach((config, index) => {
    if (config.enabled) {
      datasets.push({
        label: `${config.name}${config.unit ? '(' + config.unit + ')' : ''}`,
        data: filteredLogs.value.map(log => log[config.data_type] ?? null),
        borderColor: getChartColor(index),
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

// 動的CSVダウンロード
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

  console.log('🚀 ログ履歴ページの初期化開始')

  // 1. 設備情報取得
  await fetchEquipmentInfo()

  // 2. PLC設定取得（動的データ構造の初期化に必要）
  await fetchPLCConfigs()

  // 3. ログデータ取得（PLC設定取得後に実行）
  await fetchLogs()

  // 4. 定期的なログ更新を開始
  if (intervalId) clearInterval(intervalId)
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
