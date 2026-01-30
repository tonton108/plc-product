# 対応PLCメーカーとプロトコル

**作成日:** 2025-10-30
**最終更新:** 2025-10-30

## 概要

このドキュメントは、PLC監視システムが対応している（または対応予定の）PLCメーカーとプロトコルの一覧です。

## 対応メーカーとプロトコル

| メーカー | 主要シリーズ | プロトコル | Pythonライブラリ | ポート | 対応状況 |
|---------|------------|-----------|----------------|-------|---------|
| **三菱電機** | Q/QnU/iQ-R/iQ-F/FX | MC Protocol (SLMP/3E/4E) | pymcprotocol | 5000/5007 | ✅ 実装済み |
| **オムロン** | CP1/CJ/NJ/NX | FINS over TCP/UDP | fins | 9600 | ✅ 実装済み |
| **キーエンス** | KV/KZ | Modbus TCP | pymodbus | 502 | ✅ 実装済み |
| **シーメンス** | S7-200/300/400/1200/1500 | S7 Protocol | python-snap7 | 102 | 🚧 未実装 |
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
- 🚧 **未実装**: ドライバー構造は作成済みだが機能未実装（シーメンス）
- 🔄 **対応可能**: ライブラリまたはプロトコル仕様が公開されており、実装可能

## 実装優先順位

日本国内シェアと産業界での採用実績を考慮しています。Modbus TCP対応メーカーは既存ライブラリ（pymodbus）で即座に対応可能です。

## 関連ドキュメント

- `_docs/plc-knowledge/protocols.md` - 各プロトコルの詳細実装ガイド
- `plc-dashboard/raspi_agent/plc_agent.py` - 実装コード

---

**最終更新:** 2025-10-30
