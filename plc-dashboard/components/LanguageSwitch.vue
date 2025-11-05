<template>
  <v-menu>
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        color="white"
        size="large"
        class="modern-btn"
      >
        <v-icon>mdi-web</v-icon>
        <span class="ml-2">{{ currentLocaleName }}</span>
        <v-icon class="ml-1">mdi-chevron-down</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item
        v-for="locale in availableLocales"
        :key="locale.code"
        @click="switchLocale(locale.code)"
        :active="locale.code === currentLocale"
      >
        <v-list-item-title>{{ locale.name }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup>
import { computed } from 'vue'

const { locale, locales, setLocale } = useI18n()

const currentLocale = computed(() => locale.value)

const availableLocales = computed(() => {
  return locales.value
})

const currentLocaleName = computed(() => {
  const current = locales.value.find(l => l.code === locale.value)
  return current ? current.name : ''
})

const switchLocale = async (code) => {
  await setLocale(code)
  if (process.client) {
    localStorage.setItem('preferred_locale', code)
  }
}
</script>

