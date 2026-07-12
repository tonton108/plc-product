<template>
  <v-card elevation="6">
    <v-card-title class="bg-warning text-white">
      <v-icon class="mr-2">mdi-alert</v-icon>
      {{ $t('errorLogs.title') }}
      <v-spacer/>
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
        :items-per-page="itemsPerPage"
      >
        <!-- エラー種別 -->
        <template #item.error_type="{ item }">
          <v-chip
            :color="getErrorTypeColor(item.error_type)"
            size="small"
            variant="flat"
          >
            {{ item.error_type }}
          </v-chip>
        </template>

        <!-- 発生日時 -->
        <template #item.occurred_at="{ item }">
          {{ formatDateTime(item.occurred_at) }}
        </template>

        <!-- 解決状態 -->
        <template #item.resolved_at="{ item }">
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

        <!-- リトライ回数 -->
        <template #item.retry_count="{ item }">
          {{ item.retry_count || 0 }}
        </template>

        <!-- アクションボタン -->
        <template #item.actions="{ item }">
          <v-btn
            v-if="!item.resolved_at"
            color="success"
            size="small"
            @click="$emit('resolve', item.id)"
          >
            {{ $t('errorLogs.resolve') }}
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
/**
 * エラーログテーブルコンポーネント
 *
 * エラーログを表示し、解決アクションを提供します。
 *
 * 使用例:
 * <ErrorLogTable
 *   :error-logs="errorLogs"
 *   :loading="loading"
 *   @resolve="resolveErrorLog"
 * />
 */

defineProps({
  /**
   * エラーログリスト
   */
  errorLogs: {
    type: Array,
    required: true,
    default: () => []
  },
  /**
   * ローディング状態
   */
  loading: {
    type: Boolean,
    default: false
  },
  /**
   * 1ページあたりの表示件数
   */
  itemsPerPage: {
    type: Number,
    default: 10
  }
})

defineEmits(['resolve'])

const { errorLogHeaders } = useTableHeaders()
const { getErrorTypeColor } = useColorMapping()
const { formatDateTime } = useDateTime()
</script>
