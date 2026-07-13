<template>
  <v-row class="mb-6">
    <!-- PLC通信状態カード -->
    <v-col cols="12" md="4">
      <v-card :color="plcStatus.is_online ? 'success' : 'error'" dark elevation="4">
        <v-card-text>
          <div class="text-h6">{{ $t('plcStatus.title') }}</div>
          <div class="text-h4 mt-2 d-flex align-center">
            <v-icon size="large" class="mr-2">
              {{ plcStatus.is_online ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            <span class="text-no-wrap">{{ plcStatus.is_online ? $t('plcStatus.online') : $t('plcStatus.offline') }}</span>
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <!-- 連続エラー回数カード -->
    <v-col cols="12" md="4">
      <v-card color="warning" dark elevation="4">
        <v-card-text>
          <div class="text-h6">{{ $t('plcStatus.consecutiveErrors') }}</div>
          <div class="text-h4 mt-2 text-no-wrap">
            {{ $t('plcStatus.consecutiveErrorsValue', { count: plcStatus.consecutive_errors || 0 }) }}
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <!-- 最終通信時刻カード -->
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
</template>

<script setup>
/**
 * PLC状態表示カードコンポーネント
 *
 * PLC通信状態、連続エラー回数、最終通信時刻を3列のカードで表示します。
 *
 * 使用例:
 * <PLCStatusCards :plc-status="plcStatus" />
 */

const props = defineProps({
  /**
   * PLC状態オブジェクト
   * @type {{ is_online: boolean, consecutive_errors: number, last_communication_at: string|null, last_error_type: string|null }}
   */
  plcStatus: {
    type: Object,
    required: true,
    default: () => ({
      is_online: false,
      consecutive_errors: 0,
      last_communication_at: null,
      last_error_type: null
    })
  }
})

const { formatDateTime } = useDateTime()
</script>
