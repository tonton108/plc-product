# PLCプロトコル実装ガイド

**作成日:** 2025-10-24
**最終更新:** 2026-01-24

## 概要

このプロジェクトでサポートする主要PLCプロトコル（Modbus TCP、FINS、MC Protocol）の実装ノウハウを記録します。

## サポート対象メーカーとプロトコル

| メーカー | プロトコル | Pythonライブラリ | 実装ファイル |
|---------|----------|----------------|-------------|
| キーエンス | Modbus TCP | `pymodbus` | `plc-dashboard/raspi_agent/plc_drivers/keyence.py` |
| オムロン | FINS | `fins` | `plc-dashboard/raspi_agent/plc_drivers/omron.py` |
| 三菱電機 | MC Protocol | `pymcprotocol` | `plc-dashboard/raspi_agent/plc_drivers/mitsubishi.py` |
| シーメンス | S7 Protocol | `snap7` | `plc-dashboard/raspi_agent/plc_drivers/siemens.py` |

## 共通設計原則

### 1. エンディアンはすべてBig-Endian

**重要:** すべてのPLCでBig-Endianを使用します。

```python
# ❌ 間違い: Little-Endianで処理
value = (word2 << 16) | word1

# ✅ 正しい: Big-Endianで処理
value = (word1 << 16) | word2
```

詳細は `_docs/plc-knowledge/endianness.md` を参照。

### 2. タイムアウトは必ず設定

PLC通信は必ずタイムアウトを設定します。推奨値: 3-5秒

```python
# ❌ 間違い: タイムアウトなし
plc.connect(ip, port)

# ✅ 正しい: タイムアウト設定
plc.connect(ip, port, timeout=5.0)
```

詳細は `_docs/plc-knowledge/timeout-settings.md` を参照。

### 3. エラーハンドリングは必須

PLC通信は必ず例外処理を行います。

```python
try:
    data = plc.batchread_wordunits(addresses)
except Exception as e:
    logger.error(f"PLC通信エラー: {e}")
    return None  # フォールバック処理
```

## キーエンス（Modbus TCP）

### 実装ファイル
`plc-dashboard/raspi_agent/plc_drivers/keyence.py`

### 特徴
- Modbus TCP標準プロトコル
- レジスタアドレスは10進数（例: `D100`）
- `pymodbus`ライブラリを使用

### 接続例

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient(
    host="192.168.0.10",
    port=502,
    timeout=5.0
)
client.connect()
```

### データ読み取り

```python
# Holding Registers (D領域) を読み取り
result = client.read_holding_registers(
    address=100,  # D100
    count=10,     # 10ワード
    slave=1
)

if not result.isError():
    values = result.registers
```

### データ型変換

| PLC型 | バイト数 | 変換方法 |
|------|---------|---------|
| Word (16bit) | 2 | そのまま |
| DWord (32bit) | 4 | 2ワードを結合（Big-Endian） |
| Float (IEEE754) | 4 | `struct.unpack('>f', bytes)` |

```python
import struct

# Float32の読み取り（Big-Endian）
word1, word2 = result.registers[0:2]
bytes_data = struct.pack('>HH', word1, word2)
float_value = struct.unpack('>f', bytes_data)[0]
```

## オムロン（FINS）

### 実装ファイル
`plc-dashboard/raspi_agent/plc_drivers/omron.py`

### 特徴
- FINS (Factory Interface Network Service) プロトコル
- メモリエリア: DM, CIO, WR, HR, AR
- `fins`ライブラリを使用

### 接続例

```python
from fins.udp import UDPFinsConnection

conn = UDPFinsConnection()
conn.connect("192.168.0.10")
conn.dest_node_add = 1
conn.srce_node_add = 25
```

### データ読み取り

```python
# DM領域を読み取り
data = conn.memory_area_read(
    MemoryArea.DM,      # DM領域
    0,                  # 開始アドレス
    10                  # 読み取りワード数
)
```

### メモリエリア

| エリア | 説明 | アドレス範囲 |
|-------|------|------------|
| DM | データメモリ | 0-32767 |
| CIO | CIOエリア | 0-6143 |
| WR | ワークリレー | 0-511 |
| HR | 保持リレー | 0-511 |

## 三菱電機（MC Protocol）

### 実装ファイル
`plc-dashboard/raspi_agent/plc_drivers/mitsubishi.py`

### 特徴
- MC Protocol（MELSEC Communication Protocol）
- デバイス: D, M, X, Y, W
- `pymcprotocol`ライブラリを使用

### 接続例

```python
import pymcprotocol

plc = pymcprotocol.Type3E()
plc.connect(
    ip="192.168.0.10",
    port=5000,
    timeout=5.0
)
```

### データ読み取り

```python
# Dデバイスを一括読み取り
data = plc.batchread_wordunits(
    headdevice="D100",  # 開始デバイス
    readsize=10         # 読み取りワード数
)
```

### デバイス種別

| デバイス | 説明 | 型 |
|---------|------|----|
| D | データレジスタ | Word (16bit) |
| M | 内部リレー | Bit |
| X | 入力 | Bit |
| Y | 出力 | Bit |
| W | リンクレジスタ | Word (16bit) |

## 汎用的なデータ型変換ロジック

すべてのプロトコルで共通のデータ型変換ロジックを使用します。

### 実装場所
`plc-dashboard/raspi_agent/plc_agent.py:258-320`

### サポートデータ型

```python
def convert_plc_data(raw_value, plc_data_type, scale_factor=1.0):
    """
    PLCデータを変換

    Args:
        raw_value: 生データ（int or list of ints）
        plc_data_type: データ型（'word', 'dword', 'float32', 'bit'）
        scale_factor: スケールファクター（デフォルト1.0）

    Returns:
        変換後の値
    """
    if plc_data_type == 'word':
        # 16bit整数（0-65535）
        return int(raw_value) * scale_factor

    elif plc_data_type == 'dword':
        # 32bit整数（Big-Endian）
        word1, word2 = raw_value[0], raw_value[1]
        value = (word1 << 16) | word2  # Big-Endian
        return value * scale_factor

    elif plc_data_type == 'float32':
        # IEEE754 浮動小数点（Big-Endian）
        word1, word2 = raw_value[0], raw_value[1]
        bytes_data = struct.pack('>HH', word1, word2)
        value = struct.unpack('>f', bytes_data)[0]
        return value * scale_factor

    elif plc_data_type == 'bit':
        # ビット値（0 or 1）
        return 1 if raw_value else 0

    else:
        raise ValueError(f"Unknown data type: {plc_data_type}")
```

## ダミーモード（開発・テスト用）

実PLCがない環境でテストするため、ダミーモードを実装しています。

### 実装場所
`plc-dashboard/raspi_agent/plc_agent.py:356-388`

### 使い方

```bash
# 環境変数で有効化
export USE_DUMMY_PLC=true
python agent_app.py
```

### ダミーデータ生成

```python
def generate_dummy_data(data_points):
    """
    ダミーデータを生成

    Args:
        data_points: データポイント設定リスト

    Returns:
        ダミーデータの辞書
    """
    import random

    dummy_data = {}
    for point in data_points:
        data_type = point.get('plc_data_type', 'word')

        if data_type == 'float32':
            # 浮動小数点: 0.0-100.0のランダム値
            value = random.uniform(0.0, 100.0)
        elif data_type == 'dword':
            # 32bit整数: 0-10000のランダム値
            value = random.randint(0, 10000)
        elif data_type == 'bit':
            # ビット: 0 or 1
            value = random.choice([0, 1])
        else:  # 'word'
            # 16bit整数: 0-1000のランダム値
            value = random.randint(0, 1000)

        dummy_data[point['name']] = value

    return dummy_data
```

## トラブルシューティング

よくある問題と解決策は `_docs/plc-knowledge/troubleshooting.md` を参照してください。

## 関連ドキュメント

- `_docs/plc-knowledge/endianness.md` - エンディアン問題の詳細
- `_docs/plc-knowledge/timeout-settings.md` - タイムアウト設定のベストプラクティス
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティングガイド

---

**参考リンク:**
- [Modbus TCP/IP Specification](https://modbus.org/docs/Modbus_Messaging_Implementation_Guide_V1_0b.pdf)
- [FINS Command Reference](https://www.ia.omron.com/)
- [MELSEC Protocol Reference](https://www.mitsubishielectric.com/)
