<template>
  <v-row class="mb-6">
    <v-col cols="12">
      <v-card class="glass-card-primary pa-6">
        <v-row align="center">
          <v-col>
            <v-card-title class="text-h4 mb-2 d-flex align-center">
              <v-icon size="x-large" class="mr-4">mdi-monitor-dashboard</v-icon>
              <span class="gradient-text">{{ equipmentInfo?.equipment_id || 'N/A' }}</span>
              <span class="text-white ml-3">- リアルタイムモニタリング</span>
            </v-card-title>
            <v-card-subtitle class="text-subtitle-1 d-flex align-center mt-2 text-white">
              <v-icon size="small" class="mr-2">mdi-factory</v-icon>
              {{ equipmentInfo?.manufacturer }} {{ equipmentInfo?.series }}
              <v-chip
                :color="connectionStatus ? 'success' : 'error'"
                text-color="white"
                size="small"
                class="ml-3"
                variant="elevated"
              >
                <v-icon size="small" class="mr-1">
                  {{ connectionStatus ? 'mdi-check-circle' : 'mdi-close-circle' }}
                </v-icon>
                {{ connectionStatus ? '接続中' : '切断' }}
              </v-chip>
            </v-card-subtitle>
          </v-col>
          <v-col cols="auto">
            <v-btn @click="$emit('go-back')" variant="elevated" color="white" size="x-large" class="modern-btn">
              <template v-slot:prepend>
                <v-icon>mdi-arrow-left</v-icon>
              </template>
              戻る
            </v-btn>
          </v-col>
        </v-row>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
/**
 * モニタリング画面ヘッダーコンポーネント
 * 設備情報と接続状態を表示
 */
defineProps({
  equipmentInfo: {
    type: Object,
    default: null
  },
  connectionStatus: {
    type: Boolean,
    default: false
  }
})

defineEmits(['go-back'])
</script>
