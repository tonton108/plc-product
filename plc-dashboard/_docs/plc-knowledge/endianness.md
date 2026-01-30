# エンディアン問題と対処法

**作成日:** 2025-10-24
**最終更新:** 2026-01-24

## 概要

PLCデータ処理で最も注意すべき**エンディアン問題**について記録します。すべてのPLC（キーエンス、オムロン、三菱）で**Big-Endian**を使用しています。

## エンディアンとは

エンディアン（Byte Order）は、複数バイトのデータをメモリに格納する順序を指します。

### Big-Endian（ビッグエンディアン）
上位バイトから順に格納（人間が読みやすい順序）

```
0x12345678 → [0x12] [0x34] [0x56] [0x78]
              MSB                   LSB
```

### Little-Endian（リトルエンディアン）
下位バイトから順に格納（x86/x64 CPUの標準）

```
0x12345678 → [0x78] [0x56] [0x34] [0x12]
              LSB                   MSB
```

## PLCはすべてBig-Endian

**重要:** このプロジェクトでサポートするすべてのPLCは**Big-Endian**です。

| メーカー | プロトコル | エンディアン |
|---------|-----------|-----------|
| キーエンス | Modbus TCP | **Big-Endian** |
| オムロン | FINS | **Big-Endian** |
| 三菱電機 | MC Protocol | **Big-Endian** |
| シーメンス | S7 Protocol | **Big-Endian** |

## よくある間違い

### 間違い: Little-Endianで処理

```python
# ❌ 間違い: Little-Endianで処理
def read_dword_wrong(word1, word2):
    # word2を上位、word1を下位として結合（Little-Endian）
    value = (word2 << 16) | word1
    return value

# 例: PLC値 = 0x12345678
word1 = 0x1234  # 上位ワード
word2 = 0x5678  # 下位ワード

result = read_dword_wrong(word1, word2)
# result = (0x5678 << 16) | 0x1234 = 0x56781234 ❌ 間違い！
```

### 正しい: Big-Endianで処理

```python
# ✅ 正しい: Big-Endianで処理
def read_dword_correct(word1, word2):
    # word1を上位、word2を下位として結合（Big-Endian）
    value = (word1 << 16) | word2
    return value

# 例: PLC値 = 0x12345678
word1 = 0x1234  # 上位ワード
word2 = 0x5678  # 下位ワード

result = read_dword_correct(word1, word2)
# result = (0x1234 << 16) | 0x5678 = 0x12345678 ✅ 正しい！
```

## 実装箇所

### DWord（32bit整数）の読み取り

`plc-dashboard/raspi_agent/plc_agent.py:276-279`

```python
elif plc_data_type == 'dword':
    # 32bit整数の読み取り（Big-Endian）
    word1, word2 = raw_value[0], raw_value[1]
    value = (word1 << 16) | word2  # ✅ Big-Endian
    return value * scale_factor
```

**解説:**
- `word1`: 上位16bit（MSB）
- `word2`: 下位16bit（LSB）
- `(word1 << 16) | word2`: word1を上位に配置してword2と結合

### Float32（IEEE754浮動小数点）の読み取り

`plc-dashboard/raspi_agent/plc_agent.py:281-285`

```python
elif plc_data_type == 'float32':
    # IEEE754浮動小数点の読み取り（Big-Endian）
    word1, word2 = raw_value[0], raw_value[1]
    bytes_data = struct.pack('>HH', word1, word2)  # ✅ '>' = Big-Endian
    value = struct.unpack('>f', bytes_data)[0]
    return value * scale_factor
```

**解説:**
- `struct.pack('>HH', word1, word2)`: Big-Endianで2つのワードをバイト列に変換
  - `>`: Big-Endian指定
  - `HH`: unsigned short (16bit) × 2
- `struct.unpack('>f', bytes_data)`: Big-EndianでIEEE754形式の浮動小数点に変換
  - `>`: Big-Endian指定
  - `f`: float (32bit)

## struct.packのフォーマット文字

| 文字 | 意味 | エンディアン |
|-----|------|-----------|
| `@` | ネイティブ（デフォルト） | システム依存 |
| `=` | ネイティブ | システム依存 |
| `<` | Little-Endian | 固定 |
| `>` | **Big-Endian** | **固定（PLCで使用）** |
| `!` | Network (Big-Endian) | 固定 |

**このプロジェクトでは常に `>` を使用します。**

## デバッグ方法

### 1. バイナリダンプで確認

```python
import struct

# PLCから読み取った2ワード
word1 = 0x1234
word2 = 0x5678

# Big-Endianでバイト列に変換
bytes_big = struct.pack('>HH', word1, word2)
print(f"Big-Endian bytes: {bytes_big.hex()}")
# 出力: 12345678 ✅ 正しい

# Little-Endianでバイト列に変換（間違い）
bytes_little = struct.pack('<HH', word1, word2)
print(f"Little-Endian bytes: {bytes_little.hex()}")
# 出力: 34127856 ❌ 間違い！
```

### 2. ログ出力で確認

```python
logger.debug(f"Raw words: word1=0x{word1:04X}, word2=0x{word2:04X}")
logger.debug(f"Combined (Big-Endian): 0x{(word1 << 16) | word2:08X}")
```

### 3. 実PLC値と比較

PLCのモニタ画面で表示される値と、Pythonで読み取った値を比較します。

| PLC表示 | Python読取 | 判定 |
|--------|----------|-----|
| 1234567 | 1234567 | ✅ 正しい |
| 1234567 | 7654321 | ❌ エンディアン逆 |

## Codexレビュー観点

`.github/workflows/codex-review.yml:35` でエンディアン問題を自動チェックしています：

```yaml
- Endianness issues (all PLCs use Big-Endian)
```

Codexは以下のコードを指摘します：
- `(word2 << 16) | word1` ← Little-Endian（間違い）
- `struct.pack('<HH', ...)` ← Little-Endian指定（間違い）
- `struct.pack('HH', ...)` ← エンディアン未指定（システム依存、危険）

## 過去の問題事例

### 事例1: テストコードでエンディアンミス

**ファイル:** `plc-dashboard/raspi_agent/test_codex_review.py:37-38`（テスト用に意図的に間違えたコード）

```python
# ❌ 意図的なエンディアン間違い（Codexテスト用）
word1, word2 = plc_data[0], plc_data[1]
float_value = struct.pack('<HH', word2, word1)  # Little-Endian
```

**問題:**
1. `<` でLittle-Endianを指定（PLCはBig-Endian）
2. `word2, word1` の順序が逆

**正しい実装:**
```python
# ✅ 正しい実装
word1, word2 = plc_data[0], plc_data[1]
bytes_data = struct.pack('>HH', word1, word2)  # Big-Endian
float_value = struct.unpack('>f', bytes_data)[0]
```

## チェックリスト

PLCデータ処理を実装する際は、以下を確認してください：

- [ ] `struct.pack()`で必ず `>` (Big-Endian) を指定しているか
- [ ] `struct.unpack()`で必ず `>` (Big-Endian) を指定しているか
- [ ] DWord結合時に `(word1 << 16) | word2` の順序になっているか
- [ ] テストケースで実PLC値と比較しているか
- [ ] ログ出力でバイナリダンプを確認できるか

## 関連ドキュメント

- `_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティングガイド
- `.github/workflows/codex-review.yml` - Codex自動レビュー設定

---

**参考リンク:**
- [Wikipedia: Endianness](https://en.wikipedia.org/wiki/Endianness)
- [Python struct — Interpret bytes as packed binary data](https://docs.python.org/3/library/struct.html)
