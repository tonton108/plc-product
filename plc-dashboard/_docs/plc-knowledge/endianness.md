# エンディアンとワード順序

**作成日:** 2025-10-24
**最終更新:** 2026-07-09（一次情報による再調査で全面改訂）

## ⚠️ 重要: 旧ルールの撤回

このドキュメントの旧版には「すべてのPLCはBig-Endianであり、32bit値は常に `(word1 << 16) | word2`（先に読んだワードが上位）」という固定ルールが記載されていましたが、**2026年7月の再調査により、三菱MELSECについては誤りであることが公式マニュアルで確認されました。**

- 三菱電機公式マニュアル SH-080008（MCプロトコルリファレンス）: 実数0.75（IEEE754で`0x3F400000`）をD0/D1に格納した場合、**D0=0000H（下位ワード）、D1=3F40H（上位ワード）**
- 三菱電機公式マニュアル SH-080628ENG（共通命令編）: 32bit命令が使う2ワードのうち、**指定デバイス番号（先頭アドレス）が下位16bit、+1が上位16bit**（DMOV等の `(S+1,S)→(D+1,D)` 表記で D+1=Upper, D=Lower と明示）

つまり三菱では **先頭アドレス側が下位ワード** であり、`batchread_wordunits` が返すアドレス昇順リストに対して正しい結合は `(word2 << 16) | word1` です。

## 問題は2層に分かれる

「エンディアン」と一括りにされがちですが、実装上は独立した2つの問題です。混同しないこと。

### 第1層: ワード内のバイト順序（狭義のエンディアン）

16bitワードの中で上位バイトと下位バイトのどちらが先に伝送されるか。

**→ 通信ライブラリ（pymodbus / pymcprotocol / fins / python-snap7）がint値に変換して返すため、本プロジェクトの実装層では通常意識する必要がない。**

（参考: ワイヤレベルのバイト順はプロトコルごとに異なり、再調査でも決着していない。ライブラリを信頼する。）

### 第2層: ワード間の順序（32bit値のワードオーダー）★本題

32bit値（DWord/Float32）を2つの16bitワードに分けて格納するとき、**先頭アドレス側が上位か下位か**。これはプロトコルではなく**PLC（CPU）側のデータ格納規約に依存し、メーカー・機種ごとに異なる。**

## メーカー別ワード順序（2026-07再調査の結果）

| メーカー | 32bitワード順序 | 正しい結合式 | 検証状態 | 出典 |
|---|---|---|---|---|
| **三菱電機**（Q/L/iQ-R確認済み） | **先頭アドレス = 下位ワード** | `(word2 << 16) \| word1` | ✅ 公式マニュアルで確定（3-0×5クレーム） | SH-080008, SH-080628ENG |
| **シーメンス S7** | Big-Endian（上位バイト先行）。snap7が返すバイト列を `struct.unpack('>f', ...)` で解釈 | `(word1 << 16) \| word2` 相当 | ✅ snap7公式で確定 | snap7 "Siemens data format" |
| **オムロン FINS** | **FINSプロトコル自体は規定しない**（CPU命令仕様依存）。第1ワード=下位が示唆される | `(word2 << 16) \| word1` の可能性が高い | ⚠️ 確度medium・**実機確認必須** | W227E12 FINSコマンドリファレンス |
| **キーエンス KV** | 未検証（Modbus経由の場合は機器・設定依存） | 不明 | ❌ 未検証・**実機確認必須** | - |

**注意（三菱）:** 一次資料での裏取りはQ/L/iQ-R系まで。FX5/iQ-Fも業界的にほぼ確実に同一だが直接検証はしていない。

## 実装方針（SPEC.md §5.3）

固定ルールでは対応できないため、**ワード順序（word_order）を項目ごとに設定可能にした**（Phase 2で実装済み）:

- `PLCDataConfig.word_order`（`high_first` / `low_first`、既定 `low_first`）— DB・API・エージェント設定に一気通貫
- 変換は `raspi_agent/plc_drivers/converters.py` の `convert_words_to_value(word1, word2, data_type, word_order)`。`low_first` なら `(word2 << 16) | word1`、`high_first` なら `(word1 << 16) | word2`
- 各ドライバ（mitsubishi/omron/keyence）は設定の `word_order` を変換に渡す。既定は三菱を想定して `low_first`
- 回帰防止テスト: `raspi_agent/tests/test_word_order.py`（三菱の実数0.75の例を含む）

### 実装状況（Phase 2で解消済み）

旧版は `converters.py` が全メーカー `(word1 << 16) | word2` 固定で、**三菱の実PLCでは32bit値が化ける**状態だった。word_order 導入により項目ごとに順序を選べるようになり解消。

```python
# 三菱（既定 low_first）: 先頭アドレス=下位ワード
value = convert_words_to_value(word1, word2, "float32", "low_first")

# シーメンス等（high_first）: 先頭アドレス=上位ワード
value = convert_words_to_value(word1, word2, "float32", "high_first")
```

## struct.packのフォーマット文字

ワードのリストからfloat32を復元する際のバイト列組み立てには引き続き `>`（Big-Endian）を使う。**ワード順序の問題はpackに渡すワードの並び順で吸収する**:

```python
import struct

# word_order='high_first'（シーメンス等）
bytes_data = struct.pack('>HH', word1, word2)

# word_order='low_first'（三菱等）
bytes_data = struct.pack('>HH', word2, word1)

value = struct.unpack('>f', bytes_data)[0]
```

## デバッグ方法

### 1. 実PLC値と比較（最重要）

PLCのモニタ画面（GX Works等）で表示される値と、Pythonで読み取った値を比較する。**新しいメーカー・機種を接続したら必ず32bit値で1回実施すること。**

| PLC表示 | Python読取 | 判定 |
|--------|----------|-----|
| 123.45 | 123.45 | ✅ word_order正しい |
| 123.45 | 全く異なる巨大値/極小値 | ❌ ワード順序が逆 |

### 2. バイナリダンプで確認

```python
logger.debug(f"Raw words: word1=0x{word1:04X}, word2=0x{word2:04X}")
logger.debug(f"high_first: 0x{(word1 << 16) | word2:08X} / low_first: 0x{(word2 << 16) | word1:08X}")
```

既知のテスト値（例: PLC側に0.75を書いてもらう → `0x3F400000`）でどちらの解釈が一致するか確認する。

## チェックリスト

- [ ] 32bit値の結合前に、その設備の `word_order` を確認したか
- [ ] 新規メーカー・機種の接続時に、実PLC値との突き合わせを行ったか
- [ ] `struct.pack()`/`struct.unpack()` で `>` を指定しているか（バイト列組み立ては常にBig-Endian表記で統一）
- [ ] エンディアン未指定（`struct.pack('HH', ...)`）を使っていないか（システム依存で危険）

## 関連ドキュメント

- `_docs/plc-knowledge/protocols.md` - PLCプロトコル実装ガイド
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティングガイド
- `docs/SPEC.md` §5.3 - word_order設定の仕様

---

**参考リンク:**
- [三菱電機 SH-080008: MELSECコミュニケーションプロトコル リファレンスマニュアル](https://dl.mitsubishielectric.com/dl/fa/document/manual/plc/sh080008/sh080008ab.pdf)
- [三菱電機 SH-080628ENG: QCPU共通命令編](https://dl.mitsubishielectric.com/dl/fa/document/manual/plc/sh080628eng/sh080628engd.pdf)
- [Snap7: Siemens data format](https://snap7.sourceforge.net/siemens_dataformat.html)
- [オムロン W227E12: FINSコマンドリファレンス](https://www.myomron.com/downloads/1.Manuals/Networks/W227E12_FINS_Commands_Reference_Manual.pdf)
- [Python struct — Interpret bytes as packed binary data](https://docs.python.org/3/library/struct.html)
