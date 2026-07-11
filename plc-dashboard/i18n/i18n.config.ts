// vue-i18n の基本設定（Composition APIモード固定）。
// メッセージ辞書は nuxt.config.ts の locales/langDir（i18n/locales/*.json）から
// 遅延ロードされる。以前はここで ../locales/*.json を eager import しており、
// i18n/locales/ とルート locales/ の二重管理・乖離の原因になっていた（Issue #21 リポジトリ衛生）。
export default {
  legacy: false,
  locale: 'ja'
}
