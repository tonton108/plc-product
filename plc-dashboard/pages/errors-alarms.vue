<template>
  <v-container fluid>
    <!-- ヘッダー -->
    <v-row class="mb-6">
      <v-col cols="12">
        <v-card color="primary" dark class="pa-6" elevation="8">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h3 mb-2">
                <v-icon size="x-large" class="mr-4">mdi-alert-circle</v-icon>
                {{ $t('errorsAlarmsPage.title') }}
              </v-card-title>
              <v-card-subtitle class="text-subtitle-1">
                {{ $t('errorsAlarmsPage.subtitle') }}
              </v-card-subtitle>
            </v-col>
            <v-col cols="auto">
              <LanguageSwitch />
              <ThemeToggle />
              <v-btn
                color="white"
                size="large"
                class="ml-3 mr-3"
                :loading="loading"
                @click="loadData"
              >
                <v-icon>mdi-refresh</v-icon>
                <span class="ml-2">{{ $t('common.refresh') }}</span>
              </v-btn>
              <v-btn
                color="white"
                size="large"
                @click="$router.push('/')"
              >
                <v-icon>mdi-arrow-left</v-icon>
                <span class="ml-2">{{ $t('common.back') }}</span>
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>

    <!-- 設備選択 -->
    <v-row class="mb-6">
      <v-col cols="12" md="6">
        <v-select
          v-model="selectedEquipmentId"
          :items="equipmentList"
          item-title="equipment_id"
          item-value="equipment_id"
          :label="$t('errorsAlarmsPage.selectEquipment')"
          variant="outlined"
          prepend-icon="mdi-factory"
          @update:model-value="loadData"
        ></v-select>
      </v-col>
    </v-row>

    <div v-if="selectedEquipmentId">
      <!-- PLC状態カード -->
      <v-row class="mb-6">
        <v-col cols="12" md="4">
          <v-card :color="plcStatus.is_online ? 'success' : 'error'" dark elevation="4">
            <v-card-text>
              <div class="text-h6">{{ $t('plcStatus.title') }}</div>
              <div class="text-h3 mt-2">
                <v-icon size="x-large" class="mr-2">
                  {{ plcStatus.is_online ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                </v-icon>
                {{ plcStatus.is_online ? $t('plcStatus.online') : $t('plcStatus.offline') }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card color="warning" dark elevation="4">
            <v-card-text>
              <div class="text-h6">{{ $t('plcStatus.consecutiveErrors') }}</div>
              <div class="text-h3 mt-2">{{ $t('plcStatus.consecutiveErrorsValue', { count: plcStatus.consecutive_errors || 0 }) }}</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card color="info" dark elevation="4">
            <v-card-text>
              <div class="text-h6">{{ $t('plcStatus.lastCommunication') }}</div>
              <div class="text-body-1 mt-2">
                {{ formatDateTime(plcStatus.last_communication_at) || $t('plcStatus.notConnected') }}
              </div>
              <div v-if="plcStatus.last_error_type" class="text-body-2 mt-1">
                {{ $t('plcStatus.lastError', { error: plcStatus.last_error_type }) }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- アラーム履歴 -->
      <v-row class="mb-6">
        <v-col cols="12">
          <v-card elevation="6">
            <v-card-title class="bg-error text-white">
              <v-icon class="mr-2">mdi-alarm-light</v-icon>
              {{ $t('alarms.title') }}
              <v-spacer></v-spacer>
              <v-chip color="white" variant="outlined" size="small">
                {{ $t('alarms.count', { count: alarms.length }) }}
              </v-chip>
            </v-card-title>
            <v-card-text>
              <v-data-table
                :headers="alarmHeaders"
                :items="alarms"
                :loading="loading"
                class="elevation-1"
                :items-per-page="10"
              >
                <template v-slot:item.alarm_level="{ item }">
                  <v-chip
                    :color="getAlarmLevelColor(item.alarm_level)"
                    size="small"
                    variant="flat"
                  >
                    {{ item.alarm_level }}
                  </v-chip>
                </template>
                <template v-slot:item.occurred_at="{ item }">
                  {{ formatDateTime(item.occurred_at) }}
                </template>
                <template v-slot:item.cleared_at="{ item }">
                  <v-chip
                    v-if="item.cleared_at"
                    color="success"
                    size="small"
                    variant="outlined"
                  >
                    {{ $t('alarms.cleared') }}
                  </v-chip>
                  <v-chip
                    v-else
                    color="error"
                    size="small"
                    variant="flat"
                  >
                    {{ $t('alarms.notCleared') }}
                  </v-chip>
                </template>
                <template v-slot:item.acknowledged="{ item }">
                  <v-icon v-if="item.acknowledged" color="success">
                    mdi-check-circle
                  </v-icon>
                  <v-icon v-else color="grey">
                    mdi-circle-outline
                  </v-icon>
                </template>
                <template v-slot:item.actions="{ item }">
                  <v-btn
                    v-if="!item.acknowledged"
                    color="primary"
                    size="small"
                    @click="acknowledgeAlarm(item.id)"
                    class="mr-2"
                  >
                    {{ $t('alarms.acknowledge') }}
                  </v-btn>
                  <v-btn
                    v-if="!item.cleared_at"
                    color="success"
                    size="small"
                    @click="clearAlarm(item.id)"
                  >
                    {{ $t('alarms.clear') }}
                  </v-btn>
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- エラーログ -->
      <v-row>
        <v-col cols="12">
          <v-card elevation="6">
            <v-card-title class="bg-warning text-white">
              <v-icon class="mr-2">mdi-alert</v-icon>
              {{ $t('errorLogs.title') }}
              <v-spacer></v-spacer>
              <v-chip color="white" variant="outlined" size="small">
                {{ $t('errorLogs.count', { count: errorLogs.length }) }}
              </v-chip>
            </v-card-title>
            <v-card-text>
              <v-data-table
                :headers="errorLogHeaders"
                :items="errorLogs"
                :loading="loading"
                class="elevation-1"
                :items-per-page="10"
              >
                <template v-slot:item.error_type="{ item }">
                  <v-chip
                    :color="getErrorTypeColor(item.error_type)"
                    size="small"
                    variant="flat"
                  >
                    {{ item.error_type }}
                  </v-chip>
                </template>
                <template v-slot:item.occurred_at="{ item }">
                  {{ formatDateTime(item.occurred_at) }}
                </template>
                <template v-slot:item.resolved_at="{ item }">
                  <v-chip
                    v-if="item.resolved_at"
                    color="success"
                    size="small"
                    variant="outlined"
                  >
                    {{ $t('errorLogs.resolved') }}
                  </v-chip>
                  <v-chip
                    v-else
                    color="warning"
                    size="small"
                    variant="flat"
                  >
                    {{ $t('errorLogs.notResolved') }}
                  </v-chip>
                </template>
                <template v-slot:item.retry_count="{ item }">
                  {{ item.retry_count || 0 }}
                </template>
                <template v-slot:item.actions="{ item }">
                  <v-btn
                    v-if="!item.resolved_at"
                    color="success"
                    size="small"
                    @click="resolveErrorLog(item.id)"
                  >
                    {{ $t('errorLogs.resolve') }}
                  </v-btn>
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- 設備未選択時 -->
    <v-row v-else>
      <v-col cols="12">
        <v-card elevation="4" class="pa-12 text-center">
          <v-icon size="x-large" color="grey">mdi-information-outline</v-icon>
          <div class="text-h5 mt-4">{{ $t('errorsAlarmsPage.noEquipmentSelected') }}</div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { t } = useI18n()
const { formatDateTime } = useDateTime()
const loading = ref(false)
const equipmentList = ref([])
const selectedEquipmentId = ref(null)
const plcStatus = ref({})
const alarms = ref([])
const errorLogs = ref([])

// アラーム履歴のヘッダー
const alarmHeaders = computed(() => [
  { title: t('alarms.code'), key: 'alarm_code', sortable: true },
  { title: t('alarms.level'), key: 'alarm_level', sortable: true },
  { title: t('alarms.message'), key: 'alarm_message', sortable: false },
  { title: t('alarms.occurredAt'), key: 'occurred_at', sortable: true },
  { title: t('alarms.state'), key: 'cleared_at', sortable: true },
  { title: t('alarms.acknowledged'), key: 'acknowledged', sortable: true },
  { title: t('common.actions'), key: 'actions', sortable: false },
])

// エラーログのヘッダー
const errorLogHeaders = computed(() => [
  { title: t('errorLogs.type'), key: 'error_type', sortable: true },
  { title: t('errorLogs.message'), key: 'error_message', sortable: false },
  { title: t('errorLogs.plcIp'), key: 'plc_ip', sortable: false },
  { title: t('errorLogs.protocol'), key: 'protocol', sortable: false },
  { title: t('errorLogs.retryCount'), key: 'retry_count', sortable: true },
  { title: t('errorLogs.occurredAt'), key: 'occurred_at', sortable: true },
  { title: t('errorLogs.state'), key: 'resolved_at', sortable: true },
  { title: t('common.actions'), key: 'actions', sortable: false },
])

// 設備リストを取得
const loadEquipmentList = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/equipment')
    const data = await response.json()
    equipmentList.value = data

    // デフォルトで最初の設備を選択
    if (data.length > 0 && !selectedEquipmentId.value) {
      selectedEquipmentId.value = data[0].equipment_id
      await loadData()
    }
  } catch (error) {
    console.error('設備リスト取得エラー:', error)
  }
}

// データを読み込み
const loadData = async () => {
  if (!selectedEquipmentId.value) return

  loading.value = true
  try {
    // 並列でデータ取得
    const [plcStatusRes, alarmsRes, errorLogsRes] = await Promise.all([
      fetch(`http://localhost:5000/api/equipment/${selectedEquipmentId.value}/plc_status`),
      fetch(`http://localhost:5000/api/equipment/${selectedEquipmentId.value}/alarms`),
      fetch(`http://localhost:5000/api/equipment/${selectedEquipmentId.value}/error_logs`)
    ])

    plcStatus.value = await plcStatusRes.json()
    alarms.value = await alarmsRes.json()
    errorLogs.value = await errorLogsRes.json()
  } catch (error) {
    console.error('データ読み込みエラー:', error)
  } finally {
    loading.value = false
  }
}

// アラームレベルの色
const getAlarmLevelColor = (level) => {
  const colors = {
    'WARNING': 'warning',
    'ERROR': 'error',
    'CRITICAL': 'purple'
  }
  return colors[level] || 'grey'
}

// エラー種別の色
const getErrorTypeColor = (type) => {
  const colors = {
    'CONNECTION_FAILED': 'error',
    'CONNECTION_EXCEPTION': 'error',
    'PROTOCOL_ERROR': 'warning',
    'READ_ERROR': 'orange',
    'TIMEOUT': 'warning',
    'CONFIGURATION_ERROR': 'info'
  }
  return colors[type] || 'grey'
}

// Phase 7: アラーム確認機能
const acknowledgeAlarm = async (alarmId) => {
  try {
    const response = await fetch(
      `http://localhost:5000/api/equipment/${selectedEquipmentId.value}/alarms/${alarmId}/acknowledge`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          acknowledged_by: 'Web UI User'
        })
      }
    )

    if (response.ok) {
      console.log('アラーム確認成功')
      // データを再読み込み
      await loadData()
    } else {
      console.error('アラーム確認失敗')
    }
  } catch (error) {
    console.error('アラーム確認エラー:', error)
  }
}

// Phase 7: アラーム解除機能
const clearAlarm = async (alarmId) => {
  try {
    const response = await fetch(
      `http://localhost:5000/api/equipment/${selectedEquipmentId.value}/alarms/${alarmId}/clear`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    )

    if (response.ok) {
      console.log('アラーム解除成功')
      // データを再読み込み
      await loadData()
    } else {
      console.error('アラーム解除失敗')
    }
  } catch (error) {
    console.error('アラーム解除エラー:', error)
  }
}

// Phase 7: エラーログ解決機能
const resolveErrorLog = async (errorLogId) => {
  try {
    const response = await fetch(
      `http://localhost:5000/api/equipment/${selectedEquipmentId.value}/error_logs/${errorLogId}/resolve`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    )

    if (response.ok) {
      console.log('エラーログ解決成功')
      // データを再読み込み
      await loadData()
    } else {
      console.error('エラーログ解決失敗')
    }
  } catch (error) {
    console.error('エラーログ解決エラー:', error)
  }
}

// 初回ロード
onMounted(() => {
  loadEquipmentList()
})
</script>

<style scoped>
/* カスタムスタイル */
</style>
