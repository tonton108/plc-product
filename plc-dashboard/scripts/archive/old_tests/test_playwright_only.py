"""
Playwright フロントエンドレンダリングテストのみを実行
"""
import sys
from pathlib import Path

# 親ディレクトリからtest_e2e_deployment.pyをインポート
sys.path.insert(0, str(Path(__file__).parent))

from test_e2e_deployment import test_frontend_rendering, print_header

if __name__ == '__main__':
    print_header("Frontend Rendering Test (Playwright)")
    print("\n前提条件: http://localhost:3000/ が起動していること\n")

    success = test_frontend_rendering()

    if success:
        print("\n[SUCCESS] テスト成功！")
        sys.exit(0)
    else:
        print("\n[FAILED] テスト失敗")
        sys.exit(1)
