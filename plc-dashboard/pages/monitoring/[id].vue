<!--
🔧 リファクタリング完了: コンポーネント分割による保守性向上
-->
<template>
  <v-container fluid class="fade-in">
    <!-- ヘッダー部分 -->
    <MonitoringHeader
      :equipment-info="equipmentInfo"
      :connection-status="realtimeMonitoring.connectionStatus.value"
      @go-back="goBack"
    />

    <!-- ステータスカード & アラート -->
    <StatusCards
      :monitoring-data="monitoringData"
      :alerts="alerts"
      @remove-alert="removeAlert"
    />

    <!-- リアルタイムグラフ -->
    <ChartCards
      :chart-configs="chartConfigs"
      :debug-mode="debugMode"
      @chart-ref-set="({ el, chartId }) => setChartRef(el, chartId)"
    />

    <!-- 最新データログ -->
    <DataCards
      :data-history="dataHistory"
      :table-headers="tableHeaders"
      @export-csv="exportDataHistoryToCSV"
    />

    <!-- デバッグパネル -->
    <v-row class="mb-6" v-if="debugMode">
      <v-col cols="12">
        <MonitoringDebugPanel
          :connection-status="realtimeMonitoring.connectionStatus.value"
          :socket-info="realtimeMonitoring.socketInfo.value"
          :equipment-id="equipmentId"
          :data-history-count="dataHistory.length"
          :last-data-update="realtimeMonitoring.lastDataUpdate.value"
          :debug-counters="realtimeMonitoring.debugCounters.value"
          :debug-logs="realtimeMonitoring.debugLogs.value"
          @test-api="testLatestAPI"
          @clear-log="clearDebugLog"
        />
      </v-col>
    </v-row>

    <!-- ✅ デバッグモード切り替えボタン -->
    <v-fab
      location="bottom right"
      size="large"
      :color="debugMode ? 'success' : 'info'"
      @click="debugMode = !debugMode"
      elevation="8"
    >
      <v-icon size="large">{{ debugMode ? 'mdi-bug-check' : 'mdi-bug' }}</v-icon>
    </v-fab>
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
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '~/composables/useToast'
import { useRealtimeMonitoring } from '~/composables/useRealtimeMonitoring'
import { useChartManagement } from '~/composables/useChartManagement'

// コンポーネントのインポート
import MonitoringHeader from '~/components/monitoring/MonitoringHeader.vue'
import StatusCards from '~/components/monitoring/StatusCards.vue'
import ChartCards from '~/components/monitoring/ChartCards.vue'
import DataCards from '~/components/monitoring/DataCards.vue'

// 認証ミドルウェアを適用
definePageMeta({
  middleware: 'auth'
})

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
const { $socket } = useNuxtApp()
const config = useRuntimeConfig()
const apiBase = config.public.apiBase
const toast = useToast()

// データ定義
const equipmentId = route.params.id
const equipmentInfo = ref(null)
const dataHistory = ref([])
const alerts = ref([])

// デバッグ機能
const debugMode = ref(false)

// PLC設定情報（動的生成用）
const plcConfigs = ref([])

// モニタリングデータ（動的生成）
const monitoringData = ref({})

// テーブルヘッダー（動的生成）
const tableHeaders = ref([
  { title: '時刻', value: 'timestamp', width: '180' }
])

// リアルタイム監視コンポーザブル
const realtimeMonitoring = useRealtimeMonitoring(equipmentId, {
  debugMode: true,
  onDataUpdate: handleDataUpdate
})

// チャート管理コンポーザブル
const chartManagement = useChartManagement({
  onDebugLog: realtimeMonitoring.addDebugLog
})

// chartConfigsを直接参照（computedは不要）
const chartConfigs = chartManagement.chartConfigs

// Chart.jsインスタンスをセットアップ
const setChartRef = (el, chartId) => {
  if (!el) return

  // ClientOnlyコンポーネント内のレンダリングを待つため、少し遅延
  setTimeout(() => {
    // vue-chartjs v5では、複数の方法でChart.jsインスタンスを取得可能
    const chartInstance =
      el.chart ||                    // 直接プロパティ
      el.chartInstance ||             // vue-chartjs v5の標準プロパティ
      el.$data?.chart ||              // Options APIの場合
      el.$?.exposed?.chart ||         // Composition APIのexposeの場合
      el.$?.proxy?.chart              // Proxyの場合

    console.log(`🔍 Chart.jsインスタンス検索: ${chartId}`, {
      hasChart: !!el.chart,
      hasChartInstance: !!el.chartInstance,
      hasDataChart: !!el.$data?.chart,
      hasExposedChart: !!el.$?.exposed?.chart,
      hasProxyChart: !!el.$?.proxy?.chart,
      elKeys: Object.keys(el)
    })

    if (chartInstance) {
      console.log(`✅ Chart.jsインスタンス取得成功: ${chartId}`)
      chartManagement.registerChartInstance(chartId, chartInstance)
    } else {
      console.warn(`⚠️ Chart.jsインスタンス取得失敗: ${chartId}`, el)
    }
  }, 100) // 100ms遅延でClientOnlyのレンダリングを待つ
}

// watch関数を削除: Chart.jsインスタンスを直接操作するため、Vueのリアクティビティは不要

// メソッド
const goBack = () => {
  // ブラウザ履歴があれば戻る、なければトップページへ
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

const removeAlert = (alertId) => {
  const index = alerts.value.findIndex(alert => alert.id === alertId)
  if (index !== -1) {
    alerts.value.splice(index, 1)
  }
}

// データ更新ハンドラー（コンポーザブルから呼ばれる）
function handleDataUpdate(data) {
  updateMonitoringData(data)
  chartManagement.updateChartData(data)

  // データ履歴に追加（新しい配列を作成してリアクティビティを維持）
  const newHistory = [data, ...dataHistory.value]
  dataHistory.value = newHistory.slice(0, 100)  // 最大100件まで

  // エラーアラート
  if (data.error_code) {
    addAlert('error', 'エラー発生', `エラーコード: ${data.error_code}`)
  }
}

// デバッグログクリア
const clearDebugLog = () => {
  realtimeMonitoring.debugLogs.value = []
  Object.keys(realtimeMonitoring.debugCounters.value).forEach(key => {
    realtimeMonitoring.debugCounters.value[key] = 0
  })
  realtimeMonitoring.addDebugLog('info', 'デバッグログをクリアしました')
}

const testLatestAPI = async () => {
  realtimeMonitoring.addDebugLog('info', 'API テスト開始: /api/logs/latest')
  try {
    const response = await fetch(`${apiBase}/api/logs/${equipmentId}/latest`)
    if (response.ok) {
      const data = await response.json()
      realtimeMonitoring.addDebugLog('success', `API テスト成功: ${data.timestamp}`)
      console.log('📡 API テスト結果:', data)
    } else {
      realtimeMonitoring.addDebugLog('error', `API テスト失敗: ${response.status}`)
    }
  } catch (error) {
    realtimeMonitoring.addDebugLog('error', `API テストエラー: ${error.message}`)
  }
}

const addAlert = (type, title, message) => {
  const alert = {
    id: Date.now(),
    type,
    title,
    message,
    timestamp: new Date().toLocaleString('ja-JP'),
    icon: type === 'error' ? 'mdi-alert-circle' : 'mdi-information'
  }
  alerts.value.unshift(alert)
  
  // 最大10件のアラートを保持
  if (alerts.value.length > 10) {
    alerts.value = alerts.value.slice(0, 10)
  }
}

const updateMonitoringData = (data) => {
  realtimeMonitoring.addDebugLog('info', 'モニタリングデータ更新開始')

  // refを使用しているため、.valueでアクセス
  Object.keys(monitoringData.value).forEach(key => {
    if (data[key] !== null && data[key] !== undefined) {
      monitoringData.value[key].value = data[key]

      // ステータス判定（例：エラーコードがある場合は異常）
      if (key === 'error_code') {
        monitoringData.value[key].status = data[key] ? 'error' : 'normal'
      } else {
        monitoringData.value[key].status = 'normal'
      }

      realtimeMonitoring.addDebugLog('success', `${key}を更新: ${data[key]}`)
    }
  })
}

const fetchEquipmentInfo = async () => {
  try {
    const response = await fetch(`${apiBase}/api/equipment/${equipmentId}`)
    if (response.ok) {
      equipmentInfo.value = await response.json()
      realtimeMonitoring.addDebugLog('success', '設備情報取得成功')
    } else {
      realtimeMonitoring.addDebugLog('error', `設備情報取得失敗: ${response.status}`)
    }
  } catch (error) {
    console.error('設備情報取得エラー:', error)
    realtimeMonitoring.addDebugLog('error', `設備情報取得エラー: ${error.message}`)
  }
}

// ✅ PLC設定を取得して動的にデータ構造を生成
const fetchPLCConfigs = async () => {
  try {
    const response = await fetch(`${apiBase}/api/equipment/${equipmentId}/plc_configs`)
    if (response.ok) {
      plcConfigs.value = await response.json()
      realtimeMonitoring.addDebugLog('success', `PLC設定取得成功: ${plcConfigs.value.length}項目`)
      console.log('📋 PLC設定:', plcConfigs.value)

      // 動的にデータ構造を生成
      await initializeDynamicStructures()
    } else {
      realtimeMonitoring.addDebugLog('error', `PLC設定取得失敗: ${response.status}`)
    }
  } catch (error) {
    console.error('PLC設定取得エラー:', error)
    realtimeMonitoring.addDebugLog('error', `PLC設定取得エラー: ${error.message}`)
  }
}

// ✅ 動的データ構造の初期化
const initializeDynamicStructures = async () => {
  console.log('[START] initializeDynamicStructures')
  try {
    console.log('🔧 動的データ構造を初期化中...')
    realtimeMonitoring.addDebugLog('info', '動的データ構造を初期化中...')

    // アイコンマッピング（データ型や名前に基づいて適切なアイコンを選択）
    const getIcon = (name, dataType) => {
      const nameLower = name.toLowerCase()
      if (nameLower.includes('温度') || nameLower.includes('temp')) return 'mdi-thermometer'
      if (nameLower.includes('圧力') || nameLower.includes('press')) return 'mdi-gauge'
      if (nameLower.includes('電流') || nameLower.includes('current')) return 'mdi-flash'
      if (nameLower.includes('電圧') || nameLower.includes('volt')) return 'mdi-lightning-bolt'
      if (nameLower.includes('速度') || nameLower.includes('speed')) return 'mdi-speedometer'
      if (nameLower.includes('回転') || nameLower.includes('rpm')) return 'mdi-rotate-3d-variant'
      if (nameLower.includes('数量') || nameLower.includes('count')) return 'mdi-counter'
      if (nameLower.includes('時間') || nameLower.includes('time')) return 'mdi-timer-outline'
      if (nameLower.includes('エラー') || nameLower.includes('error')) return 'mdi-alert-circle-outline'
      return 'mdi-chart-line' // デフォルト
    }

    // 1. monitoringDataを動的生成
    const newMonitoringData = {}
    plcConfigs.value.forEach(config => {
      if (config.enabled) {
        newMonitoringData[config.data_type] = {
          label: config.name,
          value: null,
          unit: config.unit || '',
          icon: config.icon || getIcon(config.name, config.data_type),
          status: 'normal'
        }
      }
    })
    monitoringData.value = newMonitoringData
    console.log('✅ monitoringData初期化完了:', Object.keys(newMonitoringData))
    realtimeMonitoring.addDebugLog('success', `monitoringData初期化: ${Object.keys(newMonitoringData).length}項目`)

    // 2. chartConfigsを動的生成（各項目ごとにカードを作成）
    const newChartConfigs = []
    plcConfigs.value.forEach(config => {
      if (config.enabled) {
        newChartConfigs.push({
          id: config.data_type,
          title: config.name,
          icon: config.icon || getIcon(config.name, config.data_type),
          data: null,
          options: null
        })
      }
    })

    // チャート管理コンポーザブルを使って初期化
    chartManagement.initializeCharts(newChartConfigs, monitoringData.value)

    // DOMの更新を待つ（複数回実行して確実に反映）
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100)) // 100ms待機
    await nextTick()

    console.log('✅ chartConfigs初期化完了:', newChartConfigs.length, '個')
    console.log('🔍 chartManagement.chartConfigs.value:', chartManagement.chartConfigs.value)
    console.log('🔍 chartManagement.chartConfigs.value.length:', chartManagement.chartConfigs.value?.length)

    // チャートの準備完了
    await nextTick()
    console.log('✅ チャート準備完了')

    // 各チャートの状態を確認
    chartManagement.chartConfigs.value?.forEach((chart, i) => {
      console.log(`📊 チャート[${i}]:`, {
        id: chart.id,
        title: chart.title,
        hasData: !!chart.data,
        hasDatasets: !!chart.data?.datasets,
        datasetsLength: chart.data?.datasets?.length,
        hasOptions: !!chart.options
      })
    })

    realtimeMonitoring.addDebugLog('success', `chartConfigs初期化: ${newChartConfigs.length}個`)

    // 3. tableHeadersを動的生成
    const newTableHeaders = [
      { title: '時刻', value: 'timestamp', width: '180' }
    ]
    plcConfigs.value.forEach(config => {
      if (config.enabled) {
        newTableHeaders.push({
          title: `${config.name}${config.unit ? '(' + config.unit + ')' : ''}`,
          value: config.data_type,
          align: 'center'
        })
      }
    })
    tableHeaders.value = newTableHeaders
    console.log('✅ tableHeaders初期化完了:', newTableHeaders.length, '列')
    realtimeMonitoring.addDebugLog('success', `tableHeaders初期化: ${newTableHeaders.length}列`)

    console.log('✅ 全動的データ構造の初期化完了')
    realtimeMonitoring.addDebugLog('success', '全動的データ構造の初期化完了')
    console.log('[END] initializeDynamicStructures SUCCESS')
  } catch (error) {
    console.error('❌ 動的データ構造初期化エラー:', error)
    console.error('[END] initializeDynamicStructures ERROR:', error)
    realtimeMonitoring.addDebugLog('error', `動的データ構造初期化エラー: ${error.message}`)
  }
}

const fetchLatestData = async () => {
  try {
    const response = await fetch(`${apiBase}/api/logs/${equipmentId}/latest`)
    if (response.ok) {
      const data = await response.json()
      realtimeMonitoring.addDebugLog('success', `最新データ取得成功: ${data.timestamp}`)

      // handleDataUpdateを使用（updateMonitoringData + updateChartData + データ履歴追加を一括処理）
      handleDataUpdate(data)
    } else {
      realtimeMonitoring.addDebugLog('error', `最新データ取得失敗: ${response.status}`)
    }
  } catch (error) {
    console.error('最新データ取得エラー:', error)
    realtimeMonitoring.addDebugLog('error', `最新データ取得エラー: ${error.message}`)
  }
}

// CSVエクスポート機能
const exportDataHistoryToCSV = () => {
  try {
    if (!dataHistory.value || dataHistory.value.length === 0) {
      toast.warning('エクスポートするデータがありません')
      return
    }

    // ヘッダー行を動的生成（tableHeadersから取得）
    const headerFields = tableHeaders.value.map(h => h.value)
    const header = headerFields.join(',') + '\n'

    // データ行を生成
    const rows = dataHistory.value.map(log => {
      const values = headerFields.map(field => {
        const value = log[field]
        return value !== null && value !== undefined ? value : ''
      })
      return values.join(',')
    })

    const csvContent = header + rows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    a.download = `${equipmentId}_realtime_${timestamp}.csv`
    a.click()
    URL.revokeObjectURL(url)

    toast.success(`CSVファイルをダウンロードしました（${dataHistory.value.length}件）`)
  } catch (error) {
    console.error('CSVエクスポートエラー:', error)
    toast.error('CSVのダウンロードに失敗しました')
  }
}

// ライフサイクル
onMounted(async () => {
  console.log('🚀 モニタリング画面の初期化開始')
  realtimeMonitoring.addDebugLog('info', 'モニタリング画面の初期化開始')

  try {
    // 1. 設備情報の取得
    await fetchEquipmentInfo()

    // 2. PLC設定の取得と動的データ構造の初期化（チャート初期化含む）
    await fetchPLCConfigs()

    // 3. 最新データの取得
    await fetchLatestData()

    // 4. WebSocket接続の設定
    realtimeMonitoring.setupWebSocket($socket)

    console.log('✅ モニタリング画面の初期化完了')
    realtimeMonitoring.addDebugLog('success', 'モニタリング画面の初期化完了')
  } catch (error) {
    console.error('❌ 初期化エラー:', error)
    realtimeMonitoring.addDebugLog('error', `初期化エラー: ${error.message}`)
  }
})

onBeforeUnmount(() => {
  realtimeMonitoring.disconnect()
})
</script>

<style scoped>
.text-h4 {
  font-weight: 600;
}

.v-card {
  transition: all 0.3s ease;
}

.v-card:hover {
  transform: translateY(-2px);
}
</style> 