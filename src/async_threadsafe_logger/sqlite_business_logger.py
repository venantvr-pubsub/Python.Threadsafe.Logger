import datetime
import json
import logging
import os
from typing import Optional, Dict, Any

from async_sqlite_queue import AsyncSQLite

from .base_logger import BaseBusinessLogger


class SqliteBusinessLogger(BaseBusinessLogger):

    def __init__(self):
        super().__init__()
        self.table_name = "business_events"

    # --- Implementation of the Abstract Contract ---
    @property
    def logger_name(self) -> str:
        return "EVENT-SQL"

    @property
    def enabled_env_var(self) -> str:
        return "SQLITE_BUSINESS_LOGGER_ENABLED"

    @property
    def db_file_env_var(self) -> str:
        return "SQLITE_BUSINESS_LOGGER_DB_FILE"

    @staticmethod
    def _create_backend(file_path: str) -> AsyncSQLite:
        return AsyncSQLite(db_path=file_path)

    def _on_backend_ready(self):
        self.table_name = os.getenv("SQLITE_BUSINESS_LOGGER_TABLE_NAME", "business_events")
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details_json TEXT
            )
        """
        try:
            res = self.backend.execute_read(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (self.table_name,)
            )
            if not res:
                self.backend.execute_write(create_table_sql)
        except Exception as e:
            logging.error(f"Could not check or create table {self.table_name}: {e}")

    def log(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        self._ensure_initialized()

        # This explicit check resolves the "Unresolved attribute reference" error.
        if self.is_enabled and self.backend:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            details_str = f"- {details}" if details else ""
            print(f"{self._GREEN}[{self.logger_name}] {event_type} {details_str}{self._RESET}")

            details_json = json.dumps(details, ensure_ascii=False) if details else None
            sql = f"INSERT INTO {self.table_name} (timestamp, event_type, details_json) VALUES (?, ?, ?)"
            params = (timestamp, event_type, details_json)

            self.backend.execute_write(sql, params)


sqlite_business_logger = SqliteBusinessLogger()
