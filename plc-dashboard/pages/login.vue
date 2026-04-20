<template>
  <v-app>
    <v-main>
      <v-container fill-height class="fade-in">
        <v-row align="center" justify="center">
          <v-col cols="12" sm="8" md="5" lg="4">
            <div class="text-center mb-2">
              <LanguageSwitch />
            </div>
            <div class="text-center mb-8">
              <v-icon size="80" color="white" class="mb-4">mdi-factory</v-icon>
              <h1 class="text-h3 font-weight-bold mb-2 text-white">{{ $t('login.title') }}</h1>
              <p class="text-subtitle-1 text-white">{{ $t('login.subtitle') }}</p>
            </div>

            <v-card class="glass-card pa-8">
              <v-card-text>
                <v-form @submit.prevent="login">
                  <v-text-field
                    v-model="username"
                    :label="$t('login.username')"
                    prepend-inner-icon="mdi-account"
                    variant="outlined"
                    :rules="[rules.required]"
                    class="mb-4"
                    rounded="lg"
                    color="primary"
                  ></v-text-field>

                  <v-text-field
                    v-model="password"
                    :label="$t('login.password')"
                    prepend-inner-icon="mdi-lock"
                    type="password"
                    variant="outlined"
                    :rules="[rules.required]"
                    class="mb-4"
                    rounded="lg"
                    color="primary"
                  ></v-text-field>

                  <v-alert
                    v-if="errorMessage"
                    type="error"
                    class="mb-4"
                    closable
                    rounded="lg"
                    @click:close="errorMessage = ''"
                  >
                    {{ errorMessage }}
                  </v-alert>

                  <v-btn
                    type="submit"
                    color="primary"
                    block
                    size="x-large"
                    :loading="loading"
                    class="modern-btn text-h6 py-6"
                  >
                    <v-icon class="mr-2">mdi-login</v-icon>
                    {{ $t('login.loginButton') }}
                  </v-btn>
                </v-form>

                <v-divider class="my-6"></v-divider>

                <div class="text-center text-caption">
                  <v-chip size="small" variant="text" class="mb-2">
                    <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
                    {{ $t('login.intranetInfo') }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>

            <v-alert
              type="info"
              variant="tonal"
              class="glass-card mt-6"
              rounded="lg"
            >
              <v-icon class="mr-2">mdi-information-outline</v-icon>
              {{ $t('login.intranetInfo') }}
            </v-alert>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { t } = useI18n()

const username = ref('')
const password = ref('')
const errorMessage = ref('')
const loading = ref(false)

const rules = {
  required: (value: string) => !!value || t('login.required')
}

// デフォルトユーザー（開発・テスト用）
// 本番環境では環境変数またはバックエンド認証を使用してください
const DEFAULT_USERS = [
  { username: 'admin', password: 'plc-monitor-2025' },
  { username: 'operator', password: 'operator-2025' }
]

const login = async () => {
  // バリデーション
  if (!username.value || !password.value) {
    errorMessage.value = t('login.error')
    return
  }

  loading.value = true
  errorMessage.value = ''

  // 認証チェック（シンプル実装）
  // 本番環境ではバックエンドAPIで認証を行うことを推奨
  const user = DEFAULT_USERS.find(
    u => u.username === username.value && u.password === password.value
  )

  // 認証遅延（ブルートフォース対策）
  await new Promise(resolve => setTimeout(resolve, 500))

  if (user) {
    // 認証成功 - セッション情報を保存
    const authToken = btoa(`${username.value}:${Date.now()}`)
    localStorage.setItem('plc_auth_token', authToken)
    localStorage.setItem('plc_auth_user', username.value)

    // ダッシュボードにリダイレクト
    router.push('/')
  } else {
    errorMessage.value = t('login.error')
  }

  loading.value = false
}

// すでにログイン済みの場合はリダイレクト
onMounted(() => {
  const authToken = localStorage.getItem('plc_auth_token')
  if (authToken) {
    router.push('/')
  }
})
</script>
