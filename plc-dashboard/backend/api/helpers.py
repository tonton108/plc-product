"""
共通ヘルパー関数

Phase 6リファクタリング: 重複コードの統合とエラーハンドリングの統一

このモジュールは以下を提供します:
- Equipment検索のヘルパー関数（重複排除）
- 共通のAPI例外クラス
- エラーハンドリングデコレータ
"""

from functools import wraps
from flask import jsonify
import logging

from db import db
from db.models import Equipment, PLCStatus

logger = logging.getLogger(__name__)


class APIException(Exception):
    """API用カスタム例外

    使用例:
        raise APIException("Equipment not found", 404)
    """
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_equipment_or_404(equipment_id):
    """
    設備IDで設備を検索、存在しない場合はAPIExceptionを発生

    Args:
        equipment_id: 設備ID（文字列）

    Returns:
        Equipment: 設備オブジェクト

    Raises:
        APIException: 設備が見つからない場合（404）

    使用例:
        equipment = get_equipment_or_404(equipment_id)
    """
    equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
    if not equipment:
        logger.warning(f"Equipment not found: {equipment_id}")
        raise APIException("Equipment not found", 404)
    return equipment


def get_equipment_by_internal_id_or_404(internal_id):
    """
    内部ID（整数）で設備を検索

    Args:
        internal_id: 内部ID（整数）

    Returns:
        Equipment: 設備オブジェクト

    Raises:
        APIException: 設備が見つからない場合（404）
    """
    equipment = Equipment.query.get(internal_id)
    if not equipment:
        logger.warning(f"Equipment not found by internal ID: {internal_id}")
        raise APIException("Equipment not found", 404)
    return equipment


def get_equipment_by_device_info(cpu_serial_number=None, mac_address=None, ip_address=None):
    """
    複数の識別子で設備を検索（優先度順）

    検索優先度:
    1. cpu_serial_number（最優先・不変）
    2. mac_address（準不変）
    3. ip_address（可変）

    Args:
        cpu_serial_number: CPUシリアル番号
        mac_address: MACアドレス
        ip_address: IPアドレス

    Returns:
        Equipment: 設備オブジェクト、見つからない場合はNone
    """
    equipment = None

    if cpu_serial_number:
        equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()
    if not equipment and mac_address:
        equipment = Equipment.query.filter_by(mac_address=mac_address).first()
    if not equipment and ip_address:
        equipment = Equipment.query.filter_by(ip=ip_address).first()

    return equipment


def get_or_create_plc_status(equipment_internal_id):
    """PLC通信状態レコードを取得し、無ければ作成してsessionに追加する。

    PLCStatusは設備登録時には作られず、最初の通信イベント（データPOST/エラーPOST）
    で初めて必要になる。従来はどの本番経路にもPLCStatusの作成処理が無かったため、
    テーブルが常に空で、`PLCStatus.query...first()` は常にNoneを返していた。結果、
    save_log_data / save_error_log の状態更新は全て `if plc_status:` で握り潰され、
    is_online・consecutive_errors・last_communication_at が一度も永続化されず、
    PLC通信状態監視（オンライン/オフライン・連続エラー数）が実質無効化されていた。

    新規作成時は __init__ により is_online=False / consecutive_errors=0 /
    uptime_seconds=0 の初期状態になる。オンライン化・エラー計上などの状態設定は
    呼び出し側が行う（db.session.commit も呼び出し側の責務）。

    Args:
        equipment_internal_id: Equipment.id（内部整数ID。equipment_id文字列ではない）

    Returns:
        PLCStatus: 既存または新規作成したレコード
    """
    plc_status = PLCStatus.query.filter_by(equipment_id=equipment_internal_id).first()
    if plc_status is None:
        plc_status = PLCStatus(equipment_id=equipment_internal_id)
        db.session.add(plc_status)
    return plc_status


def handle_api_errors(f):
    """
    API例外を処理するデコレータ

    APIExceptionをキャッチしてJSONレスポンスに変換します。
    その他の例外は500エラーとしてログ出力します。

    使用例:
        @app.route("/api/example")
        @handle_api_errors
        def example_endpoint():
            equipment = get_equipment_or_404(equipment_id)
            return jsonify({"data": equipment.to_dict()})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIException as e:
            return jsonify({"error": e.message}), e.status_code
        except Exception as e:
            db.session.rollback()
            logger.error(f"予期しないエラー in {f.__name__}: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
    return wrapper


def validate_pagination_params(request, default_limit=100, max_limit=1000):
    """
    ページネーションパラメータを検証・取得

    Args:
        request: Flaskリクエストオブジェクト
        default_limit: デフォルトの取得件数
        max_limit: 最大取得件数

    Returns:
        tuple: (offset, limit)
    """
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', default_limit))

        if offset < 0:
            offset = 0
        if limit < 1:
            limit = default_limit
        if limit > max_limit:
            limit = max_limit

        return offset, limit
    except ValueError:
        return 0, default_limit
