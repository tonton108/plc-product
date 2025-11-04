<template>
  <v-app>
    <NuxtPage />
    <GlobalToast />
  </v-app>
</template>

<style>
/* テーマ切り替えのスムーズなトランジション */
.v-application {
  transition: background-color 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              color 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* 主要コンポーネントのみトランジション適用（パフォーマンス最適化） */
.v-card,
.v-btn,
.v-app-bar,
.v-sheet {
  transition: background-color 0.4s cubic-bezier(0.4, 0, 0.2, 1),
              color 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* GPUアクセラレーションを有効化してスムーズに */
.v-application,
.v-card,
.v-btn {
  will-change: background-color, color;
  transform: translateZ(0);
  backface-visibility: hidden;
}

/* ツールチップのグローバルスタイル */
.v-tooltip .v-overlay__content {
  background-color: #424242 !important;
  color: #ffffff !important;
  opacity: 1 !important;
}

.v-tooltip .v-overlay__content span {
  color: #ffffff !important;
}

.tooltip-custom {
  background-color: #424242 !important;
  color: #ffffff !important;
  opacity: 1 !important;
}

.tooltip-custom span {
  color: #ffffff !important;
}

/* Vuetifyのツールチップ本体 */
.v-tooltip__content {
  background-color: #424242 !important;
  color: #ffffff !important;
}

/* ボタン内のコンテンツ（アイコンとテキスト）を垂直方向で中央揃え */
.v-btn .v-btn__content {
  align-items: center !important;
  display: flex !important;
}

.v-btn .v-icon {
  align-self: center !important;
}
</style>