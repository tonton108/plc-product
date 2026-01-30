"""
設備管理API

設備（Equipment）の登録・取得・更新・検索に関するエンドポイントを提供します。

Phase 16: 型ヒント追加
"""

from flask import Blueprint, request, jsonify, Response
from sqlalchemy import or_
from datetime import datetime, timezone
from typing import Tuple, Union
import logging

from db import db
from db.models import (
    Equipment, PLCDataConfig,
    SetupStatus, OperationalStatus, PLCProtocols, CommunicationModes
)
from api.validators import (
    validate_equipment_id,
    validate_equipment_config,
    validate_plc_config,
    require_json
)
from api.serializers import EquipmentSerializer, PLCDataConfigSerializer
from api.helpers import get_equipment_by_device_info
from api.constants import DEFAULT_MODBUS_PORT

logger = logging.getLogger(__name__)

equipment_bp = Blueprint('equipment', __name__, url_prefix='/api')


@equipment_bp.route("/register", methods=["POST"])
@require_json
def api_register() -> Tuple[Response, int]:
    """設備を登録（Raspberry Piエージェントから呼び出し）"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    equipment_id = data.get("equipment_id")
    mac_address = data.get("mac_address")
    cpu_serial_number = data.get("cpu_serial_number")

    if not equipment_id or not mac_address:
        return jsonify({"error": "equipment_id and mac_address are required"}), 400

    # 入力バリデーション
    is_valid, error_msg = validate_equipment_config(data)
    if not is_valid:
        logger.warning(f"設備登録バリデーションエラー: {error_msg}")
        return jsonify({"error": error_msg}), 400

    # 既存レコード検索（cpu_serial_number > mac_address > equipment_id の優先順）
    search_conditions = []
    if cpu_serial_number:
        search_conditions.append(Equipment.cpu_serial_number == cpu_serial_number)
    search_conditions.extend([
        Equipment.mac_address == mac_address,
        Equipment.equipment_id == equipment_id
    ])

    equipment = Equipment.query.filter(or_(*search_conditions)).first()

    # PLC通信設定のデフォルト値を計算
    manufacturer = data.get("manufacturer", "")
    protocol = data.get("protocol") or PLCProtocols.get_manufacturer_default(manufacturer)
    communication_mode = data.get("communication_mode") or CommunicationModes.get_protocol_default(protocol)
    timeout = data.get("timeout", 5000)
    retry_count = data.get("retry_count", 3)
    retry_interval = data.get("retry_interval", 1000)

    if equipment:
        # 既存設備の更新
        equipment.equipment_id = equipment_id
        equipment.manufacturer = manufacturer
        equipment.series = data.get("series")
        equipment.ip = data.get("ip")
        equipment.plc_ip = data.get("plc_ip")
        equipment.mac_address = mac_address
        equipment.cpu_serial_number = cpu_serial_number
        equipment.hostname = data.get("hostname")
        equipment.port = data.get("port")
        equipment.modbus_port = data.get("modbus_port", DEFAULT_MODBUS_PORT)
        equipment.interval = data.get("interval")
        equipment.protocol = protocol
        equipment.communication_mode = communication_mode
        equipment.timeout = timeout
        equipment.retry_count = retry_count
        equipment.retry_interval = retry_interval
        equipment.setup_status = SetupStatus.BASIC_INFO_REGISTERED
    else:
        # 新規作成
        equipment = Equipment(
            equipment_id=equipment_id,
            manufacturer=manufacturer,
            series=data.get("series"),
            ip=data.get("ip"),
            plc_ip=data.get("plc_ip"),
            mac_address=mac_address,
            cpu_serial_number=cpu_serial_number,
            hostname=data.get("hostname"),
            port=data.get("port"),
            modbus_port=data.get("modbus_port", DEFAULT_MODBUS_PORT),
            interval=data.get("interval"),
            protocol=protocol,
            communication_mode=communication_mode,
            timeout=timeout,
            retry_count=retry_count,
            retry_interval=retry_interval,
            setup_status=SetupStatus.BASIC_INFO_REGISTERED,
            operational_status=OperationalStatus.NOT_STARTED
        )
        db.session.add(equipment)

    try:
        db.session.commit()
        return jsonify({
            "message": "登録完了",
            "cpu_serial_number": cpu_serial_number,
            "equipment_id": equipment_id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/equipment", methods=["GET"])
def get_all_equipment() -> Tuple[Response, int]:
    """全設備一覧を取得"""
    try:
        equipments = Equipment.query.all()
        return jsonify(EquipmentSerializer.to_list(equipments)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/check-equipment", methods=["POST"])
def check_equipment() -> Tuple[Response, int]:
    """MACアドレスとIPで設備を検索"""
    data = request.get_json()
    mac = data.get("mac_address")
    ip = data.get("ip")

    if not mac or not ip:
        return jsonify({"error": "Missing mac_address or ip"}), 400

    equipment = Equipment.query.filter_by(mac_address=mac, ip=ip).first()
    if equipment:
        return jsonify(EquipmentSerializer.to_search_result(equipment)), 200
    else:
        return jsonify({"found": False}), 200


@equipment_bp.route("/equipment/<equipment_id>", methods=["GET"])
def get_equipment_config(equipment_id: str) -> Tuple[Response, int]:
    """設備基本設定を取得"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        return jsonify(EquipmentSerializer.to_dict(equipment)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/equipment/<equipment_id>", methods=["PUT"])
@require_json
def save_equipment_config(equipment_id: str) -> Tuple[Response, int]:
    """設備基本設定を保存"""
    logger.debug("===== save_equipment_config 開始 =====")

    # URL パラメータの設備IDをバリデーション
    if not validate_equipment_id(equipment_id):
        logger.warning(f"無効な設備ID: {equipment_id}")
        return jsonify({"error": "Invalid equipment_id format"}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        # 入力バリデーション
        is_valid, error_msg = validate_equipment_config(data)
        if not is_valid:
            logger.warning(f"設備設定バリデーションエラー: {error_msg}")
            return jsonify({"error": error_msg}), 400

        # CPUシリアル番号で既存設備を検索
        cpu_serial_number = data.get("cpu_serial_number")
        equipment = None

        if cpu_serial_number:
            equipment = Equipment.query.filter_by(cpu_serial_number=cpu_serial_number).first()
            if equipment:
                logger.info(f"CPUシリアル番号で既存設備を発見: {equipment.equipment_id} -> {equipment_id}")
                equipment.equipment_id = equipment_id

        # 既存設備が見つからない場合は新規作成
        if not equipment:
            logger.info(f"新規設備を作成します: {equipment_id}")
            equipment = Equipment(
                equipment_id=equipment_id,
                manufacturer=data.get("manufacturer"),
                series=data.get("series"),
                ip=data.get("raspi_ip", data.get("ip")),
                plc_ip=data.get("plc_ip"),
                port=data.get("plc_port"),
                modbus_port=data.get("modbus_port", DEFAULT_MODBUS_PORT),
                interval=data.get("interval"),
                mac_address=data.get("mac_address"),
                cpu_serial_number=cpu_serial_number,
                hostname=data.get("hostname"),
                setup_status=SetupStatus.BASIC_INFO_REGISTERED,
                operational_status=OperationalStatus.NOT_STARTED
            )
            db.session.add(equipment)

        # 設備情報を更新
        equipment.manufacturer = data.get("manufacturer", equipment.manufacturer)
        equipment.series = data.get("series", equipment.series)
        equipment.ip = data.get("raspi_ip", data.get("ip", equipment.ip))
        equipment.plc_ip = data.get("plc_ip", equipment.plc_ip)
        equipment.port = data.get("plc_port", equipment.port)
        equipment.modbus_port = data.get("modbus_port", equipment.modbus_port)
        equipment.interval = data.get("interval", equipment.interval)
        equipment.mac_address = data.get("mac_address", equipment.mac_address)
        equipment.cpu_serial_number = data.get("cpu_serial_number", equipment.cpu_serial_number)
        equipment.hostname = data.get("hostname", equipment.hostname)
        equipment.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        logger.info(f"設備設定保存成功: {equipment_id}")
        return jsonify({"message": "Equipment config saved"}), 200

    except Exception as e:
        logger.error(f"設備設定保存エラー: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/equipment/search", methods=["GET"])
def search_equipment() -> Tuple[Response, int]:
    """デバイス情報で設備を検索

    Phase 13: helpers.get_equipment_by_device_info()を使用して重複排除
    """
    try:
        cpu_serial_number = request.args.get("cpu_serial_number")
        mac_address = request.args.get("mac_address")
        ip_address = request.args.get("ip_address")

        if not cpu_serial_number and not mac_address and not ip_address:
            return jsonify({"error": "cpu_serial_number, mac_address, or ip_address is required"}), 400

        # 共通ヘルパー関数を使用（優先順位: cpu_serial_number > mac_address > ip_address）
        equipment = get_equipment_by_device_info(
            cpu_serial_number=cpu_serial_number,
            mac_address=mac_address,
            ip_address=ip_address
        )

        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        return jsonify(EquipmentSerializer.to_dict(equipment)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/equipment/<equipment_id>/setup_status", methods=["GET"])
def get_setup_status(equipment_id: str) -> Tuple[Response, int]:
    """設備のセットアップ完了状態を確認"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        setup_completed = equipment.setup_status in [
            SetupStatus.PLC_CONFIGURED,
            SetupStatus.SETUP_COMPLETE
        ]

        return jsonify({
            "equipment_id": equipment_id,
            "setup_completed": setup_completed,
            "setup_status": equipment.setup_status,
            "operational_status": equipment.operational_status,
            "status": equipment.operational_status
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/equipment/<equipment_id>/mark_setup_completed", methods=["POST"])
def mark_setup_completed(equipment_id: str) -> Tuple[Response, int]:
    """設備のセットアップ完了をマーク"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        equipment.setup_status = SetupStatus.SETUP_COMPLETE
        equipment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "message": "Setup completed marked",
            "equipment_id": equipment_id,
            "setup_status": equipment.setup_status,
            "operational_status": equipment.operational_status
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/equipment/<equipment_id>/plc_configs", methods=["GET"])
def get_plc_data_configs(equipment_id: str) -> Tuple[Response, int]:
    """PLCデータ設定を取得"""
    try:
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        plc_configs = PLCDataConfig.query.filter_by(equipment_id=equipment.id).all()
        return jsonify(PLCDataConfigSerializer.to_list(plc_configs)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@equipment_bp.route("/equipment/<equipment_id>/plc_configs", methods=["PUT"])
@require_json
def save_plc_data_configs(equipment_id: str) -> Tuple[Response, int]:
    """PLCデータ設定を保存（Phase 6セキュリティ修正: SQLAlchemy ORM使用）"""
    if not validate_equipment_id(equipment_id):
        logger.warning(f"無効な設備ID: {equipment_id}")
        return jsonify({"error": "Invalid equipment_id format"}), 400

    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "Expected list of configurations"}), 400

        # 各PLCデータ設定をバリデーション
        for i, config_data in enumerate(data):
            is_valid, error_msg = validate_plc_config(config_data)
            if not is_valid:
                logger.warning(f"PLCデータ設定バリデーションエラー (インデックス {i}): {error_msg}")
                return jsonify({"error": f"Config {i}: {error_msg}"}), 400

        # 設備を取得
        equipment = Equipment.query.filter_by(equipment_id=equipment_id).first()
        if not equipment:
            return jsonify({"error": "Equipment not found"}), 404

        equipment_internal_id = equipment.id

        # 既存設定を削除（SQLAlchemy ORMを使用）
        # Phase 6セキュリティ修正: 生SQLからORMに変更
        PLCDataConfig.query.filter_by(equipment_id=equipment_internal_id).delete()

        # 新しい設定を追加（SQLAlchemy ORMを使用）
        # Phase 6セキュリティ修正: 動的SQL生成を排除し、ORMモデルを直接使用
        for config_data in data:
            new_config = PLCDataConfig(
                equipment_id=equipment_internal_id,
                name=config_data.get("name", ""),
                data_type=config_data.get("data_type"),
                icon=config_data.get("icon", ""),
                enabled=config_data.get("enabled", False),
                address=config_data.get("address", ""),
                scale_factor=config_data.get("scale_factor", 1),
                plc_data_type=config_data.get("plc_data_type", "word"),
                unit=config_data.get("unit", "")
            )
            db.session.add(new_config)

        # 設備ステータスを更新
        equipment.setup_status = SetupStatus.PLC_CONFIGURED
        equipment.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        logger.info(f"PLCデータ設定保存成功: {equipment_id}")
        return jsonify({"message": "PLC configs saved"}), 200

    except Exception as e:
        logger.error(f"PLCデータ設定保存エラー: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
