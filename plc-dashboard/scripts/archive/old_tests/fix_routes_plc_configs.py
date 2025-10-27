"""
routes.pyのPLCデータ設定保存処理にnameとunitフィールドを追加
"""
import re

def fix_routes():
    file_path = "D:/plc-product/plc-dashboard/backend/api/routes.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # insert_dataに name と unit を追加
    old_pattern = r'''insert_data = \{
                    "equipment_id": equipment_internal_id,
                    "data_type": config_data\.get\("data_type"\),
                    "enabled": config_data\.get\("enabled", False\),
                    "address": config_data\.get\("address", ""\),
                    "scale_factor": config_data\.get\("scale_factor", 1\),
                    "plc_data_type": config_data\.get\("plc_data_type", "word"\)
                \}'''

    new_pattern = '''insert_data = {
                    "equipment_id": equipment_internal_id,
                    "name": config_data.get("name", ""),
                    "data_type": config_data.get("data_type"),
                    "enabled": config_data.get("enabled", False),
                    "address": config_data.get("address", ""),
                    "scale_factor": config_data.get("scale_factor", 1),
                    "plc_data_type": config_data.get("plc_data_type", "word"),
                    "unit": config_data.get("unit", "")
                }'''

    content = re.sub(old_pattern, new_pattern, content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[SUCCESS] routes.pyを修正しました: name, unitフィールドを追加")

if __name__ == '__main__':
    fix_routes()
