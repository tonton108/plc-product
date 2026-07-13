#!/usr/bin/env python3
"""本番サービング エントリ（Waitress）

Flask-SocketIO(threadingモード) を Waitress で serve する。開発用の
`socketio.run()`（Werkzeug）は本番非対応（`allow_unsafe_werkzeug`）のため、
配布時（Phase 4: Windowsサービス化）はこのスクリプトで起動する。

## ingest分離（重要）

閲覧クライアントの long-polling 接続が同一プロセスにあると、Waitressでは
エージェントのPOST ingest が巻き込まれてスループットが崩壊する
（_docs/decisions/wsgi-serving-load-verification.md で実測）。これを避けるため、
**同じアプリを2プロセスで起動し、役割で受け口を分ける**:

- ingestプロセス: エージェントの `POST /api/logs` を受ける（閲覧接続はここに来ない）
- viewerプロセス: 閲覧クライアントの Socket.IO(long-polling) と 読み取りAPI を受ける

両プロセスは `SOCKETIO_MESSAGE_QUEUE`（Redis）を共有する。ingest側の emit は
Redis経由でviewer側のクライアントへ届く。実測で ingest 279 req/s・p95=74ms を維持し、
配信は100%（分離しない場合は 14 req/s・p95=22秒）。

## 起動例

    # 共有Redis前提（SOCKETIO_MESSAGE_QUEUE=redis://...）
    # ingest（例: 5000番、エージェント向け）
    PORT=5000 ROLE=ingest python serve_production.py
    # viewer（例: 5001番、閲覧向け。リバースプロキシで振り分け）
    PORT=5001 ROLE=viewer python serve_production.py

単一プロセスで動かす場合は SOCKETIO_MESSAGE_QUEUE 未設定でも動作する（小規模・
閲覧が少ない環境）。ただし想定負荷（200台ingest + 閲覧10〜20台）では分離必須。

環境変数: PORT, WAITRESS_THREADS, HOST, SOCKETIO_MESSAGE_QUEUE, ROLE(情報用)
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# 本番の設定ファイルを明示ロードする（Phase 4: Windowsサービス化）。
# サービス実行時は環境変数の注入が難しいため、`PLC_ENV_FILE`（既定
# C:\ProgramData\plc-monitor\.env）から SECRET_KEY / DATABASE_URL /
# SOCKETIO_MESSAGE_QUEUE / FRONTEND_DIST 等を読み込む。override=True で、
# app.py 側の CWD .env より本番ファイルを優先する。存在しなければ無視（開発時）。
_env_file = os.environ.get("PLC_ENV_FILE", r"C:\ProgramData\plc-monitor\.env")
if os.path.isfile(_env_file):
    load_dotenv(_env_file, override=True)

from waitress import serve

from app import create_app

app, socketio = create_app()


def main():
    import argparse

    # コマンドライン引数を env より優先する。共有 .env（DB/SECRET/Redis等）は全サービス共通、
    # PORT/ROLE はサービスごとに引数で分ける（ingest/viewer）。サービスへの環境注入が
    # 難しいWindowsサービス構成で、役割ごとの差分を確実に渡すため。
    parser = argparse.ArgumentParser(description="本番サービング（Waitress）")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--role", default=None, help="ingest|viewer|single（情報用）")
    parser.add_argument("--threads", type=int, default=None)
    args, _ = parser.parse_known_args()

    host = args.host or os.environ.get("HOST", "0.0.0.0")
    port = args.port or int(os.environ.get("PORT", "5000"))
    threads = args.threads or int(os.environ.get("WAITRESS_THREADS", "16"))
    role = args.role or os.environ.get("ROLE", "single")
    mq = os.environ.get("SOCKETIO_MESSAGE_QUEUE")
    manager = type(socketio.server.manager).__name__ if socketio.server else "N/A"

    print(
        f"[serve_production] role={role} host={host} port={port} "
        f"threads={threads} manager={manager} "
        f"message_queue={'あり' if mq else 'なし(単一プロセス)'}",
        flush=True,
    )
    serve(app, host=host, port=port, threads=threads)


if __name__ == "__main__":
    main()
