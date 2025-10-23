import { ref, nextTick, toRaw } from 'vue'

/**
 * チャート管理用コンポーザブル
 * Chart.jsの初期化とデータ更新を管理
 */
export const useChartManagement = (options = {}) => {
  const { onDebugLog = null } = options

  const chartConfigs = ref([])

  // デバッグログヘルパー
  const log = (type, message) => {
    if (onDebugLog) {
      onDebugLog(type, message)
    }
  }

  /**
   * チャート設定を初期化
   * @param {Array} configs - チャート設定配列
   * @param {Object} monitoringData - モニタリングデータ
   */
  const initializeCharts = (configs, monitoringData) => {
    try {
      console.log('📊 チャート初期化開始:', configs?.length || 0, '個')

      if (!configs || !Array.isArray(configs)) {
        console.error('❌ configs が配列ではありません:', configs)
        return
      }

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

      configs.forEach((chart, index) => {
        if (!chart) {
          console.error(`❌ チャート[${index}]がnullです`)
          return
        }

        console.log(`📊 チャート初期化中: ${chart.id}`)

        const colorIndex = index % colors.length

        chart.data = {
          labels: [],
          datasets: [
            {
              label: chart.title,
              data: [],
              borderColor: colors[colorIndex],
              backgroundColor: 'transparent',
              tension: 0.4,
              pointRadius: 3,
              pointHoverRadius: 5
            }
          ]
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

      chartConfigs.value = configs
      console.log('✅ 全チャート初期化完了')
      log('success', '全チャート初期化完了')
    } catch (error) {
      console.error('❌ チャート初期化エラー:', error)
      log('error', `チャート初期化エラー: ${error.message}`)
    }
  }

  /**
   * チャートデータを更新
   * @param {Object} newData - 新しいデータ
   */
  const updateChartData = (newData) => {
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

      // リアクティビティを無効化して循環参照を防ぐ
      nextTick(() => {
        const rawChartConfigs = toRaw(chartConfigs.value)
        rawChartConfigs.forEach((chart, index) => {
          // 多重安全チェック
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

          if (
            !chart.data.datasets ||
            !Array.isArray(chart.data.datasets) ||
            !chart.data.datasets[0]
          ) {
            console.warn(`⚠️ チャート[${index}].data.datasetsが無効:`, chart.id)
            return
          }

          if (
            !chart.data.datasets[0].data ||
            !Array.isArray(chart.data.datasets[0].data)
          ) {
            console.warn(
              `⚠️ チャート[${index}].data.datasets[0].dataが配列ではない:`,
              chart.id
            )
            return
          }

          const value = newData[chart.id]
          if (value !== null && value !== undefined) {
            // 安全にデータ追加
            chart.data.labels.push(timestamp)
            chart.data.datasets[0].data.push(value)

            // 最大50点まで保持
            if (chart.data.labels.length > 50) {
              chart.data.labels.shift()
              chart.data.datasets[0].data.shift()
            }

            log('success', `チャート更新: ${chart.id}=${value}`)
            console.log(`✅ チャート更新成功: ${chart.id}=${value}`)
          }
        })
      })
    } catch (error) {
      console.error('❌ updateChartData エラー:', error)
      log('error', `チャート更新エラー: ${error.message}`)
    }
  }

  return {
    // 状態
    chartConfigs,

    // メソッド
    initializeCharts,
    updateChartData
  }
}
