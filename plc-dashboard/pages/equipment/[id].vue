<template>
  <v-container>
    <!-- 戻るボタン -->
    <v-btn
      color="primary"
      variant="elevated"
      size="large"
      class="mb-6"
      @click="goBack"
    >
      <template v-slot:prepend>
        <v-icon>mdi-arrow-left</v-icon>
      </template>
      戻る
    </v-btn>

    <v-card class="pa-6" elevation="8">
      <v-card-title class="text-h4 mb-4 d-flex align-center">
        <v-icon size="large" class="mr-3" color="primary">mdi-chart-box-outline</v-icon>
        {{ equipment?.name }}（{{ equipment?.manufacturer }}）のロググラフ
      </v-card-title>
      <v-divider class="mb-6"></v-divider>

      <v-tabs v-model="tab" color="primary" class="mb-4" height="60">
        <v-tab value="0" class="text-h6">
          <v-icon class="mr-2">mdi-chart-line</v-icon>
          グラフ
        </v-tab>
        <v-tab value="1" class="text-h6">
          <v-icon class="mr-2">mdi-table</v-icon>
          テーブル
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
                    <div class="text-h6 text-grey mt-4">データがありません</div>
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
          CSVダウンロード
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

// ✅ PLC設定情報（動的生成用）
const plcConfigs = ref([])
const headers = ref([
  { title: '日時', value: 'timestamp' }
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
  const newHeaders = [{ title: '日時', value: 'timestamp' }]
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
  // ラベル（時刻）を生成
  const labels = filteredLogs.value.map(log =>
    new Date(log.timestamp).toLocaleString('ja-JP', {
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
  a.download = `${equipmentId}_logs.csv`
  a.click()
  URL.revokeObjectURL(url)
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
      title: { display: true, text: 'PLCデータログ' },
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

  console.log('✅ ログ履歴ページの初期化完了')
})

onBeforeUnmount(() => {
  clearInterval(intervalId)
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