import os
from typing import Optional

from tinydb import TinyDB

from .base_logger import BaseBusinessLogger


class JsonBusinessLogger(BaseBusinessLogger):
    # --- Définition des propriétés abstraites ---
    @property
    def logger_name(self) -> str:
        return "EVENT-JSON"

    @property
    def enabled_env_var(self) -> str:
        return "JSON_BUSINESS_LOGGER_ENABLED"

    @property
    def db_file_env_var(self) -> str:
        return "JSON_BUSINESS_LOGGER_DB_FILE"

    # --- Implémentation des méthodes abstraites ---
    def _setup_backend(self, db_file: str) -> bool:
        self.db: Optional[TinyDB] = None
        try:
            os.makedirs(os.path.dirname(db_file), exist_ok=True)
            self.db = TinyDB(db_file, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation de {self.logger_name} : {e}")
            return False

    def _write_log_to_backend(self, log_item: dict):
        if self.db:
            self.db.insert(log_item)

    def _shutdown_backend(self):
        if self.db:
            self.db.close()


# --- L'instance singleton reste la même ---
json_business_logger = JsonBusinessLogger()