# PLCプロトコル実装ガイド

**作成日:** 2025-10-24
**最終更新:** 2026-07-09（一次情報による再調査を反映: ワード順序・pymcprotocol API・キーエンスModbus条件）

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

### 1. 32bit値のワード順序はメーカー・機種依存（旧「すべてBig-Endian」ルールは撤回）

**重要:** 旧版の「すべてのPLCでBig-Endian、常に `(word1 << 16) | word2`」という固定ルールは、**三菱について公式マニュアルで反証された**（2026-07再調査）。三菱は先頭アドレス側が下位ワードのため、正しくは `(word2 << 16) | word1`。

```python
# 三菱（Q/L/iQ-R確認済み）: 先頭アドレス = 下位ワード
value = (word2 << 16) | word1

# シーメンスS7: 上位が先（Big-Endian）
value = (word1 << 16) | word2

# オムロン・キーエンス: 実機確認必須（設備ごとの word_order 設定で吸収する）
```

詳細とメーカー別一覧は `_docs/plc-knowledge/endianness.md` を参照。

### 2. タイムアウトは必ず設定

PLC通信は必ずタイムアウトを設定します。推奨値: 3-5秒。**設定APIはライブラリごとに異なる**（pymcprotocolは `connect()` にtimeout引数がなく `setaccessopt(timer_sec=)` を使う。デフォルトは1秒/ソケット2秒と短い）。

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

### ⚠️ 対応条件（2026-07再調査で確認）

- KV-8000シリーズのModbus対応は**CPU内蔵機能ではなく、拡張ユニットKV-XLE02の機能**（キーエンス公式仕様に基づく。確度medium）
- しかも公式仕様に記載があるのは**Modbusサーバ（スレーブ）機能のみ**
- 同じKV-XLE02は**MCプロトコル（SLMP）互換も公式サポート**しており、サードパーティの主要ドライバ（Kepware等）は上位リンク（Host Link）経由でKVを読むのが定石
- **推奨:** キーエンスはModbus固定にせず、MC（SLMP）互換での読み取りを第一候補として検討する（三菱ドライバの流用可能性）。実機・ユニット構成の確認が必須

### 特徴
- Modbus TCP標準プロトコル（KV-XLE02装着時）
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
| DWord (32bit) | 4 | 2ワードを結合（**ワード順序は設備の word_order 設定に従う**） |
| Float (IEEE754) | 4 | `struct.unpack('>f', bytes)`（packに渡すワードの並びで word_order を吸収） |

```python
import struct

# Float32の読み取り（ワード順序は設備ごとに実機確認すること）
word1, word2 = result.registers[0:2]
bytes_data = struct.pack('>HH', word1, word2)   # word_order='high_first' の場合
# bytes_data = struct.pack('>HH', word2, word1) # word_order='low_first' の場合
float_value = struct.unpack('>f', bytes_data)[0]
```

## オムロン（FINS）

### 実装ファイル
`plc-dashboard/raspi_agent/plc_drivers/omron.py`

### ⚠️ 機種別の対応条件（2026-07再調査で確認・オムロン公式マニュアルに基づく）

- **CP1/CJ系**: FINSがネイティブに使える（従来通り）
- **NX/NJ系はFINSが大幅に制限される**:
  - オムロン自身が**NX系の新規設計でのFINS使用を非推奨**と明記（将来サポート打ち切りの可能性あり）
  - FINSサーバ機能があるのは NX102 / NX502-1xxx / NX701-xx20（サーバのみ）等に限定。NX701-xx00は非対応
  - 内蔵EtherNet/IPポートは**Port 2のみFINS対応**（Port 1不可）
  - FINSで読めるのは「CJシリーズユニット互換メモリ」（CIO/WR/HR/DM/EM）のみで、**Sysmac Studioでの事前メモリ設定が必須**。ネイティブ変数は読めない（変数アクセスはCIP/EtherNet/IPが必要）
- NX/NJ系を正式サポートするなら、将来的にEtherNet/IP（CIP）ドライバの追加を検討すべき

### 特徴
- FINS (Factory Interface Network Service) プロトコル
- メモリエリア: DM, CIO, WR, HR, AR
- `fins`ライブラリを使用
- デフォルトポートはUDP/TCPとも**9600**（公式マニュアルで確認済み・変更可）

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
plc.setaccessopt(timer_sec=5)  # タイムアウト設定はconnect()ではなくここで行う
plc.connect("192.168.0.10", 5000)
```

**⚠️ `connect()` に timeout 引数は存在しない**（渡すとTypeError）。また pymcprotocol は3Eフレームのみ実機テスト済み（4Eは実装済み未テスト、1C〜4Cのシリアル系は非対応）。

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

## シーメンス（S7 Protocol）— 実装予定

### 実装ファイル
`plc-dashboard/raspi_agent/plc_drivers/siemens.py`（現状スタブ）

### PLC側の前提条件（2026-07調査で確認済み・実装時に必読）

S7-1200/1500では、**PLC側の設定なしにsnap7からDBを読むことはできない**:

1. **PUT/GET通信の許可**: TIA Portalで CPU Properties > Protection & Security > Connection mechanisms > 「Permit access with PUT/GET communication from remote partner」にチェック。未許可だと `CLI : function refused by CPU` エラー
2. **読み取り対象DBごとに「Optimized block access」を無効化**: DBのProperties > Attributesでチェックを外す。**⚠️ この変更はDBの再初期化を伴い、値がデフォルトにリセットされる。稼働中のPLCに適用してはいけない**（コミッショニング時またはバックアップ後に実施）

### 接続パラメータ

| 機種 | rack / slot |
|---|---|
| S7-1200 / S7-1500 | rack=0, **slot=1**（slot=0は誤り） |
| S7-300 | rack=0, slot=2 |
| S7-400 | ハードウェア構成に依存 |
| S7-200 / LOGO! | rack/slotではなく**TSAP指定**（`SetConnectionParams`）。S7-200はCP243経由のexperimental扱い |

- ポート: TCP 102
- **バイト順序: S7のデータ本体はBig-Endian**（snap7公式で確認）。2ワード読み → `struct.pack('>HH', word1, word2)` → `struct.unpack('>f')` の既存処理はS7に対しては正しい

### ライブラリ

- `python-snap7` 3.x を採用する。**3.0.0（2026年3月）でPure Python化**され、C共有ライブラリ（snap7.dll/.so）の同梱が不要になった。メンテナンスは活発
- S7-200 SMART / LOGO! 0BA8 の対応可否は一次情報で確認できていない。対応を謳う場合は実機検証が必要

## 汎用的なデータ型変換ロジック

すべてのプロトコルで共通のデータ型変換ロジックを使用します。

> ⚠️ **既知の問題（2026-07再調査）:** 以下の現行実装は dword/float32 のワード結合を `(word1 << 16) | word2` 固定で行っており、**三菱の実PLCでは値が化ける**（三菱は先頭アドレス=下位ワード）。Phase 2 で設備/項目ごとの `word_order` 設定を導入して修正予定。詳細は `endianness.md` を参照。

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
