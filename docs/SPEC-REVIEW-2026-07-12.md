# SPEC.md 根拠レベル棚卸し（全体レビュー第1段）

> 実施日: 2026-07-12 / 対象: `docs/SPEC.md`（ドラフト・全体レビュー待ち）
> 目的: 各仕様主張を根拠レベルでタグ付けし、「固い/薄い(調査可)/実機待ち/陳腐化(実装と乖離)」を可視化する。
> 凡例: 🟢固い(一次情報/実測) / 🟡薄い(仮定・机上調査で裏取り可) / 🔧実機待ち(物理PLC必須) / ⚠️陳腐化(仕様と実装が乖離、要更新)

---

## サマリ（優先度順）

1. **⚠️ 最優先＝陳腐化の解消**: サービング方式（§3.1/§6/§10）が実装で覆った。仕様更新が最も急ぎ。
2. **🟡 要Web裏取り**: snap7の「Cライブラリ不要」主張、保持期間/収集間隔/1Pi=1PLCの妥当性、NSSMの2026年時点の是非。
3. **🔧 実機待ち**: オムロンCP1/CJ・キーエンスSLMP・SiemensS7の word_order/前提手順（Phase 5、調べても埋まらない）。
4. **🟢 固い部分**: 認証、動的データ項目、パーティショニング、三菱/Siemensの word_order など。

---

## ⚠️ 陳腐化（仕様 ≠ 実装。最優先で仕様更新）

| 箇所 | 仕様の記述 | 実装/実測の現実 | 対応 |
|---|---|---|---|
| §3.1, §6, §10 | 「Waitress + long-polling固定を第一候補。Phase4前の負荷検証で最終確定（不合格ならgevent系へ）」 | **負荷検証実施済(#24)**: 閲覧のlong-pollingがingestを巻き込み**スループット崩壊**(14req/s・p95=22秒)。解決は**gevent化ではなくOption C=ingest分離**(Redis message_queue共有、#25)。ingest 279req/s・p95=74msで解決。`_docs/decisions/wsgi-serving-load-verification.md` | 仕様を「ingest/viewer 2プロセス+Redis」に更新。「要検証」→「検証済・確定」へ |
| §8 | カバレッジ「44%→段階的に60%へ」 | **実測75%達成**(#30-37)。CIゲート60→73%。テスト90→142件 | 目標値・現況を更新 |
| §5.2 | 「スケジューラはAPScheduler等に置き換え」 | 実装は**独自threadingスケジューラ**(`scheduler.py`)で1系統統合済(#17) | APScheduler前提を実装に合わせるか、置換を今後課題として明記 |
| §8 | 「ESLintの`|| true`を外しゲート化」 | **試行し棚上げ**(PR#38 close)。nuxt devtools由来の脆弱性・Node21+要件・lock churnで見送り | 「保留（理由・再挑戦の筋）」に更新 |
| §9 ロードマップ | Phase 0-5の未完前提の記述 | Phase 0-3完了、Phase4はingest分離まで完了、Phase5はカバレッジ/テスト完了。#8-#37マージ済 | 完了/未着手を実PRで正確化 |

---

## 🟡 薄い（仮定。机上/Web調査で裏取りすべき）

| 箇所 | 主張 | 懸念・調べるべきこと |
|---|---|---|
| §7, §3.1 | python-snap7 3.x は「Pure Python、C共有ライブラリの同梱不要」 | **重要**: 従来のpython-snap7はsnap7 Cライブラリ必須だった。3.xで本当に不要か？ 配布形態(インストーラ)に直結。要一次情報確認 |
| §1, §5.2 | 生ログ保持**30日**が「1台PCで現実的な上限」 | 製造業の品質トレース要件として30日は妥当か？（業界慣行・法令/監査要件）。ディスク実サイズ試算は実測未了（#23はクリーンアップ速度のみ検証） |
| §1 | 収集間隔**既定5秒**、同時閲覧**10-20台** | 工場PLC監視の一般的なポーリング間隔・同時閲覧規模と整合するか（内部推論ベース） |
| §1, §2 | **1 Raspberry Pi = 1 PLC** | 1Piで複数PLCを束ねる構成が一般的でないか？ コスト/保守に直結（200台=200Pi） |
| §3.1 | サービス化に**NSSM**採用（「2014年から更新なし・枯れて安定」と自認） | 2026年時点でNSSMが最善か。代替(WinSW, sc.exe, Shawl)との比較。放置プロジェクトのリスク再評価 |
| §7 | オムロンNX/NJはFINS大幅制限→EtherNet/IP(CIP)を将来課題 | NX/NJの現状（FINS対応範囲）とCIP必要性の再確認（製品ラインの主流がNX/NJに移行しているなら影響大） |
| §5.2 | エラー/アラーム保持**90日** | 実装で反映されたか要確認（今セッションは生30日/日次365日を実装。エラー/アラーム90日は未確認＝reconcile対象） |

---

## 🔧 実機待ち（Phase 5・机上調査では確定不可）

| 箇所 | 項目 | 状態 |
|---|---|---|
| §5.3, §7, §10 | オムロンCP1/CJ の32bit word_order | 一次情報で「第1ワード=下位」示唆・確度medium。実PLCで突き合わせ確定（word_order設定で吸収済みのため実害保留） |
| §7, §10 | キーエンスKV-XLE02のSLMP互換読み取り | 実機で読めれば三菱ドライバ流用。Siemens検証と同時期 |
| §7 | Siemens S7-1200 の PUT/GET許可・Optimized block access無効化 | シミュレータでは再現不可。実機1台調達して手順書ごと最終確認 |

→ これらは**追加のWeb調査では埋まらない**。実機調達（Phase 5）まで「設定で吸収・手順明記」で正しく先送りされている。

---

## 🟢 固い（一次情報 or 実測で裏付け済み。維持）

- §4 認証全般（Bearerトークン実装済み #12。ただし仕様の文言「セッション/JWT」は実装(不透明トークン)と要文言調整）
- §5.1 動的データ項目の一気通貫（実装・実機検証済 #13/#14/#15）
- §5.2 月次パーティショニング + DROPクリーンアップ（実装・200台負荷検証済 #21/#22/#23）
- §5.3 三菱 word_order=low_first（公式マニュアルで反証・訂正済）、Siemens=high_first、pymcprotocolのタイムアウトAPI（ライブラリ仕様確認済）
- §3.1 PostgreSQL同梱ライセンス（PostgreSQLライセンス確認済）、initdbの--auth/--encoding/--locale明示
- §6 設備別room配信（実装済 #16）
- §1 READ_ONLY（書き込み禁止）の安全方針

---

## 🔍 Web調査結果（2026-07-12・薄い前提の裏取り）

| 前提 | 調査結論 | 判定 |
|---|---|---|
| **python-snap7 3.x はCライブラリ不要** | ✅ **正しい**。v3.0+ は S7プロトコルスタックを純Python実装。native依存・コンパイラ不要でARM/Alpine可。ただし `python-snap7<3` はCラッパーなので **`>=3` をピン必須**（[readthedocs](https://python-snap7.readthedocs.io/en/latest/installation.html), [pypi](https://pypi.org/project/python-snap7/)） | 🟢 仕様維持（バージョンピンを明記） |
| **生ログ30日保持** | ⚠️ **要件次第で大幅に不足の可能性**。産業ヒストリアンの一般保持は**2〜5年**、ただし**圧縮(swinging door/deadband→生の1-5%)前提**。当システムは**無圧縮で生保存**。さらに**トレーサビリティ規制はもっと長い**: FDA 1年+、食品FSMA 2年、**自動車GM 15年・Stellantis 10年**（[retention各種](https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods), [ISO/自動車](https://pinnacleqms.com/blog/document-control-mastery-one-system-across-10-iso-standards-2026-chapter-6)） | ⚠️ **要件確認**（下記・最重要） |
| **収集間隔 既定5秒** | 業界は「重要変数1秒/トレンド60秒、最速100ms」。5秒は一般監視には妥当だが**クリティカル制御には遅め**。設定範囲1-60秒でカバー可（[historian best practice](https://industrialmonitordirect.com/blogs/knowledgebase/industrial-data-historian-technical-justification-and-use-cases)） | 🟢 概ね妥当（クリティカル用途は1秒推奨と明記） |
| **1 Raspberry Pi = 1 PLC** | ⚠️ **簡素化の選択で、必然ではない**。業界はゲートウェイ1台で**複数PLC**を束ねるのが一般的（Modbus多ドロップ最大247、複数TCP）。200PLC=200Piは**コスト大**（[Pi gateway](https://www.industrialshields.com/blog/raspberry-pi-for-industry-26/modbus-tcp-rtu-guide-for-raspberry-pi-plcs-python-node-red-examples-563)） | ⚠️ 1:1の理由（隔離/障害分離/簡素化）を明記 or 見直し |
| **NSSMでサービス化** | ⚠️ NSSMは**2017年最終リリースで放置**を確認。**維持されている代替**あり: **Shawl**(Rust製・winget可・保守中)、WinSW(保守モード)、Servy(新興)（[Servy vs NSSM vs WinSW](https://dev.to/aelassas/servy-vs-nssm-vs-winsw-2k46)） | ⚠️ greenfieldなら**Shawl**を再検討（NSSMでも動くが「枯れて安定」の論拠は弱まった） |

### ⭐ 最重要の要件ギャップ：この製品は「運用監視」か「品質トレーサビリティ」か
- **30日 生ログ**は、**リアルタイム運用監視/トレンド**用途なら妥当。
- しかし**バッチ品質トレース/規制監査**が用途なら、生データ保持が**年単位（自動車系なら10-15年）**必要で、30日は致命的に短い。日次/月次集計(365日/永続)は avg/max/min の粗い粒度で、生トレースの代替にならない。
- **SPEC.mdはどちらの用途か明記していない**。ここが「要件が十分に裏取りされていない」最大の箇所。→ **ユーザー判断が必要**（対象顧客・業界・監査要件）。

---

## 次アクション提案

1. **⚠️の仕様更新**（実装に追随。最も価値が高く、調査不要）— SPEC.md §3.1/§6/§8/§9/§10 を実測結果で書き換え。
2. **🟡のWeb裏取り**（薄い前提の確証）— 優先: ①snap7 3.xのCライブラリ要否、②製造業のデータ保持/収集間隔の慣行、③1Pi=1PLC構成の是非、④NSSMの2026年代替。
3. **🔧はPhase5で実機**（今は正しく先送り）。
