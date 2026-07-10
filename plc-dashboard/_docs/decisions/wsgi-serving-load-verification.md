# 本番WSGIサービング方式の負荷検証（Phase 4 着手ゲート）

**作成日:** 2026-07-10
**ステータス:** 調査完了・**方式は要判断**（本文書の選択肢からの決定待ち）
**関連:** SPEC.md §3.1/§10（「Waitress+long-polling を第一候補・要追加調査」）、`app.py`（`async_mode='threading'`）

## 背景

Phase 4（配布形態: Windowsサービス化）の着手ゲートとして、本番WSGI構成
「**Waitress + Socket.IO(threadingモード) + long-polling**」が、想定負荷
（エージェント最大200台のHTTP POST + 閲覧クライアント10〜20台のリアルタイム受信）
で成立するかを実機検証した。CLAUDE.md は greenletエラー回避のため
`async_mode='threading'` を必須としており、threadingモードでは
ネイティブWebSocketが使えず閲覧クライアントは long-polling にフォールバックする。

## 検証環境

- 実PostgreSQL 15.18（Docker）、Flaskアプリを Waitress で serve（`waitress.serve(app, threads=N)`）
- `python-socketio` の polling クライアントを N 個接続し、各設備の room に参加
- エージェント役が `POST /api/logs`（room配信をトリガ）を並列投入
- 比較対象として、現行の開発サーバ（`socketio.run` = Werkzeug threaded）でも同条件を測定

## 検証結果

### 1. 機能面: 問題なし
- Waitress が Flask-SocketIO(threading) を serve でき、long-polling クライアントは
  transport=polling を維持したまま room ブロードキャストを受信できる。
- 配信の完全性: 8クライアント × 40配信で **320/320（100%）**、全クライアントが漏れなく受信。

### 2. 単発レイテンシ: 問題なし（「2秒」はテストの環境要因）
- 検証初期に「全リクエストが一律 ~2秒」という現象が出たが、原因は
  **Windowsで接続先に `localhost` を使うとIPv6 `::1` を先に試み、Waitressが
  IPv4のみlistenのため ~2秒のフォールバック待ち**が入るテスト側アーティファクトだった。
  `127.0.0.1`（IPv4明示）では **26ms/req**、keep-alive再利用で 18ms。
  → 本番はサーバIP直指定・keep-alive前提のため無関係。**検証時は `localhost` を避ける**こと。

### 3. 【重大】long-polling接続中の POST スループット崩壊（Waitress固有）

| 条件（8クライアント×40POST 相当） | スループット | p50 | p95 | p99 |
|---|---|---|---|---|
| Waitress・クライアント0個（純POST） | **269 req/s** | 57ms | 70ms | 93ms |
| Waitress・8 long-pollingクライアント接続 | **14 req/s** | 63ms | **22,000ms** | 22,000ms |
| 開発サーバ(Werkzeug threaded)・8クライアント接続 | **176 req/s** | 89ms | 104ms | 110ms |

- **long-pollingクライアントが接続しているだけで、Waitressの POST スループットが
  269→14 req/s に崩壊し、テールが p95=22秒（≈engine.io pingTimeout 20s）に達する。**
- **Waitressのスレッド数を 16→64 に増やしても改善しない**（=単純なスレッド枯渇ではない）。
- 同じワークロードを**開発サーバ(Werkzeug threaded)で実行すると劣化しない**（176 req/s、p95=104ms）。
  → この崩壊は **threadingモードSocket.IO固有ではなく Waitress 固有**。

### 推定原因
Waitress は全ソケットI/Oを**単一のasyncore selectループ**で捌く。long-polling接続が
常時そのI/Oスレッドを占有・往復するため、閲覧クライアントが増えるほど
エージェントのPOST処理が直列化・待たされると考えられる。Werkzeug threaded は
接続ごとにスレッドを持つためこのボトルネックが出ない。

## 含意

**SPEC の「Waitress + long-polling 第一候補」は、想定負荷（閲覧10〜20台 + 200台ingest）
では成立しない。** 200台が数秒間隔で送る中、閲覧が数台つながるだけで ingest の
テールが20秒級になり、実運用に耐えない。開発サーバ(Werkzeug)は劣化しないが、
本番用途では非推奨（単一acceptループ・堅牢性・`allow_unsafe_werkzeug`）。

## 選択肢（要判断）

- **A. async_mode を eventlet/gevent に変更しネイティブWebSocket化**
  非同期I/OはアイドルなWS接続にスレッドを占有しないため多数接続に強い。
  ただし CLAUDE.md の threading必須方針・過去のgreenletエラー・Windows上での
  gevent/eventletの安定性という懸念があり、**別途この構成の実機検証が必要**。
- **B. threadingのまま、接続ごとにスレッドを張る本番サーバを選ぶ**
  gunicorn+gevent は requirements にあるが gunicorn は Windows非対応（配布ターゲットはWindows）。
  Windowsで動く「接続ごとスレッド」型の堅牢なWSGIサーバの選定が要る。
- **C. ingest と Socket.IO を分離**
  エージェントの `POST /api/logs`（ingest）と閲覧向け Socket.IO を別プロセス/別ポートで動かし、
  閲覧のlong-pollingが ingest を巻き込まないようにする。threading方針を維持できる。
- **D. Waitressの深掘りチューニング**
  pingInterval短縮・I/Oスレッド構成等。64スレッドで無改善だったことから効果は不透明。

## 推奨（暫定）

long-polling を固定プール/単一I/Oスレッドのサーバで捌くのは高頻度ingestと本質的に相性が悪い。
**C（ingest分離）で threading方針を保ちつつ崩壊を回避** するか、**A（eventlet/geventでWebSocket化）を
別途検証** するのが筋。いずれも Phase 4 の配布・サービス化に着手する前に方式を確定させる必要がある。
（本文書は事実の記録と選択肢提示まで。どれを採るかは未決。）

## 再現方法

`scripts/` には未コミット。検証は以下の要領（`localhost`ではなく`127.0.0.1`を使うこと）:
1. `waitress.serve(create_app()[0], host='0.0.0.0', port=5055, threads=N)` でserve
2. `python-socketio` の polling クライアントを複数接続し room 参加、並列で `POST /api/logs`
3. クライアント0個 vs 接続時で POST の p95/スループットを比較
