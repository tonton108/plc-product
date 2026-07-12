<template>
  <v-card elevation="6">
    <v-card-title class="bg-error text-white">
      <v-icon class="mr-2">mdi-alarm-light</v-icon>
      {{ $t('alarms.title') }}
      <v-spacer/>
      <v-chip color="white" variant="outlined" size="small">
        {{ $t('alarms.count', { count: alarms.length }) }}
      </v-chip>
    </v-card-title>
    <v-card-text>
      <v-data-table
        :headers="alarmHeaders"
        :items="alarms"
        :loading="loading"
        class="elevation-1"
        :items-per-page="itemsPerPage"
      >
        <!-- アラームレベル -->
        <template #item.alarm_level="{ item }">
          <v-chip
            :color="getAlarmLevelColor(item.alarm_level)"
            size="small"
            variant="flat"
          >
            {{ item.alarm_level }}
          </v-chip>
        </template>

        <!-- 発生日時 -->
        <template #item.occurred_at="{ item }">
          {{ formatDateTime(item.occurred_at) }}
        </template>

        <!-- 解除状態 -->
        <template #item.cleared_at="{ item }">
          <v-chip
            v-if="item.cleared_at"
            color="success"
            size="small"
            variant="outlined"
          >
            {{ $t('alarms.cleared') }}
          </v-chip>
          <v-chip
            v-else
            color="error"
            size="small"
            variant="flat"
          >
            {{ $t('alarms.notCleared') }}
          </v-chip>
        </template>

        <!-- 確認状態 -->
        <template #item.acknowledged="{ item }">
          <v-icon v-if="item.acknowledged" color="success">
            mdi-check-circle
          </v-icon>
          <v-icon v-else color="grey">
            mdi-circle-outline
          </v-icon>
        </template>

        <!-- アクションボタン -->
        <template #item.actions="{ item }">
          <v-btn
            v-if="!item.acknowledged"
            color="primary"
            size="small"
            class="mr-2"
            @click="$emit('acknowledge', item.id)"
          >
            {{ $t('alarms.acknowledge') }}
          </v-btn>
          <v-btn
            v-if="!item.cleared_at"
            color="success"
            size="small"
            @click="$emit('clear', item.id)"
          >
            {{ $t('alarms.clear') }}
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
/**
 * アラーム履歴テーブルコンポーネント
 *
 * アラーム履歴を表示し、確認・解除アクションを提供します。
 *
 * 使用例:
 * <AlarmHistoryTable
 *   :alarms="alarms"
 *   :loading="loading"
 *   @acknowledge="acknowledgeAlarm"
 *   @clear="clearAlarm"
 * />
 */

defineProps({
  /**
   * アラームリスト
   */
  alarms: {
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

defineEmits(['acknowledge', 'clear'])

const { alarmHeaders } = useTableHeaders()
const { getAlarmLevelColor } = useColorMapping()
const { formatDateTime } = useDateTime()
</script>
