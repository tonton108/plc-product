<template>
  <v-dialog
    :model-value="modelValue"
    max-width="1100"
    scrollable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="bg-deep-purple text-white d-flex align-center">
        <v-icon class="mr-2">mdi-clipboard-text-search</v-icon>
        {{ $t('incidents.dialogTitle') }}
        <v-spacer></v-spacer>
        <v-btn
          icon="mdi-close"
          variant="text"
          size="small"
          :aria-label="$t('common.close')"
          @click="$emit('update:modelValue', false)"
        ></v-btn>
      </v-card-title>

      <v-card-text style="max-height: 75vh;">
        <!-- 読み込み中 -->
        <div v-if="loading" class="text-center py-12">
          <v-progress-circular indeterminate color="deep-purple" size="48" />
        </div>

        <!-- 取得失敗 -->
        <v-alert v-else-if="!context" type="error" variant="tonal" class="my-4">
          {{ $t('incidents.loadFailed') }}
        </v-alert>

        <template v-else>
          <!-- メタ情報 -->
          <v-list density="compact" class="mb-2 bg-transparent">
            <v-list-item class="px-0">
              <template #prepend>
                <v-icon :color="context.event_type === 'error' ? 'error' : 'warning'" class="mr-2">
                  {{ context.event_type === 'error' ? 'mdi-alert-circle' : 'mdi-bell-alert' }}
                </v-icon>
              </template>
              <v-list-item-title>
                <strong>{{ $t('incidents.type') }}:</strong>
                {{ context.event_type === 'error' ? $t('incidents.typeError') : $t('incidents.typeAlarm') }}
                <span class="ml-4"><strong>{{ $t('incidents.occurredAt') }}:</strong> {{ formatDateTime(context.event_time) }}</span>
              </v-list-item-title>
            </v-list-item>
          </v-list>

          <!-- 発生前（リードアップ） -->
          <div class="text-subtitle-1 font-weight-bold mt-4 mb-1">
            <v-icon color="primary" size="small" class="mr-1">mdi-ray-start-arrow</v-icon>
            {{ $t('incidents.leadupSection') }}
            <span class="text-caption text-medium-emphasis ml-2">
              {{ formatDateTime(context.window_start) }} 〜 {{ formatDateTime(context.window_end) }}
            </span>
          </div>
          <v-data-table
            :headers="leadupHeaders"
            :items="context.context_data || []"
            density="compact"
            :items-per-page="10"
            class="elevation-1 mb-4"
            :no-data-text="$t('incidents.noLogsInWindow')"
          >
            <template v-slot:item.timestamp="{ item }">
              {{ formatDateTime(item.timestamp) }}
            </template>
          </v-data-table>

          <!-- 発生後（アフターマス） -->
          <div class="text-subtitle-1 font-weight-bold mt-4 mb-1">
            <v-icon color="deep-purple" size="small" class="mr-1">mdi-ray-end-arrow</v-icon>
            {{ $t('incidents.aftermathSection') }}
            <span v-if="context.after_window_end" class="text-caption text-medium-emphasis ml-2">
              {{ formatDateTime(context.event_time) }} 〜 {{ formatDateTime(context.after_window_end) }}
            </span>
          </div>
          <!-- 対象外（移行前の既存行） -->
          <v-alert
            v-if="!context.after_window_end"
            type="info"
            variant="tonal"
            density="compact"
          >
            {{ $t('incidents.afterNotApplicableHint') }}
          </v-alert>
          <!-- 未捕捉（backfill待ち） -->
          <v-alert
            v-else-if="!context.after_captured"
            type="warning"
            variant="tonal"
            density="compact"
          >
            {{ $t('incidents.afterPendingHint') }}
          </v-alert>
          <!-- 捕捉済み -->
          <v-data-table
            v-else
            :headers="aftermathHeaders"
            :items="context.after_context_data || []"
            density="compact"
            :items-per-page="10"
            class="elevation-1"
            :no-data-text="$t('incidents.noLogsInWindow')"
          >
            <template v-slot:item.timestamp="{ item }">
              {{ formatDateTime(item.timestamp) }}
            </template>
          </v-data-table>
        </template>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="$emit('update:modelValue', false)">
          {{ $t('common.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
/**
 * インシデント文脈 詳細ダイアログ（SPEC §5.2）
 *
 * 発生前（リードアップ）・発生後（アフターマス）の生ログスナップショットを
 * 動的カラムのテーブルで表示する。生ログ本体が消えた後もここで再現できる。
 *
 * 使用例:
 * <IncidentContextDialog
 *   v-model="contextDialog"
 *   :context="selectedContext"
 *   :loading="contextLoading"
 * />
 */

const props = defineProps({
  /** ダイアログ開閉（v-model） */
  modelValue: {
    type: Boolean,
    default: false,
  },
  /** インシデント文脈（context_data / after_context_data を含む詳細） */
  context: {
    type: Object,
    default: null,
  },
  /** 詳細取得中フラグ */
  loading: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['update:modelValue'])

const { formatDateTime } = useDateTime()

// 生ログ配列からカラムを動的生成する。timestampを先頭に固定し、
// 残りのキーは出現順で並べる（設備ごとにデータ項目が異なるため）。
const buildHeaders = (rows) => {
  const seen = new Set()
  const keys = []
  for (const row of rows || []) {
    for (const k of Object.keys(row)) {
      if (k !== 'timestamp' && !seen.has(k)) {
        seen.add(k)
        keys.push(k)
      }
    }
  }
  return [
    { title: 'timestamp', key: 'timestamp', align: 'start' },
    ...keys.map((k) => ({ title: k, key: k, align: 'end' })),
  ]
}

const leadupHeaders = computed(() => buildHeaders(props.context?.context_data))
const aftermathHeaders = computed(() => buildHeaders(props.context?.after_context_data))
</script>
