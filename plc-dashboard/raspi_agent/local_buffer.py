"""
ローカルバッファ管理モジュール

中央サーバーへの送信に失敗したPLCデータを一時的にSQLiteに保存し、
サーバー復旧時に自動的に再送信する機能を提供します。

主な機能：
- データの一時保存
- 未送信データの取得
- 送信成功後の削除
- 古いデータの自動クリーンアップ
- 統計情報の取得
"""

import sqlite3
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class LocalBuffer:
    """ローカルバッファ管理クラス

    SQLiteを使用してPLCデータを一時保存し、中央サーバーへの
    送信が失敗した場合でもデータロスを防ぎます。
    """

    def __init__(self, db_path: str = 'config/buffer.db', max_retry: int = 10):
        """
        Args:
            db_path: SQLiteデータベースファイルのパス
            max_retry: 最大再試行回数（これを超えたデータは削除される）
        """
        self.db_path = db_path
        self.max_retry = max_retry
        self._lock = threading.RLock()

        # データベースディレクトリが存在しない場合は作成
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # データベース接続（スレッドセーフにするため check_same_thread=False + ロックで保護）
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # カラム名でアクセス可能にする

        self.create_table()
        logger.info(f"[BUFFER] ローカルバッファ初期化完了: {db_path}")

    def create_table(self):
        """バッファテーブルを作成"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS pending_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_retry_at TIMESTAMP,
                error_message TEXT
            )
        ''')

        # インデックス作成（検索高速化）
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_equipment_created
            ON pending_data(equipment_id, created_at)
        ''')

        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_retry_count
            ON pending_data(retry_count)
        ''')

        self.conn.commit()
        logger.debug("[SUCCESS] バッファテーブル作成完了")

    def save(self, equipment_id: str, data: Dict) -> int:
        """データをバッファに保存

        Args:
            equipment_id: 設備ID
            data: PLCデータ（辞書形式）

        Returns:
            挿入されたレコードのID
        """
        with self._lock:
            try:
                cursor = self.conn.execute(
                    '''INSERT INTO pending_data (equipment_id, data, created_at)
                       VALUES (?, ?, ?)''',
                    (equipment_id, json.dumps(data, ensure_ascii=False), datetime.now())
                )
                self.conn.commit()
                record_id = cursor.lastrowid
                logger.debug(f"💾 バッファ保存: ID={record_id}, 設備={equipment_id}")
                return record_id
            except Exception as e:
                logger.error(f"[ERROR] バッファ保存エラー: {e}")
                return -1

    def get_pending(self, limit: int = 100) -> List[Tuple[int, str, Dict]]:
        """未送信データを取得

        再試行回数では除外しない。サーバー障害が長引いた場合でも、データは
        送信成功するか、日数ベースのクリーンアップ（cleanup_old_data）で
        期限切れになるまで再送対象であり続ける。
        以前は WHERE retry_count < max_retry で除外していたが、これだと
        約10分（retry_interval 60秒 × max_retry 10回）を超える障害で未配信
        データが再送対象から外れ、その後 cleanup_max_retry_exceeded で恒久削除
        されていた（バッファの「障害時データ保全」目的を損なう欠損バグ）。

        Args:
            limit: 取得する最大件数

        Returns:
            [(record_id, equipment_id, data), ...] のリスト
        """
        try:
            cursor = self.conn.execute(
                '''SELECT id, equipment_id, data
                   FROM pending_data
                   ORDER BY created_at
                   LIMIT ?''',
                (limit,)
            )

            results = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row['data'])
                    results.append((row['id'], row['equipment_id'], data))
                except json.JSONDecodeError as e:
                    logger.error(f"[ERROR] JSONデコードエラー（ID={row['id']}）: {e}")
                    # 破損データは削除
                    self.delete(row['id'])

            return results
        except Exception as e:
            logger.error(f"[ERROR] 未送信データ取得エラー: {e}")
            return []

    def mark_as_sent(self, record_id: int):
        """送信成功後にデータを削除

        Args:
            record_id: 削除するレコードのID
        """
        with self._lock:
            try:
                self.conn.execute('DELETE FROM pending_data WHERE id = ?', (record_id,))
                self.conn.commit()
                logger.debug(f"[SUCCESS] バッファから削除: ID={record_id}")
            except Exception as e:
                logger.error(f"[ERROR] バッファ削除エラー（ID={record_id}）: {e}")

    def delete(self, record_id: int):
        """データを削除（エイリアス）"""
        self.mark_as_sent(record_id)

    def increment_retry(self, record_id: int, error_message: Optional[str] = None):
        """再試行回数をインクリメント

        Args:
            record_id: レコードID
            error_message: エラーメッセージ（オプション）
        """
        with self._lock:
            try:
                self.conn.execute(
                    '''UPDATE pending_data
                       SET retry_count = retry_count + 1,
                           last_retry_at = ?,
                           error_message = ?
                       WHERE id = ?''',
                    (datetime.now(), error_message, record_id)
                )
                self.conn.commit()
                logger.debug(f"🔄 再試行カウント更新: ID={record_id}")
            except Exception as e:
                logger.error(f"[ERROR] 再試行カウント更新エラー（ID={record_id}）: {e}")

    def cleanup_old_data(self, days: int = 7) -> int:
        """古いデータを削除

        Args:
            days: 保存期間（日数）

        Returns:
            削除されたレコード数
        """
        with self._lock:
            try:
                cutoff = datetime.now() - timedelta(days=days)
                cursor = self.conn.execute(
                    'DELETE FROM pending_data WHERE created_at < ?',
                    (cutoff,)
                )
                self.conn.commit()
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    logger.info(f"🗑️ 古いバッファデータを削除: {deleted_count}件（{days}日以上前）")

                return deleted_count
            except Exception as e:
                logger.error(f"[ERROR] クリーンアップエラー: {e}")
                return 0

    def cleanup_max_retry_exceeded(self) -> int:
        """最大再試行回数を超えたデータを削除

        ⚠️ このメソッドは配信成否・経過日数を問わず retry_count>=max_retry の
        レコードを削除するため、未配信データの恒久欠損を招く。自動クリーンアップ
        （cleanup_buffer）からは呼ばれない（保持ポリシーは cleanup_old_data の
        日数ベースに一本化した）。明示的に「諦めて捨てる」運用が必要な場合のみ
        手動で使うこと。

        Returns:
            削除されたレコード数
        """
        with self._lock:
            try:
                cursor = self.conn.execute(
                    'DELETE FROM pending_data WHERE retry_count >= ?',
                    (self.max_retry,)
                )
                self.conn.commit()
                deleted_count = cursor.rowcount

                if deleted_count > 0:
                    logger.warning(f"[WARNING] 再試行上限を超えたデータを削除: {deleted_count}件")

                return deleted_count
            except Exception as e:
                logger.error(f"[ERROR] 再試行上限超過データ削除エラー: {e}")
                return 0

    def get_stats(self) -> Dict:
        """バッファの統計情報を取得

        Returns:
            統計情報の辞書
        """
        try:
            # 総件数
            total_count = self.conn.execute(
                'SELECT COUNT(*) as count FROM pending_data'
            ).fetchone()['count']

            # 設備別件数
            equipment_stats = {}
            cursor = self.conn.execute(
                '''SELECT equipment_id, COUNT(*) as count
                   FROM pending_data
                   GROUP BY equipment_id'''
            )
            for row in cursor.fetchall():
                equipment_stats[row['equipment_id']] = row['count']

            # 再試行回数別件数
            retry_stats = {}
            cursor = self.conn.execute(
                '''SELECT retry_count, COUNT(*) as count
                   FROM pending_data
                   GROUP BY retry_count
                   ORDER BY retry_count'''
            )
            for row in cursor.fetchall():
                retry_stats[row['retry_count']] = row['count']

            # 最古のデータ
            oldest_record = self.conn.execute(
                'SELECT created_at FROM pending_data ORDER BY created_at LIMIT 1'
            ).fetchone()
            oldest_date = oldest_record['created_at'] if oldest_record else None

            return {
                'total_count': total_count,
                'equipment_stats': equipment_stats,
                'retry_stats': retry_stats,
                'oldest_date': oldest_date
            }
        except Exception as e:
            logger.error(f"[ERROR] 統計情報取得エラー: {e}")
            return {
                'total_count': 0,
                'equipment_stats': {},
                'retry_stats': {},
                'oldest_date': None
            }

    def print_stats(self):
        """統計情報をログに出力"""
        stats = self.get_stats()

        logger.info("=" * 60)
        logger.info("📊 ローカルバッファ統計")
        logger.info("=" * 60)
        logger.info(f"総件数: {stats['total_count']}件")

        if stats['equipment_stats']:
            logger.info("\n設備別:")
            for equipment_id, count in stats['equipment_stats'].items():
                logger.info(f"  - {equipment_id}: {count}件")

        if stats['retry_stats']:
            logger.info("\n再試行回数別:")
            for retry_count, count in stats['retry_stats'].items():
                logger.info(f"  - {retry_count}回: {count}件")

        if stats['oldest_date']:
            logger.info(f"\n最古のデータ: {stats['oldest_date']}")

        logger.info("=" * 60)

    def close(self):
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            logger.info("🔒 ローカルバッファ接続を閉じました")

    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.close()


if __name__ == '__main__':
    # テスト用コード
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # バッファのテスト
    with LocalBuffer(db_path='test_buffer.db') as buffer:
        # データ保存テスト
        test_data = {
            'timestamp': datetime.now().isoformat(),
            'data_points': {
                'temp': 25.5,
                'pressure': 1013.25
            }
        }

        record_id = buffer.save('TEST_001', test_data)
        logger.info(f"保存完了: ID={record_id}")

        # 未送信データ取得テスト
        pending = buffer.get_pending()
        logger.info(f"未送信データ: {len(pending)}件")

        # 統計情報テスト
        buffer.print_stats()
