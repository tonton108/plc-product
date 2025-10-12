<template>
  <v-container>
    <v-row class="mb-4">
      <v-col>
        <v-card class="pa-4" color="primary" dark>
          <v-card-title class="text-h4">PLC リアルタイムモニタリング</v-card-title>
          <v-card-subtitle>設備一覧からモニタリングしたい設備を選択してください</v-card-subtitle>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="loading">
      <v-col class="text-center">
        <v-progress-circular indeterminate color="primary" size="50"></v-progress-circular>
        <p class="mt-3">設備データを読み込み中...</p>
      </v-col>
    </v-row>

    <v-row v-else-if="equipmentList.length === 0">
      <v-col class="text-center">
        <v-alert type="info">
          登録されている設備がありません。
        </v-alert>
      </v-col>
    </v-row>

    <v-row v-else>
      <v-col
        v-for="equipment in equipmentList"
        :key="equipment.id"
        cols="12" sm="6" md="4"
      >
        <v-card class="mx-auto" outlined hover>
          <v-card-title class="text-h6">
            {{ equipment.equipment_id }}
            <v-chip
              :color="getStatusColor(equipment.status)"
              text-color="white"
              size="small"
              class="ml-2"
            >
              {{ equipment.status }}
            </v-chip>
          </v-card-title>
          <v-card-subtitle>
            {{ equipment.manufacturer }} - {{ equipment.series }}
          </v-card-subtitle>
          <v-card-text>
            <div><strong>ラズパイIP:</strong> {{ equipment.ip }}</div>
            <div><strong>PLC IP:</strong> {{ equipment.plc_ip || 'N/A' }}</div>
            <div><strong>ポート:</strong> {{ equipment.port }}</div>
            <div><strong>更新間隔:</strong> {{ equipment.interval }}秒</div>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" @click="goToMonitoring(equipment.equipment_id)">
              <v-icon left>mdi-monitor-dashboard</v-icon>
              リアルタイム監視
            </v-btn>
            <v-btn color="secondary" @click="goToLogs(equipment.equipment_id)">
              <v-icon left>mdi-chart-line</v-icon>
              ログ表示
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="error" color="error" timeout="5000">
      {{ errorMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const equipmentList = ref([])
const loading = ref(true)
const error = ref(false)
const errorMessage = ref('')

const fetchEquipment = async () => {
  try {
    loading.value = true
    const response = await fetch('http://localhost:5000/api/equipment')
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    equipmentList.value = data
  } catch (err) {
    console.error('設備データ取得エラー:', err)
    errorMessage.value = '設備データの取得に失敗しました'
    error.value = true
  } finally {
    loading.value = false
  }
}

const getStatusColor = (status) => {
  switch (status) {
    case '正常':
    case '設定済み':
      return 'success'
    case '登録済み':
      return 'warning'
    case 'エラー':
      return 'error'
    default:
      return 'grey'
  }
}

const goToMonitoring = (equipmentId) => {
  router.push(`/monitoring/${equipmentId}`)
}

const goToLogs = (equipmentId) => {
  router.push(`/equipment/${equipmentId}`)
}

onMounted(() => {
  fetchEquipment()
})
</script>
  