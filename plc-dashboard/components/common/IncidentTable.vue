<template>
  <v-card elevation="6">
    <v-card-title class="bg-deep-purple text-white">
      <v-icon class="mr-2">mdi-history</v-icon>
      {{ $t('incidents.title') }}
      <v-spacer></v-spacer>
      <v-chip color="white" variant="outlined" size="small">
        {{ $t('incidents.count', { count: incidents.length }) }}
      </v-chip>
    </v-card-title>
    <v-card-text>
      <v-alert
        type="info"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        {{ $t('incidents.description') }}
      </v-alert>
      <v-data-table
        :headers="headers"
        :items="incidents"
        :loading="loading"
        class="elevation-1"
        :items-per-page="itemsPerPage"
        :no-data-text="$t('incidents.noData')"
      >
        <!-- 種別（エラー / アラーム） -->
        <template v-slot:item.event_type="{ item }">
          <v-chip
            :color="item.event_type === 'error' ? 'error' : 'warning'"
            size="small"
            variant="flat"
          >
            <v-icon start size="small">
              {{ item.event_type === 'error' ? 'mdi-alert-circle' : 'mdi-bell-alert' }}
            </v-icon>
            {{ item.event_type === 'error' ? $t('incidents.typeError') : $t('incidents.typeAlarm') }}
          </v-chip>
        </template>

        <!-- 発生日時 -->
        <template v-slot:item.event_time="{ item }">
          {{ formatDateTime(item.event_time) }}
        </template>

        <!-- 発生前ログ件数 -->
        <template v-slot:item.log_count="{ item }">
          <v-chip color="primary" size="small" variant="outlined">
            {{ $t('incidents.logCountValue', { count: item.log_count }) }}
          </v-chip>
        </template>

        <!-- 発生後（アフターマス）捕捉状況 -->
        <template v-slot:item.aftermath="{ item }">
          <v-chip
            :color="aftermathColor(item)"
            size="small"
            :variant="item.after_captured ? 'flat' : 'outlined'"
          >
            <v-icon start size="small">{{ aftermathIcon(item) }}</v-icon>
            {{ aftermathLabel(item) }}
          </v-chip>
        </template>

        <!-- 操作 -->
        <template v-slot:item.actions="{ item }">
          <v-btn
            color="deep-purple"
            size="small"
            variant="elevated"
            prepend-icon="mdi-magnify"
            @click="$emit('view', item.id)"
          >
            {{ $t('incidents.viewContext') }}
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
/**
 * インシデント文脈一覧テーブルコンポーネント（SPEC §5.2）
 *
 * エラー/アラーム発生時に保全された文脈（発生前・発生後の生ログ）の一覧を表示し、
 * 詳細表示アクション（@view）を提供します。
 *
 * 使用例:
 * <IncidentTable :incidents="incidents" :loading="loading" @view="openIncidentContext" />
 */

const props = defineProps({
  /** インシデント一覧（軽量版・context_dataは含まない） */
  incidents: {
    type: Array,
    required: true,
    default: () => [],
  },
  /** ローディング状態 */
  loading: {
    type: Boolean,
    default: false,
  },
  /** 1ページあたりの表示件数 */
  itemsPerPage: {
    type: Number,
    default: 10,
  },
})

defineEmits(['view'])

const { t } = useI18n()
const { formatDateTime } = useDateTime()

const headers = computed(() => [
  { title: t('incidents.type'), key: 'event_type', align: 'start' },
  { title: t('incidents.occurredAt'), key: 'event_time', align: 'start' },
  { title: t('incidents.leadup'), key: 'log_count', align: 'center', sortable: false },
  { title: t('incidents.aftermath'), key: 'aftermath', align: 'center', sortable: false },
  { title: t('incidents.actions'), key: 'actions', align: 'center', sortable: false },
])

// 発生後（アフターマス）の捕捉状況を3状態で表す:
// - 対象外: after_window_end 未設定（移行前の既存行）
// - 捕捉済み: backfill完了（after_captured=true）
// - 待機中: backfill待ち（after_window_end設定済みだが未捕捉）
const aftermathLabel = (item) => {
  if (!item.after_window_end) return t('incidents.afterNotApplicable')
  if (item.after_captured) {
    return t('incidents.afterCaptured', { count: item.after_log_count })
  }
  return t('incidents.afterPending')
}
const aftermathColor = (item) => {
  if (!item.after_window_end) return 'grey'
  return item.after_captured ? 'success' : 'orange'
}
const aftermathIcon = (item) => {
  if (!item.after_window_end) return 'mdi-minus-circle-outline'
  return item.after_captured ? 'mdi-check-circle' : 'mdi-clock-outline'
}
</script>
