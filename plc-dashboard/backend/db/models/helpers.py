"""
ヘルパー関数モジュール

モデル関連のヘルパー関数を提供します。

Phase 17: models.pyから分割
"""

from db import db
from .equipment import PLCDataConfig
from .constants import DataTypes


def create_default_plc_configs(equipment_id: int) -> None:
    """
    設備登録時に呼び出してデフォルトのPLC設定を作成

    Args:
        equipment_id: 設備の内部ID（equipmentsテーブルのid）
    """
    default_configs = [
        {
            "data_type": DataTypes.PRODUCTION_COUNT,
            "enabled": False,
            "address": "D150",
            "scale_factor": 1,
            "plc_data_type": "word"
        },
        {
            "data_type": DataTypes.CURRENT,
            "enabled": True,
            "address": "D100",
            "scale_factor": 10,
            "plc_data_type": "word"
        },
        {
            "data_type": DataTypes.TEMPERATURE,
            "enabled": True,
            "address": "D101",
            "scale_factor": 10,
            "plc_data_type": "float32"
        },
        {
            "data_type": DataTypes.PRESSURE,
            "enabled": True,
            "address": "D102",
            "scale_factor": 100,
            "plc_data_type": "word"
        },
        {
            "data_type": DataTypes.CYCLE_TIME,
            "enabled": False,
            "address": "D200",
            "scale_factor": 1,
            "plc_data_type": "dword"
        },
        {
            "data_type": DataTypes.ERROR_CODE,
            "enabled": False,
            "address": "D300",
            "scale_factor": 1,
            "plc_data_type": "word"
        },
    ]

    for config in default_configs:
        plc_config = PLCDataConfig(
            equipment_id=equipment_id,
            data_type=config["data_type"],
            enabled=config["enabled"],
            address=config["address"],
            scale_factor=config["scale_factor"],
            plc_data_type=config["plc_data_type"]
        )
        db.session.add(plc_config)

    db.session.commit()
