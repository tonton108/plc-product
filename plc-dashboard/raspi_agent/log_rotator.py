#!/usr/bin/env python3
"""
ログローテーションユーティリティ

Raspberry Piエージェント起動時に自動的にログローテーションを実行します。
"""

import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def rotate_log_file(log_file_path, keep_days=7, compress=True):
    """
    ログファイルをローテーション

    Args:
        log_file_path (str): ログファイルのパス
        keep_days (int): 保持期間（日数）
        compress (bool): gzip圧縮するか

    Returns:
        bool: 成功したらTrue
    """
    log_path = Path(log_file_path)

    # ログファイルが存在しない、または空の場合はスキップ
    if not log_path.exists():
        logger.debug(f"ログファイルが存在しません: {log_file_path}")
        return False

    if log_path.stat().st_size == 0:
        logger.debug(f"ログファイルが空です: {log_file_path}")
        return False

    # ファイルサイズが1MB未満ならスキップ（ローテーション不要）
    if log_path.stat().st_size < 1024 * 1024:  # 1MB
        logger.debug(f"ログファイルが小さいためスキップ: {log_file_path} ({log_path.stat().st_size} bytes)")
        return False

    try:
        # 日付サフィックス
        date_suffix = datetime.now().strftime('%Y%m%d')
        rotated_name = f"{log_file_path}.{date_suffix}"

        # すでに今日ローテーション済みの場合はスキップ
        if Path(rotated_name).exists() or Path(f"{rotated_name}.gz").exists():
            logger.debug(f"今日既にローテーション済み: {log_file_path}")
            return False

        logger.info(f"🔄 ログローテーション開始: {log_path.name}")

        # 1. ログファイルをコピー
        shutil.copy2(log_file_path, rotated_name)

        # 2. 元のログファイルをクリア
        with open(log_file_path, 'w') as f:
            f.write('')

        logger.info(f"   [SUCCESS] ローテーション完了: {log_path.name}")

        # 3. gzip圧縮
        if compress:
            compressed_name = f"{rotated_name}.gz"
            with open(rotated_name, 'rb') as f_in:
                with gzip.open(compressed_name, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 圧縮前のファイルを削除
            os.remove(rotated_name)

            original_size = log_path.stat().st_size
            compressed_size = Path(compressed_name).stat().st_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            logger.info(f"   [SUCCESS] 圧縮完了: {ratio:.1f}% 削減")

        # 4. 古いログファイルを削除
        deleted_count = _delete_old_logs(log_path, keep_days)
        if deleted_count > 0:
            logger.info(f"   🗑️  {deleted_count} 個の古いログを削除")

        return True

    except Exception as e:
        logger.error(f"ログローテーション失敗: {log_file_path} - {e}")
        return False

def _delete_old_logs(log_path, keep_days):
    """
    古いログファイルを削除

    Args:
        log_path (Path): ログファイルのパス
        keep_days (int): 保持期間（日数）

    Returns:
        int: 削除したファイル数
    """
    log_dir = log_path.parent
    log_name = log_path.name
    cutoff_date = datetime.now() - timedelta(days=keep_days)

    deleted_count = 0

    # ローテーション済みファイルを検索（*.log.YYYYMMDD または *.log.YYYYMMDD.gz）
    for file_path in log_dir.glob(f"{log_name}.*"):
        try:
            # ファイル名から日付を抽出
            parts = file_path.name.split('.')
            if len(parts) >= 3:
                date_str = parts[-1] if not parts[-1].endswith('gz') else parts[-2]
                file_date = datetime.strptime(date_str, '%Y%m%d')

                if file_date < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"削除: {file_path.name} （{keep_days}日以上前）")
        except (ValueError, IndexError):
            # 日付形式でない場合はスキップ
            continue

    return deleted_count

def rotate_all_logs(log_dir=None, keep_days=7):
    """
    ディレクトリ内のすべての.logファイルをローテーション

    Args:
        log_dir (str): ログディレクトリのパス（Noneの場合は現在のディレクトリ）
        keep_days (int): 保持期間（日数）
    """
    if log_dir is None:
        log_dir = os.path.dirname(os.path.abspath(__file__))

    log_path = Path(log_dir)

    logger.info("=" * 50)
    logger.info("[LOG] ログローテーションチェック開始")
    logger.info("=" * 50)

    rotated_count = 0

    # .logファイルを検索
    for log_file in log_path.glob("*.log"):
        if rotate_log_file(str(log_file), keep_days=keep_days):
            rotated_count += 1

    if rotated_count > 0:
        logger.info(f"[SUCCESS] {rotated_count} 個のログファイルをローテーションしました")
    else:
        logger.info("[INFO]  ローテーション対象のログファイルはありません")

    logger.info("=" * 50)

if __name__ == '__main__':
    # テスト実行
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    rotate_all_logs()
