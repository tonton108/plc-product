<template>
  <v-container>
    <v-card class="pa-4" elevation="4">
      <v-card-title class="text-h6">
        {{ equipment?.name }}（{{ equipment?.manufacturer }}）のロググラフ
      </v-card-title>

      <v-tabs v-model="tab">
        <v-tab>グラフ</v-tab>
        <v-tab>テーブル</v-tab>
      </v-tabs>

      <v-card-text>
        <v-window v-model="tab">
          <v-window-item :value="0">
            <div style="height: 400px">
              <div v-if="filteredLogs.length === 0" class="text-center text-grey">
                データがありません
              </div>
              <Chart
                v-else
                :data="chartData"
                :options="chartOptions"
                type="line"
              />
            </div>
          </v-window-item>

          <v-window-item :value="1">
            <v-data-table
              :headers="headers"
              :items="filteredLogs"
              dense
              class="mt-4"
            />
          </v-window-item>
        </v-window>

        <v-alert v-if="hasAbnormalValue" type="error" class="mt-4" dense text>
          異常値が検出されました（110以下 または 130以上）！
        </v-alert>

        <v-btn class="mt-4" color="primary" @click="downloadCSV">
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
import { useRoute } from 'vue-router'

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
const config = useRuntimeConfig()
const apiBase = config.public.apiBase
const equipmentId = route.params.id

const tab = ref(0)
const chartData = ref(null)
const chartOptions = ref({})
const logsRaw = ref([])
const selectedPeriod = ref('24h')
const periodOptions = ['1h', '6h', '24h', '7d', '30d']
const equipment = ref(null)

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

const filteredLogs = computed(() => {
  const now = new Date()
  const rangeMs = {
    '1h': 60 * 60 * 1000,
    '6h': 6 * 60 * 60 * 1000,
    '24h': 24 * 60 * 60 * 1000,
  }[selectedPeriod.value]
  return logsRaw.value.filter(log => now - new Date(log.timestamp) <= rangeMs)
})

const updateChart = () => {
  chartData.value = {
    labels: filteredLogs.value.map(log =>
      new Date(log.timestamp).toLocaleString('ja-JP', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
      })
    ),
    datasets: [
      {
        label: 'D100',
        data: filteredLogs.value.map(log => log.value),
        borderColor: 'blue',
        backgroundColor: 'lightblue',
        tension: 0.2,
      },
    ],
  }
}

const hasAbnormalValue = computed(() => {
  return logsRaw.value.some(log => log.value >= 130 || log.value <= 110)
})

const headers = [
  { title: '日時', value: 'timestamp' },
  { title: '値', value: 'value' },
]

const downloadCSV = () => {
  const header = 'timestamp,value\n'
  const rows = logsRaw.value.map(log => `${log.timestamp},${log.value}`)
  const csvContent = header + rows.join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = `${equipment?.id}_logs.csv`
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

  await fetchEquipmentInfo()
  await fetchLogs()
  intervalId = setInterval(fetchLogs, 10000)
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