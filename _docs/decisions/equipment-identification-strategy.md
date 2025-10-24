# 設備識別の優先順位設計

**作成日:** 2025-10-24

## 結論

設備識別は以下の優先順位で行います：

1. **cpu_serial_number**（最優先・不変）
2. **mac_address**（準不変）
3. **equipment_id**（可変・ユーザー定義）

## 実装

`plc-dashboard/backend/api/routes.py:388-432`

```python
# ✅ cpu_serial_numberで既存設備を検索
equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()

if equipment:
    # 既存設備の場合、equipment_idを更新
    equipment.equipment_id = equipment_id
else:
    # 新規設備の場合、登録
    equipment = Equipment(
        cpu_serial_number=cpu_serial_number,
        mac_address=mac_address,
        equipment_id=equipment_id
    )
```

## 判断理由

### cpu_serial_number（最優先）

**メリット:**
- Raspberry PiのCPUシリアル番号は不変
- SD カード交換・OSクリーンインストールでも変わらない
- ハードウェアレベルの一意識別子

**用途:** 設備の物理的な識別

### mac_address（準不変）

**メリット:**
- ネットワークカード固有の識別子
- 99%のケースで不変

**デメリット:**
- ネットワークカード交換で変わる
- 仮想環境では変更可能

**用途:** cpu_serial_numberのバックアップ識別子

### equipment_id（可変）

**メリット:**
- ユーザーが自由に設定可能
- 分かりやすい名前（"LINE_A_PLC01"等）

**デメリット:**
- ユーザーが変更可能
- 重複の可能性

**用途:** ユーザー向けの表示名

## 却下した代替案

### 案1: equipment_idのみで識別

❌ ユーザーが変更すると別設備として認識される

### 案2: IPアドレスで識別

❌ DHCP環境で変わる可能性がある

### 案3: MACアドレスのみで識別

❌ ネットワークカード交換で変わる

## 関連ドキュメント

- `plc-dashboard/backend/db/models.py` - Equipmentモデル
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティング

---

**最終更新:** 2025-10-24
