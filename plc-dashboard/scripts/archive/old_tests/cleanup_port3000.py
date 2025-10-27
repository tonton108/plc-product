#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ポート3000を使用しているプロセスをクリーンアップ"""

import subprocess
import sys
import time

def cleanup_port_3000():
    print("[INFO] Cleaning up processes on port 3000...")

    try:
        # netstatでポート3000を使用しているプロセスを確認
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            check=True
        )

        pids = set()
        for line in result.stdout.split('\n'):
            if ':3000' in line and 'LISTENING' in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.add(pid)

        if not pids:
            print("[OK] No processes found on port 3000")
            return True

        print(f"[INFO] Found {len(pids)} process(es) on port 3000: {pids}")

        # 各プロセスを停止
        for pid in pids:
            print(f"[INFO] Killing process {pid}...")
            try:
                subprocess.run(
                    ['taskkill', '/F', '/PID', pid],
                    capture_output=True,
                    check=False
                )
                print(f"[OK] Process {pid} killed")
            except Exception as e:
                print(f"[WARNING] Failed to kill process {pid}: {e}")

        # 少し待機
        time.sleep(2)

        # 再度確認
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            check=True
        )

        remaining = []
        for line in result.stdout.split('\n'):
            if ':3000' in line and 'LISTENING' in line:
                remaining.append(line.strip())

        if remaining:
            print(f"[WARNING] Some processes still remain on port 3000:")
            for line in remaining:
                print(f"  {line}")
            return False
        else:
            print("[SUCCESS] Port 3000 is now free!")
            return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = cleanup_port_3000()
    sys.exit(0 if success else 1)
