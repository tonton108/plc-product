<template>
  <v-row class="mb-6">
    <v-col cols="12">
      <v-card class="glass-card pa-6" color="accent">
        <v-row align="center">
          <v-col>
            <v-card-title class="text-h4 mb-2 d-flex align-center text-white">
              <v-icon size="x-large" class="mr-4" color="white">mdi-monitor-dashboard</v-icon>
              <span class="font-weight-bold">{{ equipmentInfo?.equipment_id || 'N/A' }}</span>
              <span class="ml-3">- {{ $t('monitoring.title') }}</span>
            </v-card-title>
            <v-card-subtitle class="text-subtitle-1 d-flex align-center mt-2 text-white" style="opacity: 1 !important;">
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
                {{ connectionStatus ? $t('monitoring.connected') : $t('monitoring.disconnected') }}
              </v-chip>
            </v-card-subtitle>
          </v-col>
          <v-col cols="auto">
            <LanguageSwitch />
            <ThemeToggle />
            <v-btn
              variant="elevated"
              color="secondary"
              size="x-large"
              class="ml-3 modern-btn"
              @click="router.push(`/equipment/${equipmentInfo?.equipment_id}`)"
            >
              <template #prepend>
                <v-icon>mdi-chart-line</v-icon>
              </template>
              {{ $t('monitoring.historyData') }}
            </v-btn>
            <v-btn variant="elevated" color="white" size="x-large" class="ml-3 modern-btn" @click="$emit('go-back')">
              <template #prepend>
                <v-icon>mdi-arrow-left</v-icon>
              </template>
              {{ $t('common.back') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { useRouter } from 'vue-router'

/**
 * モニタリング画面ヘッダーコンポーネント
 * 設備情報と接続状態を表示
 */
const router = useRouter()

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
