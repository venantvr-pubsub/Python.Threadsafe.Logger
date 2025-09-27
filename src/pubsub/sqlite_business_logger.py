import datetime
import json
import os
import queue
import sqlite3
import threading
from typing import Optional, Dict, Any


class SqliteBusinessLogger:
    _instance = None
    _lock = threading.Lock()
    _GREEN = "\033[92m"
    _RESET = "\033[0m"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized_flag'):
            self._initialized_flag = False
            self.is_enabled = False
            self._init_lock = threading.Lock()

    def _lazy_initialize(self):
        with self._init_lock:
            if self._initialized_flag:
                return

            enabled = os.getenv("BUSINESS_LOGGER_ENABLED", "false").lower() in ("true", "1", "yes")
            db_file = os.getenv("BUSINESS_LOGGER_DB_FILE")

            if enabled and db_file:
                self.db_file = db_file
                self.table_name = os.getenv("BUSINESS_LOGGER_TABLE_NAME", "business_events")

                if self._create_table():
                    self.is_enabled = True
                    self.log_queue = queue.Queue()
                    self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
                    self.worker_thread.start()
                    print(f"✅ SqliteBusinessLogger auto-configuré. Logs dans '{self.db_file}'.")

            self._initialized_flag = True

    def _create_table(self) -> bool:
        """Crée la table de la BDD. Retourne True en cas de succès."""
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        details_json TEXT
                    )
                """)
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la création de la table pour SqliteBusinessLogger : {e}")
            return False

    def _process_queue(self):
        with sqlite3.connect(self.db_file, check_same_thread=False) as conn:
            cursor = conn.cursor()
            while True:
                try:
                    log_item = self.log_queue.get()
                    if log_item is None: break
                    timestamp, event_type, details = log_item
                    details_json = json.dumps(details) if details else None
                    cursor.execute(
                        f"INSERT INTO {self.table_name} (timestamp, event_type, details_json) VALUES (?, ?, ?)",
                        (timestamp, event_type, details_json)
                    )
                    conn.commit()
                    self.log_queue.task_done()
                except Exception as e:
                    print(f"❌ Erreur dans le worker SqliteBusinessLogger : {e}")

    def log(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        if not self._initialized_flag: self._lazy_initialize()
        if not self.is_enabled: return

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        details_str = f"- {details}" if details else ""
        console_output = f"[EVENT-SQL] {event_type} {details_str}"
        print(f"{self._GREEN}{console_output}{self._RESET}")
        self.log_queue.put((timestamp, event_type, details))

    def shutdown(self, wait=True):
        if not self._initialized_flag: self._lazy_initialize()
        if not self.is_enabled or not hasattr(self, 'log_queue'): return
        if wait: self.log_queue.join()
        self.log_queue.put(None)
        if hasattr(self, 'worker_thread'): self.worker_thread.join(timeout=5)
        print("✅ SqliteBusinessLogger arrêté proprement.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.shutdown()


sqlite_business_logger = SqliteBusinessLogger()