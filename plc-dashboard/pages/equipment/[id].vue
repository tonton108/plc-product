<template>
  <v-container>
    <!-- ヘッダーボタン群 -->
    <div class="d-flex align-center mb-6">
      <v-btn
        color="primary"
        variant="elevated"
        size="large"
        @click="goBack"
      >
        <template v-slot:prepend>
          <v-icon>mdi-arrow-left</v-icon>
        </template>
        {{ $t('common.back') }}
      </v-btn>
      <v-spacer></v-spacer>
      <v-btn
        color="success"
        variant="elevated"
        size="large"
        class="mr-3"
        @click="$router.push(`/monitoring/${$route.params.id}`)"
      >
        <template v-slot:prepend>
          <v-icon>mdi-monitor-dashboard</v-icon>
        </template>
        {{ $t('monitoring.realtimeMonitoring') }}
      </v-btn>
      <LanguageSwitch />
      <ThemeToggle />
    </div>

    <v-card class="pa-6 glass-card" elevation="0">
      <v-card-title class="text-h4 mb-4 d-flex align-center font-weight-bold">
        <v-icon size="large" class="mr-3" color="primary">mdi-chart-box-outline</v-icon>
        {{ $t('equipmentDetail.logGraph', { name: equipment?.name || '', manufacturer: equipment?.manufacturer || '' }) }}
      </v-card-title>
      <v-divider class="mb-6"></v-divider>

      <!-- 期間選択（7d/30dは日次集計ビュー） -->
      <v-btn-toggle
        v-model="selectedPeriod"
        color="primary"
        mandatory
        density="comfortable"
        class="mb-4"
        data-testid="period-toggle"
      >
        <v-btn value="1h">1時間</v-btn>
        <v-btn value="6h">6時間</v-btn>
        <v-btn value="24h">24時間</v-btn>
        <v-btn value="7d">7日</v-btn>
        <v-btn value="30d">30日</v-btn>
      </v-btn-toggle>

      <v-tabs v-model="tab" color="primary" class="mb-4" height="60">
        <v-tab value="0" class="text-h6">
          <v-icon class="mr-2">mdi-chart-line</v-icon>
          {{ $t('equipmentDetail.tabs.graph') }}
        </v-tab>
        <v-tab value="1" class="text-h6">
          <v-icon class="mr-2">mdi-table</v-icon>
          {{ $t('equipmentDetail.tabs.table') }}
        </v-tab>
        <v-tab value="2" class="text-h6">
          <v-icon class="mr-2">mdi-alert-circle</v-icon>
          {{ $t('equipmentDetail.tabs.errorsAlarms') }}
        </v-tab>
        <v-tab value="3" class="text-h6">
          <v-icon class="mr-2">mdi-cog</v-icon>
          {{ $t('plcConfigEdit.tab') }}
        </v-tab>
      </v-tabs>

      <v-card-text class="pa-6">
        <v-window v-model="tab">
          <!-- グラフタブ -->
          <v-window-item value="0">
            <v-card variant="outlined" class="pa-4">
              <div style="height: 500px">
                <div v-if="filteredLogs.length === 0" class="d-flex align-center justify-center" style="height: 100%;">
                  <div class="text-center">
                    <v-icon size="80" color="grey-lighten-1">mdi-chart-line-variant</v-icon>
                    <div class="text-h6 text-grey mt-4">{{ $t('common.noData') }}</div>
                  </div>
                </div>
                <Chart
                  v-else
                  :data="chartData"
                  :options="chartOptions"
                  type="line"
                />
              </div>
            </v-card>
          </v-window-item>

          <!-- テーブルタブ -->
          <v-window-item value="1">
            <v-card variant="outlined">
              <v-data-table
                :headers="headers"
                :items="filteredLogs"
                density="comfortable"
                :items-per-page="15"
                class="elevation-0"
              />
            </v-card>
          </v-window-item>

          <!-- エラー・アラームタブ（共通コンポーネント使用） -->
          <v-window-item value="2">
            <!-- PLC状態カード -->
            <PLCStatusCards :plc-status="plcStatus" />

            <!-- アラーム履歴 -->
            <v-row class="mb-6">
              <v-col cols="12">
                <AlarmHistoryTable
                  :alarms="alarms"
                  :loading="loadingErrors"
                  @acknowledge="acknowledgeAlarm"
                  @clear="clearAlarm"
                />
              </v-col>
            </v-row>

            <!-- エラーログ -->
            <v-row>
              <v-col cols="12">
                <ErrorLogTable
                  :error-logs="errorLogs"
                  :loading="loadingErrors"
                  @resolve="resolveErrorLog"
                />
              </v-col>
            </v-row>
          </v-window-item>

          <!-- PLC設定タブ（データ項目のCRUD編集） -->
          <v-window-item value="3">
            <v-alert
              v-if="!isAdmin"
              type="info"
              variant="tonal"
              density="comfortable"
              class="mb-4"
            >
              {{ $t('plcConfigEdit.readOnlyNotice') }}
            </v-alert>

            <div class="d-flex align-center mb-4">
              <div class="text-h6">{{ $t('plcConfigEdit.title') }}</div>
              <v-spacer></v-spacer>
              <v-btn
                v-if="isAdmin"
                color="primary"
                variant="tonal"
                prepend-icon="mdi-plus"
                data-testid="add-plc-config"
                @click="openAddConfig"
              >
                {{ $t('plcConfigEdit.addItem') }}
              </v-btn>
            </div>

            <v-card variant="outlined">
              <v-table density="comfortable" data-testid="plc-config-table">
                <thead>
                  <tr>
                    <th>{{ $t('plcConfigEdit.fields.enabled') }}</th>
                    <th>{{ $t('plcConfigEdit.fields.name') }}</th>
                    <th>{{ $t('plcConfigEdit.fields.dataType') }}</th>
                    <th>{{ $t('plcConfigEdit.fields.address') }}</th>
                    <th>{{ $t('plcConfigEdit.fields.plcDataType') }}</th>
                    <th>{{ $t('plcConfigEdit.fields.wordOrder') }}</th>
                    <th class="text-right">{{ $t('plcConfigEdit.fields.scaleFactor') }}</th>
                    <th>{{ $t('plcConfigEdit.fields.unit') }}</th>
                    <th v-if="isAdmin" class="text-right">{{ $t('plcConfigEdit.fields.actions') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="editConfigs.length === 0">
                    <td :colspan="isAdmin ? 9 : 8" class="text-center text-grey py-6">
                      {{ $t('plcConfigEdit.empty') }}
                    </td>
                  </tr>
                  <tr v-for="(cfg, i) in editConfigs" :key="i">
                    <td>
                      <v-icon :color="cfg.enabled ? 'success' : 'grey'">
                        {{ cfg.enabled ? 'mdi-check-circle' : 'mdi-circle-outline' }}
                      </v-icon>
                    </td>
                    <td>{{ cfg.icon }} {{ cfg.name }}</td>
                    <td><code>{{ cfg.data_type }}</code></td>
                    <td>{{ cfg.address }}</td>
                    <td>{{ cfg.plc_data_type }}</td>
                    <td>{{ is32bit(cfg.plc_data_type) ? cfg.word_order : '—' }}</td>
                    <td class="text-right">{{ cfg.scale_factor }}</td>
                    <td>{{ cfg.unit }}</td>
                    <td v-if="isAdmin" class="text-right">
                      <v-btn
                        icon="mdi-pencil"
                        size="small"
                        variant="text"
                        :aria-label="$t('plcConfigEdit.editItem')"
                        @click="openEditConfig(i)"
                      ></v-btn>
                      <v-btn
                        icon="mdi-delete"
                        size="small"
                        variant="text"
                        color="error"
                        :aria-label="$t('plcConfigEdit.deleteItem')"
                        @click="removeConfig(i)"
                      ></v-btn>
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </v-card>

            <v-btn
              v-if="isAdmin"
              class="mt-6"
              color="success"
              variant="elevated"
              size="large"
              :loading="savingConfigs"
              prepend-icon="mdi-content-save"
              data-testid="save-plc-config"
              @click="savePLCConfigs"
            >
              {{ $t('plcConfigEdit.save') }}
            </v-btn>
          </v-window-item>
        </v-window>

        <v-btn
          v-if="tab !== '3'"
          class="mt-6"
          color="primary"
          variant="elevated"
          size="large"
          @click="downloadCSV"
        >
          <template v-slot:prepend>
            <v-icon>mdi-download</v-icon>
          </template>
          {{ $t('equipmentDetail.csvDownload') }}
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- PLCデータ項目 追加/編集ダイアログ -->
    <v-dialog v-model="configDialog" max-width="620" persistent>
      <v-card>
        <v-card-title class="text-h6">
          {{ editingIndex === null ? $t('plcConfigEdit.addItem') : $t('plcConfigEdit.editItem') }}
        </v-card-title>
        <v-card-text>
          <v-form ref="configForm">
            <v-text-field
              v-model="configDraft.name"
              :label="$t('plcConfigEdit.fields.name')"
              maxlength="100"
              variant="outlined"
              density="comfortable"
            ></v-text-field>
            <v-text-field
              v-model="configDraft.data_type"
              :label="$t('plcConfigEdit.fields.dataType')"
              :hint="$t('plcConfigEdit.hints.dataType')"
              persistent-hint
              maxlength="50"
              :rules="[rules.required, rules.dataType]"
              variant="outlined"
              density="comfortable"
              class="mb-2"
            ></v-text-field>
            <v-text-field
              v-model="configDraft.address"
              :label="$t('plcConfigEdit.fields.address')"
              :hint="$t('plcConfigEdit.hints.address')"
              persistent-hint
              maxlength="20"
              :rules="configDraft.enabled ? [rules.required] : []"
              variant="outlined"
              density="comfortable"
              class="mb-2"
            ></v-text-field>
            <v-select
              v-model="configDraft.plc_data_type"
              :items="plcDataTypeOptions"
              :label="$t('plcConfigEdit.fields.plcDataType')"
              variant="outlined"
              density="comfortable"
            ></v-select>
            <v-select
              v-if="is32bit(configDraft.plc_data_type)"
              v-model="configDraft.word_order"
              :items="wordOrderOptions"
              :label="$t('plcConfigEdit.fields.wordOrder')"
              :hint="$t('plcConfigEdit.hints.wordOrder')"
              persistent-hint
              variant="outlined"
              density="comfortable"
              class="mb-2"
            ></v-select>
            <v-text-field
              v-model.number="configDraft.scale_factor"
              type="number"
              :label="$t('plcConfigEdit.fields.scaleFactor')"
              :rules="[rules.number]"
              variant="outlined"
              density="comfortable"
            ></v-text-field>
            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model="configDraft.unit"
                  :label="$t('plcConfigEdit.fields.unit')"
                  maxlength="20"
                  variant="outlined"
                  density="comfortable"
                ></v-text-field>
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model="configDraft.icon"
                  :label="$t('plcConfigEdit.fields.icon')"
                  maxlength="10"
                  variant="outlined"
                  density="comfortable"
                ></v-text-field>
              </v-col>
            </v-row>
            <v-switch
              v-model="configDraft.enabled"
              :label="$t('plcConfigEdit.fields.enabled')"
              color="success"
              density="comfortable"
              hide-details
            ></v-switch>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="configDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" variant="elevated" @click="applyConfigDraft">{{ $t('common.ok') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
/**
 * 設備詳細ページ
 *
 * ログ履歴のグラフ・テーブル表示、エラー・アラーム管理機能を提供します。
 * Phase 3リファクタリング: 共通コンポーネントとcomposablesを使用。
 */
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
} from 'chart.js'
import { Chart } from 'vue-chartjs'
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement
)

const route = useRoute()
const router = useRouter()
const { apiFetch } = useApi()
const { isAdmin } = useAuth()
const equipmentId = route.params.id
const toast = useToast()
const { t } = useI18n()
const { formatDateTime } = useDateTime()
const { getChartColor } = useColorMapping()

// useErrorsAlarms composableを使用（エラー・アラームタブ用）
const {
  loading: loadingErrors,
  plcStatus,
  alarms,
  errorLogs,
  loadErrorsAndAlarms,
  acknowledgeAlarm,
  clearAlarm,
  resolveErrorLog
} = useErrorsAlarms(equipmentId)

// 戻るボタンのハンドラー
const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

const tab = ref(0)
const chartData = ref(null)
const chartOptions = ref({})
const logsRaw = ref([])
// 履歴データの種別: 'raw_logs'（生ログ・1h/6h/24h）or 'daily_summaries'（日次集計・7d/30d）。
// 日次集計は値が <項目名>_avg 等の集計キーになるため、参照キーを切り替える。
const dataSource = ref('raw_logs')
const selectedPeriod = ref('24h')
const equipment = ref(null)

// PLC設定情報（動的生成用）
const plcConfigs = ref([])
const headers = ref([
  { title: t('equipmentDetail.timestamp'), value: 'timestamp' }
])

// 設備情報を取得
const fetchEquipmentInfo = async () => {
  try {
    equipment.value = await apiFetch(`/api/equipment/${equipmentId}`)
  } catch (error) {
    console.error('設備情報取得エラー:', error)
  }
}

// PLC設定を取得
const fetchPLCConfigs = async () => {
  try {
    plcConfigs.value = await apiFetch(`/api/equipment/${equipmentId}/plc_configs`)
    console.log('📋 PLC設定取得成功:', plcConfigs.value)
    initializeDynamicHeaders()
    syncEditConfigs()
  } catch (error) {
    console.error('PLC設定取得エラー:', error)
  }
}

// --- PLCデータ項目 編集UI（Issue #14に続くIssue #15対応） ---
// 編集はローカルコピー(editConfigs)に対して行い、保存時にPUTで全件置換する
// （APIが配列を受け取り既存設定を全削除→再作成する仕様のため）。
const editConfigs = ref([])
const configDialog = ref(false)
const editingIndex = ref(null)   // null=新規追加, 数値=既存行の編集
const configForm = ref(null)
const savingConfigs = ref(false)

// PLCデータ型の選択肢（bit/word=16bit/dword・float32=32bit）
const plcDataTypeOptions = [
  { title: 'bit', value: 'bit' },
  { title: 'word (16bit)', value: 'word' },
  { title: 'dword (32bit)', value: 'dword' },
  { title: 'float32 (32bit)', value: 'float32' },
]
// ワード順序の選択肢（32bit値のみ有効）。既定はlow_first（三菱MELSEC想定）。
const wordOrderOptions = computed(() => [
  { title: t('plcConfigEdit.wordOrder.lowFirst'), value: 'low_first' },
  { title: t('plcConfigEdit.wordOrder.highFirst'), value: 'high_first' },
])

// 32bit値（word_orderが意味を持つ型）か判定
const is32bit = (dataType) => dataType === 'dword' || dataType === 'float32'

// 入力バリデーション（バックエンドvalidate_plc_configと整合）
const rules = {
  required: (v) => (v !== null && v !== undefined && String(v).trim() !== '') || t('plcConfigEdit.rules.required'),
  // data_type: 英数字・アンダースコア・ハイフンのみ1〜50文字（validators.py:173と同一）
  dataType: (v) => /^[A-Za-z0-9_-]{1,50}$/.test(v || '') || t('plcConfigEdit.rules.dataType'),
  number: (v) => !isNaN(parseFloat(v)) || t('plcConfigEdit.rules.number'),
}

// 新規項目の初期値（DB既定に合わせる）
const defaultDraft = () => ({
  name: '', data_type: '', icon: '', unit: '',
  address: '', scale_factor: 1, plc_data_type: 'word',
  word_order: 'low_first', enabled: true,
})
const configDraft = ref(defaultDraft())

// 取得済みplcConfigsを編集用ローカルコピーに反映（保存/再取得のたびに同期）
const syncEditConfigs = () => {
  editConfigs.value = plcConfigs.value.map((c) => ({ ...c }))
}

const openAddConfig = () => {
  editingIndex.value = null
  configDraft.value = defaultDraft()
  configDialog.value = true
}

const openEditConfig = (i) => {
  editingIndex.value = i
  configDraft.value = { ...editConfigs.value[i] }
  configDialog.value = true
}

// ダイアログのOK: バリデーション後にローカルコピーへ反映（この時点では未保存）
const applyConfigDraft = async () => {
  const result = await configForm.value?.validate()
  if (result && result.valid === false) return

  // 内部キー(data_type)の重複を防止（重複すると動的ヘッダ/CSVの列キーが衝突する。
  // バックエンドに重複検知がないためクライアント側で弾く）。編集中の行自身は除外。
  const key = (configDraft.value.data_type || '').trim()
  const dup = editConfigs.value.some((c, idx) => idx !== editingIndex.value && c.data_type === key)
  if (dup) {
    toast.error(t('plcConfigEdit.rules.duplicate', { key }))
    return
  }

  // scale_factorは数値化。NaNのときのみ既定1（0や負値はそのまま保持）
  const sf = Number(configDraft.value.scale_factor)
  const draft = {
    ...configDraft.value,
    // 項目名が空ならバックエンド同様に内部キーで補完（表示の即時整合）
    name: (configDraft.value.name || '').trim() || key,
    scale_factor: Number.isFinite(sf) ? sf : 1,
  }
  if (editingIndex.value === null) {
    editConfigs.value.push(draft)
  } else {
    editConfigs.value[editingIndex.value] = draft
  }
  configDialog.value = false
}

const removeConfig = (i) => {
  editConfigs.value.splice(i, 1)
}

// 保存: 編集後の全項目をPUTで送信（サーバ側で全件置換）
const savePLCConfigs = async () => {
  savingConfigs.value = true
  try {
    await apiFetch(`/api/equipment/${equipmentId}/plc_configs`, {
      method: 'PUT',
      body: editConfigs.value,
    })
    toast.success(t('plcConfigEdit.saved'))
    // 再取得して動的ヘッダ/チャート/編集コピーを最新化
    await fetchPLCConfigs()
    await fetchLogs()
  } catch (error) {
    console.error('PLC設定保存エラー:', error)
    const status = error?.response?.status || error?.status
    // 400: バックエンドの検証エラー詳細（例「Config 0: Invalid data_type」）を表示
    // 403: 非管理者、それ以外は汎用エラー
    const detail = error?.data?.error || error?.response?._data?.error
    if (status === 403) {
      toast.error(t('plcConfigEdit.forbidden'))
    } else if (status === 400 && detail) {
      toast.error(detail)
    } else {
      toast.error(t('plcConfigEdit.saveError'))
    }
  } finally {
    savingConfigs.value = false
  }
}

// 動的テーブルヘッダーを初期化
const initializeDynamicHeaders = () => {
  const newHeaders = [{ title: t('equipmentDetail.timestamp'), value: 'timestamp' }]
  plcConfigs.value.forEach(config => {
    if (config.enabled) {
      newHeaders.push({
        title: `${config.name}${config.unit ? '(' + config.unit + ')' : ''}`,
        value: config.data_type,
        align: 'center'
      })
    }
  })
  headers.value = newHeaders
  console.log('✅ 動的ヘッダー生成完了:', headers.value)
}

const filteredLogs = computed(() => {
  // 日次集計（7d/30d）はAPI側で期間フィルタ済み。かつtimestampを持たない
  // （dateキー）ため、クライアント側の時間フィルタは行わずそのまま使う。
  if (dataSource.value === 'daily_summaries') {
    return logsRaw.value
  }
  const now = new Date()
  const rangeMs = {
    '1h': 60 * 60 * 1000,
    '6h': 6 * 60 * 60 * 1000,
    '24h': 24 * 60 * 60 * 1000,
  }[selectedPeriod.value]
  return logsRaw.value.filter(log => now - new Date(log.timestamp) <= rangeMs)
})

// 履歴データ種別に応じて、1つのログ/集計から config の値を取り出す。
// 生ログは素のキー（例 temp_a）、日次集計は平均キー（例 temp_a_avg）を参照する。
const logValue = (log, config) => {
  if (dataSource.value === 'daily_summaries') {
    return log[`${config.data_type}_avg`] ?? null
  }
  return log[config.data_type] ?? null
}

// 動的チャートデータ生成
const updateChart = () => {
  const isDaily = dataSource.value === 'daily_summaries'
  const labels = filteredLogs.value.map(log =>
    isDaily
      ? log.date
      : formatDateTime(log.timestamp, {
          month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
        })
  )

  const datasets = []
  plcConfigs.value.forEach((config, index) => {
    if (config.enabled) {
      const suffix = isDaily ? ' (avg)' : ''
      datasets.push({
        label: `${config.name}${suffix}${config.unit ? '(' + config.unit + ')' : ''}`,
        data: filteredLogs.value.map(log => logValue(log, config)),
        borderColor: getChartColor(index),
        backgroundColor: 'transparent',
        tension: 0.2,
        pointRadius: 3,
        pointHoverRadius: 5
      })
    }
  })

  chartData.value = {
    labels,
    datasets
  }
}

// 動的CSVダウンロード
const downloadCSV = () => {
  try {
    if (logsRaw.value.length === 0) {
      toast.warning(t('equipmentDetail.noExportData'))
      return
    }

    // ヘッダー行を動的生成
    const headerFields = ['timestamp']
    plcConfigs.value.forEach(config => {
      if (config.enabled) {
        headerFields.push(config.data_type)
      }
    })
    const header = headerFields.join(',') + '\n'

    // データ行を動的生成
    const isDaily = dataSource.value === 'daily_summaries'
    const rows = logsRaw.value.map(log => {
      // 生ログはtimestamp、日次集計はdateを1列目に出す
      const values = [isDaily ? log.date : log.timestamp]
      plcConfigs.value.forEach(config => {
        if (config.enabled) {
          values.push(logValue(log, config) ?? '')
        }
      })
      return values.join(',')
    })

    const csvContent = header + rows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    a.download = `${equipmentId}_logs_${timestamp}.csv`
    a.click()
    URL.revokeObjectURL(url)

    toast.success(t('equipmentDetail.csvDownloaded', { count: logsRaw.value.length }))
  } catch (error) {
    console.error('CSVダウンロードエラー:', error)
    toast.error(t('equipmentDetail.csvDownloadError'))
  }
}

let intervalId = null

const fetchLogs = async () => {
  try {
    const data = await apiFetch(`/api/logs/${equipmentId}/history_optimized?period=${selectedPeriod.value}`)
    // APIは配列を `data` キーで返す（旧実装は `data.logs` を読んでおり常に空だった）。
    // data_source で生ログ/日次集計を判別し、値の参照キーを切り替える。
    logsRaw.value = data.data || []
    dataSource.value = data.data_source || 'raw_logs'
    updateChart()
  } catch (err) {
    console.error('ログ取得失敗:', err)
  }
}

onMounted(async () => {
  const { default: zoomPlugin } = await import('chartjs-plugin-zoom')
  ChartJS.register(zoomPlugin)

  chartOptions.value = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500, easing: 'easeInOutQuad' },
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: t('chart.title') },
      zoom: {
        zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' },
        pan: { enabled: true, mode: 'x' },
      },
    },
  }

  console.log('🚀 ログ履歴ページの初期化開始')

  // 1. 設備情報取得
  await fetchEquipmentInfo()

  // 2. PLC設定取得（動的データ構造の初期化に必要）
  await fetchPLCConfigs()

  // 3. ログデータ取得（PLC設定取得後に実行）
  await fetchLogs()

  // 4. 定期的なログ更新を開始
  if (intervalId) clearInterval(intervalId)
  intervalId = setInterval(fetchLogs, 10000)

  // 5. エラー・アラームデータを読み込み（初回のみ）
  await loadErrorsAndAlarms()

  console.log('✅ ログ履歴ページの初期化完了')
})

onBeforeUnmount(() => {
  clearInterval(intervalId)
})

// タブが切り替わったときにエラー・アラームデータを再読み込み
watch(tab, (newTab) => {
  if (newTab === '2') {
    loadErrorsAndAlarms()
  }
})

// 期間切替時は再fetch（生ログ/日次集計で参照先APIが変わるため）。
// fetchLogs内でupdateChartも呼ばれる。
watch(selectedPeriod, fetchLogs)
</script>

<style scoped>
canvas {
  max-width: 100%;
  height: auto !important;
  display: block;
}
</style>
