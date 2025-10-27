"""
get_plc_data_configs関数にnameとunitフィールドを追加
"""
import re

def fix_get_configs():
    file_path = "D:/plc-product/plc-dashboard/backend/api/routes.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # configs.append の部分を修正
    old_pattern = r'''configs\.append\(\{
                    "data_type": config\.data_type,
                    "enabled": config\.enabled,
                    "address": config\.address,
                    "scale_factor": config\.scale_factor,
                    "plc_data_type": getattr\(config, "plc_data_type", "word"\)
                \}\)'''

    new_pattern = '''configs.append({
                    "name": getattr(config, "name", ""),
                    "data_type": config.data_type,
                    "enabled": config.enabled,
                    "address": config.address,
                    "scale_factor": config.scale_factor,
                    "plc_data_type": getattr(config, "plc_data_type", "word"),
                    "unit": getattr(config, "unit", "")
                })'''

    content = re.sub(old_pattern, new_pattern, content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[SUCCESS] get_plc_data_configs関数を修正しました: name, unitフィールドを追加")

if __name__ == '__main__':
    fix_get_configs()
