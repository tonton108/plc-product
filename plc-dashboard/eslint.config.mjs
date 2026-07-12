// @ts-check
import withNuxt from './.nuxt/eslint.config.mjs'

// Nuxtアプリ本体（pages/components/composables/plugins等）を対象とする。
// electron/ と desktop-app/ は別サブプロジェクト（desktop-app はSPEC Phase4で廃止予定）
// のため、Nuxtのlint対象からは除外する。
export default withNuxt(
  {
    ignores: ['electron/**', 'desktop-app/**', 'scripts/**'],
  },
  {
    rules: {
      // Vuetifyのデータテーブル等は <template v-slot:item.xxx> のように
      // v-slot に修飾子を付ける正当な記法を使うため許可する
      'vue/valid-v-slot': ['error', { allowModifiers: true }],
      // 段階導入のため any は警告に留める（将来的に型付けして解消）
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
)
