<template>
  <div>
    <!-- ステータスカード -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="2" v-for="(item, key) in monitoringData" :key="key" class="card-grid-item">
        <v-card :color="getCardColor(item.status)" class="status-card text-center pa-4" dark>
          <v-icon size="48" class="mb-3">{{ item.icon }}</v-icon>
          <div
            class="text-h3 font-weight-bold mb-2"
            :class="getValueAnimationClass(key)"
            :key="`value-${key}-${item.value}`"
          >
            {{ item.value || 'N/A' }}
          </div>
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
import { ref, watch } from 'vue'

/**
 * ステータスカードとアラート表示コンポーネント
 * リアルタイムデータの状態を可視化（数値変化時のアニメーション付き）
 */
const props = defineProps({
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

// 前回の値を保持（数値変化の検知用）
const previousValues = ref({})

// 数値変化のアニメーションクラスを管理
const animationClasses = ref({})

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

/**
 * 数値変化時のアニメーションクラスを取得
 * @param {string} key - データキー
 * @returns {string} アニメーションクラス
 */
const getValueAnimationClass = (key) => {
  return animationClasses.value[key] || ''
}

/**
 * monitoringDataの変化を監視してアニメーションを適用
 */
watch(
  () => props.monitoringData,
  (newData) => {
    Object.keys(newData).forEach((key) => {
      const newValue = newData[key]?.value
      const oldValue = previousValues.value[key]

      // 数値が変化した場合のみアニメーションを適用
      if (oldValue !== undefined && newValue !== oldValue && newValue !== null && newValue !== 'N/A') {
        // 数値型に変換して比較
        const newNum = parseFloat(newValue)
        const oldNum = parseFloat(oldValue)

        if (!isNaN(newNum) && !isNaN(oldNum)) {
          if (newNum > oldNum) {
            // 数値増加時
            animationClasses.value[key] = 'value-pulse value-increase'
          } else if (newNum < oldNum) {
            // 数値減少時
            animationClasses.value[key] = 'value-pulse value-decrease'
          } else {
            // 変化なし
            animationClasses.value[key] = 'value-pulse'
          }

          // 200ms後にアニメーションクラスをクリア（ガイドライン準拠のアニメーション時間）
          setTimeout(() => {
            animationClasses.value[key] = ''
          }, 200)
        } else {
          // 数値でない場合は通常のパルスのみ
          animationClasses.value[key] = 'value-pulse'
          setTimeout(() => {
            animationClasses.value[key] = ''
          }, 200)
        }
      }

      // 前回の値を更新
      previousValues.value[key] = newValue
    })
  },
  { deep: true }
)
</script>

<style scoped>
/* ステータスカード（ガイドライン準拠） */
.status-card {
  transition: all 0.2s ease-out; /* 200ms、ease-out */
  min-height: 120px; /* タッチ操作考慮 */
  min-width: 160px; /* タッチ操作考慮 */
}

.status-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

/* 数値表示はJetBrains Mono */
.text-h3 {
  font-family: 'JetBrains Mono', 'Courier New', monospace !important;
  font-variant-numeric: tabular-nums; /* 等幅数字 */
}

.card-grid-item {
  animation: fadeIn 0.2s ease-out; /* 200ms */
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

/* アクセシビリティ対応 */
@media (prefers-reduced-motion: reduce) {
  .status-card,
  .card-grid-item {
    animation: none !important;
    transition: none !important;
  }
}
</style>
