// plugins/vuetify.ts
// ガイドライン準拠カラーパレット（ブルーグレー + 落ち着いたグリーン）
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
// Vuetifyの中国語ロケールは zhHans/zhHant 名で提供される（zh は存在しない）。
// 本アプリのロケールコード 'zh'（簡体字）に zhHans を割り当てる。
import { ja, en, zhHans as zh } from 'vuetify/locale'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

// ライトテーマ（ガイドライン準拠）
const lightTheme = {
  dark: false,
  colors: {
    primary: '#0891b2',      // 情報色: ティール系（控えめな彩度）
    secondary: '#64748b',    // 停止・無効: グレー系
    accent: '#22c55e',       // 主要アクセント: 落ち着いたグリーン
    error: '#dc2626',        // 異常・エラー: ディープレッド
    info: '#0891b2',         // 情報ラベル: シアン～ティール系
    success: '#16a34a',      // 成功・稼働中: グリーン系
    warning: '#d97706',      // 注意・警告: アンバー系
    background: '#f8fafc',   // 背景: ごく薄いグレー
    surface: '#ffffff',      // サーフェス: 白ベース
  }
}

// ダークテーマ（ガイドライン準拠）
const darkTheme = {
  dark: true,
  colors: {
    primary: '#14b8a6',      // 情報色: ティール系
    secondary: '#94a3b8',    // 停止・無効: グレー系
    accent: '#22c55e',       // 主要アクセント: 落ち着いたグリーン
    error: '#ef4444',        // 異常・エラー: ディープレッド
    info: '#06b6d4',         // 情報ラベル: シアン～ティール系
    success: '#22c55e',      // 成功・稼働中: グリーン系
    warning: '#fbbf24',      // 注意・警告: アンバー系
    background: '#0f172a',   // 背景: かなり暗いブルーグレー
    surface: '#1e293b',      // サーフェス: 背景 + 少しだけ明るい
  }
}

export default defineNuxtPlugin((nuxtApp) => {
  const vuetify = createVuetify({
    components,
    directives,
    // Vuetify組込み文言（データテーブルのフッター「Items per page」「0-0 of 0」、
    // 既定のno-dataテキスト等）を日本語化する。既定は英語で、日本語モード固定の
    // 本UIでは英語が混ざって「雑」に見えるため。既定ロケールは日本語。
    locale: {
      locale: 'ja',
      fallback: 'en',
      messages: { ja, en, zh },
    },
    theme: {
      defaultTheme: 'light', // デフォルトはライトモード
      themes: {
        light: lightTheme,
        dark: darkTheme,
      },
    },
    icons: {
      defaultSet: 'mdi',
    },
    defaults: {
      VTooltip: {
        color: 'grey-darken-3',
      },
    },
  })

  nuxtApp.vueApp.use(vuetify)
})
