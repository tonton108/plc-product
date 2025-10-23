<template>
  <v-container>
    <v-row class="mb-6">
      <v-col>
        <v-card class="pa-6" color="primary" dark elevation="8">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h4 mb-2">PLC リアルタイムモニタリング</v-card-title>
              <v-card-subtitle class="text-subtitle-1">設備一覧からモニタリングしたい設備を選択してください</v-card-subtitle>
            </v-col>
            <v-col cols="auto">
              <ThemeToggle />
              <v-btn
                color="white"
                size="large"
                class="ml-3 mr-3"
                @click="$router.push('/dashboard')"
              >
                <v-icon>mdi-view-dashboard</v-icon>
                <span class="ml-2">ダッシュボード</span>
              </v-btn>
              <v-btn
                color="white"
                size="large"
                class="mr-3"
                :loading="loading"
                @click="fetchEquipment"
              >
                <v-icon>mdi-refresh</v-icon>
                <span class="ml-2">更新</span>
              </v-btn>
              <v-btn-toggle
                v-model="viewMode"
                mandatory
                color="white"
                divided
                rounded="lg"
              >
                <v-btn value="card" size="large">
                  <v-icon>mdi-view-grid</v-icon>
                  <span class="ml-2">カード</span>
                </v-btn>
                <v-btn value="list" size="large">
                  <v-icon>mdi-view-list</v-icon>
                  <span class="ml-2">リスト</span>
                </v-btn>
              </v-btn-toggle>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="loading">
      <v-col class="text-center">
        <v-progress-circular indeterminate color="primary" size="50"></v-progress-circular>
        <p class="mt-3">設備データを読み込み中...</p>
      </v-col>
    </v-row>

    <v-row v-else-if="equipmentList.length === 0">
      <v-col class="text-center">
        <v-alert type="info">
          登録されている設備がありません。
        </v-alert>
      </v-col>
    </v-row>

    <!-- カード表示 -->
    <v-row v-else-if="viewMode === 'card'">
      <v-col
        v-for="equipment in equipmentList"
        :key="equipment.id"
        cols="12" sm="6" md="4"
      >
        <v-card class="mx-auto" elevation="4" hover>
          <v-card-title class="text-h5 d-flex align-center pa-4">
            <span class="flex-grow-1">{{ equipment.equipment_id }}</span>
            <v-chip
              :color="getStatusColor(equipment.status)"
              text-color="white"
              size="small"
            >
              {{ equipment.status }}
            </v-chip>
          </v-card-title>
          <v-divider></v-divider>
          <v-card-subtitle class="pt-3 pb-2">
            <v-icon size="small" class="mr-1">mdi-factory</v-icon>
            {{ equipment.manufacturer }} - {{ equipment.series }}
          </v-card-subtitle>
          <v-card-text class="pb-2">
            <v-list density="compact" class="bg-transparent">
              <v-list-item density="compact">
                <template #prepend>
                  <v-icon size="small">mdi-raspberry-pi</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>ラズパイIP:</strong> {{ equipment.ip }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item density="compact">
                <template #prepend>
                  <v-icon size="small">mdi-server-network</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>PLC IP:</strong> {{ equipment.plc_ip || 'N/A' }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item density="compact">
                <template #prepend>
                  <v-icon size="small">mdi-ethernet</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>ポート:</strong> {{ equipment.port }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item density="compact">
                <template #prepend>
                  <v-icon size="small">mdi-timer-outline</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>更新間隔:</strong> {{ equipment.interval }}秒
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-divider></v-divider>
          <v-card-actions class="pa-3">
            <v-row dense>
              <v-col cols="6">
                <v-tooltip text="リアルタイムモニタリング" location="bottom">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      color="primary"
                      variant="elevated"
                      block
                      size="large"
                      @click="goToMonitoring(equipment.equipment_id)"
                    >
                      <v-icon class="mr-1" color="white">mdi-monitor-dashboard</v-icon>監視
                    </v-btn>
                  </template>
                </v-tooltip>
              </v-col>
              <v-col cols="6">
                <v-tooltip text="履歴データ・グラフ表示" location="bottom">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      color="secondary"
                      variant="elevated"
                      block
                      size="large"
                      @click="goToLogs(equipment.equipment_id)"
                    >
                      <v-icon class="mr-1" color="white">mdi-chart-line</v-icon>ログ
                    </v-btn>
                  </template>
                </v-tooltip>
              </v-col>
            </v-row>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- リスト表示 -->
    <v-row v-else>
      <v-col cols="12">
        <v-data-table
          :headers="tableHeaders"
          :items="equipmentList"
          item-value="equipment_id"
          class="elevation-2"
        >
          <template #[`item.equipment_id`]="{ item }">
            <strong>{{ item.equipment_id }}</strong>
          </template>
          <template #[`item.status`]="{ item }">
            <v-chip
              :color="getStatusColor(item.status)"
              text-color="white"
              size="small"
            >
              {{ item.status }}
            </v-chip>
          </template>
          <template #[`item.manufacturer`]="{ item }">
            {{ item.manufacturer }} - {{ item.series }}
          </template>
          <template #[`item.plc_ip`]="{ item }">
            {{ item.plc_ip || 'N/A' }}
          </template>
          <template #[`item.interval`]="{ item }">
            {{ item.interval }}秒
          </template>
          <template #[`item.actions`]="{ item }">
            <v-btn
              color="primary"
              size="small"
              variant="elevated"
              class="mr-2"
              @click="goToMonitoring(item.equipment_id)"
            >
              <template #prepend>
                <v-icon size="small">mdi-monitor-dashboard</v-icon>
              </template>
              監視
            </v-btn>
            <v-btn
              color="secondary"
              size="small"
              variant="elevated"
              @click="goToLogs(item.equipment_id)"
            >
              <template #prepend>
                <v-icon size="small">mdi-chart-line</v-icon>
              </template>
              ログ
            </v-btn>
          </template>
        </v-data-table>
      </v-col>
    </v-row>

    <v-snackbar v-model="error" color="error" timeout="5000">
      {{ errorMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '~/composables/useToast'

const router = useRouter()
const config = useRuntimeConfig()
const apiBase = config.public.apiBase
const toast = useToast()

const equipmentList = ref([])
const loading = ref(true)
const error = ref(false)
const errorMessage = ref('')

// 表示モード（デフォルト: カード表示）
const viewMode = ref('card')

// テーブルヘッダー定義
const tableHeaders = [
  { title: '設備ID', key: 'equipment_id', align: 'start' },
  { title: 'ステータス', key: 'status', align: 'center' },
  { title: 'メーカー・シリーズ', key: 'manufacturer', align: 'start' },
  { title: 'ラズパイIP', key: 'ip', align: 'start' },
  { title: 'PLC IP', key: 'plc_ip', align: 'start' },
  { title: 'ポート', key: 'port', align: 'center' },
  { title: '更新間隔', key: 'interval', align: 'center' },
  { title: '操作', key: 'actions', align: 'center', sortable: false }
]

const fetchEquipment = async () => {
  try {
    loading.value = true
    const response = await fetch(`${apiBase}/api/equipment`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    equipmentList.value = data
    toast.success(`設備データを更新しました（${data.length}件）`)
  } catch (err) {
    console.error('設備データ取得エラー:', err)
    errorMessage.value = '設備データの取得に失敗しました'
    error.value = true
    toast.error('設備データの取得に失敗しました')
  } finally {
    loading.value = false
  }
}

const getStatusColor = (status) => {
  switch (status) {
    case '正常':
    case '設定済み':
      return 'success'
    case '登録済み':
      return 'warning'
    case 'エラー':
      return 'error'
    default:
      return 'grey'
  }
}

const goToMonitoring = (equipmentId) => {
  router.push(`/monitoring/${equipmentId}`)
}

const goToLogs = (equipmentId) => {
  router.push(`/equipment/${equipmentId}`)
}

// localStorageから表示モードを復元
onMounted(() => {
  if (process.client) {
    const savedViewMode = localStorage.getItem('equipmentListViewMode')
    if (savedViewMode) {
      viewMode.value = savedViewMode
    }
  }
  fetchEquipment()
})

// 表示モードをlocalStorageに保存
watch(viewMode, (newMode) => {
  if (process.client) {
    localStorage.setItem('equipmentListViewMode', newMode)
  }
})
</script>
  