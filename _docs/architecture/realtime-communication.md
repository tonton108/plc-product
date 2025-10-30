# リアルタイム通信の実装

**作成日:** 2025-10-30
**最終更新:** 2025-10-30

## 技術スタック

- **プロトコル:** WebSocket（Socket.IO）
- **サーバー:** Flask-SocketIO（threading mode）
- **クライアント:** Socket.IO Client（Nuxt.js）

## Socket.IO初期化

### バックエンド設定

**重要:** 必ず`async_mode='threading'`で初期化してください。

```python
# backend/app.py
socketio.init_app(
    app,
    cors_allowed_origins=["http://localhost:3000"],
    async_mode='threading',
    logger=False,
    engineio_logger=False
)
```

**理由:** Greenletエラーを回避し、Flaskとの互換性を確保するため。

詳細は `_docs/decisions/socketio-threading-mode.md` を参照。

### フロントエンド設定

```typescript
// pages/monitoring/[id].vue
import { io } from 'socket.io-client'

const socket = io('http://localhost:5000', {
  transports: ['websocket'],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5
})
```

## 接続フロー

### 1. クライアント接続

```
[Nuxt UI] → ws://localhost:5000 → [Flask Backend]
```

**ステップ:**
1. ユーザーが`/monitoring/[id]`ページを開く
2. Socket.IO Clientが自動的にバックエンドに接続
3. `connect`イベントが発火
4. クライアントが`join_monitoring`イベントを送信

### 2. ルーム参加

```typescript
// フロントエンド
socket.emit('join_monitoring', { equipment_id: 'DEMO_001' })
```

```python
# バックエンド (routes.py:1084-1092)
@socketio.on('join_monitoring')
def handle_join_monitoring(data):
    equipment_id = data.get('equipment_id')
    join_room(f'equipment_{equipment_id}')
    join_room('monitoring')
    logger.info(f"🔌 {request.sid} joined monitoring for {equipment_id}")
```

### 3. データ送信（Raspberry Pi → Flask）

```python
# Raspberry Pi (raspi_agent/plc_agent.py)
response = requests.post(
    f'{CENTRAL_SERVER_URL}/api/logs',
    json={
        'equipment_id': equipment_id,
        'timestamp': datetime.now().isoformat(),
        'data': {
            'temperature': 25.5,
            'pressure': 101.3
        }
    }
)
```

### 4. WebSocket配信（Flask → Nuxt UI）

```python
# バックエンド (routes.py:874-912)
@app.route('/api/logs', methods=['POST'])
def save_logs():
    # 1. データベースに保存
    log = Log(equipment_id=equipment_id, timestamp=timestamp, data=data)
    db.session.add(log)
    db.session.commit()

    # 2. WebSocketで全クライアントに配信
    socketio.emit('plc_data_update', {
        'equipment_id': equipment_id,
        'timestamp': timestamp,
        'data': data
    }, room='monitoring')

    # 3. 特定設備のクライアントにも配信
    socketio.emit('equipment_data_update', {
        'equipment_id': equipment_id,
        'timestamp': timestamp,
        'data': data
    }, room=f'equipment_{equipment_id}')
```

### 5. クライアント側でデータ受信

```typescript
// フロントエンド
socket.on('equipment_data_update', (update) => {
  console.log('📊 データ更新:', update)
  // グラフ更新
  chartData.value.push({
    x: new Date(update.timestamp),
    y: update.data.temperature
  })
})
```

## WebSocketルーム設計

### ルームの種類

| ルーム名 | 用途 | 参加者 |
|---------|------|-------|
| `monitoring` | 全設備のモニタリング | すべてのモニタリングクライアント |
| `equipment_{equipment_id}` | 特定設備のモニタリング | 該当設備のモニタリングページを開いているクライアント |

### ルームのメリット

1. **データ配信の効率化** - 必要なクライアントにのみデータを送信
2. **スケーラビリティ** - 設備数が増えてもパフォーマンス維持
3. **柔軟性** - 設備ごとに異なるデータ更新頻度を設定可能

## Socket.IOイベント一覧

### クライアント → サーバー

| イベント名 | 説明 | ペイロード例 |
|----------|------|------------|
| `connect` | WebSocket接続確立 | - |
| `disconnect` | WebSocket接続切断 | - |
| `join_monitoring` | モニタリングルーム参加 | `{equipment_id: 'DEMO_001'}` |
| `leave_monitoring` | モニタリングルーム退出 | `{equipment_id: 'DEMO_001'}` |
| `get_realtime_status` | リアルタイム状態取得要求 | `{equipment_id: 'DEMO_001'}` |

### サーバー → クライアント

| イベント名 | 説明 | ペイロード例 |
|----------|------|------------|
| `plc_data_update` | PLCデータ更新通知（全設備） | `{equipment_id: 'DEMO_001', timestamp: '2025-01-15T10:30:00', data: {...}}` |
| `equipment_data_update` | 設備別データ更新通知 | `{equipment_id: 'DEMO_001', timestamp: '2025-01-15T10:30:00', data: {...}}` |

## データフロー全体図

```
┌─────────────────┐
│  Raspberry Pi   │
│  (PLCエージェント)│
└────────┬────────┘
         │ HTTP POST /api/logs
         │ 5秒間隔
         ↓
┌─────────────────┐
│  Flask Backend  │
│  ┌───────────┐  │
│  │ PostgreSQL│  │  WebSocket (Socket.IO)
│  └───────────┘  │  ←─────────────────┐
└────────┬────────┘                    │
         │ emit('plc_data_update')     │
         │ emit('equipment_data_update')│
         ↓                              │
┌─────────────────┐                    │
│   Nuxt.js UI    │                    │
│  (モニタリング画面)│────────────────────┘
└─────────────────┘   ws://localhost:5000
```

## エラーハンドリング

### 接続エラー

```typescript
// フロントエンド
socket.on('connect_error', (error) => {
  console.error('❌ WebSocket接続エラー:', error)
  // リトライロジック
})

socket.on('disconnect', (reason) => {
  console.warn('⚠️ WebSocket切断:', reason)
  if (reason === 'io server disconnect') {
    // サーバー側から切断された場合、手動で再接続
    socket.connect()
  }
})
```

### タイムアウト設定

```python
# バックエンド
socketio.init_app(
    app,
    ping_timeout=60,        # Pingタイムアウト（秒）
    ping_interval=25,       # Ping送信間隔（秒）
    async_mode='threading'
)
```

## パフォーマンス最適化

### 1. バッチ配信

複数のデータ更新を1つのメッセージにまとめて送信：

```python
# ❌ 悪い例: 1つずつ送信
for data_point in data_points:
    socketio.emit('plc_data_update', data_point)

# ✅ 良い例: バッチで送信
socketio.emit('plc_data_batch_update', {
    'equipment_id': equipment_id,
    'data_points': data_points
})
```

### 2. データ圧縮

大量のデータを送信する場合は、不要なフィールドを削除：

```python
# ✅ 必要なフィールドのみ送信
socketio.emit('plc_data_update', {
    'equipment_id': equipment_id,
    'timestamp': timestamp.isoformat(),
    'data': {k: v for k, v in data.items() if v is not None}
})
```

### 3. ルームの適切な使用

特定設備のデータは該当ルームにのみ配信：

```python
# ✅ 特定設備のルームにのみ配信
socketio.emit('equipment_data_update', data, room=f'equipment_{equipment_id}')

# ❌ 悪い例: すべてのクライアントに配信
socketio.emit('equipment_data_update', data)
```

## トラブルシューティング

### データが届かない

**確認ポイント:**
1. Socket.IO接続状態を確認（ブラウザ開発者ツール → Network → WS）
2. ルームに正しく参加しているか確認
3. CORSオリジン設定を確認（`backend/app.py:18-20, 60`）

```bash
# バックエンドログで確認
docker compose logs -f backend | grep "📡 WebSocket"
```

### 接続が頻繁に切断される

**原因:**
- ネットワークの不安定性
- Pingタイムアウトが短すぎる

**解決方法:**
```python
# Pingタイムアウトを延長
socketio.init_app(app, ping_timeout=120, ping_interval=25)
```

### グラフが更新されない

**確認ポイント:**
1. Socket.IOイベントが受信されているか（ブラウザコンソール）
2. Chart.jsのデータ更新ロジックが正しいか
3. データ形式が正しいか（timestampがISO 8601形式か）

## 関連ドキュメント

- `_docs/decisions/socketio-threading-mode.md` - Socket.IO設定の詳細
- `_docs/architecture/backend.md` - バックエンドアーキテクチャ
- `_docs/architecture/frontend.md` - フロントエンドアーキテクチャ

---

**最終更新:** 2025-10-30
