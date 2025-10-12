<!--
🔧 キャッシュバスター: 2025-07-23 08:51:00 
このコメントはブラウザキャッシュを無効化するために追加されました
-->
<template>
  <v-container fluid>
    <!-- ヘッダー部分 -->
    <v-row class="mb-4">
      <v-col cols="12">
        <v-card color="primary" dark class="pa-4">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h4">
                <v-icon large class="mr-3">mdi-monitor-dashboard</v-icon>
                {{ equipmentInfo?.equipment_id || 'N/A' }} - リアルタイムモニタリング
              </v-card-title>
              <v-card-subtitle>
                {{ equipmentInfo?.manufacturer }} {{ equipmentInfo?.series }}
                <v-chip 
                  :color="connectionStatus ? 'success' : 'error'" 
                  text-color="white" 
                  size="small" 
                  class="ml-2"
                >
                  {{ connectionStatus ? '接続中' : '切断' }}
                </v-chip>
              </v-card-subtitle>
            </v-col>
            <v-col cols="auto">
              <v-btn @click="goBack" variant="outlined" color="white">
                <v-icon left>mdi-arrow-left</v-icon>
                戻る
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>

    <!-- ステータスカード -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="2" v-for="(item, key) in monitoringData" :key="key">
        <v-card :color="getCardColor(item.status)" class="text-center pa-3" dark>
          <v-icon size="40" class="mb-2">{{ item.icon }}</v-icon>
          <div class="text-h4 font-weight-bold">{{ item.value || 'N/A' }}</div>
          <div class="text-subtitle-1">{{ item.label }}</div>
          <div class="text-caption">{{ item.unit }}</div>
          <v-chip 
            size="x-small" 
            :color="item.status === 'normal' ? 'success' : 'error'"
            class="mt-1"
          >
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
    <v-row>
      <v-col cols="12" md="6" v-for="chart in chartConfigs" :key="chart.id">
        <v-card class="pa-4" elevation="3">
          <v-card-title class="text-h6">
            <v-icon class="mr-2">{{ chart.icon }}</v-icon>
            {{ chart.title }}
          </v-card-title>
          <div style="height: 300px;">
            <Chart
              v-if="chart.data && chart.data.datasets[0].data.length > 0"
              :data="chart.data"
              :options="chart.options"
              type="line"
            />
            <div v-else class="d-flex align-center justify-center" style="height: 100%;">
              <div class="text-center text-grey">
                <v-icon size="48" color="grey">mdi-chart-line</v-icon>
                <div class="mt-2">データ待機中...</div>
              </div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 最新データログ -->
    <v-row class="mt-4">
      <v-col cols="12">
        <v-card class="pa-4" elevation="3">
          <v-card-title class="text-h6">
            <v-icon class="mr-2">mdi-table</v-icon>
            最新データ履歴（最新{{ dataHistory.length }}件）
          </v-card-title>
          <v-data-table
            :headers="tableHeaders"
            :items="dataHistory"
            density="compact"
            :items-per-page="10"
            class="mt-3"
          >
            <template #[`item.timestamp`]="{ item }">
              {{ formatDateTime(item.timestamp) }}
            </template>
            <template #[`item.error_code`]="{ item }">
              <v-chip
                size="small"
                :color="item.error_code ? 'error' : 'success'"
                text-color="white"
              >
                {{ item.error_code || '正常' }}
              </v-chip>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- ✅ デバッグパネル -->
    <v-row class="mt-4" v-if="debugMode">
      <v-col cols="12">
        <v-card class="pa-4" elevation="3" color="grey-lighten-4">
          <v-card-title class="text-h6 d-flex align-center">
            <v-icon class="mr-2" color="info">mdi-bug</v-icon>
            デバッグ情報
            <v-spacer></v-spacer>
            <v-btn @click="testLatestAPI" size="small" color="primary">
              <v-icon left>mdi-api</v-icon>
              API テスト
            </v-btn>
            <v-btn @click="clearDebugLog" size="small" color="warning" class="ml-2">
              <v-icon left>mdi-delete</v-icon>
              ログクリア
            </v-btn>
          </v-card-title>
          
          <v-row>
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-3">
                <v-card-subtitle class="text-subtitle-2 font-weight-bold">WebSocket状態</v-card-subtitle>
                <div class="text-body-2">
                  <div>接続状態: <v-chip size="small" :color="connectionStatus ? 'success' : 'error'">{{ connectionStatus ? '接続中' : '切断' }}</v-chip></div>
                  <div>Socket ID: {{ socketInfo.id || 'N/A' }}</div>
                  <div>設備ID: {{ equipmentId }}</div>
                  <div>データ履歴件数: {{ dataHistory.length }}</div>
                  <div>最終更新: {{ lastDataUpdate || 'なし' }}</div>
                </div>
              </v-card>
            </v-col>
            
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-3">
                <v-card-subtitle class="text-subtitle-2 font-weight-bold">受信イベント数</v-card-subtitle>
                <div class="text-body-2">
                  <div>plc_data_update: {{ debugCounters.plc_data_update }}</div>
                  <div>equipment_data_update: {{ debugCounters.equipment_data_update }}</div>
                  <div>status: {{ debugCounters.status }}</div>
                  <div>connect: {{ debugCounters.connect }}</div>
                  <div>disconnect: {{ debugCounters.disconnect }}</div>
                </div>
              </v-card>
            </v-col>
          </v-row>
          
          <v-card variant="outlined" class="pa-3 mt-3">
            <v-card-subtitle class="text-subtitle-2 font-weight-bold">デバッグログ (最新20件)</v-card-subtitle>
            <div style="height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px;">
              <div v-for="(log, index) in debugLogs.slice(-20)" :key="index" :class="getLogClass(log.type)">
                [{{ log.timestamp }}] {{ log.message }}
              </div>
            </div>
          </v-card>
        </v-card>
      </v-col>
    </v-row>

    <!-- ✅ デバッグモード切り替えボタン -->
    <v-fab
      location="bottom right"
      size="small"
      :color="debugMode ? 'success' : 'info'"
      @click="debugMode = !debugMode"
    >
      <v-icon>{{ debugMode ? 'mdi-bug-check' : 'mdi-bug' }}</v-icon>
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
import { ref, onMounted, onBeforeUnmount, reactive, computed, nextTick, toRaw } from 'vue'
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
const { $socket } = useNuxtApp()

// データ定義
const equipmentId = route.params.id
const equipmentInfo = ref(null)
const connectionStatus = ref(false)
const dataHistory = ref([])
const alerts = ref([])

// ✅ デバッグ機能追加
const debugMode = ref(false)
const debugLogs = ref([])
const debugCounters = reactive({
  plc_data_update: 0,
  equipment_data_update: 0,
  status: 0,
  connect: 0,
  disconnect: 0
})
const socketInfo = ref({})
const lastDataUpdate = ref(null)

// モニタリングデータ
const monitoringData = reactive({
  production_count: {
    label: '生産数量',
    value: null,
    unit: '個',
    icon: 'mdi-counter',
    status: 'normal'
  },
  current: {
    label: '電流',
    value: null,
    unit: 'A',
    icon: 'mdi-flash',
    status: 'normal'
  },
  temperature: {
    label: '温度',
    value: null,
    unit: '℃',
    icon: 'mdi-thermometer',
    status: 'normal'
  },
  pressure: {
    label: '圧力',
    value: null,
    unit: 'MPa',
    icon: 'mdi-gauge',
    status: 'normal'
  },
  cycle_time: {
    label: 'サイクルタイム',
    value: null,
    unit: 's',
    icon: 'mdi-timer-outline',
    status: 'normal'
  },
  error_code: {
    label: 'エラーコード',
    value: null,
    unit: '',
    icon: 'mdi-alert-circle-outline',
    status: 'normal'
  }
})

// グラフ設定
const chartConfigs = ref([
  {
    id: 'current',
    title: '電流値',
    icon: 'mdi-flash',
    data: null,
    options: null
  },
  {
    id: 'temperature',
    title: '温度',
    icon: 'mdi-thermometer',
    data: null,
    options: null
  },
  {
    id: 'pressure',
    title: '圧力',
    icon: 'mdi-gauge',
    data: null,
    options: null
  },
  {
    id: 'cycle_time',
    title: 'サイクルタイム',
    icon: 'mdi-timer-outline',
    data: null,
    options: null
  }
])

// テーブルヘッダー
const tableHeaders = [
  { title: '時刻', value: 'timestamp', width: '180' },
  { title: '生産数量', value: 'production_count', align: 'center' },
  { title: '電流(A)', value: 'current', align: 'center' },
  { title: '温度(℃)', value: 'temperature', align: 'center' },
  { title: '圧力(MPa)', value: 'pressure', align: 'center' },
  { title: 'サイクルタイム(s)', value: 'cycle_time', align: 'center' },
  { title: 'エラーコード', value: 'error_code', align: 'center' }
]

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
  router.push('/')
}

const removeAlert = (alertId) => {
  const index = alerts.value.findIndex(alert => alert.id === alertId)
  if (index !== -1) {
    alerts.value.splice(index, 1)
  }
}

// ✅ デバッグ用ヘルパーメソッド
const addDebugLog = (type, message) => {
  try {
    const timestamp = new Date().toLocaleTimeString('ja-JP')
    
    // デバッグログ配列の安全性チェック
    if (!debugLogs.value) {
      debugLogs.value = []
    }
    
    debugLogs.value.push({ type, message, timestamp })
    
    if (debugLogs.value.length > 100) {
      debugLogs.value = debugLogs.value.slice(-50)
    }
  } catch (error) {
    console.error('デバッグログエラー:', error)
  }
}

const getLogClass = (type) => {
  switch (type) {
    case 'error': return 'text-red'
    case 'warning': return 'text-orange'
    case 'success': return 'text-green'
    case 'info': return 'text-blue'
    default: return 'text-grey'
  }
}

const clearDebugLog = () => {
  debugLogs.value = []
  Object.keys(debugCounters).forEach(key => {
    debugCounters[key] = 0
  })
  addDebugLog('info', 'デバッグログをクリアしました')
}

const testLatestAPI = async () => {
  addDebugLog('info', 'API テスト開始: /api/logs/latest')
  try {
    const response = await fetch(`http://localhost:5000/api/logs/${equipmentId}/latest`)
    if (response.ok) {
      const data = await response.json()
      addDebugLog('success', `API テスト成功: ${data.timestamp}`)
      console.log('📡 API テスト結果:', data)
    } else {
      addDebugLog('error', `API テスト失敗: ${response.status}`)
    }
  } catch (error) {
    addDebugLog('error', `API テストエラー: ${error.message}`)
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

const initializeCharts = () => {
  try {
    console.log('📊 チャート初期化開始:', chartConfigs.value?.length || 0, '個')
    
    if (!chartConfigs.value || !Array.isArray(chartConfigs.value)) {
      console.error('❌ chartConfigs.value が配列ではありません:', chartConfigs.value)
      return
    }
    
    chartConfigs.value.forEach((chart, index) => {
      if (!chart) {
        console.error(`❌ チャート[${index}]がnullです`)
        return
      }
      
      console.log(`📊 チャート初期化中: ${chart.id}`)
      
      chart.data = {
        labels: [],
        datasets: [{
          label: chart.title,
          data: [],
          borderColor: chart.id === 'current' ? '#2196F3' : 
                       chart.id === 'temperature' ? '#FF5722' :
                       chart.id === 'pressure' ? '#4CAF50' : '#FF9800',
          backgroundColor: 'transparent',
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 5
        }]
      }
      
      chart.options = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        scales: {
          x: {
            title: { display: true, text: '時刻' },
            type: 'category'
          },
          y: {
            title: { 
              display: true, 
              text: monitoringData[chart.id]?.unit || ''
            }
          }
        },
        plugins: {
          legend: { display: false },
          title: { display: false }
        }
      }
      
      console.log(`✅ チャート初期化完了: ${chart.id}`)
    })
    
    console.log('✅ 全チャート初期化完了')
  } catch (error) {
    console.error('❌ チャート初期化エラー:', error)
    try {
      addDebugLog('error', `チャート初期化エラー: ${error.message}`)
    } catch (logError) {
      console.error('デバッグログエラー:', logError)
    }
  }
}

const updateChartData = (newData) => {
  // ✅ 完全な安全性チェック（エラー完全防止）
  try {
    if (!newData || !newData.timestamp) {
      console.warn('⚠️ 無効なデータ:', newData)
      return
    }
    
    if (!chartConfigs.value || !Array.isArray(chartConfigs.value)) {
      console.warn('⚠️ chartConfigs が無効:', chartConfigs.value)
      return
    }
    
    const timestamp = new Date(newData.timestamp).toLocaleTimeString('ja-JP')
    
    // 🔑 リアクティビティを無効化して循環参照を防ぐ
    nextTick(() => {
      const rawChartConfigs = toRaw(chartConfigs.value)
      rawChartConfigs.forEach((chart, index) => {
        // 🛡️ 多重安全チェック
        if (!chart) {
          console.warn(`⚠️ チャート[${index}]がnull`)
          return
        }
        
        if (!chart.data) {
          console.warn(`⚠️ チャート[${index}].dataがnull:`, chart.id)
          return
        }
        
        if (!chart.data.labels || !Array.isArray(chart.data.labels)) {
          console.warn(`⚠️ チャート[${index}].data.labelsが配列ではない:`, chart.id)
          return
        }
        
        if (!chart.data.datasets || !Array.isArray(chart.data.datasets) || !chart.data.datasets[0]) {
          console.warn(`⚠️ チャート[${index}].data.datasetsが無効:`, chart.id)
          return
        }
        
        if (!chart.data.datasets[0].data || !Array.isArray(chart.data.datasets[0].data)) {
          console.warn(`⚠️ チャート[${index}].data.datasets[0].dataが配列ではない:`, chart.id)
          return
        }
        
        const value = newData[chart.id]
        if (value !== null && value !== undefined) {
          // 🔒 安全にデータ追加
          chart.data.labels.push(timestamp)
          chart.data.datasets[0].data.push(value)
          
          // 最大50点まで保持
          if (chart.data.labels.length > 50) {
            chart.data.labels.shift()
            chart.data.datasets[0].data.shift()
          }
          
          if (typeof addDebugLog === 'function') {
            addDebugLog('success', `チャート更新: ${chart.id}=${value}`)
          }
          
          console.log(`✅ チャート更新成功: ${chart.id}=${value}`)
        }
      })
    })
    
  } catch (error) {
    console.error('❌ updateChartData エラー:', error)
    if (typeof addDebugLog === 'function') {
      addDebugLog('error', `チャート更新エラー: ${error.message}`)
    }
  }
}

const updateMonitoringData = (data) => {
  addDebugLog('info', 'モニタリングデータ更新開始')
  
  Object.keys(monitoringData).forEach(key => {
    if (data[key] !== null && data[key] !== undefined) {
      monitoringData[key].value = data[key]
      
      // ステータス判定（例：エラーコードがある場合は異常）
      if (key === 'error_code') {
        monitoringData[key].status = data[key] ? 'error' : 'normal'
      } else {
        monitoringData[key].status = 'normal'
      }
      
      addDebugLog('success', `${key}を更新: ${data[key]}`)
    }
  })
}

const fetchEquipmentInfo = async () => {
  try {
    const response = await fetch(`http://localhost:5000/api/equipment/${equipmentId}`)
    if (response.ok) {
      equipmentInfo.value = await response.json()
      addDebugLog('success', '設備情報取得成功')
    } else {
      addDebugLog('error', `設備情報取得失敗: ${response.status}`)
    }
  } catch (error) {
    console.error('設備情報取得エラー:', error)
    addDebugLog('error', `設備情報取得エラー: ${error.message}`)
  }
}

const fetchLatestData = async () => {
  try {
    const response = await fetch(`http://localhost:5000/api/logs/${equipmentId}/latest`)
    if (response.ok) {
      const data = await response.json()
      addDebugLog('success', `最新データ取得成功: ${data.timestamp}`)
      
      // ✅ 安全にデータ更新を実行
      updateMonitoringData(data)
      updateChartData(data)
      
      // ✅ データ履歴の安全な追加
      if (dataHistory.value) {
        dataHistory.value.unshift(data)
        if (dataHistory.value.length > 100) {
          dataHistory.value = dataHistory.value.slice(0, 100)
        }
        addDebugLog('success', `データ履歴追加: 総件数=${dataHistory.value.length}`)
      }
    } else {
      addDebugLog('error', `最新データ取得失敗: ${response.status}`)
    }
  } catch (error) {
    console.error('最新データ取得エラー:', error)
    addDebugLog('error', `最新データ取得エラー: ${error.message}`)
  }
}

// WebSocket接続設定
const setupWebSocket = () => {
  // Socket.IOクライアントが利用可能かチェック
  if (!$socket) {
    console.warn('❌ Socket.IO client not available')
    addDebugLog('error', 'Socket.IO クライアントが利用できません')
    return
  }
  
  console.log('🔌 WebSocket接続を開始...')
  addDebugLog('info', 'WebSocket接続を開始')
  $socket.connect()
  
  $socket.on('connect', () => {
    connectionStatus.value = true
    debugCounters.connect++
    socketInfo.value = { id: $socket.id }
    console.log('✅ WebSocket接続完了')
    console.log('🔗 Socket ID:', $socket.id)
    addDebugLog('success', `WebSocket接続完了 (ID: ${$socket.id})`)
    
    // モニタリングルームに参加
    $socket.emit('join_monitoring', { equipment_id: equipmentId })
    console.log(`🏠 モニタリングルーム参加: equipment_${equipmentId}`)
    addDebugLog('info', `モニタリングルーム参加: equipment_${equipmentId}`)
  })
  
  $socket.on('disconnect', () => {
    connectionStatus.value = false
    debugCounters.disconnect++
    socketInfo.value = {}
    console.log('❌ WebSocket切断')
    addDebugLog('warning', 'WebSocket切断')
  })
  
  // ✅ 接続状態の確認
  $socket.on('status', (data) => {
    debugCounters.status++
    console.log('📊 WebSocket状態:', data)
    addDebugLog('info', `状態受信: ${data.msg}`)
  })
  
  // ✅ エラーハンドリング追加
  $socket.on('connect_error', (error) => {
    console.error('❌ WebSocket接続エラー:', error)
    addDebugLog('error', `接続エラー: ${error.message}`)
  })
  
  // リアルタイムデータ受信
  $socket.on('plc_data_update', (data) => {
    debugCounters.plc_data_update++
    lastDataUpdate.value = new Date().toLocaleTimeString('ja-JP')
    console.log('📥 plc_data_update 受信:', data)
    console.log('🔍 設備ID比較:', { 受信: data.equipment_id, 現在: equipmentId, 一致: data.equipment_id === equipmentId })
    addDebugLog('info', `plc_data_update 受信 (${data.equipment_id})`)
    
    if (data.equipment_id === equipmentId) {
      console.log('🔄 PLCデータ受信 (plc_data_update):', data)
      addDebugLog('success', `PLCデータ処理開始: 生産数=${data.production_count}`)
      
      updateMonitoringData(data)
      updateChartData(data)
      
      // データ履歴に追加
      dataHistory.value.unshift(data)
      console.log('📝 データ履歴更新:', { 新規追加: data.timestamp, 総件数: dataHistory.value.length })
      addDebugLog('success', `データ履歴更新: 総件数=${dataHistory.value.length}`)
      
      if (dataHistory.value.length > 100) {
        dataHistory.value = dataHistory.value.slice(0, 100)
      }
      
      // エラーアラート
      if (data.error_code) {
        addAlert('error', 'エラー発生', `エラーコード: ${data.error_code}`)
        addDebugLog('warning', `エラー検出: ${data.error_code}`)
      }
    } else {
      console.log('⚠️ 設備IDが不一致のため処理をスキップ')
      addDebugLog('warning', `設備ID不一致: 受信=${data.equipment_id}, 期待=${equipmentId}`)
    }
  })
  
  // 設備固有データ受信
  $socket.on('equipment_data_update', (data) => {
    debugCounters.equipment_data_update++
    console.log('📥 equipment_data_update 受信:', data)
    addDebugLog('info', `equipment_data_update 受信 (${data.equipment_id})`)
    
    if (data.equipment_id === equipmentId) {
      console.log('🔄 設備データ受信 (equipment_data_update):', data)
      updateMonitoringData(data)
      updateChartData(data)
      
      dataHistory.value.unshift(data)
      console.log('📝 設備固有データ履歴更新:', { 新規追加: data.timestamp, 総件数: dataHistory.value.length })
      addDebugLog('success', `設備固有データ更新: 総件数=${dataHistory.value.length}`)
      
      if (dataHistory.value.length > 100) {
        dataHistory.value = dataHistory.value.slice(0, 100)
      }
    }
  })
  
  // ✅ 定期的な接続確認
  setInterval(() => {
    if ($socket) {
      const status = {
        接続状態: $socket.connected,
        SocketID: $socket.id,
        設備ID: equipmentId,
        履歴件数: dataHistory.value.length
      }
      console.log('🔍 WebSocket状態確認:', status)
      addDebugLog('info', `定期確認: ${$socket.connected ? '接続中' : '切断'}, 履歴=${dataHistory.value.length}件`)
    }
  }, 10000) // 10秒ごと
}

// ライフサイクル
onMounted(async () => {
  // ✅ デバッグログの初期化を最優先で実行
  if (!debugLogs.value) {
    debugLogs.value = []
  }
  
  console.log('🚀 モニタリング画面の初期化開始')
  addDebugLog('info', 'モニタリング画面の初期化開始')
  
  try {
    // ✅ 1. チャートの初期化（最優先で実行）
    console.log('📊 チャートを初期化中...')
    addDebugLog('info', 'チャートを初期化中...')
    initializeCharts()
    
    // ✅ 2. 設備情報の取得
    console.log('🔧 設備情報を取得中...')
    addDebugLog('info', '設備情報を取得中...')
    await fetchEquipmentInfo()
    
    // ✅ 3. 最新データの取得（チャート初期化後に実行）
    console.log('📥 最新データを取得中...')
    addDebugLog('info', '最新データを取得中...')
    await fetchLatestData()
    
    // ✅ 4. WebSocket接続の設定
    console.log('🔌 WebSocket接続を設定中...')
    addDebugLog('info', 'WebSocket接続を設定中...')
    setupWebSocket()
    
    console.log('✅ モニタリング画面の初期化完了')
    addDebugLog('success', 'モニタリング画面の初期化完了')
  } catch (error) {
    console.error('❌ 初期化エラー:', error)
    try {
      addDebugLog('error', `初期化エラー: ${error.message}`)
    } catch (logError) {
      console.error('デバッグログ記録エラー:', logError)
    }
  }
})

onBeforeUnmount(() => {
  if ($socket) {
    $socket.emit('leave_monitoring', { equipment_id: equipmentId })
    $socket.disconnect()
  }
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