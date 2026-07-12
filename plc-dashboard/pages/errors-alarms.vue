<template>
  <v-container fluid>
    <!-- ヘッダー -->
    <v-row class="mb-6">
      <v-col cols="12">
        <v-card class="pa-6 glass-card" elevation="0">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h3 mb-2 font-weight-bold">
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
                @click="loadErrorsAndAlarms"
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
          @update:model-value="onEquipmentChange"
        />
      </v-col>
    </v-row>

    <div v-if="selectedEquipmentId">
      <!-- PLC状態カード（共通コンポーネント使用） -->
      <PLCStatusCards :plc-status="plcStatus" />

      <!-- アラーム履歴（共通コンポーネント使用） -->
      <v-row class="mb-6">
        <v-col cols="12">
          <AlarmHistoryTable
            :alarms="alarms"
            :loading="loading"
            @acknowledge="acknowledgeAlarm"
            @clear="clearAlarm"
          />
        </v-col>
      </v-row>

      <!-- エラーログ（共通コンポーネント使用） -->
      <v-row>
        <v-col cols="12">
          <ErrorLogTable
            :error-logs="errorLogs"
            :loading="loading"
            @resolve="resolveErrorLog"
          />
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
/**
 * エラー・アラーム管理ページ
 *
 * PLC通信エラーとアラーム履歴を一覧表示・管理します。
 * 共通コンポーネントとcomposablesを使用してコードを簡潔化しています。
 */
import { ref, onMounted } from 'vue'

const { apiFetch } = useApi()
const selectedEquipmentId = ref(null)
const equipmentList = ref([])

// useErrorsAlarms composableを使用
const {
  loading,
  plcStatus,
  alarms,
  errorLogs,
  loadErrorsAndAlarms,
  acknowledgeAlarm,
  clearAlarm,
  resolveErrorLog,
  resetData
} = useErrorsAlarms(selectedEquipmentId)

/**
 * 設備リストを取得
 */
const loadEquipmentList = async () => {
  try {
    const data = await apiFetch('/api/equipment')
    equipmentList.value = data

    // デフォルトで最初の設備を選択
    if (data.length > 0 && !selectedEquipmentId.value) {
      selectedEquipmentId.value = data[0].equipment_id
      await loadErrorsAndAlarms()
    }
  } catch (error) {
    console.error('設備リスト取得エラー:', error)
  }
}

/**
 * 設備変更時のハンドラ
 */
const onEquipmentChange = async () => {
  if (selectedEquipmentId.value) {
    await loadErrorsAndAlarms()
  } else {
    resetData()
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
