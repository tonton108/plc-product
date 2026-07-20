<template>
  <v-container class="fade-in">
    <!-- ヘッダー -->
    <v-row class="mb-6">
      <v-col>
        <v-card class="glass-card pa-6" color="accent">
          <v-row align="center">
            <v-col>
              <v-card-title class="text-h4 mb-2 font-weight-bold text-white">
                <v-icon size="x-large" class="mr-3" color="white">mdi-account-cog</v-icon>
                {{ $t('userManagement.title') }}
              </v-card-title>
              <v-card-subtitle class="text-subtitle-1 text-white" style="opacity: 1 !important;">
                {{ $t('userManagement.subtitle') }}
              </v-card-subtitle>
            </v-col>
            <v-col cols="auto">
              <LanguageSwitch />
              <ThemeToggle />
              <v-btn color="white" size="large" class="mr-3 modern-btn" @click="goHome">
                <v-icon>mdi-arrow-left</v-icon>
                <span class="ml-2">{{ $t('common.back') }}</span>
              </v-btn>
              <v-btn color="white" size="large" class="mr-3 modern-btn" :loading="loading" @click="reload">
                <v-icon>mdi-refresh</v-icon>
                <span class="ml-2">{{ $t('common.refresh') }}</span>
              </v-btn>
              <v-btn color="primary" size="large" class="modern-btn" @click="openCreate">
                <v-icon>mdi-account-plus</v-icon>
                <span class="ml-2">{{ $t('userManagement.create') }}</span>
              </v-btn>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>

    <!-- 一覧 -->
    <v-row>
      <v-col cols="12">
        <v-data-table
          :headers="headers"
          :items="users"
          :loading="loading"
          item-value="id"
          class="glass-card"
          data-testid="users-table"
        >
          <template #[`item.role`]="{ item }">
            <v-chip :color="item.role === 'admin' ? 'primary' : 'secondary'" size="small" variant="elevated">
              {{ $t(`userManagement.roles.${item.role}`) }}
            </v-chip>
          </template>
          <template #[`item.is_active`]="{ item }">
            <v-chip :color="item.is_active ? 'success' : 'grey'" size="small" variant="elevated">
              {{ item.is_active ? $t('userManagement.statusActive') : $t('userManagement.statusInactive') }}
            </v-chip>
          </template>
          <template #[`item.created_at`]="{ item }">
            {{ formatDateTime(item.created_at) || '-' }}
          </template>
          <template #[`item.actions`]="{ item }">
            <div class="d-flex justify-center align-center ga-2">
              <v-btn
                color="secondary" size="small" variant="elevated" class="modern-btn"
                prepend-icon="mdi-key-variant"
                @click="confirmResetPassword(item)"
              >
                {{ $t('userManagement.resetPassword') }}
              </v-btn>
              <v-btn
                v-if="item.is_active"
                color="error" size="small" variant="elevated" class="modern-btn"
                prepend-icon="mdi-account-off"
                :disabled="isSelf(item)"
                @click="confirmDeactivate(item)"
              >
                {{ $t('userManagement.deactivate') }}
              </v-btn>
              <v-btn
                v-else
                color="success" size="small" variant="elevated" class="modern-btn"
                prepend-icon="mdi-account-check"
                @click="confirmActivate(item)"
              >
                {{ $t('userManagement.activate') }}
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </v-col>
    </v-row>

    <!-- 作成ダイアログ -->
    <v-dialog v-model="createDialog" max-width="480">
      <v-card>
        <v-card-title>{{ $t('userManagement.createDialog.title') }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="form.username"
            :label="$t('userManagement.createDialog.username')"
            variant="outlined"
            data-testid="create-username"
            autofocus
          />
          <v-select
            v-model="form.role"
            :items="roleOptions"
            :label="$t('userManagement.createDialog.role')"
            variant="outlined"
          />
          <v-text-field
            v-model="form.password"
            :label="$t('userManagement.createDialog.password')"
            variant="outlined"
            type="text"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="createDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" variant="elevated" :loading="submitting" data-testid="create-submit" @click="submitCreate">
            {{ $t('userManagement.createDialog.submit') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 生成パスワード表示ダイアログ -->
    <v-dialog v-model="generatedDialog" max-width="480" persistent>
      <v-card>
        <v-card-title>
          <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
          {{ $t('userManagement.generated.title') }}
        </v-card-title>
        <v-card-text>
          <p class="mb-4">{{ $t('userManagement.generated.message') }}</p>
          <v-text-field
            :model-value="generatedPassword"
            :label="$t('userManagement.generated.label')"
            variant="outlined"
            readonly
            append-inner-icon="mdi-content-copy"
            data-testid="generated-password"
            @click:append-inner="copyPassword"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="elevated" @click="generatedDialog = false">{{ $t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 確認ダイアログ -->
    <v-dialog v-model="confirmDialog" max-width="460">
      <v-card>
        <v-card-title>{{ $t('common.confirm') }}</v-card-title>
        <v-card-text>{{ confirmMessage }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" variant="elevated" :loading="submitting" data-testid="confirm-ok" @click="runConfirmed">
            {{ $t('common.ok') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, reactive } from 'vue'

// admin ロール限定（グローバルの auth.global.ts でログインは担保済み）
definePageMeta({ middleware: 'admin' })

const { t } = useI18n()
const router = useRouter()
const auth = useAuth()
const toast = useToast()
const { formatDateTime } = useDateTime()
const {
  users, loading, loadUsers, createUser, resetPassword, deactivateUser, activateUser,
} = useUsers()

const headers = [
  { title: t('userManagement.columns.username'), key: 'username', align: 'start' },
  { title: t('userManagement.columns.role'), key: 'role', align: 'start' },
  { title: t('userManagement.columns.status'), key: 'is_active', align: 'center' },
  { title: t('userManagement.columns.createdAt'), key: 'created_at', align: 'start' },
  { title: t('userManagement.columns.actions'), key: 'actions', align: 'center', sortable: false },
]

const roleOptions = [
  { title: t('userManagement.roles.admin'), value: 'admin' },
  { title: t('userManagement.roles.operator'), value: 'operator' },
]

const submitting = ref(false)

// --- 作成 ---
const createDialog = ref(false)
const form = reactive({ username: '', role: 'operator', password: '' })

const openCreate = () => {
  form.username = ''
  form.role = 'operator'
  form.password = ''
  createDialog.value = true
}

// --- 生成パスワード表示 ---
const generatedDialog = ref(false)
const generatedPassword = ref('')

const showGenerated = (password) => {
  generatedPassword.value = password
  generatedDialog.value = true
}

const copyPassword = async () => {
  try {
    await navigator.clipboard.writeText(generatedPassword.value)
    toast.success('OK')
  } catch {
    /* クリップボード不可でも致命ではない */
  }
}

// --- 確認ダイアログ（無効化/有効化/再設定の共通） ---
const confirmDialog = ref(false)
const confirmMessage = ref('')
let confirmAction = null

const askConfirm = (message, action) => {
  confirmMessage.value = message
  confirmAction = action
  confirmDialog.value = true
}

const serverError = (err) =>
  err?.data?.error || err?.response?._data?.error || t('userManagement.messages.actionError')

const isSelf = (item) => auth.user.value?.id === item.id

const reload = async () => {
  try {
    await loadUsers()
  } catch (err) {
    toast.error(t('userManagement.messages.loadError'))
  }
}

const submitCreate = async () => {
  if (!form.username.trim()) {
    toast.error(t('userManagement.messages.usernameRequired'))
    return
  }
  submitting.value = true
  try {
    const res = await createUser({
      username: form.username.trim(),
      role: form.role,
      password: form.password.trim() || undefined,
    })
    createDialog.value = false
    toast.success(t('userManagement.messages.created'))
    await reload()
    if (res?.generated_password) showGenerated(res.generated_password)
  } catch (err) {
    toast.error(serverError(err))
  } finally {
    submitting.value = false
  }
}

const confirmResetPassword = (item) => {
  askConfirm(t('userManagement.confirm.resetPassword', { name: item.username }), async () => {
    const res = await resetPassword(item.id)
    toast.success(t('userManagement.messages.passwordReset'))
    if (res?.generated_password) showGenerated(res.generated_password)
  })
}

const confirmDeactivate = (item) => {
  askConfirm(t('userManagement.confirm.deactivate', { name: item.username }), async () => {
    await deactivateUser(item.id)
    toast.success(t('userManagement.messages.deactivated'))
  })
}

const confirmActivate = (item) => {
  askConfirm(t('userManagement.confirm.activate', { name: item.username }), async () => {
    await activateUser(item.id)
    toast.success(t('userManagement.messages.activated'))
  })
}

const runConfirmed = async () => {
  if (!confirmAction) return
  submitting.value = true
  try {
    await confirmAction()
    confirmDialog.value = false
    await reload()
  } catch (err) {
    toast.error(serverError(err))
  } finally {
    submitting.value = false
  }
}

const goHome = () => router.push('/')

onMounted(reload)
</script>
