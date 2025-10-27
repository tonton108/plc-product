<template>
  <v-card class="pa-6" elevation="6" color="grey-lighten-4">
    <v-card-title class="text-h5 mb-4 d-flex align-center">
      <v-icon size="large" class="mr-3" color="info">mdi-bug</v-icon>
      デバッグ情報
      <v-spacer></v-spacer>
      <v-btn @click="$emit('test-api')" size="small" color="primary" variant="elevated" class="mr-2">
        <template #prepend>
          <v-icon>mdi-api</v-icon>
        </template>
        API テスト
      </v-btn>
      <v-btn @click="$emit('clear-log')" size="small" color="warning" variant="elevated">
        <template #prepend>
          <v-icon>mdi-delete</v-icon>
        </template>
        ログクリア
      </v-btn>
    </v-card-title>
    <v-divider class="mb-4"></v-divider>

    <v-row>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <v-card-subtitle class="text-subtitle-2 font-weight-bold">WebSocket状態</v-card-subtitle>
          <div class="text-body-2">
            <div>
              接続状態:
              <v-chip size="small" :color="connectionStatus ? 'success' : 'error'">
                {{ connectionStatus ? '接続中' : '切断' }}
              </v-chip>
            </div>
            <div>Socket ID: {{ socketInfo.id || 'N/A' }}</div>
            <div>設備ID: {{ equipmentId }}</div>
            <div>データ履歴件数: {{ dataHistoryCount }}</div>
            <div>最終更新: {{ lastDataUpdate || 'なし' }}</div>
          </div>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3">
          <v-card-subtitle class="text-subtitle-2 font-weight-bold">受信イベント数</v-card-subtitle>
          <div class="text-body-2">
            <div>plc_data_update: {{ debugCounters.plc_data_update }}</div>
            <div>equipment_data_update: {{ debugCounters.equipment_data_update }}</div>
            <div>status: {{ debugCounters.status }}</div>
            <div>connect: {{ debugCounters.connect }}</div>
            <div>disconnect: {{ debugCounters.disconnect }}</div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <v-card variant="outlined" class="pa-3 mt-3">
      <v-card-subtitle class="text-subtitle-2 font-weight-bold">デバッグログ (最新20件)</v-card-subtitle>
      <div style="height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px">
        <div v-for="(log, index) in debugLogs.slice(-20)" :key="index" :class="getLogClass(log.type)">
          [{{ log.timestamp }}] {{ log.message }}
        </div>
      </div>
    </v-card>
  </v-card>
</template>

<script setup>
const props = defineProps({
  connectionStatus: {
    type: Boolean,
    required: true
  },
  socketInfo: {
    type: Object,
    required: true
  },
  equipmentId: {
    type: String,
    required: true
  },
  dataHistoryCount: {
    type: Number,
    required: true
  },
  lastDataUpdate: {
    type: String,
    default: null
  },
  debugCounters: {
    type: Object,
    required: true
  },
  debugLogs: {
    type: Array,
    required: true
  }
})

defineEmits(['test-api', 'clear-log'])

const getLogClass = (type) => {
  switch (type) {
    case 'error':
      return 'text-red'
    case 'warning':
      return 'text-orange'
    case 'success':
      return 'text-green'
    case 'info':
      return 'text-blue'
    default:
      return 'text-grey'
  }
}
</script>
