# よく使うコンポーネントパターン

このガイドラインは、PLC監視システムで頻繁に使用されるUIコンポーネントの標準パターンを定義します。

## ステータスカード（設備状態表示）

**構成:**
- アイコン（左上） + 状態ラベル（右上） + 数値（中央大きく） + 単位（数値の右）
- 色分け: 稼働中（グリーン）/ 停止中（グレー）/ エラー（レッド）
- タッチ可能な場合は視覚的フィードバックを明確に（ripple エフェクト）

**実装例（Vuetify）:**
```vue
<v-card :color="statusColor" class="status-card">
  <v-card-title class="d-flex justify-space-between">
    <v-icon :icon="statusIcon" size="32" />
    <v-chip :color="statusChipColor" size="small">{{ statusLabel }}</v-chip>
  </v-card-title>
  <v-card-text class="text-center">
    <div class="text-h3 font-weight-bold">{{ value }}</div>
    <div class="text-caption text-medium-emphasis">{{ unit }}</div>
  </v-card-text>
</v-card>
```

**デザイン原則:**
- カードの高さは最低 120px、幅は最低 160px（タッチ操作考慮）
- 数値は JetBrains Mono で表示
- ステータス変化時は 200ms のカラーフェード

## データテーブル（ログ・履歴）

**構成:**
- ヘッダーは固定（sticky）、ボディはスクロール可能
- ソート・フィルタは必須
- モバイルでは横スクロールではなくカード表示に切り替え

**実装例（Vuetify）:**
```vue
<v-data-table
  :headers="headers"
  :items="items"
  :items-per-page="20"
  :sort-by="[{ key: 'timestamp', order: 'desc' }]"
  :search="search"
  class="elevation-1"
  fixed-header
  height="500px"
>
  <template #top>
    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      label="検索"
      single-line
      hide-details
      class="mb-4"
    />
  </template>
</v-data-table>
```

**デザイン原則:**
- 行の高さは最低 48px（タッチ操作考慮）
- 奇数行・偶数行で背景色を微妙に変える（zebra striping）
- タイムスタンプ列は常に表示
- 長いテキストは省略（...）して、ツールチップで全文表示

## リアルタイムグラフ（Chart.js）

**構成:**
- canvas 要素のみ更新、カード全体を再描画しない
- 時系列データは左から右へ流れる
- グリッド線は控えめに（透明度 0.1 ～ 0.2）

**実装例（Nuxt + Chart.js）:**
```vue
<template>
  <v-card>
    <v-card-title>{{ title }}</v-card-title>
    <v-card-text>
      <canvas ref="chartCanvas" />
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Chart } from 'chart.js/auto'

const chartCanvas = ref(null)
let chart = null

const props = defineProps({
  data: Array,
  title: String
})

onMounted(() => {
  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: props.title,
        data: [],
        borderColor: '#14b8a6',
        backgroundColor: 'rgba(20, 184, 166, 0.1)',
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      plugins: { legend: { display: false } }
    }
  })
})

watch(() => props.data, (newData) => {
  if (chart) {
    chart.data.labels = newData.map(d => d.label)
    chart.data.datasets[0].data = newData.map(d => d.value)
    chart.update('none') // アニメーションなしで即座に更新
  }
}, { deep: true })
</script>
```

**デザイン原則:**
- チャートの高さは最低 300px
- データポイントは最新 50～100 件に制限（パフォーマンス考慮）
- しきい値ラインは破線で表示

## アラーム・エラー通知

**構成:**
- アイコン（左） + メッセージ（中央） + アクションボタン（右）
- 重要度別に色分け（エラー: レッド、警告: アンバー、情報: ブルー）
- 確認・解除ボタンで状態を更新

**実装例（Vuetify）:**
```vue
<v-alert
  :type="alertType"
  :icon="alertIcon"
  closable
  @click:close="handleClose"
>
  <template #title>{{ title }}</template>
  <template #text>{{ message }}</template>
  <template #append>
    <v-btn variant="outlined" size="small" @click="handleAction">
      {{ actionLabel }}
    </v-btn>
  </template>
</v-alert>
```

**デザイン原則:**
- 画面上部または右下に表示（toast）
- 自動消去は情報レベルのみ（エラー・警告は手動確認必須）
- 複数のアラートがある場合はスタック表示

## フォーム（設備設定・PLC設定）

**構成:**
- ラベル上 + 入力フィールド下（縦積み）
- 必須項目は赤いアスタリスク（*）で明示
- バリデーションエラーはフィールド直下に表示

**実装例（Vuetify）:**
```vue
<v-form @submit.prevent="handleSubmit">
  <v-text-field
    v-model="form.equipmentId"
    label="設備ID"
    :rules="[v => !!v || '設備IDは必須です']"
    required
    variant="outlined"
    class="mb-4"
  />
  <v-text-field
    v-model="form.plcIp"
    label="PLC IPアドレス"
    :rules="[v => !!v || 'IPアドレスは必須です', v => /^(\d{1,3}\.){3}\d{1,3}$/.test(v) || 'IPアドレスの形式が不正です']"
    required
    variant="outlined"
    class="mb-4"
  />
  <v-btn type="submit" color="primary" block>保存</v-btn>
</v-form>
```

**デザイン原則:**
- フィールド間の余白は 16px ～ 24px
- 保存ボタンはフォーム下部に固定
- ローディング中はボタンを disabled にしてスピナー表示
