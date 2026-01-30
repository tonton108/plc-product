# データフロー全体図

**作成日:** 2025-10-31
**最終更新:** 2025-10-31

このドキュメントでは、PLCの生データがどのように収集され、処理され、最終的にNuxt UI上でリアルタイム表示されるまでの**エンドツーエンドのデータフロー**を詳細に解説します。

---

## 1. 全体概要図

```
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ1: PLCがデータを保持                                             │
│                                                                        │
│  [PLC内部メモリ/レジスタ]                                               │
│   - D100: 温度 (float32) = 25.5℃                                      │
│   - D102: 圧力 (float32) = 101.3kPa                                    │
│   - D200: 生産数 (int16) = 1250                                        │
│   - D201: 電流 (int16) = 15A                                           │
└─────────────────┬──────────────────────────────────────────────────────┘
                  │ Modbus TCP / FINS / MC Protocol
                  ↓
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ2: Raspberry Piがデータ読み取り                                  │
│                                                                        │
│  [Raspberry Pi エージェント]                                           │
│   - plc_agent.py: read_from_plc() でPLC接続                            │
│   - Big-Endian形式でfloat32/int16を読み取り                            │
│   - 5秒間隔でポーリング (デフォルト)                                     │
└─────────────────┬──────────────────────────────────────────────────────┘
                  │ Pythonオブジェクト
                  ↓
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ3: データ加工・バッファリング                                     │
│                                                                        │
│  [db_utils.py: DatabaseAPI]                                            │
│   - ローカルSQLiteバッファに一時保存                                     │
│   - JSON形式に変換                                                      │
│   - タイムスタンプ付与 (UTC)                                            │
└─────────────────┬──────────────────────────────────────────────────────┘
                  │ HTTP POST /api/logs (JSON)
                  ↓
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ4: 中央サーバーに送信                                            │
│                                                                        │
│  POST http://192.168.1.10:5000/api/logs                               │
│  Content-Type: application/json                                        │
│  Body: {                                                               │
│    "equipment_id": "PLC_001",                                          │
│    "timestamp": "2025-10-31T10:30:00Z",                                │
│    "temperature": 25.5,                                                │
│    "pressure": 101.3,                                                  │
│    "production_count": 1250,                                           │
│    "current": 15                                                       │
│  }                                                                     │
└─────────────────┬──────────────────────────────────────────────────────┘
                  │ Flask Backend受信
                  ↓
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ5: Flask Backendでデータ受信・検証                               │
│                                                                        │
│  [routes.py: save_log_data()]                                          │
│   - JSON形式の検証                                                      │
│   - 設備ID存在確認 (Equipment テーブル)                                 │
│   - タイムスタンプ正規化 (ISO 8601 → datetime)                          │
└─────────────────┬──────────────────────────────────────────────────────┘
                  │ SQLAlchemy ORM
                  ↓
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ6: PostgreSQLに保存                                              │
│                                                                        │
│  [Log テーブル]                                                         │
│   INSERT INTO logs (                                                   │
│     equipment_id, timestamp, temperature, pressure,                    │
│     production_count, current, cycle_time, error_code                  │
│   ) VALUES (1, '2025-10-31 10:30:00', 25.5, 101.3, 1250, 15, ...)     │
└─────────────────┬──────────────────────────────────────────────────────┘
                  │ Socket.IO emit
                  ↓
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ7: WebSocketでリアルタイム配信                                    │
│                                                                        │
│  [Socket.IO (threading mode)]                                          │
│   - 全モニタリングクライアントに配信                                      │
│     socketio.emit('plc_data_update', data, room='monitoring')          │
│   - 特定設備のクライアントに配信                                          │
│     socketio.emit('equipment_data_update', data,                       │
│                   room='equipment_PLC_001')                            │
└─────────────────┬──────────────────────────────────────────────────────┘
                  │ WebSocket (ws://192.168.1.10:5000)
                  ↓
┌────────────────────────────────────────────────────────────────────────┐
│ ステップ8: Nuxt UIでデータ受信→Chart.jsでグラフ描画                      │
│                                                                        │
│  [pages/monitoring/[id].vue]                                           │
│   - Socket.IO Clientがイベント受信                                      │
│   - useRealtimeMonitoring composable でデータ処理                       │
│   - useChartManagement composable でグラフ更新                          │
│   - Chart.js が canvas にリアルタイムグラフを描画                        │
└────────────────────────────────────────────────────────────────────────┘
                  │
                  ↓
           [ブラウザ画面に表示]
```

---

## 2. 各ステップの詳細

### ステップ1: PLCがデータを保持

**概要:**
PLC（Programmable Logic Controller）は、製造装置から収集したセンサーデータを内部メモリ（レジスタ）に保持します。

**データ形式:**
- **Dレジスタ（三菱）/ DMエリア（オムロン）:** データメモリ領域
- **型:**
  - `float32` (4バイト): 温度、圧力などの実数値
  - `int16` (2バイト): 生産数、電流などの整数値
  - `bool` (1ビット): 運転状態、エラーフラグ

**実装例:**
```
[三菱PLCの例]
D100-D101 → 温度 (float32) = 25.5℃
D102-D103 → 圧力 (float32) = 101.3kPa
D200      → 生産数 (int16) = 1250
D201      → 電流 (int16) = 15A
```

**関連ドキュメント:**
- `plc-dashboard/_docs/plc-knowledge/protocols.md` - PLCプロトコル詳細
- `plc-dashboard/_docs/plc-knowledge/plc-manufacturers.md` - メーカー別レジスタ仕様

---

### ステップ2: Raspberry Piがデータ読み取り

**概要:**
Raspberry Pi上のエージェントプログラムが、PLC通信プロトコル（Modbus TCP、FINS、MC Protocol）を使用してPLCからデータを読み取ります。

**実装箇所:** `plc-dashboard/raspi_agent/plc_agent.py:74-115`

```python
def read_from_plc(config):
    """設定ファイルに基づいて動的にPLCからデータを読み取り"""
    ip = config.get("plc_ip", PLC_IP)
    port = config.get("plc_port", PLC_PORT)
    manufacturer = config.get("manufacturer", PLC_MANUFACTURER)
    data_points = config.get("data_points", {})

    # 実際のPLC接続を試行
    result = read_from_real_plc(config, ip, port, manufacturer, data_points)
    return result
```

**通信プロトコル例（三菱PLC）:**
```python
# plc_drivers.py: read_mitsubishi_plc()
plc = pymcprotocol3e.Type3E()
plc.connect(ip, port, timeout=5.0)  # タイムアウト必須

# 2ワード読み取り (float32)
word_values = plc.batchread_wordunits(headdevice="D100", readsize=2)

# Big-Endian形式で結合
word1, word2 = word_values[0], word_values[1]
combined = (word1 << 16) | word2
temperature = struct.unpack('>f', struct.pack('>I', combined))[0]  # Big-Endian
```

**タイムアウト設定:**
- **必須:** すべてのPLC接続に3-5秒のタイムアウトを設定
- **理由:** PLCが応答しない場合にプログラムがハングするのを防ぐ

**エラーハンドリング:**
```python
try:
    plc.connect(ip, port, timeout=5.0)
except Exception as e:
    logger.error(f"PLC接続エラー: {e}")
    return generate_dummy_data(data_points)  # フォールバック
```

**関連ドキュメント:**
- `plc-dashboard/_docs/plc-knowledge/endianness.md` - Big-Endian必須の理由
- `plc-dashboard/_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定ベストプラクティス

---

### ステップ3: データ加工・バッファリング

**概要:**
読み取ったPLCデータをJSON形式に変換し、ローカルSQLiteバッファに一時保存してから中央サーバーへの送信を試行します。

**実装箇所:** `plc-dashboard/raspi_agent/db_utils.py:155-185`

```python
def send_log_data(self, equipment_id, log_data):
    """ログデータを送信（バッファリング対応）"""
    payload = {
        "equipment_id": equipment_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        **log_data
    }

    # 1. ローカルバッファに保存
    record_id = self.buffer.save(equipment_id, payload)

    # 2. 中央サーバーへの送信を試行
    response = requests.post(f"{self.base_url}/logs", json=payload, timeout=5)
    if response.status_code == 200:
        # 送信成功 → バッファから削除
        self.buffer.mark_as_sent(record_id)
        return True
    else:
        # 送信失敗 → バッファに残す
        self.buffer.increment_retry(record_id, f"HTTP {response.status_code}")
        return False
```

**バッファリング戦略:**

| 項目 | 設定値 |
|------|--------|
| 再送信間隔 | 60秒ごと |
| クリーンアップ間隔 | 1時間ごと |
| 古いデータ削除 | 7日以上前のデータを削除 |
| 最大リトライ回数 | 制限なし（無期限リトライ） |

**データ形式変換:**
```python
# PLCデータ（Python dict）
plc_data = {
    "temperature": 25.5,
    "pressure": 101.3,
    "production_count": 1250,
    "current": 15
}

# JSON形式に変換
payload = {
    "equipment_id": "PLC_001",
    "timestamp": "2025-10-31 10:30:00",  # UTC
    "temperature": 25.5,
    "pressure": 101.3,
    "production_count": 1250,
    "current": 15
}
```

**関連ドキュメント:**
- `plc-dashboard/_docs/architecture/raspi-agent.md` - ローカルバッファリング機能詳細（local_buffer.pyセクション参照）

---

### ステップ4: 中央サーバーに送信

**概要:**
HTTP POSTリクエストで中央サーバー（Flask Backend）にJSON形式のデータを送信します。

**実装箇所:** `plc-dashboard/raspi_agent/db_utils.py:174`

**HTTP リクエスト例:**
```http
POST http://192.168.1.10:5000/api/logs HTTP/1.1
Content-Type: application/json
User-Agent: RaspberryPi-Agent/1.0

{
  "equipment_id": "PLC_001",
  "timestamp": "2025-10-31T10:30:00Z",
  "temperature": 25.5,
  "pressure": 101.3,
  "production_count": 1250,
  "current": 15,
  "cycle_time": 30.2,
  "error_code": null
}
```

**ネットワーク要件:**
- **プロトコル:** HTTP/1.1
- **ポート:** 5000（デフォルト）
- **タイムアウト:** 5秒
- **リトライ戦略:** 失敗時はローカルバッファに残し、60秒後に再送信

**セキュリティ考慮:**
- **イントラネット専用:** 工場内LAN（例: 192.168.1.0/24）でのみ使用
- **認証:** 現在は未実装（将来的にAPI KeyまたはJWT認証を追加予定）

---

### ステップ5: Flask Backendでデータ受信・検証

**概要:**
中央サーバーのFlask Backendが、Raspberry Piから送信されたデータを受信し、検証してからデータベースに保存します。

**実装箇所:** `plc-dashboard/backend/api/routes.py:467-550`

```python
@app.route("/api/logs", methods=["POST"])
def save_log_data():
    """ログデータをDBに保存 + WebSocketでリアルタイム配信"""
    data = request.get_json()

    # 1. 必須フィールド検証
    equipment_id = data.get("equipment_id")
    if not equipment_id:
        return jsonify({"error": "equipment_id is required"}), 400

    # 2. 設備の存在確認
    equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
    if not equipment:
        return jsonify({"error": "Equipment not found"}), 404

    # 3. タイムスタンプの処理
    timestamp = data.get("timestamp")
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    elif timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # 4. DB保存（次のステップで詳細説明）
    # ...
```

**検証項目:**

| 項目 | 検証内容 | エラー時の動作 |
|------|---------|--------------|
| JSONフォーマット | 有効なJSON形式か | 400 Bad Request |
| equipment_id | 必須フィールド | 400 Bad Request |
| 設備存在確認 | Equipmentテーブルに存在するか | 404 Not Found |
| タイムスタンプ | ISO 8601形式 | 現在時刻（UTC）をデフォルト使用 |

**タイムスタンプ正規化:**
```python
# ISO 8601文字列 → datetime オブジェクト
timestamp = datetime.fromisoformat("2025-10-31T10:30:00Z".replace('Z', '+00:00'))
# 結果: datetime(2025, 10, 31, 10, 30, 0, tzinfo=timezone.utc)
```

**ログ出力:**
```python
print(f"[PLC_DATA] PLCデータ受信: 設備ID={equipment_id}, タイムスタンプ={timestamp}")
print(f"   生産数={data.get('production_count')}, 電流={data.get('current')}A, 温度={data.get('temperature')}℃")
```

---

### ステップ6: PostgreSQLに保存

**概要:**
検証済みのデータをPostgreSQLデータベースの`logs`テーブルに保存します。

**実装箇所:** `plc-dashboard/backend/api/routes.py:497-509`

```python
# ログエントリー作成
log_entry = Log()
log_entry.equipment_id = equipment.id  # 外部キー
log_entry.timestamp = timestamp
log_entry.production_count = data.get("production_count")
log_entry.current = data.get("current")
log_entry.temperature = data.get("temperature")
log_entry.pressure = data.get("pressure")
log_entry.cycle_time = data.get("cycle_time")
log_entry.error_code = data.get("error_code")

# DB保存
db.session.add(log_entry)
db.session.commit()
```

**データベーススキーマ:**
```sql
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    production_count INTEGER,
    current DECIMAL(10, 2),
    temperature DECIMAL(10, 2),
    pressure DECIMAL(10, 2),
    cycle_time DECIMAL(10, 2),
    error_code VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_equipment_timestamp (equipment_id, timestamp DESC)
);
```

**パフォーマンス最適化:**
- **インデックス:** `(equipment_id, timestamp DESC)` で高速クエリ
- **パーティショニング:** 将来的に日付ベースのパーティショニングを検討
- **アーカイブ:** 古いデータは`logs_hourly`、`logs_daily`に集約

**関連ドキュメント:**
- `plc-dashboard/_docs/architecture/database.md` - データベース設計詳細
- `plc-dashboard/_docs/decisions/data-archiving-strategy.md` - 階層化アーカイブ戦略
- `plc-dashboard/_docs/decisions/query-optimization.md` - クエリ最適化戦略

---

### ステップ7: WebSocketでリアルタイム配信

**概要:**
データベース保存後、Socket.IOを使用してWebSocket経由で接続中のすべてのクライアントにリアルタイムでデータを配信します。

**実装箇所:** `plc-dashboard/backend/api/routes.py:529-544`

```python
# WebSocketで全クライアントに配信
socketio.emit('plc_data_update', {
    'equipment_id': equipment_id,
    'timestamp': timestamp.isoformat(),
    'production_count': data.get('production_count'),
    'current': data.get('current'),
    'temperature': data.get('temperature'),
    'pressure': data.get('pressure'),
    'cycle_time': data.get('cycle_time'),
    'error_code': data.get('error_code')
}, room='monitoring')

# 特定設備のクライアントにも配信
socketio.emit('equipment_data_update', {
    'equipment_id': equipment_id,
    'timestamp': timestamp.isoformat(),
    'production_count': data.get('production_count'),
    'current': data.get('current'),
    'temperature': data.get('temperature'),
    'pressure': data.get('pressure'),
    'cycle_time': data.get('cycle_time'),
    'error_code': data.get('error_code')
}, room=f'equipment_{equipment_id}')
```

**ルーム設計:**

| ルーム名 | 用途 | 配信対象 |
|---------|------|---------|
| `monitoring` | 全設備のモニタリング | すべてのモニタリングクライアント |
| `equipment_{equipment_id}` | 特定設備のモニタリング | 該当設備のモニタリングページを開いているクライアント |

**Socket.IO設定:**
```python
# backend/app.py
socketio.init_app(
    app,
    async_mode='threading',  # 必須: Greenletエラー回避
    cors_allowed_origins=["http://localhost:3000"],
    ping_timeout=60,
    ping_interval=25
)
```

**イベント一覧:**

| イベント名 | 方向 | 説明 |
|----------|------|------|
| `connect` | Client → Server | WebSocket接続確立 |
| `join_monitoring` | Client → Server | モニタリングルーム参加 |
| `plc_data_update` | Server → Client | 全設備のデータ更新通知 |
| `equipment_data_update` | Server → Client | 特定設備のデータ更新通知 |

**関連ドキュメント:**
- `plc-dashboard/_docs/architecture/realtime-communication.md` - リアルタイム通信実装詳細
- `plc-dashboard/_docs/decisions/socketio-threading-mode.md` - Socket.IO threading mode選択理由

---

### ステップ8: Nuxt UIでデータ受信→Chart.jsでグラフ描画

**概要:**
ブラウザ上のNuxt.jsアプリケーションがSocket.IOクライアントでWebSocketイベントを受信し、Chart.jsでリアルタイムグラフを描画します。

**実装箇所:**
- `plc-dashboard/pages/monitoring/[id].vue:1-150`
- `plc-dashboard/composables/useRealtimeMonitoring.ts`
- `plc-dashboard/composables/useChartManagement.ts`

#### 8-1. Socket.IO接続確立

```javascript
// pages/monitoring/[id].vue
const { $socket } = useNuxtApp()

// WebSocket接続（自動）
// nuxt.config.ts で設定済み: http://localhost:5000
```

#### 8-2. モニタリングルーム参加

```javascript
$socket.on('connect', () => {
  console.log('✅ WebSocket接続確立')
  $socket.emit('join_monitoring', { equipment_id: equipmentId })
})
```

#### 8-3. データ受信イベント処理

```javascript
// composables/useRealtimeMonitoring.ts
$socket.on('equipment_data_update', (update) => {
  console.log('📊 データ更新:', update)

  // データ更新ハンドラを呼び出し
  if (options.onDataUpdate) {
    options.onDataUpdate(update)
  }
})
```

#### 8-4. グラフデータ更新

```javascript
// pages/monitoring/[id].vue
function handleDataUpdate(update) {
  // 各チャートのデータ配列に追加
  chartManagement.updateChartData('temperatureChart', {
    x: new Date(update.timestamp),
    y: update.temperature
  })

  chartManagement.updateChartData('currentChart', {
    x: new Date(update.timestamp),
    y: update.current
  })

  // Chart.jsインスタンスを更新
  chartManagement.refreshCharts()
}
```

#### 8-5. Chart.js描画

```javascript
// composables/useChartManagement.ts
function refreshCharts() {
  chartInstances.value.forEach((chartInstance) => {
    if (chartInstance) {
      chartInstance.update('none')  // アニメーションなしで更新
    }
  })
}
```

**Chart.js設定例:**
```javascript
{
  type: 'line',
  data: {
    datasets: [{
      label: '温度 (℃)',
      data: [],  // リアルタイムで追加
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: 'time',
        time: {
          displayFormats: { second: 'HH:mm:ss' }
        }
      }
    },
    animation: false  // パフォーマンス向上のためアニメーション無効
  }
}
```

**パフォーマンス最適化:**
1. **アニメーション無効:** `animation: false` でCPU負荷を削減
2. **データポイント制限:** 直近100-200ポイントのみ保持
3. **部分更新:** カード全体ではなく、canvasのみ更新

**関連ドキュメント:**
- `plc-dashboard/_docs/architecture/frontend.md` - フロントエンドアーキテクチャ詳細

---

## 3. タイミング図（時系列）

以下は、PLCデータが1サイクル（5秒間隔）で流れる際の時系列を示します。

```
時刻: 00:00:00
  [Raspberry Pi] PLC接続開始
  [PLC]          データ読み取りリクエスト受信

時刻: 00:00:00.1
  [PLC]          レジスタデータを返送（D100-D201）

時刻: 00:00:00.2
  [Raspberry Pi] データ解析完了（Big-Endian → float/int）
  [Raspberry Pi] JSON形式に変換
  [Raspberry Pi] ローカルSQLiteバッファに保存

時刻: 00:00:00.3
  [Raspberry Pi] HTTP POST送信開始

時刻: 00:00:00.4
  [Flask Backend] HTTPリクエスト受信
  [Flask Backend] JSON検証 & 設備確認

時刻: 00:00:00.5
  [Flask Backend] PostgreSQL INSERT実行

時刻: 00:00:00.6
  [PostgreSQL]   トランザクションコミット完了

時刻: 00:00:00.7
  [Flask Backend] Socket.IO emit実行
  [Flask Backend] → 'plc_data_update' を全クライアントに配信
  [Flask Backend] → 'equipment_data_update' を該当クライアントに配信

時刻: 00:00:00.8
  [Nuxt UI]      WebSocketイベント受信
  [Nuxt UI]      useRealtimeMonitoring で処理
  [Nuxt UI]      chartData配列に追加

時刻: 00:00:00.9
  [Nuxt UI]      Chart.js.update() 実行
  [ブラウザ]      canvas再描画（グラフ更新）

時刻: 00:05:00
  [Raspberry Pi] 次のサイクル開始（5秒間隔）
```

**レイテンシ:**
- **PLC読み取り:** 0.1-0.3秒
- **HTTP送信:** 0.1-0.2秒
- **DB保存:** 0.1-0.2秒
- **WebSocket配信:** 0.1-0.2秒
- **UI更新:** 0.1秒
- **合計:** 約0.5-1秒（理想的な環境）

---

## 4. データ形式の変化

データがPLCからブラウザまで流れる過程で、形式がどのように変化するかを示します。

### 4-1. PLC内部（バイナリ）

```
D100-D101 (4バイト): 0x41CC0000 → 25.5 (float32, Big-Endian)
D102-D103 (4バイト): 0x42CA6666 → 101.3 (float32, Big-Endian)
D200 (2バイト):      0x04E2      → 1250 (int16)
D201 (2バイト):      0x000F      → 15 (int16)
```

### 4-2. Raspberry Pi（Pythonオブジェクト）

```python
{
    "temperature": 25.5,      # float
    "pressure": 101.3,        # float
    "production_count": 1250, # int
    "current": 15             # int
}
```

### 4-3. HTTP送信（JSON文字列）

```json
{
  "equipment_id": "PLC_001",
  "timestamp": "2025-10-31T10:30:00Z",
  "temperature": 25.5,
  "pressure": 101.3,
  "production_count": 1250,
  "current": 15
}
```

### 4-4. PostgreSQL（リレーショナルテーブル）

```sql
| id   | equipment_id | timestamp           | temperature | pressure | production_count | current |
|------|--------------|---------------------|-------------|----------|------------------|---------|
| 1234 | 1            | 2025-10-31 10:30:00 | 25.50       | 101.30   | 1250             | 15.00   |
```

### 4-5. WebSocket配信（JSON）

```json
{
  "equipment_id": "PLC_001",
  "timestamp": "2025-10-31T10:30:00Z",
  "temperature": 25.5,
  "pressure": 101.3,
  "production_count": 1250,
  "current": 15
}
```

### 4-6. Chart.js（JavaScriptオブジェクト）

```javascript
{
  x: new Date("2025-10-31T10:30:00Z"),  // Date オブジェクト
  y: 25.5                                 // number
}
```

---

## 5. エラーハンドリング

各ステップでのエラー処理戦略を示します。

### 5-1. PLC接続エラー

**症状:** PLC応答なし、ネットワーク障害

**対策:**
```python
# タイムアウト設定（必須）
plc.connect(ip, port, timeout=5.0)

# フォールバック: ダミーデータ返送
if USE_DUMMY_PLC:
    return generate_dummy_data(data_points)
```

### 5-2. HTTP送信失敗

**症状:** 中央サーバーがダウン、ネットワーク障害

**対策:**
```python
# ローカルバッファに保存
record_id = self.buffer.save(equipment_id, payload)

# 60秒後に自動リトライ
retry_counter += interval / 1000.0
if retry_counter >= retry_interval:
    success, failure, total = db_api.retry_pending_data(batch_size=100)
```

### 5-3. DB保存エラー

**症状:** PostgreSQL接続エラー、ディスク容量不足

**対策:**
```python
try:
    db.session.add(log_entry)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    logger.error(f"DB保存エラー: {e}")
    return jsonify({"error": str(e)}), 500
```

### 5-4. WebSocket切断

**症状:** ネットワーク不安定、サーバー再起動

**対策:**
```javascript
socket.on('disconnect', (reason) => {
  console.warn('⚠️ WebSocket切断:', reason)
  if (reason === 'io server disconnect') {
    // サーバー側から切断された場合、手動で再接続
    socket.connect()
  }
})

// 自動再接続設定
const socket = io('http://localhost:5000', {
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5
})
```

---

## 6. パフォーマンス考慮点

### 6-1. データ収集頻度

| 間隔 | 1時間あたりのデータ量 | 推奨用途 |
|------|---------------------|---------|
| 1秒 | 3,600レコード | 高精度モニタリング（短期間のみ） |
| 5秒（デフォルト） | 720レコード | 標準モニタリング |
| 10秒 | 360レコード | 低頻度モニタリング |
| 60秒 | 60レコード | 長期トレンド分析 |

### 6-2. データベース容量見積もり

**前提条件:**
- 1設備
- 5秒間隔
- 1レコード = 200バイト（平均）

**計算:**
```
1日のデータ量 = (86,400秒 / 5秒) × 200バイト ≈ 3.4MB
1ヶ月のデータ量 = 3.4MB × 30日 ≈ 102MB
1年のデータ量 = 102MB × 12ヶ月 ≈ 1.2GB
```

**10設備の場合:**
- 1年間で約12GB

**対策:**
- 古いデータのアーカイブ（`logs_hourly`、`logs_daily`に集約）
- パーティショニング（月次または年次）

### 6-3. WebSocket配信負荷

**問題:**
- 100クライアント × 5秒間隔 = 秒間20メッセージ配信

**対策:**
- ルーム機能で配信先を限定
- 不要なフィールドを削除してペイロードサイズを削減

---

## 7. 関連ドキュメント

### アーキテクチャ
- `plc-dashboard/_docs/architecture/backend.md` - バックエンド詳細
- `plc-dashboard/_docs/architecture/frontend.md` - フロントエンド詳細
- `plc-dashboard/_docs/architecture/database.md` - データベース設計詳細
- `plc-dashboard/_docs/architecture/realtime-communication.md` - リアルタイム通信詳細
- `plc-dashboard/_docs/architecture/raspi-agent.md` - Raspberry Piエージェント詳細

### 設計判断
- `plc-dashboard/_docs/decisions/socketio-threading-mode.md` - Socket.IO設定
- `plc-dashboard/_docs/decisions/equipment-identification-strategy.md` - 設備識別戦略
- `plc-dashboard/_docs/decisions/data-archiving-strategy.md` - データアーカイブ戦略
- `plc-dashboard/_docs/decisions/query-optimization.md` - クエリ最適化
- `plc-dashboard/_docs/decisions/performance-optimization.md` - パフォーマンス最適化

### PLC知見
- `plc-dashboard/_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド
- `plc-dashboard/_docs/plc-knowledge/endianness.md` - エンディアン問題
- `plc-dashboard/_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定
- `plc-dashboard/_docs/plc-knowledge/troubleshooting.md` - トラブルシューティング

### テスト
- `plc-dashboard/_docs/testing/debugging-guide.md` - テスト・デバッグガイド

---

**最終更新:** 2025-10-31
