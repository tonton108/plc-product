<template>
  <v-container fluid>
    <!-- ヘッダー -->
    <v-row class="mb-6">
      <v-col cols="12">
        <v-card color="primary" dark class="pa-6" elevation="8">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h3 mb-2">
                <v-icon size="x-large" class="mr-4">mdi-view-dashboard</v-icon>
                複数設備監視ダッシュボード
              </v-card-title>
              <v-card-subtitle class="text-subtitle-1">
                全設備のリアルタイムデータを一覧表示
              </v-card-subtitle>
            </v-col>
            <v-col cols="auto">
              <ThemeToggle />
              <v-btn
                color="white"
                size="large"
                class="ml-3 mr-3"
                :loading="loading"
                @click="refreshAll"
              >
                <v-icon>mdi-refresh</v-icon>
                <span class="ml-2">全更新</span>
              </v-btn>
              <v-btn
                color="white"
                size="large"
                @click="$router.push('/')"
              >
                <v-icon>mdi-arrow-left</v-icon>
                <span class="ml-2">戻る</span>
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>

    <!-- サマリーカード -->
    <v-row class="mb-6">
      <v-col cols="12" md="3">
        <v-card color="success" dark elevation="4">
          <v-card-text>
            <div class="text-h6">正常稼働</div>
            <div class="text-h2 mt-2">{{ normalCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="warning" dark elevation="4">
          <v-card-text>
            <div class="text-h6">警告</div>
            <div class="text-h2 mt-2">{{ warningCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="error" dark elevation="4">
          <v-card-text>
            <div class="text-h6">エラー</div>
            <div class="text-h2 mt-2">{{ errorCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card color="info" dark elevation="4">
          <v-card-text>
            <div class="text-h6">総設備数</div>
            <div class="text-h2 mt-2">{{ equipmentList.length }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 設備カードグリッド -->
    <v-row>
      <v-col
        v-for="equipment in equipmentList"
        :key="equipment.equipment_id"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card elevation="6" hover>
          <v-card-title class="d-flex align-center">
            <v-icon size="large" class="mr-3" :color="getStatusColor(equipment.status)">
              mdi-factory
            </v-icon>
            {{ equipment.equipment_id }}
            <v-spacer></v-spacer>
            <v-chip
              :color="getStatusColor(equipment.status)"
              size="small"
              variant="flat"
            >
              {{ equipment.status || '未接続' }}
            </v-chip>
          </v-card-title>

          <v-divider></v-divider>

          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template #prepend>
                  <v-icon size="small">mdi-factory</v-icon>
                </template>
                <v-list-item-title>
                  {{ equipment.manufacturer }} {{ equipment.series }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon size="small">mdi-ip-network</v-icon>
                </template>
                <v-list-item-title>
                  PLC: {{ equipment.plc_ip || 'N/A' }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon size="small">mdi-clock-outline</v-icon>
                </template>
                <v-list-item-title>
                  更新間隔: {{ equipment.interval }}秒
                </v-list-item-title>
              </v-list-item>
            </v-list>

            <!-- 最新データプレビュー -->
            <v-divider class="my-3"></v-divider>
            <div v-if="latestData[equipment.equipment_id]" class="mt-3">
              <div class="text-subtitle-2 mb-2">最新データ:</div>
              <v-chip
                v-for="(value, key) in getPreviewData(latestData[equipment.equipment_id])"
                :key="key"
                size="small"
                class="mr-2 mb-2"
                variant="outlined"
              >
                {{ key }}: {{ value }}
              </v-chip>
            </div>
            <div v-else class="text-grey text-caption mt-3">
              データ待機中...
            </div>
          </v-card-text>

          <v-divider></v-divider>

          <v-card-actions>
            <v-btn
              color="primary"
              variant="elevated"
              size="small"
              @click="$router.push(`/monitoring/${equipment.equipment_id}`)"
            >
              <v-icon size="small" class="mr-1">mdi-monitor-dashboard</v-icon>
              詳細監視
            </v-btn>
            <v-btn
              color="secondary"
              variant="elevated"
              size="small"
              @click="$router.push(`/equipment/${equipment.equipment_id}`)"
            >
              <v-icon size="small" class="mr-1">mdi-chart-line</v-icon>
              ログ表示
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- データがない場合 -->
    <v-row v-if="equipmentList.length === 0 && !loading">
      <v-col cols="12">
        <v-card class="pa-8" elevation="4">
          <div class="text-center">
            <v-icon size="80" color="grey-lighten-1">mdi-alert-circle-outline</v-icon>
            <div class="text-h5 text-grey mt-4">設備が登録されていません</div>
            <v-btn
              color="primary"
              size="large"
              class="mt-6"
              @click="$router.push('/')"
            >
              設備一覧に戻る
            </v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '~/composables/useToast'

const router = useRouter()
const config = useRuntimeConfig()
const apiBase = config.public.apiBase
const toast = useToast()
const { $socket } = useNuxtApp()

const equipmentList = ref([])
const latestData = ref({})
const loading = ref(true)

// サマリー統計
const normalCount = computed(() =>
  equipmentList.value.filter(e => e.status === '正常' || e.status === '設定済み').length
)
const warningCount = computed(() =>
  equipmentList.value.filter(e => e.status === '警告' || e.status === '登録済み').length
)
const errorCount = computed(() =>
  equipmentList.value.filter(e => e.status === 'エラー').length
)

const getStatusColor = (status) => {
  switch (status) {
    case '正常':
    case '設定済み':
      return 'success'
    case '警告':
    case '登録済み':
      return 'warning'
    case 'エラー':
      return 'error'
    default:
      return 'grey'
  }
}

// 最新データのプレビュー（最初の3項目のみ表示）
const getPreviewData = (data) => {
  if (!data) return {}
  const filtered = Object.fromEntries(
    Object.entries(data).filter(([key]) =>
      !['equipment_id', 'timestamp'].includes(key)
    )
  )
  return Object.fromEntries(Object.entries(filtered).slice(0, 3))
}

const fetchEquipment = async () => {
  try {
    loading.value = true
    const response = await fetch(`${apiBase}/api/equipment`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    equipmentList.value = data
  } catch (err) {
    console.error('設備データ取得エラー:', err)
    toast.error('設備データの取得に失敗しました')
  } finally {
    loading.value = false
  }
}

const fetchLatestDataForAll = async () => {
  for (const equipment of equipmentList.value) {
    try {
      const response = await fetch(`${apiBase}/api/logs/${equipment.equipment_id}/latest`)
      if (response.ok) {
        const data = await response.json()
        latestData.value[equipment.equipment_id] = data
      }
    } catch (error) {
      console.error(`最新データ取得エラー (${equipment.equipment_id}):`, error)
    }
  }
}

const refreshAll = async () => {
  await fetchEquipment()
  await fetchLatestDataForAll()
  toast.success('全設備のデータを更新しました')
}

// WebSocket接続設定
const setupWebSocket = () => {
  if (!$socket) {
    console.warn('Socket.IO client not available')
    return
  }

  $socket.connect()

  $socket.on('connect', () => {
    console.log('✅ Dashboard WebSocket接続完了')
    // 全設備のモニタリングルームに参加
    equipmentList.value.forEach(equipment => {
      $socket.emit('join_monitoring', { equipment_id: equipment.equipment_id })
    })
  })

  // リアルタイムデータ受信
  $socket.on('plc_data_update', (data) => {
    if (data.equipment_id) {
      latestData.value[data.equipment_id] = data
    }
  })

  $socket.on('equipment_data_update', (data) => {
    if (data.equipment_id) {
      latestData.value[data.equipment_id] = data
    }
  })
}

onMounted(async () => {
  await fetchEquipment()
  await fetchLatestDataForAll()
  setupWebSocket()
})

onBeforeUnmount(() => {
  if ($socket) {
    equipmentList.value.forEach(equipment => {
      $socket.emit('leave_monitoring', { equipment_id: equipment.equipment_id })
    })
    $socket.disconnect()
  }
})
</script>

<style scoped>
.v-card {
  transition: all 0.3s ease;
}

.v-card:hover {
  transform: translateY(-4px);
}
</style>
