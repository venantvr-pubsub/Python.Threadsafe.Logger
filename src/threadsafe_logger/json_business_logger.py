import datetime
from typing import Optional, Dict, Any

from async_jsonl_queue import AsyncJsonlQueue

from .base_logger import BaseBusinessLogger


class JsonBusinessLogger(BaseBusinessLogger):

    # --- Implementation of the Abstract Contract ---
    @property
    def logger_name(self) -> str: return "EVENT-JSONL"

    @property
    def enabled_env_var(self) -> str: return "JSON_BUSINESS_LOGGER_ENABLED"

    @property
    def db_file_env_var(self) -> str: return "JSON_BUSINESS_LOGGER_DB_FILE"

    @staticmethod
    def _create_backend(file_path: str) -> AsyncJsonlQueue:
        return AsyncJsonlQueue(file_path=file_path)

    def _on_backend_ready(self):
        # Nothing to do for JSONL after the worker starts.
        pass

    def log(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        self._ensure_initialized()

        # This explicit check resolves the "Unresolved attribute reference" error.
        if self.is_enabled and self.backend:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            details_str = f"- {details}" if details else ""
            print(f"{self._GREEN}[{self.logger_name}] {event_type} {details_str}{self._RESET}")

            log_data = {'timestamp': timestamp, 'event_type': event_type, 'details': details}
            self.backend.write(log_data)

json_business_logger = JsonBusinessLogger()
