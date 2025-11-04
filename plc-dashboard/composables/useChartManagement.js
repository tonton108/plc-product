import { ref, nextTick } from 'vue'

/**
 * チャート管理用コンポーザブル
 * Chart.jsの初期化とデータ更新を管理
 */
export const useChartManagement = (options = {}) => {
  const { onDebugLog = null } = options

  const chartConfigs = ref([])

  // Chart.jsインスタンスを直接管理（Vueのリアクティビティ外）
  const chartInstances = new Map()

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

      // mapを使って新しい配列を作成（リアクティビティ確保）
      const initializedConfigs = configs.map((chart, index) => {
        if (!chart) {
          console.error(`❌ チャート[${index}]がnullです`)
          return chart
        }

        console.log(`📊 チャート初期化中: ${chart.id}`)

        const colorIndex = index % colors.length

        // 新しいオブジェクトを作成（ネイティブ配列を明示的に作成）
        const newChart = {
          ...chart,
          data: {
            labels: Array(0), // ネイティブ配列を明示的に作成
            datasets: [
              {
                label: chart.title,
                data: Array(0), // ネイティブ配列を明示的に作成
                borderColor: colors[colorIndex],
                backgroundColor: 'transparent',
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 5
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false, // アニメーション無効化でチラつき防止
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
        }

        console.log(`✅ チャート初期化完了: ${chart.id}`)
        return newChart
      })

      chartConfigs.value = initializedConfigs
      console.log('✅ 全チャート初期化完了')
      log('success', '全チャート初期化完了')
    } catch (error) {
      console.error('❌ チャート初期化エラー:', error)
      log('error', `チャート初期化エラー: ${error.message}`)
    }
  }

  /**
   * Chart.jsインスタンスを登録
   * @param {string} chartId - チャートID
   * @param {Object} chartInstance - Chart.jsインスタンス
   */
  const registerChartInstance = (chartId, chartInstance) => {
    // VueのProxyをネイティブ配列に置き換え（スタックオーバーフロー防止）
    if (chartInstance.data && chartInstance.data.labels) {
      chartInstance.data.labels = Array.from(chartInstance.data.labels)
    }
    if (chartInstance.data && chartInstance.data.datasets) {
      chartInstance.data.datasets.forEach(dataset => {
        if (dataset.data) {
          dataset.data = Array.from(dataset.data)
        }
      })
    }

    chartInstances.set(chartId, chartInstance)
    console.log(`✅ Chart.jsインスタンス登録: ${chartId}`, {
      labelsType: chartInstance.data?.labels?.constructor?.name,
      dataType: chartInstance.data?.datasets?.[0]?.data?.constructor?.name
    })
  }

  /**
   * チャートデータを更新（Chart.js直接操作版 - カード再レンダリングなし）
   * @param {Object} newData - 新しいデータ
   */
  const updateChartData = (newData) => {
    try {
      if (!newData || !newData.timestamp) {
        console.warn('⚠️ 無効なデータ:', newData)
        return
      }

      const timestamp = new Date(newData.timestamp).toLocaleTimeString('ja-JP')

      // Chart.jsインスタンスを直接操作（Vueのリアクティビティをバイパス）
      chartInstances.forEach((chartInstance, chartId) => {
        const value = newData[chartId]
        if (value !== null && value !== undefined) {
          // Chart.jsインスタンスとDOM要素の存在確認
          if (!chartInstance || !chartInstance.canvas || !chartInstance.canvas.ownerDocument) {
            console.warn(`⚠️ チャートがDOMから削除されています: ${chartId}`)
            return
          }

          // Chart.jsの内部データを直接操作（toRaw不要、ネイティブ配列を使用）
          const labels = chartInstance.data.labels
          const dataArray = chartInstance.data.datasets[0].data

          // 配列操作（VueのProxyではなく、ネイティブ配列として）
          labels.push(timestamp)
          dataArray.push(value)

          // 最大50点を超えたら古いデータを削除
          if (labels.length > 50) {
            labels.shift()
            dataArray.shift()
          }

          // Chart.jsのupdate()を呼び出し（'none'でアニメーション無効化）
          chartInstance.update('none')

          console.log(`✅ チャート直接更新: ${chartId}=${value}, データ数: ${dataArray.length}`)
        }
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
    updateChartData,
    registerChartInstance
  }
}
