# 対応PLCメーカーとプロトコル

**作成日:** 2025-10-30
**最終更新:** 2026-07-09（主要4メーカーの対応条件を一次情報で再調査）

## 概要

このドキュメントは、PLC監視システムが対応している（または対応予定の）PLCメーカーとプロトコルの一覧です。

## 対応メーカーとプロトコル

| メーカー | 主要シリーズ | プロトコル | Pythonライブラリ | ポート | 対応状況 |
|---------|------------|-----------|----------------|-------|---------|
| **三菱電機** | Q/QnU/iQ-R/iQ-F/FX | MC Protocol (3E/4E) ※1 | pymcprotocol | 5000/5007 ※2 | ✅ 実装済み |
| **オムロン** | CP1/CJ/NJ/NX ※3 | FINS over TCP/UDP | fins | 9600 | ✅ 実装済み |
| **キーエンス** | KV ※4 | Modbus TCP（KV-XLE02拡張ユニット必須・サーバ機能のみ）/ MC(SLMP)互換 | pymodbus | 502 | ✅ 実装済み（条件付き） |
| **シーメンス** | S7-300/400/1200/1500 ※5 | S7 Protocol | python-snap7 (3.x, Pure Python) | 102 | ✅ 実装済み（実機検証待ち） |
| **Schneider Electric** | Modicon M221/M340/M580 | Modbus TCP | pymodbus | 502 | 🔄 対応可能 |
| **Rockwell Automation** | CompactLogix/ControlLogix | EtherNet/IP (CIP) | pycomm3 | 44818 | 🔄 対応可能 |
| **ABB** | AC500/AC500-eCo | Modbus TCP | pymodbus | 502 | 🔄 対応可能 |
| **Panasonic** | FP-XH/FP-X/FP0H | MEWTOCOL | - | 8500 | 🔄 対応可能 |
| **Fuji Electric** | FLEX-PC/MICREX-SX | 独自プロトコル | - | - | 🔄 対応可能 |
| **Yokogawa** | STARDOM | VDS/Modbus TCP | pymodbus | 502 | 🔄 対応可能 |
| **Delta Electronics** | DVP/AH500 | Modbus RTU/ASCII/TCP | pymodbus | 502 | 🔄 対応可能 |
| **LS Electric** | XGK/XGB | Cnet/Fnet | - | 2004 | 🔄 対応可能 |
| **Beckhoff** | CX/TwinCAT | ADS (Automation Device Specification) | pyads | 48898 | 🔄 対応可能 |
| **IDEC** | MicroSmart FC6A | Modbus TCP/RTU | pymodbus | 502 | 🔄 対応可能 |
| **AutomationDirect** | Click/Click PLUS/DirectLogic | Modbus TCP/RTU | pymodbus | 502 | 🔄 対応可能 |
| **GE/Emerson** | PACSystems RX3i | SRTP/EGD/Modbus TCP | pymodbus | 18245/502 | 🔄 対応可能 |
| **Hitachi** | EH/MICRO-EH | HI-PROTOCOL | - | - | 🔄 対応可能 |
| **Bosch Rexroth** | IndraLogic XLC/XMC | CODESYS/EtherCAT | - | - | 🔄 対応可能 |
| **Phoenix Contact** | PLCnext AXC F | Modbus/PROFINET/EtherNet/IP | pymodbus | 502 | 🔄 対応可能 |
| **Wago** | 750/PFC100/PFC200 | Modbus TCP/EtherNet/IP | pymodbus | 502 | 🔄 対応可能 |
| **FANUC** | 0i/30i/31i/32i (PMC) | FOCAS (HSSB/Ethernet) | - | 8193 | 🔄 対応可能 |
| **Toshiba** | T2/EX100 | Modbus RTU | pymodbus | - | 🔄 対応可能 |
| **Yaskawa** | MP2000/MP2200/MP3000 | EtherCAT | - | - | 🔄 対応可能 |

## 凡例

- ✅ **実装済み**: 現在のシステムで動作確認済み（三菱、オムロン、キーエンス）
- ✅ **実装済み（実機検証待ち）**: ドライバー実装＋Snap7 server demoでの実通信検証済み。実機（S7-1200）での最終確認のみ残る（シーメンス。SPEC.md §7）
- 🔄 **対応可能**: ライブラリまたはプロトコル仕様が公開されており、実装可能

## 主要4メーカーの注記（2026-07再調査で確認）

- **※1 三菱:** pymcprotocolが実機テスト済みなのは3Eフレームのみ（4Eは実装済み未テスト、1C〜4Cのシリアル系は非対応）。32bit値は**先頭アドレス=下位ワード**（`endianness.md`参照）
- **※2 三菱ポート:** 5000/5007という記載は再調査でも一次情報の裏付けが取れていない（未検証）。実際のポートはPLC側のユニット設定に依存するため、設備ごとに確認すること
- **※3 オムロン:** NX/NJ系はFINSが大幅制限（オムロン公式が新規設計での使用を非推奨、対応CPU・ポート限定、CJ互換メモリのみ・Sysmac Studioでの事前設定必須）。NX/NJの本格対応にはEtherNet/IP (CIP) ドライバの追加が必要。詳細は`protocols.md`参照
- **※4 キーエンス:** Modbus TCPはCPU内蔵ではなく拡張ユニットKV-XLE02のサーバ機能（公式仕様）。同ユニットはMC(SLMP)互換も公式対応しており、実務ではそちらが定石の可能性が高い。旧表記の「KZ」シリーズ対応は根拠未確認のため削除
- **※5 シーメンス:** S7-200はCP243経由のexperimental扱い・TSAP指定接続。S7-1200/1500はPLC側の事前設定（PUT/GET許可・最適化ブロックアクセス無効化）が必須。詳細は`protocols.md`参照

## 実装優先順位

日本国内シェアと産業界での採用実績を考慮しています。Modbus TCP対応メーカーは既存ライブラリ（pymodbus）で即座に対応可能です。

## 関連ドキュメント

- `_docs/plc-knowledge/protocols.md` - 各プロトコルの詳細実装ガイド
- `plc-dashboard/raspi_agent/plc_agent.py` - 実装コード

---

**最終更新:** 2026-07-09
