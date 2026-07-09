import { ref, onBeforeUnmount } from 'vue'

/**
 * リアルタイムモニタリング用コンポーザブル
 * WebSocket接続とデータ受信を管理
 * 最終更新: 2025-10-27
 */
export const useRealtimeMonitoring = (equipmentId, options = {}) => {
  const {
    onDataUpdate = null,
    onConnect = null,
    onDisconnect = null,
    debugMode = false
  } = options

  // 状態管理
  const connectionStatus = ref(false)
  const socketInfo = ref({})
  const lastDataUpdate = ref(null)
  const debugLogs = ref([])
  const debugCounters = ref({
    plc_data_update: 0,
    status: 0,
    connect: 0,
    disconnect: 0
  })

  // デバッグログ追加
  const addDebugLog = (type, message) => {
    if (!debugMode) return

    try {
      const timestamp = new Date().toLocaleTimeString('ja-JP')
      const newLog = { type, message, timestamp }

      // 新しい配列を作成してリアクティビティを正しく管理
      const currentLogs = debugLogs.value || []
      const newLogs = [...currentLogs, newLog]
      debugLogs.value = newLogs.slice(-100)  // 最大100件まで
    } catch (error) {
      console.error('デバッグログエラー:', error)
    }
  }

  // クリーンアップ関数（setupWebSocket が設定し、disconnect が呼ぶ）
  let cleanup = null

  // WebSocket接続設定
  const setupWebSocket = ($socket) => {
    if (!$socket) {
      console.warn('❌ Socket.IO client not available')
      addDebugLog('error', 'Socket.IO クライアントが利用できません')
      return
    }

    // 再セットアップ時は前回のリスナー・タイマーを先に解除
    if (cleanup) cleanup()

    console.log('🔌 WebSocket接続を開始...')
    addDebugLog('info', 'WebSocket接続を開始')
    $socket.connect()

    // 接続イベント
    $socket.on('connect', () => {
      connectionStatus.value = true
      debugCounters.value.connect++
      socketInfo.value = { id: $socket.id }
      console.log('✅ WebSocket接続完了')
      console.log('🔗 Socket ID:', $socket.id)
      addDebugLog('success', `WebSocket接続完了 (ID: ${$socket.id})`)

      // モニタリングルームに参加
      $socket.emit('join_monitoring', { equipment_id: equipmentId })
      console.log(`🏠 モニタリングルーム参加: equipment_${equipmentId}`)
      addDebugLog('info', `モニタリングルーム参加: equipment_${equipmentId}`)

      // コールバック実行
      if (onConnect) onConnect()
    })

    // 切断イベント
    $socket.on('disconnect', () => {
      connectionStatus.value = false
      debugCounters.value.disconnect++
      socketInfo.value = {}
      console.log('❌ WebSocket切断')
      addDebugLog('warning', 'WebSocket切断')

      // コールバック実行
      if (onDisconnect) onDisconnect()
    })

    // ステータスイベント
    $socket.on('status', (data) => {
      debugCounters.value.status++
      console.log('📊 WebSocket状態:', data)
      addDebugLog('info', `状態受信: ${data.msg}`)
    })

    // 接続エラーイベント
    $socket.on('connect_error', (error) => {
      console.error('❌ WebSocket接続エラー:', error)
      addDebugLog('error', `接続エラー: ${error.message}`)

      // サーバーが接続を拒否した場合、トークン失効が原因なら無限リトライせず
      // 再認証へ誘導する。/api/auth/me で有効性を確認し、401なら useApi が
      // セッション破棄＋ログイン画面遷移を行う（期限切れで失効済みトークンが
      // localStorageに残っているケースも捕捉できる）
      const { apiFetch } = useApi()
      apiFetch('/api/auth/me').catch(() => {
        // 401はuseApi側で処理済み。到達不能等のその他エラーはリトライに委ねる
        $socket.disconnect()
      })
    })

    // PLCデータ更新イベント（重複回避のためこのイベントのみ使用）
    $socket.on('plc_data_update', (data) => {
      debugCounters.value.plc_data_update++
      lastDataUpdate.value = new Date().toLocaleTimeString('ja-JP')
      console.log('📥 plc_data_update 受信:', data)
      console.log('🔍 設備ID比較:', {
        受信: data.equipment_id,
        現在: equipmentId,
        一致: data.equipment_id === equipmentId
      })
      addDebugLog('info', `plc_data_update 受信 (${data.equipment_id})`)

      if (data.equipment_id === equipmentId) {
        console.log('🔄 PLCデータ受信 (plc_data_update):', data)
        const dataKeys = Object.keys(data).filter(
          (k) => k !== 'equipment_id' && k !== 'timestamp'
        )
        const dataPreview = dataKeys
          .slice(0, 2)
          .map((k) => `${k}=${data[k]}`)
          .join(', ')
        addDebugLog('success', `PLCデータ処理開始: ${dataPreview}`)

        // コールバック実行
        if (onDataUpdate) onDataUpdate(data)
      } else {
        console.log('⚠️ 設備IDが不一致のため処理をスキップ')
        addDebugLog(
          'warning',
          `設備ID不一致: 受信=${data.equipment_id}, 期待=${equipmentId}`
        )
      }
    })

    // 定期的な接続確認（10秒ごと）
    const intervalId = setInterval(() => {
      if ($socket) {
        const status = {
          接続状態: $socket.connected,
          SocketID: $socket.id,
          設備ID: equipmentId
        }
        console.log('🔍 WebSocket状態確認:', status)
        addDebugLog(
          'info',
          `定期確認: ${$socket.connected ? '接続中' : '切断'}`
        )
      }
    }, 10000)

    // クリーンアップ関数を保持して返す
    // （従来は return するだけで呼び出し元が受け取っておらず、disconnect() が
    //   常に no-op になってリスナーと setInterval がページ遷移ごとに蓄積していた）
    cleanup = () => {
      clearInterval(intervalId)
      if ($socket) {
        // 個別イベントリスナーを解除してメモリリークを防止
        $socket.off('connect')
        $socket.off('disconnect')
        $socket.off('status')
        $socket.off('connect_error')
        $socket.off('plc_data_update')
        $socket.emit('leave_monitoring', { equipment_id: equipmentId })
        $socket.disconnect()
      }
    }
    return cleanup
  }

  // クリーンアップ（コンポーネントアンマウント時）
  const disconnect = () => {
    if (cleanup) {
      cleanup()
      cleanup = null
    }
  }

  onBeforeUnmount(() => {
    disconnect()
  })

  return {
    // 状態
    connectionStatus,
    socketInfo,
    lastDataUpdate,
    debugLogs,
    debugCounters,

    // メソッド
    setupWebSocket,
    disconnect,
    addDebugLog
  }
}
