<template>
  <v-app>
    <v-app-bar color="primary" dark>
      <v-app-bar-title>PLC Monitoring System</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-chip color="success" size="small" class="mr-2">
        <v-icon left size="small">mdi-server</v-icon>
        サーバー稼働中
      </v-chip>
    </v-app-bar>

    <v-main>
      <router-view></router-view>
    </v-main>
  </v-app>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const serverStatus = ref('checking')

onMounted(async () => {
  // Flask backendの状態をチェック
  if (window.electronAPI) {
    try {
      const status = await window.electronAPI.checkFlaskStatus()
      serverStatus.value = status.running ? 'running' : 'stopped'
      console.log('Flask Server Status:', status)
    } catch (error) {
      console.error('Failed to check Flask status:', error)
      serverStatus.value = 'error'
    }
  }
})
</script>

<style scoped>
/* グローバルスタイル */
</style>
