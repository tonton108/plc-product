<template>
  <v-container class="fade-in">
    <v-row class="mb-6">
      <v-col>
        <v-card class="glass-card-primary pa-6">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h4 mb-2 gradient-text">
                <v-icon size="x-large" class="mr-3">mdi-factory</v-icon>
                PLC リアルタイムモニタリング
              </v-card-title>
              <v-card-subtitle class="text-subtitle-1 text-white">設備一覧からモニタリングしたい設備を選択してください</v-card-subtitle>
            </v-col>
            <v-col cols="auto">
              <ThemeToggle />
              <v-btn
                color="white"
                size="large"
                class="ml-3 mr-3 modern-btn"
                @click="$router.push('/dashboard')"
              >
                <v-icon>mdi-view-dashboard</v-icon>
                <span class="ml-2">ダッシュボード</span>
              </v-btn>
              <v-btn
                color="white"
                size="large"
                class="mr-3 modern-btn"
                :loading="loading"
                @click="fetchEquipment"
              >
                <v-icon>mdi-refresh</v-icon>
                <span class="ml-2">更新</span>
              </v-btn>
              <v-btn
                color="white"
                size="large"
                class="mr-3 modern-btn"
                @click="logout"
              >
                <v-icon>mdi-logout</v-icon>
                <span class="ml-2">ログアウト</span>
              </v-btn>
              <v-btn-toggle
                v-model="viewMode"
                mandatory
                color="white"
                divided
                rounded="xl"
                class="modern-btn"
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
        v-for="(equipment, index) in equipmentList"
        :key="equipment.id"
        cols="12" sm="6" md="4"
        class="card-grid-item"
        :style="{ 'animation-delay': `${index * 0.1}s` }"
      >
        <v-card class="glass-card mx-auto">
          <v-card-title class="text-h5 d-flex align-center pa-4">
            <v-icon size="large" color="primary" class="mr-2">mdi-server</v-icon>
            <span class="flex-grow-1 font-weight-bold">{{ equipment.equipment_id }}</span>
            <v-chip
              :color="getStatusColor(equipment.status)"
              text-color="white"
              size="small"
              variant="elevated"
            >
              <v-icon size="x-small" class="mr-1">mdi-circle</v-icon>
              {{ equipment.status }}
            </v-chip>
          </v-card-title>
          <v-divider opacity="0.2"></v-divider>
          <v-card-subtitle class="pt-3 pb-2 d-flex align-center">
            <v-icon size="small" class="mr-2" color="primary">mdi-factory</v-icon>
            <span class="font-weight-medium">{{ equipment.manufacturer }} - {{ equipment.series }}</span>
          </v-card-subtitle>
          <v-card-text class="pb-2">
            <v-list density="compact" class="bg-transparent">
              <v-list-item density="compact" class="px-0">
                <template #prepend>
                  <v-icon size="small" color="success">mdi-raspberry-pi</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>ラズパイIP:</strong> {{ equipment.ip }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item density="compact" class="px-0">
                <template #prepend>
                  <v-icon size="small" color="info">mdi-server-network</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>PLC IP:</strong> {{ equipment.plc_ip || 'N/A' }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item density="compact" class="px-0">
                <template #prepend>
                  <v-icon size="small" color="warning">mdi-ethernet</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>ポート:</strong> {{ equipment.port }}
                </v-list-item-title>
              </v-list-item>
              <v-list-item density="compact" class="px-0">
                <template #prepend>
                  <v-icon size="small" color="purple">mdi-timer-outline</v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  <strong>更新間隔:</strong> {{ equipment.interval }}秒
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-divider opacity="0.2"></v-divider>
          <v-card-actions class="pa-4">
            <v-row dense>
              <v-col cols="6">
                <v-tooltip location="bottom" content-class="tooltip-custom">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      color="primary"
                      variant="elevated"
                      block
                      size="large"
                      class="modern-btn"
                      @click="goToMonitoring(equipment.equipment_id)"
                    >
                      <v-icon class="mr-1">mdi-monitor-dashboard</v-icon>監視
                    </v-btn>
                  </template>
                  <span>リアルタイムモニタリング</span>
                </v-tooltip>
              </v-col>
              <v-col cols="6">
                <v-tooltip location="bottom" content-class="tooltip-custom">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      color="secondary"
                      variant="elevated"
                      block
                      size="large"
                      class="modern-btn"
                      @click="goToLogs(equipment.equipment_id)"
                    >
                      <v-icon class="mr-1">mdi-chart-line</v-icon>ログ
                    </v-btn>
                  </template>
                  <span>履歴データ・グラフ表示</span>
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
          class="glass-card"
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
            <div class="d-flex justify-center align-center">
              <v-tooltip location="bottom" content-class="tooltip-custom">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    color="primary"
                    size="default"
                    variant="elevated"
                    class="mr-2 modern-btn list-action-btn"
                    prepend-icon="mdi-monitor-dashboard"
                    @click="goToMonitoring(item.equipment_id)"
                  >
                    監視
                  </v-btn>
                </template>
                <span>リアルタイムモニタリング</span>
              </v-tooltip>
              <v-tooltip location="bottom" content-class="tooltip-custom">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    color="secondary"
                    size="default"
                    variant="elevated"
                    class="modern-btn list-action-btn"
                    prepend-icon="mdi-chart-line"
                    @click="goToLogs(item.equipment_id)"
                  >
                    ログ
                  </v-btn>
                </template>
                <span>履歴データ・グラフ表示</span>
              </v-tooltip>
            </div>
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

// 認証ミドルウェアを適用
definePageMeta({
  middleware: 'auth'
})

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

const logout = () => {
  if (process.client) {
    localStorage.removeItem('plc_auth_token')
    localStorage.removeItem('plc_auth_user')
    toast.success('ログアウトしました')
    router.push('/login')
  }
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

<style>
/* ツールチップのカスタムスタイル（グローバル） */
.tooltip-custom {
  background-color: #424242 !important;
  color: #ffffff !important;
  opacity: 0.95 !important;
}

.tooltip-custom span {
  color: #ffffff !important;
}

/* データテーブルの行フォーカス時の紫色のバーを非表示 */
.v-data-table tbody tr:focus {
  border-bottom: none !important;
  outline: none !important;
}

.v-data-table tbody tr:focus::after {
  display: none !important;
}

/* ボタン内のコンテンツ（アイコンとテキスト）を垂直方向で中央揃え */
.v-btn .v-btn__content {
  align-items: center !important;
  display: flex !important;
}

.v-btn .v-icon {
  align-self: center !important;
}

/* リスト表示のアクションボタン（size="small"）用の追加調整 */
.list-action-btn.v-btn--size-small {
  min-height: 32px !important;
  height: 32px !important;
  display: flex !important;
  align-items: center !important;
  padding-top: 6px !important;
  padding-bottom: 6px !important;
}

.list-action-btn.v-btn--size-small .v-btn__prepend {
  align-self: center !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

.list-action-btn.v-btn--size-small .v-btn__content {
  align-self: center !important;
  line-height: 1 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

.list-action-btn.v-btn--size-small .v-icon {
  line-height: 1 !important;
  vertical-align: middle !important;
  align-self: center !important;
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}
</style>
