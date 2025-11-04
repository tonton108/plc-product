# フロントエンドアーキテクチャ（Nuxt.js）

**作成日:** 2025-10-24

## 技術スタック

- **フレームワーク:** Nuxt.js 3
- **UIライブラリ:** Vuetify 3
- **グラフ:** Chart.js
- **リアルタイム通信:** Socket.IO Client

## 主要ファイル

### `plc-dashboard/pages/index.vue`

**役割:** ダッシュボードトップページ

**機能:**
- 全設備一覧表示
- 各設備の最新ステータス表示
- モニタリングページへのリンク

### `plc-dashboard/pages/monitoring/[id].vue`

**役割:** リアルタイムモニタリングページ

**機能:**
- Socket.IOでPLCデータをリアルタイム受信
- Chart.jsでグラフ表示
- 期間選択（1h, 6h, 24h, 7d, 30d）
- データポイントごとの表示切り替え

**Socket.IO接続:**
```javascript
const socket = io('http://localhost:5000', {
  transports: ['websocket'],
  autoConnect: true
});

socket.emit('join_monitoring', { equipment_id: props.id });

socket.on('plc_data_update', (data) => {
  // グラフ更新
});
```

### `plc-dashboard/pages/equipment/index.vue`

**役割:** 設備管理ページ

**機能:**
- 設備一覧表示
- 設備詳細編集
- 設備削除

### `plc-dashboard/components/`

**主要コンポーネント:**
- `EquipmentCard.vue` - 設備カード表示
- `RealtimeChart.vue` - リアルタイムグラフ
- `DataPointSelector.vue` - データポイント選択UI

## データフロー

```
[中央サーバー（Flask）]
    ↓ Socket.IO
[Nuxt.js Client]
    ↓ Chart.js
[ブラウザ表示]
```

1. Socket.IOで中央サーバーに接続
2. `join_monitoring`イベントで設備IDを登録
3. `plc_data_update`イベントでリアルタイムデータ受信
4. Chart.jsでグラフを動的更新

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

## 環境変数

`.env`ファイルで設定：

```bash
# バックエンドAPI URL
NUXT_PUBLIC_API_URL=http://localhost:5000

# Socket.IO URL
NUXT_PUBLIC_SOCKET_URL=http://localhost:5000
```

## 関連ドキュメント

- `_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `_docs/commands/development.md` - 開発コマンド集

---

**最終更新:** 2025-10-24
