"""
設定管理モジュール

Phase 8リファクタリング: db_utils.pyから分割
Phase 9: loggerを使用するように更新
Phase 19: デバイス識別関数をdevice_utils.pyからインポート

このモジュールはローカル設定の管理を担当します：
- ConfigManager: DB + JSONフォールバック方式の設定管理
- PLC設定の読み込み・保存
- 初回起動判定
"""

import os
import json
import logging
from api_client import DatabaseAPI
from device_utils import get_mac_address, get_ip_address
from config.constants import DEFAULT_MODBUS_PORT, DEFAULT_PLC_IP

# モジュール用ロガー
logger = logging.getLogger(__name__)


class ConfigManager:
    """設定管理クラス（DB + JSONフォールバック）

    主な機能：
    - データベースベースの初回起動判定
    - PLC設定の読み込み（DB優先、JSONフォールバック）
    - PLC設定の保存（DB + JSONバックアップ）
    - 管理者パスワードの管理
    """

    def __init__(self):
        self.db_api = DatabaseAPI()
        self.json_config_path = 'config/plc_config.json'

    def is_first_run_db(self):
        """データベースベースの初回起動判定"""
        try:
            # デバイス固有の情報を取得
            mac_address = get_mac_address()
            ip_address = get_ip_address()

            logger.debug(f"デバイス情報で設備検索: MAC={mac_address}, IP={ip_address}")

            # データベースから設備を検索
            equipment_info = self.db_api.get_equipment_by_device_info(
                mac_address=mac_address,
                ip_address=ip_address
            )

            if not equipment_info:
                logger.warning(" データベースに設備が未登録 → 初回起動")
                return True

            equipment_id = equipment_info.get("equipment_id")
            if not equipment_id:
                logger.warning(" 設備IDが取得できない → 初回起動")
                return True

            # 設備の初回セットアップ完了状態をチェック
            setup_completed = self.db_api.check_equipment_setup_completed(equipment_id)
            if not setup_completed:
                logger.warning(f" 設備 {equipment_id} のセットアップ未完了 → 初回起動")
                return True

            # PLCデータ設定が存在し、有効な項目があるかチェック
            plc_configs = self.db_api.get_plc_data_configs(equipment_id)
            if not plc_configs:
                logger.warning(f" 設備 {equipment_id} のPLC設定が存在しない → 初回起動")
                return True

            # 有効なPLC設定があるかチェック
            enabled_configs = [config for config in plc_configs if config.get("enabled", False)]
            if not enabled_configs:
                logger.warning(f" 設備 {equipment_id} に有効なPLC設定がない → 初回起動")
                return True

            logger.info(f" 設備 {equipment_id} は設定済み → 通常起動")
            return False

        except Exception as e:
            logger.error(f" 初回起動判定エラー: {e} → 初回起動として扱う")
            return True

    def load_plc_config(self):
        """PLC設定を読み込み（DB優先、JSONフォールバック）"""
        # まずローカルJSONファイルから設備IDを取得
        local_config = self._load_json_config()
        equipment_id = local_config.get("equipment_id")

        if not equipment_id:
            logger.warning(" 設備IDが未設定です。")
            return local_config

        # DBから設備設定を取得
        equipment_config = self.db_api.get_equipment_config(equipment_id)
        plc_data_configs = self.db_api.get_plc_data_configs(equipment_id)

        if equipment_config and plc_data_configs is not None:
            # DB設定をローカル形式に変換
            config = {
                "equipment_id": equipment_config.get("equipment_id"),
                "plc_ip": equipment_config.get("ip"),
                "plc_port": equipment_config.get("port"),
                "modbus_port": equipment_config.get("modbus_port", DEFAULT_MODBUS_PORT),  # Modbusポート追加
                "manufacturer": equipment_config.get("manufacturer"),
                "series": equipment_config.get("series"),
                "interval": equipment_config.get("interval"),
                "central_server_ip": self.db_api.central_server_ip,
                "central_server_port": self.db_api.central_server_port,
                "data_points": {}
            }

            # PLCデータ設定を変換
            for plc_config in plc_data_configs:
                data_type = plc_config.get("data_type")
                config["data_points"][data_type] = {
                    "name": plc_config.get("name", data_type),  # 項目名
                    "icon": plc_config.get("icon", ""),  # アイコン
                    "unit": plc_config.get("unit", ""),  # 単位
                    "address": plc_config.get("address"),
                    "data_type": plc_config.get("plc_data_type", "word"),  # 新しいPLCデータ型フィールド
                    "scale": plc_config.get("scale_factor", 1),
                    "enabled": plc_config.get("enabled", False)
                }

            logger.info(f" DB設定読み込み成功: {equipment_id}")
            return config
        else:
            logger.warning(" DB設定読み込み失敗、JSONファイルを使用")
            return local_config

    def save_plc_config(self, config_data):
        """PLC設定を保存（DB + JSONバックアップ）"""
        # JSONファイルにもバックアップ保存
        self._save_json_config(config_data)

        new_equipment_id = config_data.get("equipment_id")
        if not new_equipment_id:
            logger.error(" 設備IDが未設定のためDB保存をスキップ")
            return False

        # 現在の設備をMACアドレスで特定
        mac_address = config_data.get("mac_address")
        current_equipment = None
        current_equipment_id = None

        if mac_address:
            # まず中央サーバーで検索を試行
            current_equipment = self.db_api.get_equipment_by_device_info(mac_address=mac_address)
            if current_equipment:
                current_equipment_id = current_equipment.get("equipment_id")
                logger.debug(f"現在の設備を特定（DB）: {current_equipment_id} → {new_equipment_id}")
            else:
                # 中央サーバーAPIが利用できない場合、JSONファイルから既存設備IDを取得
                try:
                    json_config = self._load_json_config()
                    json_mac = json_config.get("mac_address")
                    json_equipment_id = json_config.get("equipment_id")

                    # MACアドレスが一致し、設備IDが設定されている場合は既存設備として扱う
                    if json_mac == mac_address and json_equipment_id:
                        current_equipment_id = json_equipment_id
                        logger.debug(f"現在の設備を特定（JSON）: {current_equipment_id} → {new_equipment_id}")
                except Exception as e:
                    logger.warning(f" JSONファイルから既存設備ID取得に失敗: {e}")

        # 追加チェック：新しい設備IDが既存設備として中央サーバーに存在するか確認
        if not current_equipment_id and new_equipment_id:
            try:
                existing_equipment = self.db_api.get_equipment_config(new_equipment_id)
                if existing_equipment:
                    current_equipment_id = new_equipment_id
                    logger.debug(f"設備IDによる既存設備を特定: {new_equipment_id}")
            except Exception as e:
                logger.warning(f" 設備ID検索に失敗: {e}")

        # 設備基本情報をDB保存
        equipment_data = {
            "equipment_id": new_equipment_id,                 # 新しい設備ID（データ内容）
            "manufacturer": config_data.get("manufacturer"),
            "series": config_data.get("series"),
            "ip": config_data.get("raspi_ip"),                # ラズパイのIPアドレス（DB側のipフィールド）
            "plc_ip": config_data.get("plc_ip"),              # PLCのIPアドレス（新しいplc_ipフィールド）
            "port": config_data.get("plc_port"),              # PLCのポート
            "modbus_port": config_data.get("modbus_port", DEFAULT_MODBUS_PORT),  # Modbusポート追加
            "interval": config_data.get("interval"),
            # ラズパイのデバイス情報も保存
            "mac_address": config_data.get("mac_address"),
            "hostname": config_data.get("hostname"),
            "raspi_ip": config_data.get("raspi_ip")           # ラズパイのIPアドレス（APIとの互換性用）
        }

        # PLCデータ設定をDB形式に変換
        plc_configs = []
        data_points = config_data.get("data_points", {})
        for data_type, setting in data_points.items():
            plc_configs.append({
                "data_type": data_type,
                "name": setting.get("name", data_type),  # 項目名（なければdata_typeをフォールバック）
                "icon": setting.get("icon", ""),  # アイコン
                "unit": setting.get("unit", ""),  # 単位
                "enabled": setting.get("enabled", False),
                "address": setting.get("address", ""),
                "scale_factor": setting.get("scale", 1),
                "plc_data_type": setting.get("data_type", "word")  # PLCデータ型追加
            })

        # DB保存実行（現在の設備IDでURL生成、新しい設備IDでデータ更新）
        target_equipment_id = current_equipment_id if current_equipment_id else new_equipment_id

        equipment_success = self.db_api.save_equipment_config_by_id(target_equipment_id, equipment_data)
        plc_success = self.db_api.save_plc_data_configs(target_equipment_id, plc_configs)

        # 設定保存が成功した場合、セットアップ完了フラグを設定
        if equipment_success and plc_success:
            # セットアップ完了フラグは新しい設備IDで設定
            self.db_api.mark_setup_completed(new_equipment_id)
            logger.info(f" DB設定保存成功: {target_equipment_id} → {new_equipment_id}")
            return True
        else:
            logger.error(" DB設定保存失敗")
            return False

    def _load_json_config(self):
        """JSONファイルから設定を読み込み

        Phase 18: 裸のexcept修正 - 具体的な例外型を指定
        """
        try:
            with open(self.json_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logger.debug(f"JSON設定ファイル読み込みエラー（デフォルト値を使用）: {e}")
            return {
                "plc_ip": DEFAULT_PLC_IP,
                "plc_port": 5000,
                "modbus_port": DEFAULT_MODBUS_PORT,
                "manufacturer": "三菱",
                "series": "FX",
                "equipment_id": "",
                "interval": 1000,
                "data_points": {
                    "production_count": {"address": "D150", "data_type": "word", "scale": 1, "enabled": False},
                    "current": {"address": "D100", "data_type": "word", "scale": 10, "enabled": True},
                    "temperature": {"address": "D101", "data_type": "float32", "scale": 1, "enabled": True},
                    "pressure": {"address": "D102", "data_type": "word", "scale": 100, "enabled": True},
                    "cycle_time": {"address": "D200", "data_type": "dword", "scale": 1, "enabled": False},
                    "error_code": {"address": "D300", "data_type": "word", "scale": 1, "enabled": False}
                }
            }

    def _save_json_config(self, config_data):
        """JSONファイルに設定を保存"""
        os.makedirs('config', exist_ok=True)
        with open(self.json_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

    def save_equipment_id(self, equipment_id):
        """設備IDを設定に保存"""
        try:
            # 現在の設定を読み込み
            config_data = self._load_json_config()

            # 設備IDを更新
            config_data["equipment_id"] = equipment_id

            # 設定を保存
            self._save_json_config(config_data)
            logger.info(f"設備ID '{equipment_id}' をローカル設定に保存しました")

            return True
        except Exception as e:
            logger.error(f" 設備ID保存エラー: {e}")
            return False

    def save_admin_password(self, password_hash):
        """管理者パスワードハッシュをローカル設定に保存"""
        try:
            # 現在の設定を読み込み
            config_data = self._load_json_config()

            # パスワードハッシュを更新
            config_data["admin_password_hash"] = password_hash

            # 設定を保存
            self._save_json_config(config_data)
            logger.info("管理者パスワードをローカル設定に保存しました")

            return True
        except Exception as e:
            logger.error(f" 管理者パスワード保存エラー: {e}")
            return False

    def get_admin_password_hash(self):
        """管理者パスワードハッシュを取得（ローカル設定優先）"""
        try:
            config_data = self._load_json_config()
            local_hash = config_data.get("admin_password_hash")

            if local_hash:
                logger.info(" ローカル設定のパスワードハッシュを使用")
                return local_hash
            else:
                logger.warning(" ローカル設定にパスワードなし、デフォルトを使用")
                return None  # デフォルトまたは環境変数を使用

        except Exception as e:
            logger.error(f" パスワードハッシュ取得エラー: {e}")
            return None
