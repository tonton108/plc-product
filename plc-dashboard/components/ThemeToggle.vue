<template>
  <v-tooltip location="bottom" content-class="tooltip-custom">
    <template #activator="{ props }">
      <v-btn
        v-bind="props"
        :icon="isDark ? 'mdi-white-balance-sunny' : 'mdi-weather-night'"
        :disabled="isTransitioning"
        variant="text"
        size="large"
        @click="toggleTheme"
      />
    </template>
    <span>{{ isDark ? 'ライトモードに切り替え' : 'ダークモードに切り替え' }}</span>
  </v-tooltip>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTheme } from 'vuetify'

const theme = useTheme()
const isDark = ref(false)
const isTransitioning = ref(false)

// ローカルストレージからテーマ設定を読み込み
onMounted(() => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    theme.global.name.value = savedTheme
    isDark.value = savedTheme === 'dark'
  } else {
    isDark.value = theme.global.name.value === 'dark'
  }
})

const toggleTheme = () => {
  // トランジション中は処理をスキップ
  if (isTransitioning.value) return

  isTransitioning.value = true
  isDark.value = !isDark.value
  const newTheme = isDark.value ? 'dark' : 'light'
  theme.global.name.value = newTheme

  // ローカルストレージに保存
  localStorage.setItem('theme', newTheme)

  // トランジション時間（400ms）後に再度クリック可能にする
  setTimeout(() => {
    isTransitioning.value = false
  }, 400)
}
</script>
