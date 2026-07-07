import os
import json
from typing import Dict, Any

from uitls.log import get_log


class Config:

    def get(self, name: str, default_value=None) -> Any:
        pass


def load_config(config_file: str, default_value: Any):
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log = get_log()
            if log is not None:
                log.error(f"Load config error {config_file}: {e}")
    if default_value is None:
        default_value = {}
    return default_value


class CascadeConfig(Config):
    def __init__(self, config_file: str, default_val: Dict[str, Any] = None, parent: Config = None):
        self.parent = parent
        self.config = load_config(config_file, default_val)

    def get(self, name: str, default_value=None) -> Any:
        if name in self.config:
            return self.config[name]
        if self.parent is not None:
            return self.parent.get(name, default_value)
        return default_value


def save_json_config(file_name: str, config):
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger = get_log()
        if logger is not None:
            logger.error(f"Save config error {file_name}: {e}")
        else:
            print(f"Save config error {file_name}: {e}")
