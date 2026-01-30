<template>
  <v-row class="mb-6">
    <v-col cols="12">
      <v-card class="glass-card pa-6">
        <v-card-title class="text-h5 mb-4 d-flex align-center">
          <v-icon size="large" class="mr-3" color="primary">mdi-table</v-icon>
          最新データ履歴
          <v-chip size="small" color="info" class="ml-3" variant="flat">
            {{ dataHistory.length }}件
          </v-chip>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            variant="elevated"
            class="modern-btn"
            @click="$emit('export-csv')"
          >
            <template #prepend>
              <v-icon>mdi-download</v-icon>
            </template>
            CSV出力
          </v-btn>
        </v-card-title>
        <v-divider class="mb-4"></v-divider>
        <v-data-table
          :headers="tableHeaders"
          :items="dataHistory"
          density="comfortable"
          :items-per-page="15"
          class="elevation-0"
        >
          <template #[`item.timestamp`]="{ item }">
            <span class="text-body-2">{{ formatDateTime(item.timestamp) }}</span>
          </template>
          <template #[`item.error_code`]="{ item }">
            <v-chip
              size="small"
              :color="item.error_code ? 'error' : 'success'"
              text-color="white"
              variant="flat"
            >
              <v-icon size="x-small" class="mr-1">
                {{ item.error_code ? 'mdi-alert-circle' : 'mdi-check-circle' }}
              </v-icon>
              {{ item.error_code || '正常' }}
            </v-chip>
          </template>
        </v-data-table>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
/**
 * データ履歴テーブルコンポーネント
 * 最新データを表形式で表示
 *
 * Phase 3リファクタリング: useDateTime composableを使用して多言語対応
 */
defineProps({
  dataHistory: {
    type: Array,
    default: () => []
  },
  tableHeaders: {
    type: Array,
    default: () => []
  }
})

defineEmits(['export-csv'])

// useDateTime composableを使用（多言語対応）
const { formatDateTime } = useDateTime()
</script>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.modern-btn {
  text-transform: none;
  letter-spacing: normal;
}
</style>
