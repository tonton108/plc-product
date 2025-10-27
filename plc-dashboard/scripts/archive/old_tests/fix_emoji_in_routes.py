"""
routes.pyの絵文字を削除してWindows環境のcp932エラーを修正
"""
import re

def fix_emoji():
    file_path = "D:/plc-product/plc-dashboard/backend/api/routes.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 絵文字を安全な文字列に置換
    replacements = {
        '📥 PLC': '[PLC_DATA] PLC',
        '💾 DB': '[DB] DB',
        '📡 WebSocket': '[WEBSOCKET] WebSocket',
        '🔧 [DEBUG]': '[DEBUG]',
        '🔍 [DEBUG]': '[DEBUG]',
        '🔄 [DEBUG]': '[DEBUG]',
        ' [DEBUG]': '[ERROR]',
        '💾 [DEBUG]': '[DEBUG]'
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[SUCCESS] routes.pyの絵文字を削除しました: {file_path}")

if __name__ == '__main__':
    fix_emoji()
