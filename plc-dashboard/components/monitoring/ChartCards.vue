<template>
  <v-row class="mb-6" v-if="chartConfigs && chartConfigs.length > 0">
    <v-col
      cols="12"
      md="6"
      v-for="(chart, index) in chartConfigs"
      :key="chart.id"
      class="card-grid-item"
      v-memo="[chart.id, chart.title]"
    >
      <v-card class="glass-card pa-6">
        <v-card-title class="text-h5 mb-4 d-flex align-center">
          <v-icon size="large" class="mr-3" color="primary">{{ chart.icon }}</v-icon>
          {{ chart.title }}
          <v-chip
            size="x-small"
            color="info"
            class="ml-2"
            variant="flat"
            v-if="debugMode"
          >
            {{ chart.data?.datasets?.[0]?.data?.length || 0 }}点
          </v-chip>
        </v-card-title>
        <v-divider class="mb-4"></v-divider>
        <div class="chart-container" style="height: 350px;">
          <!-- デバッグ用情報 -->
          <div v-if="debugMode" class="text-caption mb-2">
            チャート状態: data={{ !!chart.data }}, datasets={{ !!chart.data?.datasets }}, length={{ chart.data?.datasets?.length || 0 }}, options={{ !!chart.options }}
          </div>
          <!-- チャート表示 -->
          <ClientOnly v-if="chart.data && chart.data.datasets && chart.options">
            <Line
              :ref="el => setChartRef(el, chart.id)"
              :data="chart.data"
              :options="chart.options"
            />
          </ClientOnly>
          <!-- データ待機中表示 -->
          <div v-else class="d-flex align-center justify-center" style="height: 100%;">
            <div class="text-center">
              <v-icon size="80" color="grey-lighten-1">mdi-chart-line</v-icon>
              <div class="text-h6 text-grey mt-4">データ待機中...</div>
              <v-progress-circular indeterminate color="primary" size="40" class="mt-4"></v-progress-circular>
              <div class="text-caption text-grey mt-2">
                data: {{ !!chart.data }}, datasets: {{ !!chart.data?.datasets }}, options: {{ !!chart.options }}
              </div>
            </div>
          </div>
        </div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { Line } from 'vue-chartjs'

/**
 * チャートカード表示コンポーネント
 * リアルタイムグラフを表示（v-memoでカード再レンダリング防止）
 */
defineProps({
  chartConfigs: {
    type: Array,
    default: () => []
  },
  debugMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['chart-ref-set'])

/**
 * Chart.jsのrefを設定
 * @param {Object} el - Chart.jsコンポーネント
 * @param {string} chartId - チャートID
 */
const setChartRef = (el, chartId) => {
  emit('chart-ref-set', { el, chartId })
}
</script>

<style scoped>
.chart-container {
  position: relative;
  width: 100%;
}

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.glass-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.card-grid-item {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
