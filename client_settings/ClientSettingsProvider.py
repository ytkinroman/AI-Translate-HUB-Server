import os
import yaml

class ClientSettingsProvider:
    def __init__(self, params: dict):
        self.ui_lang = params.get("ui_lang", "ru")
        self.version = params.get("version", "1")
        self.config = self._load_config()

    def _load_config(self) -> dict:
        config_path = os.path.join(os.path.dirname(__file__), "versions", f"v{self.version}.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def execute(self) -> dict:
        """Получает настройки для текущего языка UI"""
        return self.config[self.ui_lang]
