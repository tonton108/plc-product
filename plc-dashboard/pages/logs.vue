<template>
    <v-container class="py-8">
      <!-- 設備選択 -->
      <v-select
        v-model="selectedEquipmentId"
        :items="equipmentList"
        item-title="equipment_id"
        item-value="equipment_id"
        label="設備を選択"
        class="mb-4 glass-card pa-4"
        elevation="0"
        density="comfortable"
      />

      <v-card class="pa-4 glass-card" elevation="0">
        <v-card-title class="d-flex justify-space-between align-center">
          <span class="text-h5 font-weight-bold">PLC ロググラフ</span>
          <div class="d-flex align-center gap-4">
            <v-select
              v-model="themeColor"
              :items="['blue', 'green', 'red']"
              label="テーマ"
              density="compact"
              style="max-width: 100px"
            />
            <v-select
              v-model="selectedPeriod"
              :items="periodOptions"
              label="期間"
              density="compact"
              style="max-width: 100px"
            />
          </div>
        </v-card-title>
        <ClientOnly>
          <v-tabs v-model="tab">
            <v-tab>グラフ</v-tab>
            <v-tab>テーブル</v-tab>
          </v-tabs>
        </ClientOnly>

        <v-card-text>
          <v-window v-model="tab">
            <v-window-item :value="0">
              <div style="height: 400px">
                <div v-if="filteredLogs.length === 0" class="text-center text-grey">データがありません</div>
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
                density="compact"
                class="mt-4"
              />
            </v-window-item>
          </v-window>

          <v-alert v-if="hasAbnormalValue" type="error" class="mt-4" density="compact" variant="tonal">
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

  const config = useRuntimeConfig()

  ChartJS.register(
    Title,
    Tooltip,
    Legend,
    LineElement,
    CategoryScale,
    LinearScale,
    PointElement,
  )

  const chartData = ref(null)
  const chartOptions = ref({})
  const logsRaw = ref([])
  const selectedPeriod = ref('1h')
  const periodOptions = ['1h', '6h', '24h']
  const themeColor = ref('blue')
  const tab = ref(0)
  const selectedEquipmentId = ref('DEMO_001')
  const equipmentList = ref([])

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
      labels: filteredLogs.value.map((log) =>
        new Date(log.timestamp).toLocaleString('ja-JP', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        })
      ),
      datasets: [
        {
          label: 'D100',
          data: filteredLogs.value.map((log) => log.value),
          borderColor: themeColor.value || 'blue',
          backgroundColor: 'lightblue',
          tension: 0.2,
        },
      ],
    }
  }

  const hasAbnormalValue = computed(() => {
    return logsRaw.value.some((log) => log.value >= 130 || log.value <= 110)
  })

  const headers = [
    { title: '日時', value: 'timestamp' },
    { title: '値', value: 'value' },
  ]

  const downloadCSV = () => {
    const header = 'timestamp,value\n'
    const rows = logsRaw.value.map((log) => `${log.timestamp},${log.value}`)
    const csvContent = header + rows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = 'plc_logs.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  // 設備一覧を取得
  const fetchEquipment = async () => {
    try {
      const res = await fetch(`${config.public.apiBase}/api/equipment`)
      const data = await res.json()
      equipmentList.value = data
      if (data.length > 0 && !selectedEquipmentId.value) {
        selectedEquipmentId.value = data[0].equipment_id
      }
    } catch (err) {
      console.error('設備一覧取得失敗:', err)
    }
  }

  let intervalId = null
  const fetchLogs = async () => {
    if (!selectedEquipmentId.value) return

    try {
      // 正しいエンドポイント: /api/logs/<equipment_id>/history_optimized
      const period = selectedPeriod.value || '1h'
      const res = await fetch(`${config.public.apiBase}/api/logs/${selectedEquipmentId.value}/history_optimized?period=${period}`)
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      const response = await res.json(); const logs = response.data || response
      logsRaw.value = logs
      updateChart()
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
      animation: {
        duration: 500,
        easing: 'easeInOutQuad'
      },
      plugins: {
        legend: { position: 'top' },
        title: {
          display: true,
          text: 'PLC D100 ログ',
        },
        zoom: {
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: 'x',
          },
          pan: {
            enabled: true,
            mode: 'x',
          },
        },
      },
    }

    await fetchEquipment()
    await fetchLogs()
    if (intervalId) clearInterval(intervalId)
    intervalId = setInterval(fetchLogs, 5000)
  })

  onBeforeUnmount(() => {
    clearInterval(intervalId)
  })

  watch([selectedPeriod, themeColor, logsRaw], updateChart)
  watch(selectedEquipmentId, fetchLogs)
  </script>

  <style scoped>
  canvas {
    max-width: 100%;
    height: auto !important;
    display: block;
  }
  </style>
