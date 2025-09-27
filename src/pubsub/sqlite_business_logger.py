import json
import os
import sqlite3

from .base_logger import BaseBusinessLogger


class SqliteBusinessLogger(BaseBusinessLogger):
    # --- Définition des propriétés abstraites ---
    @property
    def logger_name(self) -> str:
        return "EVENT-SQL"

    @property
    def enabled_env_var(self) -> str:
        return "BUSINESS_LOGGER_ENABLED"

    @property
    def db_file_env_var(self) -> str:
        return "BUSINESS_LOGGER_DB_FILE"

    # --- Implémentation des méthodes abstraites ---
    def _setup_backend(self, db_file: str) -> bool:
        self.db_file = db_file
        self.table_name = os.getenv("BUSINESS_LOGGER_TABLE_NAME", "business_events")
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
            print(f"❌ Erreur lors de la création de la table pour {self.logger_name} : {e}")
            return False

    def _write_log_to_backend(self, log_item: dict):
        with sqlite3.connect(self.db_file, check_same_thread=False) as conn:
            cursor = conn.cursor()
            details_json = json.dumps(log_item['details']) if log_item['details'] else None
            cursor.execute(
                f"INSERT INTO {self.table_name} (timestamp, event_type, details_json) VALUES (?, ?, ?)",
                (log_item['timestamp'], log_item['event_type'], details_json)
            )
            conn.commit()

    def _shutdown_backend(self):
        # Rien à faire pour sqlite3 avec 'with', la connexion est déjà fermée.
        pass


# --- L'instance singleton reste la même ---
sqlite_business_logger = SqliteBusinessLogger()