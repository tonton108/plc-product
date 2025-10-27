<template>
  <div>
    <!-- ステータスカード -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="2" v-for="(item, key) in monitoringData" :key="key" class="card-grid-item">
        <v-card :color="getCardColor(item.status)" class="status-card text-center pa-4" dark>
          <v-icon size="48" class="mb-3">{{ item.icon }}</v-icon>
          <div class="text-h3 font-weight-bold mb-2">{{ item.value || 'N/A' }}</div>
          <div class="text-h6 mb-1">{{ item.label }}</div>
          <div class="text-body-2 mb-2">{{ item.unit }}</div>
          <v-chip
            size="small"
            :color="item.status === 'normal' ? 'success' : 'error'"
            class="mt-2"
            variant="flat"
          >
            <v-icon size="x-small" class="mr-1">
              {{ item.status === 'normal' ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            {{ item.status === 'normal' ? '正常' : '異常' }}
          </v-chip>
        </v-card>
      </v-col>
    </v-row>

    <!-- アラート表示 -->
    <v-row v-if="alerts.length > 0" class="mb-4">
      <v-col cols="12">
        <v-alert
          v-for="alert in alerts"
          :key="alert.id"
          :type="alert.type"
          prominent
          border="start"
          :icon="alert.icon"
          closable
          @click:close="$emit('remove-alert', alert.id)"
        >
          <v-alert-title>{{ alert.title }}</v-alert-title>
          {{ alert.message }}
          <template v-slot:append>
            <div class="text-caption">{{ alert.timestamp }}</div>
          </template>
        </v-alert>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
/**
 * ステータスカードとアラート表示コンポーネント
 * リアルタイムデータの状態を可視化
 */
defineProps({
  monitoringData: {
    type: Object,
    default: () => ({})
  },
  alerts: {
    type: Array,
    default: () => []
  }
})

defineEmits(['remove-alert'])

/**
 * ステータスに応じたカード色を取得
 * @param {string} status - ステータス（normal, warning, error）
 * @returns {string} カラーコード
 */
const getCardColor = (status) => {
  switch (status) {
    case 'normal':
      return 'success'
    case 'warning':
      return 'warning'
    case 'error':
      return 'error'
    default:
      return 'grey'
  }
}
</script>

<style scoped>
.status-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.status-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.card-grid-item {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
