"""
PLCドライバーモジュール

メーカー別のPLC通信ドライバーを提供します。
- Mitsubishi: 三菱電機PLC（MC Protocol / SLMP）
- Omron: オムロンPLC（FINS Protocol）
- Keyence: キーエンスPLC（Modbus TCP）
- Siemens: シーメンスPLC（S7 Protocol）
"""
from .base import (
    update_error_stats,
    print_error_stats,
    validate_plc_ip,
    check_write_permission,
    retry_on_failure,
    safe_plc_read,
    extract_address_number,
    group_continuous_word_addresses,
    generate_dummy_data,
    MAX_RETRY_ATTEMPTS,
    CONNECTION_TIMEOUT,
    READ_TIMEOUT,
)

from .mitsubishi import connect_mitsubishi_plc, read_mitsubishi_plc
from .omron import connect_omron_plc, read_omron_plc
from .keyence import connect_keyence_plc, read_keyence_plc
from .siemens import connect_siemens_plc, read_siemens_plc

__all__ = [
    # base
    'update_error_stats',
    'print_error_stats',
    'validate_plc_ip',
    'check_write_permission',
    'retry_on_failure',
    'safe_plc_read',
    'extract_address_number',
    'group_continuous_word_addresses',
    'generate_dummy_data',
    'MAX_RETRY_ATTEMPTS',
    'CONNECTION_TIMEOUT',
    'READ_TIMEOUT',
    # mitsubishi
    'connect_mitsubishi_plc',
    'read_mitsubishi_plc',
    # omron
    'connect_omron_plc',
    'read_omron_plc',
    # keyence
    'connect_keyence_plc',
    'read_keyence_plc',
    # siemens
    'connect_siemens_plc',
    'read_siemens_plc',
]
