# フロントエンドアーキテクチャ（Nuxt.js）

**作成日:** 2025-10-24
**最終更新:** 2026-01-19

## 技術スタック

- **フレームワーク:** Nuxt.js 3
- **UIライブラリ:** Vuetify 3
- **グラフ:** Chart.js + chartjs-plugin-zoom
- **リアルタイム通信:** Socket.IO Client
- **多言語対応:** @nuxtjs/i18n（日本語・英語・中国語）

---

## ページ構成（全6ページ）

```
plc-dashboard/pages/
├── login.vue              # ログイン画面
├── index.vue              # ホーム・設備一覧
├── monitoring/
│   └── [id].vue          # リアルタイムモニタリング
├── equipment/
│   └── [id].vue          # 設備詳細・ログ履歴
├── errors-alarms.vue      # エラー・アラーム管理
└── logs.vue               # ロググラフ（従来型）
```

---

### 1. `pages/login.vue` - ログイン画面

**役割:** ユーザー認証

**機能:**
- ローカル認証（LocalStorageベース）
- デフォルトユーザー: `admin` / `plc-monitor-2025`, `operator` / `operator-2025`
- ブルートフォース対策（500ms遅延）
- 既ログイン時の自動リダイレクト
- 言語切り替え対応

**認証フロー:**
```javascript
// トークン保存
localStorage.setItem('plc_auth_token', btoa(username + ':' + timestamp))
localStorage.setItem('plc_auth_user', username)
```

---

### 2. `pages/index.vue` - ホーム・設備一覧

**役割:** ダッシュボードトップページ

**機能:**
- 全設備一覧表示（API: `GET /api/equipment`）
- 2つの表示モード:
  - **カード表示**: 設備をカード形式で表示（アニメーション付き）
  - **リスト表示**: Vuetify DataTableで表示
- 各設備の情報表示（設備ID、メーカー、IP、ポート等）
- ステータス色分け（正常/設定済み/登録済み/エラー）
- 表示モードのLocalStorage保存

**主なアクション:**
- 設備カードクリック → `/monitoring/{id}` へ遷移
- 「監視」ボタン → `/monitoring/{id}` へ遷移
- 「ログ」ボタン → `/equipment/{id}` へ遷移
- ログアウト → LocalStorageクリア

---

### 3. `pages/monitoring/[id].vue` - リアルタイムモニタリング ⭐主要機能

**役割:** PLCデータのリアルタイム監視

**機能:**
- Socket.IOでリアルタイムデータ受信
- PLC設定に基づく動的グラフ生成
- ステータスカード表示（現在値）
- データ履歴テーブル（最新100件）
- デバッグパネル（FABボタンで開閉）
- CSVエクスポート

**使用コンポーネント:**
- `MonitoringHeader.vue` - ヘッダー（戻るボタン、接続状態）
- `StatusCards.vue` - 現在値カード
- `ChartCards.vue` - リアルタイムグラフ
- `DataCards.vue` - データ履歴テーブル
- `MonitoringDebugPanel.vue` - デバッグ情報

**使用コンポーザブル:**
- `useRealtimeMonitoring` - Socket.IO接続・データ管理
- `useChartManagement` - Chart.jsインスタンス管理

**Socket.IO接続:**
```javascript
// composables/useRealtimeMonitoring.js
socket.emit('join_monitoring', { equipment_id: equipmentId })
socket.on('plc_data_update', (data) => {
  // リアルタイムデータ更新
})
```

**API呼び出し:**
- `GET /api/equipment/{id}` - 設備情報
- `GET /api/equipment/{id}/plc_configs` - PLC設定
- `GET /api/logs/{id}/latest` - 最新データ

---

### 4. `pages/equipment/[id].vue` - 設備詳細・ログ履歴

**役割:** 設備の詳細情報と履歴データの表示

**機能:**
- 3つのタブ:
  1. **グラフタブ**: 履歴データのラインチャート
  2. **テーブルタブ**: 履歴データ一覧
  3. **エラー・アラームタブ**: PLC状態とアラーム/エラーログ
- 期間選択: 1h, 6h, 24h, 7d, 30d
- CSVエクスポート
- アラーム/エラーログの操作（確認・解除・解決）

**API呼び出し:**
- `GET /api/equipment/{id}` - 設備情報
- `GET /api/equipment/{id}/plc_configs` - PLC設定
- `GET /api/logs/{id}/history_optimized?period={period}` - 履歴データ
- `GET /api/equipment/{id}/plc_status` - PLC状態
- `GET /api/equipment/{id}/alarms` - アラーム履歴
- `GET /api/equipment/{id}/error_logs` - エラーログ
- `PATCH /api/equipment/{id}/alarms/{alarmId}/acknowledge` - アラーム確認
- `PATCH /api/equipment/{id}/alarms/{alarmId}/clear` - アラーム解除
- `PATCH /api/equipment/{id}/error_logs/{logId}/resolve` - エラー解決

---

### 5. `pages/errors-alarms.vue` - エラー・アラーム管理

**役割:** 全設備のエラー・アラームを一括管理

**機能:**
- 設備選択ドロップダウン
- PLC状態表示（オンライン/オフライン、連続エラー回数）
- アラーム履歴テーブル（WARNING/ERROR/CRITICAL）
- エラーログテーブル
- アクションボタン: 確認・解除・解決

**API呼び出し:**
- `GET /api/equipment` - 設備一覧
- `GET /api/equipment/{id}/plc_status` - PLC状態
- `GET /api/equipment/{id}/alarms` - アラーム履歴
- `GET /api/equipment/{id}/error_logs` - エラーログ

---

### 6. `pages/logs.vue` - ロググラフ（従来型）

**役割:** シンプルなログ表示ページ

**機能:**
- 設備選択
- グラフ/テーブル切り替え
- テーマカラー選択（blue, green, red）
- 期間選択: 1h, 6h, 24h
- 異常値検出（110以下 or 130以上でAlert）
- 5秒ごとの自動更新
- CSVエクスポート

---

## コンポーネント構成

```
plc-dashboard/components/
├── MonitoringHeader.vue       # モニタリングヘッダー
├── StatusCards.vue            # ステータスカード
├── ChartCards.vue             # グラフカード
├── DataCards.vue              # データテーブルカード
├── MonitoringDebugPanel.vue   # デバッグパネル
├── GlobalToast.vue            # トースト通知
├── ThemeToggle.vue            # ダークモード切り替え
└── LanguageSwitch.vue         # 言語切り替え
```

---

## コンポーザブル

```
plc-dashboard/composables/
├── useRealtimeMonitoring.js   # Socket.IO接続・リアルタイムデータ管理
├── useChartManagement.js      # Chart.jsインスタンス管理
├── useToast.js                # トースト通知
└── useDateTime.ts             # 日時フォーマット（多言語対応）
```

### `useRealtimeMonitoring.js`

**役割:** Socket.IO WebSocket管理とリアルタイムデータ受信

```javascript
// 使用例
const {
  isConnected,
  latestData,
  dataHistory,
  debugLogs
} = useRealtimeMonitoring(equipmentId)
```

### `useChartManagement.js`

**役割:** Chart.jsの複数グラフインスタンス管理

```javascript
// 使用例
const {
  chartInstances,
  initializeCharts,
  updateCharts
} = useChartManagement()
```

---

## データフロー

```
┌─────────────────────────────────────────────────────────────┐
│  Raspberry Pi (raspi_agent)                                 │
│  └─ PLCからデータ収集 (Modbus/FINS/MC Protocol)             │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP POST /api/data
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Flask Backend (Port 5000)                                  │
│  ├─ データ保存 (PostgreSQL)                                 │
│  └─ WebSocket配信 (Socket.IO)                               │
└────────────────────┬────────────────────────────────────────┘
                     │ Socket.IO / REST API
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Nuxt.js Frontend (Port 3000)                               │
│  ├─ useRealtimeMonitoring (Socket.IO受信)                   │
│  ├─ useChartManagement (Chart.js描画)                       │
│  └─ Vuetify UI                                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  ブラウザ表示                                                │
│  └─ リアルタイムグラフ・データテーブル                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 認証・セッション管理

**方式:** LocalStorageベースのシンプル実装

```javascript
// トークン
localStorage.getItem('plc_auth_token')  // Base64(username:timestamp)
localStorage.getItem('plc_auth_user')   // ユーザー名

// ミドルウェア
middleware/auth.js  // ログインチェック
```

**注意:** 本番環境ではバックエンド認証への切り替えを推奨

---

## 多言語対応（i18n）

**対応言語:** 日本語、英語、中国語

```
plc-dashboard/locales/
├── ja.json   # 日本語
├── en.json   # 英語
└── zh.json   # 中国語
```

**切り替え:** `LanguageSwitch.vue` コンポーネント

---

## UI/UX特徴

| 特徴 | 実装 |
|------|------|
| ダークモード | `ThemeToggle.vue` + Vuetify theme |
| Glass Morphism | カードのガラス風デザイン |
| アニメーション | ページ遷移・カードのフェードイン |
| レスポンシブ | スマホ・タブレット対応 |
| ツールチップ | `content-class="tooltip-custom"` 必須（下記参照） |

### Vuetifyツールチップの実装ルール

**問題:** Vuetifyのデフォルトツールチップは、ダークモードで黒背景に黒文字となり見えなくなる。

**必ず`content-class`を使用:**

```vue
<!-- ✅ 正しい実装 -->
<v-tooltip location="bottom" content-class="tooltip-custom">
  <template #activator="{ props }">
    <v-btn v-bind="props" color="primary">ボタン</v-btn>
  </template>
  <span>ツールチップのテキスト</span>
</v-tooltip>

<!-- ❌ 避けるべき実装 -->
<v-tooltip text="ツールチップ" location="bottom">
  <!-- text属性を使うとcontent-classが適用されない -->
</v-tooltip>
```

**設定ファイル:**
- `plugins/vuetify.ts:50-54` - VTooltipデフォルト設定
- `app.vue:8-35` - `.tooltip-custom` グローバルCSS

**チェックリスト:**
- [ ] `content-class="tooltip-custom"` を追加
- [ ] `<span>` タグでテキストを囲む
- [ ] Playwrightでダークモード表示を確認

**実装箇所:**
- `pages/index.vue:150,168,222,240`
- `pages/dashboard.vue:156,174`
- `components/ThemeToggle.vue:2`

---

## ビルド・デプロイ

### 開発サーバー起動

```bash
cd plc-dashboard
npm run dev
```

**ポート:** 3000（デフォルト）

### プロダクションビルド

```bash
npm run build
npm run preview
```

### Electronアプリ（開発）

```bash
cd plc-dashboard
npm run electron:dev
```

---

## 環境変数

`.env`ファイルで設定：

```bash
# バックエンドAPI URL
NUXT_PUBLIC_API_URL=http://localhost:5000

# Socket.IO URL
NUXT_PUBLIC_SOCKET_URL=http://localhost:5000
```

---

## 関連ドキュメント

- `plc-dashboard/_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `plc-dashboard/_docs/architecture/realtime-communication.md` - リアルタイム通信
- `plc-dashboard/_docs/commands/development.md` - 開発コマンド集
- `plc-dashboard/_docs/features/phase2-7-error-alarm-system.md` - エラー・アラームシステム
