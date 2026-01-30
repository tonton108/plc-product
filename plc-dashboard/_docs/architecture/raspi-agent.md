# Raspberry Piエージェントアーキテクチャ

**作成日:** 2025-10-24

## 技術スタック

- **Webフレームワーク:** Flask + Flask-SocketIO（WebUI用）
- **PLC通信ライブラリ:**
  - `pymcprotocol` - 三菱電機（MC Protocol）
  - `fins` - オムロン（FINS）
  - `pymodbus` - キーエンス（Modbus TCP）
- **マルチスレッド:** PLCエージェントはバックグラウンドスレッドで動作

## 主要ファイル

### `plc-dashboard/raspi_agent/agent_app.py`

**役割:** Flaskアプリケーション本体

**機能:**
- 初期設定画面（設備ID、PLCメーカー、IP等の登録）
- モニタリング画面（リアルタイムデータ表示）
- 認証機能による保護
- PLCエージェントのライフサイクル管理（起動・停止・再起動）

**重要な動作:**
1. CPUシリアル番号で設備を自動識別
2. 設定済み → モニタリング画面へ遷移
3. 未設定 → 初期設定画面へ遷移

### `plc-dashboard/raspi_agent/plc_agent.py`

**役割:** PLCデータ収集エージェント

**対応メーカー:**
- 三菱電機（MC Protocol）
- オムロン（FINS）
- キーエンス（Modbus TCP）
- シーメンス（未実装）

**重要な関数:**

#### `read_from_plc(config)`

設定に基づいてPLCからデータを読み取ります。実PLC接続失敗時は自動的にダミーモードにフォールバック。

#### `auto_identify_equipment()`

CPUシリアル番号で設備を自動識別します。

#### `main_loop()`

設定された間隔でデータを取得し、中央サーバーに送信します。

**データ型サポート:**

| 型 | サイズ | 説明 |
|----|-------|------|
| `word` | 16bit | 整数（0-65535） |
| `dword` | 32bit | 整数（Big-Endian） |
| `float32` | 32bit | IEEE754浮動小数点（Big-Endian） |
| `bit` | 1bit | ビット値（0/1） |

詳細は `plc-dashboard/_docs/plc-knowledge/protocols.md` を参照。

### `plc-dashboard/raspi_agent/db_utils.py`

**役割:** 設定管理とデータベースAPI

**主要クラス:**

#### ConfigManager

ローカル設定管理（DB優先、`plc_config.json`フォールバック）

#### DatabaseAPI

中央サーバーとのHTTP通信 + ローカルバッファリング

**重要な機能:**
- `send_log_data()` - データ送信（失敗時は自動的にローカルバッファに保存）
- `retry_pending_data()` - 未送信データを一括再送信
- `cleanup_buffer()` - 古いバッファデータを削除
- `get_buffer_stats()` - バッファ統計表示

### `plc-dashboard/raspi_agent/local_buffer.py`

**役割:** ローカルバッファ管理（2025-01追加）

中央サーバーへの送信に失敗したPLCデータをSQLiteで一時保存し、サーバー復旧時に自動再送します。

**ユースケース:**
- 中央サーバーの計画的シャットダウン時のデータ保全
- ネットワーク障害時のデータロス防止
- 一時的なサーバーメンテナンス時の継続運用

**動作フロー:**
```
[PLCデータ取得]
    ↓
[ローカルバッファに保存] ← 必ず保存（データロス防止）
    ↓
[中央サーバーに送信]
    ├─ 成功 → バッファから削除
    └─ 失敗 → バッファに残す（後で再送）
         ↓
    [60秒ごとに自動再送]
         ↓
    [1時間ごとにクリーンアップ]
```

**設定パラメータ:**
- `retry_interval`: 60秒（未送信データの再送信間隔）
- `cleanup_interval`: 3600秒（クリーンアップ間隔）
- `max_retry`: 10回（最大再試行回数）
- `retention_days`: 7日（データ保存期間）

※ ローカルバッファリング機能の詳細は上記セクションに記載。

### `plc-dashboard/raspi_agent/plc_drivers/`

**役割:** PLC通信ドライバー

**ファイル構成:**
- `keyence_driver.py` - キーエンス（Modbus TCP）
- `omron_driver.py` - オムロン（FINS）
- `mitsubishi_driver.py` - 三菱電機（MC Protocol）

詳細は `plc-dashboard/_docs/plc-knowledge/protocols.md` を参照。

## 起動方法

### ローカル開発（ダミーPLCモード）

```bash
cd plc-dashboard/raspi_agent
export USE_DUMMY_PLC=true
python agent_app.py
```

**ポート:** 8080（デフォルト）

### 実機PLC接続モード

```bash
export USE_DUMMY_PLC=false
export PLC_IP=192.168.0.10
python agent_app.py
```

### systemdサービス化

```bash
sudo cp plc_ui.service /etc/systemd/system/
sudo systemctl enable plc_ui.service
sudo systemctl start plc_ui.service
```

詳細は `plc-dashboard/_docs/deployment/raspi-deployment.md` を参照。

## 環境変数

`.env`ファイルで設定：

```bash
# PLC設定
USE_DUMMY_PLC=false
PLC_IP=192.168.0.10
PLC_PORT=5000
PLC_MANUFACTURER=Mitsubishi
LOG_INTERVAL_MS=5000

# 中央サーバー設定
CENTRAL_SERVER_IP=192.168.1.10
CENTRAL_SERVER_PORT=5000
```

詳細は `plc-dashboard/_docs/deployment/environment-variables.md` を参照。

## 関連ドキュメント

- `plc-dashboard/_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド
- `plc-dashboard/_docs/plc-knowledge/troubleshooting.md` - トラブルシューティング
- `plc-dashboard/_docs/deployment/raspi-deployment.md` - ラズパイデプロイ手順
- `plc-dashboard/_docs/deployment/environment-variables.md` - 環境変数設定

---

**最終更新:** 2026-01-19
