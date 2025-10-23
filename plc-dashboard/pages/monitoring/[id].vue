<!--
🔧 キャッシュバスター: 2025-07-23 08:51:00 
このコメントはブラウザキャッシュを無効化するために追加されました
-->
<template>
  <v-container fluid>
    <!-- ヘッダー部分 -->
    <v-row class="mb-6">
      <v-col cols="12">
        <v-card color="primary" dark class="pa-6" elevation="8">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h4 mb-2 d-flex align-center">
                <v-icon size="x-large" class="mr-4">mdi-monitor-dashboard</v-icon>
                {{ equipmentInfo?.equipment_id || 'N/A' }} - リアルタイムモニタリング
              </v-card-title>
              <v-card-subtitle class="text-subtitle-1 d-flex align-center mt-2">
                <v-icon size="small" class="mr-2">mdi-factory</v-icon>
                {{ equipmentInfo?.manufacturer }} {{ equipmentInfo?.series }}
                <v-chip
                  :color="connectionStatus ? 'success' : 'error'"
                  text-color="white"
                  size="small"
                  class="ml-3"
                  variant="flat"
                >
                  <v-icon size="small" class="mr-1">
                    {{ connectionStatus ? 'mdi-check-circle' : 'mdi-close-circle' }}
                  </v-icon>
                  {{ connectionStatus ? '接続中' : '切断' }}
                </v-chip>
              </v-card-subtitle>
            </v-col>
            <v-col cols="auto">
              <v-btn @click="goBack" variant="elevated" color="white" size="x-large">
                <template v-slot:prepend>
                  <v-icon>mdi-arrow-left</v-icon>
                </template>
                戻る
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>

    <!-- ステータスカード -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="2" v-for="(item, key) in monitoringData" :key="key">
        <v-card :color="getCardColor(item.status)" class="text-center pa-4" dark elevation="6" hover>
          <v-icon size="48" class="mb-3">{{ item.icon }}</v-icon>
          <div class="text-h3 font-weight-bold mb-2">{{ item.value || 'N/A' }}</div>
          <div class="text-h6 mb-1">{{ item.label }}</div>
          <div class="text-body-2 mb-2">{{ item.unit }}</div>
          <v-chip
            size="small"
            :color="item.status === 'normal' ? 'success' : 'error'"
            class="mt-2"
            variant="flat"
          >
            <v-icon size="x-small" class="mr-1">
              {{ item.status === 'normal' ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            {{ item.status === 'normal' ? '正常' : '異常' }}
          </v-chip>
        </v-card>
      </v-col>
    </v-row>

    <!-- アラート表示 -->
    <v-row v-if="alerts.length > 0" class="mb-4">
      <v-col cols="12">
        <v-alert
          v-for="alert in alerts"
          :key="alert.id"
          :type="alert.type"
          prominent
          border="start"
          :icon="alert.icon"
          closable
          @click:close="removeAlert(alert.id)"
        >
          <v-alert-title>{{ alert.title }}</v-alert-title>
          {{ alert.message }}
          <template v-slot:append>
            <div class="text-caption">{{ alert.timestamp }}</div>
          </template>
        </v-alert>
      </v-col>
    </v-row>

    <!-- リアルタイムグラフ -->
    <v-row class="mb-6">
      <v-col cols="12" md="6" v-for="chart in chartManagement.chartConfigs.value" :key="chart.id">
        <v-card class="pa-6" elevation="6">
          <v-card-title class="text-h5 mb-4 d-flex align-center">
            <v-icon size="large" class="mr-3" color="primary">{{ chart.icon }}</v-icon>
            {{ chart.title }}
          </v-card-title>
          <v-divider class="mb-4"></v-divider>
          <div style="height: 350px;">
            <Chart
              v-if="chart.data && chart.data.datasets[0].data.length > 0"
              :data="chart.data"
              :options="chart.options"
              type="line"
            />
            <div v-else class="d-flex align-center justify-center" style="height: 100%;">
              <div class="text-center">
                <v-icon size="80" color="grey-lighten-1">mdi-chart-line</v-icon>
                <div class="text-h6 text-grey mt-4">データ待機中...</div>
              </div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 最新データログ -->
    <v-row class="mb-6">
      <v-col cols="12">
        <v-card class="pa-6" elevation="6">
          <v-card-title class="text-h5 mb-4 d-flex align-center">
            <v-icon size="large" class="mr-3" color="primary">mdi-table</v-icon>
            最新データ履歴
            <v-chip size="small" color="info" class="ml-3" variant="flat">
              {{ dataHistory.length }}件
            </v-chip>
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              variant="elevated"
              @click="exportDataHistoryToCSV"
            >
              <template #prepend>
                <v-icon>mdi-download</v-icon>
              </template>
              CSV出力
            </v-btn>
          </v-card-title>
          <v-divider class="mb-4"></v-divider>
          <v-data-table
            :headers="tableHeaders"
            :items="dataHistory"
            density="comfortable"
            :items-per-page="15"
            class="elevation-0"
          >
            <template #[`item.timestamp`]="{ item }">
              <span class="text-body-2">{{ formatDateTime(item.timestamp) }}</span>
            </template>
            <template #[`item.error_code`]="{ item }">
              <v-chip
                size="small"
                :color="item.error_code ? 'error' : 'success'"
                text-color="white"
                variant="flat"
              >
                <v-icon size="x-small" class="mr-1">
                  {{ item.error_code ? 'mdi-alert-circle' : 'mdi-check-circle' }}
                </v-icon>
                {{ item.error_code || '正常' }}
              </v-chip>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

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
import { Chart } from 'vue-chartjs'
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '~/composables/useToast'
import { useRealtimeMonitoring } from '~/composables/useRealtimeMonitoring'
import { useChartManagement } from '~/composables/useChartManagement'

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

// メソッド
const getCardColor = (status) => {
  switch (status) {
    case 'error': return 'error'
    case 'warning': return 'warning'
    default: return 'primary'
  }
}

const formatDateTime = (timestamp) => {
  return new Date(timestamp).toLocaleString('ja-JP')
}

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

  // データ履歴に追加
  dataHistory.value.unshift(data)
  if (dataHistory.value.length > 100) {
    dataHistory.value = dataHistory.value.slice(0, 100)
  }

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
      initializeDynamicStructures()
    } else {
      realtimeMonitoring.addDebugLog('error', `PLC設定取得失敗: ${response.status}`)
    }
  } catch (error) {
    console.error('PLC設定取得エラー:', error)
    realtimeMonitoring.addDebugLog('error', `PLC設定取得エラー: ${error.message}`)
  }
}

// ✅ 動的データ構造の初期化
const initializeDynamicStructures = () => {
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

    // 2. chartConfigsを動的生成
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
    console.log('✅ chartConfigs初期化完了:', newChartConfigs.length, '個')
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
  } catch (error) {
    console.error('❌ 動的データ構造初期化エラー:', error)
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