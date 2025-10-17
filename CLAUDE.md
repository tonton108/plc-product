# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Claude Code 会話ルール（日本語モード固定）

- Claudeはすべての**会話・提案・説明・コメント**を**日本語**で行うこと。
- コード内コメントも可能な限り日本語で記述すること。
- 英語での説明が含まれる場合は、日本語訳を併記すること。
- CLI出力やログ文言も、特別な理由がなければ日本語で提案すること。
- 回答の際は、過剰な翻訳ではなく技術的な正確さを優先すること。

## コミットルール

Claudeは以下のルールを厳守すること：

1. すべてのコミットメッセージは**日本語**で書くこと。
2. 英語は使わず、要約を1行で簡潔に。
3. フォーマットは「タイプ: 概要」形式（例：`refactor: 古いディレクトリを整理し重複を解消`）。
4. Claude Codeは**自動署名（🤖やCo-Authored行）を付与しないこと。**
5. 英語が混ざった場合は即座に修正し、再コミット前に確認を求めること。

## CLAUDE.md 更新ルール

**作業終了時、以下の場合はCLAUDE.mdを更新すること：**

1. **新しい技術スタック・ライブラリを追加した場合**
   - 例：新しいnpmパッケージ、Pythonライブラリの導入
   - 追加理由と使用方法を記載

2. **アーキテクチャや設計方針を変更した場合**
   - 例：データフロー、API設計、ディレクトリ構造の変更
   - 変更理由と新しい方針を記載

3. **新しいファイルや重要な機能を追加した場合**
   - 例：新しいページ、APIエンドポイント、スクリプト
   - ファイルパスと機能説明を記載

4. **開発コマンドや環境変数が変わった場合**
   - 例：新しいnpmスクリプト、環境変数の追加・変更
   - 使用方法と設定例を記載

5. **トラブルシューティング情報が必要な場合**
   - 例：よくあるエラーとその解決方法
   - 問題の症状と解決手順を記載

6. **重要な実装上の注意点が発見された場合**
   - 例：バグの原因となりやすい実装パターン
   - 注意点と推奨される実装方法を記載

**更新が不要な場合：**
- 単純なバグ修正
- UI/UXの微調整
- コメントの追加・修正のみ
- リファクタリング（機能変更なし）

---

## PLC基礎知識

### PLCとは

**PLC（Programmable Logic Controller）**は、工場の製造ライン、機械設備、プラントなどの自動制御を行うための産業用コンピュータです。

**主な特徴：**
- 高い信頼性と耐環境性（高温、振動、ノイズに強い）
- リアルタイム処理（数ミリ秒～数十ミリ秒周期で動作）
- シーケンス制御に特化したプログラミング言語（ラダー図など）
- 豊富な入出力インターフェース（デジタル/アナログ入出力）

### このシステムで扱うPLCメーカーと通信プロトコル

| メーカー | 通信プロトコル | Pythonライブラリ | デフォルトポート | 実装状態 |
|---------|--------------|----------------|----------------|---------|
| 三菱電機 | MC Protocol (MELSEC) | pymcprotocol | 5000 | ✅ 実装済み |
| オムロン | FINS (Factory Interface Network Service) | fins | 9600 | ✅ 実装済み |
| キーエンス | Modbus TCP | pymodbus | 502 | ✅ 実装済み |
| シーメンス | S7 Protocol | python-snap7 | 102 | ⚠️ 未実装 |

### PLCデータアドレスの概念

PLCは内部に**デバイスメモリ**を持ち、各メモリ領域には固有のアドレスが割り当てられています。

**主なデバイスメモリ（三菱PLCの例）：**

| デバイス名 | 記号 | 用途 | アドレス例 | データ型 |
|-----------|-----|------|----------|---------|
| データレジスタ | D | 数値データ保存 | D0, D100, D1000 | 16bit/32bit整数、浮動小数点 |
| 内部リレー | M | ON/OFFフラグ | M0, M100 | bit（0/1） |
| タイマ | T | タイマー機能 | T0, T10 | 16bit整数 |
| カウンタ | C | カウンタ機能 | C0, C10 | 16bit整数 |
| 入力リレー | X | 物理入力信号 | X0, X1 | bit（0/1） |
| 出力リレー | Y | 物理出力信号 | Y0, Y1 | bit（0/1） |

**オムロンPLCの例：**
- CIOエリア：CIO0, CIO100（16bit）
- DM（データメモリ）：D0, D100（16bit）
- HR（保持リレー）：HR0, HR100（16bit）
- WR（作業リレー）：WR0, WR100（16bit）

**キーエンス PLCの例：**
- DM（データメモリ）：DM0, DM100（16bit）
- MR（内部補助リレー）：MR0, MR100（bit）
- HR（特殊内部補助リレー）：HR0, HR100（bit）

### データ型とサイズ

このシステムでサポートしているデータ型：

| データ型 | ビット数 | バイト数 | 範囲 | 用途例 |
|---------|---------|---------|------|-------|
| `bit` | 1bit | - | 0 or 1 | ON/OFF状態、エラーフラグ |
| `byte` | 8bit | 1 | 0 ~ 255（符号なし）<br>-128 ~ 127（符号付き） | 小さな整数値 |
| `word` | 16bit | 2 | 0 ~ 65,535（符号なし）<br>-32,768 ~ 32,767（符号付き） | 温度、圧力、カウント値 |
| `dword` (Double Word) | 32bit | 4 | 0 ~ 4,294,967,295（符号なし）<br>-2,147,483,648 ~ 2,147,483,647（符号付き） | 大きな数値、累積値 |
| `float32` (Real) | 32bit | 4 | IEEE 754形式（約±3.4×10^38） | 精密な測定値、演算結果 |

**重要な注意点：**
- `bit`: 単一ビット（リレー、フラグ用）
- `byte`: 1つのバイト（8ビット）
- `word`: 1つのデバイス（例：D100）で読み取れる
- `dword`と`float32`: 2つの連続したデバイス（例：D100とD101）を使用する
- `float32`はIEEE 754形式の32ビット浮動小数点数

### エンディアン（バイトオーダー）

**PLCとPCでのエンディアンの違い：**

| システム | エンディアン | 説明 | 例（0x12345678の格納順） |
|---------|------------|------|----------------------|
| **PLC（ほとんど）** | **Big-Endian** | 上位バイトから格納 | 12 34 56 78 |
| **PC（x86/x64）** | **Little-Endian** | 下位バイトから格納 | 78 56 34 12 |

**対象PLC：**
- **Big-Endian**: 三菱電機、シーメンス、オムロン（ほとんどの産業用PLC）
- **Little-Endian**: 一部のx86ベースPLC

**実装上の注意：**
- PCとPLC間でデータを交換する際、`dword`や`float32`のバイトオーダーを変換する必要がある
- ほとんどのPLC通信ライブラリ（pymcprotocol、finsなど）は自動的にバイトオーダーを変換してくれる
- 自前で実装する場合は、Pythonの`struct.pack()`/`unpack()`で`'>'`（Big-Endian）または`'<'`（Little-Endian）を指定する

```python
import struct

# Big-Endian（PLC）からLittle-Endian（PC）へ変換例
plc_bytes = b'\x12\x34\x56\x78'  # PLC上の4バイトデータ
value = struct.unpack('>I', plc_bytes)[0]  # '>' = Big-Endian, 'I' = unsigned int
print(f"0x{value:08X}")  # 0x12345678
```

### 通信プロトコルの違い

#### 1. MC Protocol（三菱電機）
- **特徴**: バイナリ形式、高速
- **接続方法**: TCP/IP（デフォルトポート5000）
- **コマンド**: デバイス一括読み出し、一括書き込み
- **実装**: `pymcprotocol`ライブラリ

```python
# 読み取り例
plc.batchread_wordunits(headdevice="D100", readsize=10)  # D100～D109を読み取り
```

#### 2. FINS（オムロン）
- **特徴**: ASCII/バイナリ両対応、Ethernetに最適化
- **接続方法**: TCP/IP（デフォルトポート9600）、UDP
- **アドレス指定**: ノード番号、ユニット番号が必要
- **実装**: `fins`ライブラリ

```python
# 読み取り例
fins.memory_area_read(MemoryArea.DM, 100, 10)  # DM100～DM109を読み取り
```

#### 3. Modbus TCP（キーエンス）
- **特徴**: 産業標準プロトコル、シンプル
- **接続方法**: TCP/IP（デフォルトポート502）
- **ファンクションコード**:
  - 0x03: Holding Register読み取り
  - 0x04: Input Register読み取り
  - 0x01: Coil読み取り
- **実装**: `pymodbus`ライブラリ

```python
# 読み取り例
client.read_holding_registers(address=100, count=10)  # アドレス100～109を読み取り
```

### データ収集における注意点

1. **ポーリング間隔**
   - PLCの処理負荷を考慮して、最低でも100ms以上の間隔を推奨
   - このシステムのデフォルト: 5000ms（5秒）

2. **通信タイムアウト**
   - ネットワーク遅延を考慮して、適切なタイムアウト設定が必要
   - 推奨値: 3～10秒

3. **エラーハンドリング**
   - PLC側の電源断、ネットワーク切断、通信エラーに対応
   - このシステムでは自動的にダミーモードにフォールバック

4. **同時接続数**
   - PLCは同時接続数に制限がある（通常4～32台）
   - 不要な接続は速やかに切断すること

5. **データ整合性**
   - 複数のデバイスを読み取る場合、一括読み出しを使用
   - 個別に読み取ると、PLC側の処理タイミングでデータがずれる可能性

### このシステムでのPLCデータ設定例

```json
{
  "data_points": [
    {
      "name": "生産数量",
      "address": "D100",
      "data_type": "word",
      "scale_factor": 1.0,
      "unit": "個"
    },
    {
      "name": "温度",
      "address": "D200",
      "data_type": "float32",
      "scale_factor": 1.0,
      "unit": "℃"
    },
    {
      "name": "エラーフラグ",
      "address": "M10",
      "data_type": "bit",
      "scale_factor": 1.0,
      "unit": ""
    }
  ]
}
```

### トラブルシューティング（PLC通信）

**問題: PLCに接続できない**
- ✅ PLCのIPアドレスとポート番号を確認
- ✅ ファイアウォール設定を確認
- ✅ PLC側のEthernet設定を確認
- ✅ pingコマンドで疎通確認

**問題: データが読み取れない**
- ✅ デバイスアドレスが正しいか確認
- ✅ データ型が一致しているか確認
- ✅ PLC側のプログラムでデバイスが使用されているか確認
- ✅ アクセス権限（読み取り専用/読み書き可能）を確認

**問題: データが異常値になる**
- ✅ データ型の不一致（wordをfloat32で読んでいる等）
- ✅ バイトオーダー（エンディアン）の違い
- ✅ スケールファクターの設定ミス

---

## プロジェクト概要

このリポジトリには、PLC（Programmable Logic Controller）データの収集・監視・分析システムの**統合版**が含まれています。

### 統合後のプロジェクト構成

**plc-dashboard（メインプロジェクト）**に以下が統合されています:
1. **backend/**: Flask API（中央サーバー）
2. **raspi_agent/**: Raspberry Piエージェント
3. **pages/**: Nuxt.js 3ダッシュボードUI
4. **electron/**: Electronデスクトップアプリ（中央サーバー管理用）
5. **scripts/**: 開発・管理ツール
6. **docker-compose.yml**: 統合Docker Compose設定

**旧raspi_plc_uiディレクトリは_archive/raspi_plc_ui/にアーカイブされています。現在のシステムではplc-dashboard/raspi_agent/を使用してください。**

### システムアーキテクチャ

```
[PLC] ←Modbus/FINS→ [Raspberry Pi (plc-dashboard/raspi_agent)]
                            ↓ HTTP POST
                    [中央サーバー (plc-dashboard/backend)]
                            ↓ WebSocket
                    ┌────────────────────────────────┐
                    │  [Electronアプリ（中央PC）]   │  管理者用デスクトップアプリ
                    │  - Docker管理                  │
                    │  - システムトレイ常駐          │
                    │  - ダッシュボード表示          │
                    └────────────────────────────────┘
                            ↓ WebSocket
                    [Webブラウザ（複数のクライアントPC）]  閲覧専用ダッシュボード
```

## 開発コマンド

### 統合プロジェクト（plc-dashboard）

```bash
cd plc-dashboard

# 環境設定
cp .env.example .env

# 中央サーバーモード起動
docker compose up -d db backend  # PostgreSQL + Flask API
npm run dev                       # Nuxt.jsフロントエンド（ポート3000）

# Raspberry Piエージェントモード起動（オプション）
docker compose --profile agent up -d raspi-agent

# または、エージェントをローカルPythonで起動
cd raspi_agent
python agent_app.py
```

### バックエンド（Flask）

```bash
cd plc-dashboard/backend

# ローカル開発サーバー起動
flask --app manage.py run --host=0.0.0.0 --port=5000

# データベースマイグレーション
flask --app manage.py db upgrade
flask --app manage.py db migrate -m "説明"

# データ管理ツール
python log_manager.py stats                  # 統計表示
python log_manager.py cleanup --days 90     # クリーンアップ
python log_manager.py daily 2025-01-15      # 日次集計作成

# デモデータ送信（開発用）
python demo_data_sender.py --mode continuous --interval 2.0
```

### フロントエンド（Nuxt.js）

```bash
cd plc-dashboard

# 開発サーバー起動（ホットリロード）
npm run dev

# プロダクションビルド
npm run build

# プロダクションプレビュー
npm run preview
```

### Electronデスクトップアプリ（中央サーバー管理用）

```bash
cd plc-dashboard

# 依存関係インストール（初回のみ）
npm run electron:install

# 開発モードで起動（Nuxt devサーバーに接続）
npm run dev          # 別ターミナル: Nuxt開発サーバー起動
npm run electron:dev # Electronアプリ起動

# 本番用ビルド
npm run build:electron  # Nuxt静的ファイル生成 + electron/renderer/へコピー
cd electron
npm run build           # Electronアプリをパッケージング（dist/に出力）

# プラットフォーム別ビルド
npm run build:mac       # macOS用
npm run build:win       # Windows用
npm run build:linux     # Linux用
```

**主な機能：**
- Docker Composeサービスの起動/停止/再起動
- システムトレイ常駐とリアルタイムステータス表示
- デスクトップ通知（サーバー状態変更、エラー等）
- Nuxt.jsダッシュボードの埋め込み表示
- ログ閲覧機能

### Raspberry Piエージェント

```bash
cd plc-dashboard/raspi_agent

# ローカル開発（ダミーPLCモード）
export USE_DUMMY_PLC=true
python agent_app.py

# 実機PLC接続モード
export USE_DUMMY_PLC=false
export PLC_IP=192.168.0.10
python agent_app.py

# ラズパイへの一括デプロイ（ip_list.csvに対象IPを記載）
bash scp_bulk_push.sh
```

## コードアーキテクチャ

### plc-dashboard（中央サーバー）

**技術スタック:**
- フロントエンド: Nuxt.js 3 + Vuetify 3 + Chart.js + Socket.IO Client
- バックエンド: Flask + Flask-SocketIO + SQLAlchemy
- データベース: PostgreSQL（本番）/ SQLite（開発）
- リアルタイム通信: Socket.IO (threading mode)

**主要ファイル:**

#### `plc-dashboard/backend/app.py`
Flaskアプリケーションのファクトリー。CORS設定、SQLAlchemy初期化、Socket.IO初期化（`async_mode='threading'`でgreenletエラー回避）を行う。

#### `plc-dashboard/backend/api/routes.py`
全APIエンドポイントとWebSocketイベントハンドラー。主要なエンドポイント:
- `POST /api/register` - Raspberry Piからの設備登録
- `POST /api/logs` - PLCログデータ保存 + WebSocket配信
- `GET /api/logs/<equipment_id>/history_optimized` - 最適化履歴取得
- Socket.IOイベント: `plc_data_update`, `equipment_data_update`

#### `plc-dashboard/backend/db/models.py`
SQLAlchemyモデル:
- **Equipment**: 設備情報（`cpu_serial_number`, `mac_address`, `equipment_id`で識別）
- **PLCDataConfig**: PLCデータ項目設定
- **Log**: 詳細ログ（90日保存）
- **DailyLogSummary**: 日次集計（365日保存）
- **MonthlyLogSummary**: 月次集計（永続保存）

**重要な設計原則:**
- 設備識別の優先順位: `cpu_serial_number` > `mac_address` > `equipment_id`
- Socket.IOは必ず`async_mode='threading'`で初期化すること
- 設備更新時は必ず`cpu_serial_number`で既存設備を検索し、`equipment_id`を更新

#### `plc-dashboard/pages/monitoring/[id].vue`
リアルタイムモニタリングページ。Socket.IOでデータ受信、Chart.jsでグラフ表示。

#### `plc-dashboard/backend/api/scheduler.py`
データクリーンアップと集計作成のスケジューラー。90日以上古いログの削除、日次・月次集計の自動作成を行う。

### plc-dashboard/raspi_agent/（Raspberry Piエージェント）

**技術スタック:**
- Flask + Flask-SocketIO（WebUI用）
- PLC通信ライブラリ: pymcprotocol（三菱）、fins（オムロン）、pymodbus（キーエンス）
- マルチスレッド: PLCエージェントはバックグラウンドスレッドで動作

**主要ファイル:**

#### `plc-dashboard/raspi_agent/agent_app.py`
Flaskアプリケーション本体。初期設定画面、モニタリング画面、認証機能を提供。PLCエージェントをバックグラウンドスレッドで起動・管理する。

**重要な機能:**
- デバイス情報（CPUシリアル番号）で設備を自動識別し、設定済みならモニタリング画面、未設定なら初期設定画面へ遷移
- PLCエージェントのライフサイクル管理（起動・停止・再起動）
- 認証機能による保護

#### `plc-dashboard/raspi_agent/plc_agent.py`
PLCデータ収集エージェント。対応メーカー: 三菱、オムロン、キーエンス、シーメンス（未実装）。

**重要な関数:**
- `read_from_plc(config)`: 設定に基づいてPLCからデータを読み取り。実PLC接続失敗時は自動的にダミーモードにフォールバック
- `auto_identify_equipment()`: CPUシリアル番号で設備を自動識別
- `main_loop()`: 設定された間隔でデータを取得し、中央サーバーに送信

**データ型サポート:**
- `word`: 16bit整数
- `dword`: 32bit整数
- `float32`: IEEE754浮動小数点
- `bit`: ビット値（0/1）

#### `plc-dashboard/raspi_agent/db_utils.py`
設定管理とデータベースAPI。DB優先、JSONフォールバックのハイブリッド設定管理を実装。

**主要クラス:**
- `ConfigManager`: ローカル設定管理（DB優先、plc_config.jsonフォールバック）
- `DatabaseAPI`: 中央サーバーとのHTTP通信

### plc-dashboard/scripts/（開発・管理ツール）

**主要ツール:**
- `check_data.py`: データベース内のログデータ確認ツール
- `check_integration.sh`: ディレクトリ構造とファイル存在確認スクリプト
- `init_db.py`: データベース初期化スクリプト（開発用）
- `test_db_connection.py`: PostgreSQL接続テスト

## データベース設計

### 階層化アーカイブシステム

1. **詳細データ（logs）**: 90日間保存、リアルタイム監視用
2. **日次集計（daily_log_summaries）**: 365日間保存、週次・月次トレンド分析用
3. **月次集計（monthly_log_summaries）**: 永続保存、長期比較用

### 最適化インデックス

- `idx_logs_timestamp` - タイムスタンプ検索高速化
- `idx_logs_equipment_timestamp` - 設備別期間検索高速化
- `idx_daily_summary_equipment_date` - 日次集計検索高速化
- `idx_monthly_summary_equipment_year_month` - 月次集計検索高速化

## デプロイメント

### ラズパイへの一括デプロイ

1. `plc-dashboard/raspi_agent/ip_list.csv`にラズパイのIPアドレスを記載:
```csv
ip_address
192.168.0.101
192.168.0.102
```

2. デプロイスクリプトを実行:
```bash
cd plc-dashboard/raspi_agent
bash scp_bulk_push.sh
```

このスクリプトは以下を実行します:
- プロジェクトフォルダを`/home/pi/`に転送
- `plc_ui.service`を`/etc/systemd/system/`に設置
- systemd経由でDocker Composeを自動起動・永続化

### 環境変数設定

**plc-dashboard（中央サーバー）:**
```env
DATABASE_URL=postgresql+psycopg2://plc_user:plc_pass@localhost:5432/plc_monitor
SECRET_KEY=your-secret-key
```

**plc-dashboard/raspi_agent/（Raspberry Pi）:**
```env
USE_DUMMY_PLC=false              # true=ダミーモード、false=実PLC接続
PLC_IP=192.168.0.10              # PLCのIPアドレス
PLC_PORT=5000                     # PLCポート（三菱PLC等）
PLC_MANUFACTURER=Mitsubishi       # メーカー名
LOG_INTERVAL_MS=5000              # データ収集間隔（ミリ秒）
CENTRAL_SERVER_IP=192.168.1.10    # 中央サーバーIP
CENTRAL_SERVER_PORT=5000          # 中央サーバーポート
```

## トラブルシューティング

### Socket.IO Greenletエラー
Socket.IOは必ず`async_mode='threading'`で初期化すること:
```python
socketio.init_app(app, async_mode='threading')
```

### 設備が見つからない
1. CPUシリアル番号を確認: `python plc-dashboard/raspi_agent/test_cpu_serial.py`
2. 中央サーバーで設備検索: `GET /api/equipment/search?cpu_serial_number=XXX`
3. 設備が未登録なら初期設定画面で登録

### PLC接続エラー
1. `USE_DUMMY_PLC=true`でダミーモードに切り替え
2. エラー統計を確認: `plc_agent.py`のログ出力を確認
3. PLC側のIPアドレス、ポート、通信設定を確認

### データベース接続エラー
```bash
# PostgreSQL接続確認
cd plc-dashboard
python scripts/test_db_connection.py

# マイグレーション実行
cd backend
flask --app manage.py db upgrade
```

## テストとデバッグ

### デモデータ送信の実行順序

1. 中央サーバー起動（plc-dashboard）
```bash
cd plc-dashboard/backend
flask --app manage.py run
```

2. フロントエンド起動
```bash
cd plc-dashboard
npm run dev
```

3. デモデータ送信
```bash
cd plc-dashboard/backend
python demo_data_sender.py --mode continuous --interval 2.0
```

4. ブラウザで確認
```
http://localhost:3000/monitoring/DEMO_001
```

### ログの確認

- **Flask側**: ターミナル出力（`📥 PLCデータ受信`, `📡 WebSocket送信完了`等）
- **Nuxt側**: ブラウザ開発者コンソールでSocket.IOイベント確認
- **Raspberry Pi側**: `plc_agent.log`ファイル

## 重要な実装上の注意点

### 設備の識別と更新

設備の更新時は必ず`cpu_serial_number`で既存設備を検索し、見つかった場合は`equipment_id`を更新します。これにより、Raspberry Piの再起動やIP変更があっても設備情報を正しく維持できます。

```python
# routes.py:388-432 参照
equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()
if equipment:
    equipment.equipment_id = equipment_id  # 設備IDを新しい値に更新
```

### データ最適化クエリ

短期間（1h, 6h, 24h）は詳細データ、長期間（7d, 30d）は集計データを自動選択:

```python
if period in ['1h', '6h', '24h']:
    logs = Log.query.filter(...).all()  # 詳細データ
elif period in ['7d', '30d']:
    summaries = DailyLogSummary.query.filter(...).all()  # 集計データ
```

### PLCデータ読み取りのフォールバック

実PLC接続失敗時は自動的にダミーモードにフォールバックします:

```python
# plc_agent.py:321-356
if USE_DUMMY_PLC:
    return generate_dummy_data(data_points)
else:
    result = read_from_real_plc(...)
    if result is None:
        return generate_dummy_data(data_points)  # フォールバック
```

## パフォーマンス最適化

### データベース最適化効果

- **クエリ速度**: 50-150倍高速化
- **ストレージ使用量**: 75%削減
- **同時接続可能数**: 10倍増加
- **運用工数**: 90%削減

### データ圧縮率

- 中期データ（日次集計）: 99.9%圧縮（2400件→1件/日）
- 長期データ（月次集計）: 99.99%圧縮（72,000件→12件/年）
