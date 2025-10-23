<template>
  <v-tooltip :text="isDark ? 'ライトモードに切り替え' : 'ダークモードに切り替え'" location="bottom">
    <template #activator="{ props }">
      <v-btn
        v-bind="props"
        :icon="isDark ? 'mdi-white-balance-sunny' : 'mdi-weather-night'"
        @click="toggleTheme"
        variant="text"
        size="large"
      ></v-btn>
    </template>
  </v-tooltip>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTheme } from 'vuetify'

const theme = useTheme()
const isDark = ref(false)

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
  isDark.value = !isDark.value
  const newTheme = isDark.value ? 'dark' : 'light'
  theme.global.name.value = newTheme

  // ローカルストレージに保存
  localStorage.setItem('theme', newTheme)
}
</script>
