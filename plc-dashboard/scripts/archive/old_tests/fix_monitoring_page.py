"""
モニタリングページのconnectionStatusバグを修正
"""
import re

file_path = "D:/plc-product/plc-dashboard/pages/monitoring/[id].vue"

# ファイルを読み取り
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修正1: :color="connectionStatus ? → :color="realtimeMonitoring.connectionStatus.value ?
content = re.sub(
    r':color="connectionStatus \?',
    r':color="realtimeMonitoring.connectionStatus.value ?',
    content,
    count=1
)

# 修正2: {{ connectionStatus ? 'mdi-check-circle' → {{ realtimeMonitoring.connectionStatus.value ? 'mdi-check-circle'
content = re.sub(
    r'\{\{ connectionStatus \? \'mdi-check-circle\'',
    r'{{ realtimeMonitoring.connectionStatus.value ? \'mdi-check-circle\'',
    content,
    count=1
)

# 修正3: {{ connectionStatus ? '接続中' → {{ realtimeMonitoring.connectionStatus.value ? '接続中'
content = re.sub(
    r'\{\{ connectionStatus \? \'接続中\'',
    r'{{ realtimeMonitoring.connectionStatus.value ? \'接続中\'',
    content,
    count=1
)

# ファイルに書き戻し
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("[SUCCESS] モニタリングページのconnectionStatusバグを修正しました")
print("[INFO] 修正箇所:")
print("  - 22行目: :color属性")
print("  - 29行目: アイコン表示")
print("  - 31行目: テキスト表示")
