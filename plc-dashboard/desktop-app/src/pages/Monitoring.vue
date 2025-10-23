<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <v-btn @click="goBack" color="grey">
          <v-icon left>mdi-arrow-left</v-icon>
          戻る
        </v-btn>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-h5">
            {{ equipmentId }} - リアルタイムモニタリング
            <v-chip :color="statusColor" text-color="white" size="small" class="ml-2">
              {{ statusText }}
            </v-chip>
          </v-card-title>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="6" lg="3" v-for="item in dataItems" :key="item.key">
        <v-card>
          <v-card-title>{{ item.label }}</v-card-title>
          <v-card-text>
            <div class="text-h4">{{ currentData[item.key] || '--' }}</div>
            <div class="text-caption text-grey">{{ item.unit }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>データ履歴</v-card-title>
          <v-card-text>
            <div ref="chartContainer" style="height: 400px;">
              <canvas ref="chartCanvas"></canvas>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { io } from 'socket.io-client'
import axios from 'axios'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const route = useRoute()
const router = useRouter()
const equipmentId = route.params.id
const apiBase = 'http://localhost:5000'

const currentData = ref({})
const statusColor = ref('grey')
const statusText = ref('接続中...')
const chartCanvas = ref(null)
let chart = null
let socket = null

const dataItems = [
  { key: 'production_count', label: '生産数量', unit: '個' },
  { key: 'current', label: '電流', unit: 'A' },
  { key: 'temperature', label: '温度', unit: '℃' },
  { key: 'pressure', label: '圧力', unit: 'MPa' }
]

const goBack = () => {
  router.push('/')
}

const initChart = () => {
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: '電流 (A)',
          data: [],
          borderColor: 'rgb(75, 192, 192)',
          tension: 0.1
        },
        {
          label: '温度 (℃)',
          data: [],
          borderColor: 'rgb(255, 99, 132)',
          tension: 0.1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  })
}

const updateChart = (data) => {
  if (!chart) return

  const timestamp = new Date(data.timestamp).toLocaleTimeString()
  chart.data.labels.push(timestamp)
  chart.data.datasets[0].data.push(data.current)
  chart.data.datasets[1].data.push(data.temperature)

  // 最新50件のみ表示
  if (chart.data.labels.length > 50) {
    chart.data.labels.shift()
    chart.data.datasets.forEach(dataset => dataset.data.shift())
  }

  chart.update()
}

const connectSocket = () => {
  socket = io(apiBase, {
    transports: ['websocket', 'polling']
  })

  socket.on('connect', () => {
    console.log('Socket.IO接続成功')
    statusText.value = '接続中'
    statusColor.value = 'success'

    // モニタリングルームに参加
    socket.emit('join_monitoring', { equipment_id: equipmentId })
  })

  socket.on('disconnect', () => {
    console.log('Socket.IO切断')
    statusText.value = '切断'
    statusColor.value = 'error'
  })

  socket.on('equipment_data_update', (data) => {
    if (data.equipment_id === equipmentId) {
      currentData.value = data
      updateChart(data)
    }
  })
}

const fetchLatestData = async () => {
  try {
    const response = await axios.get(`${apiBase}/api/logs/${equipmentId}/latest`)
    currentData.value = response.data
  } catch (error) {
    console.error('最新データ取得エラー:', error)
  }
}

onMounted(async () => {
  await fetchLatestData()
  initChart()
  connectSocket()
})

onBeforeUnmount(() => {
  if (socket) {
    socket.emit('leave_monitoring', { equipment_id: equipmentId })
    socket.disconnect()
  }
  if (chart) {
    chart.destroy()
  }
})
</script>
