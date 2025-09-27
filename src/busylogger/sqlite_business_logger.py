import json
import logging
import os
import sqlite3

from .base_logger import BaseBusinessLogger


class SqliteBusinessLogger(BaseBusinessLogger):

    @property
    def logger_name(self) -> str:
        return "EVENT-SQL"

    @property
    def enabled_env_var(self) -> str:
        return "BUSINESS_LOGGER_ENABLED"

    @property
    def db_file_env_var(self) -> str:
        return "BUSINESS_LOGGER_DB_FILE"

    def _setup_backend(self, db_file: str) -> bool:
        """
        Cette méthode s'assure que le répertoire et la table existent,
        mais n'ouvre pas de connexion persistante.
        """
        self.db_file = db_file
        self.table_name = os.getenv("BUSINESS_LOGGER_TABLE_NAME", "business_events")
        self.conn = None
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
            logging.error(f"Erreur lors de la création de la table pour {self.logger_name} : {e}")
            return False

    def _initialize_backend_for_worker(self):
        """Crée la connexion à la base de données une seule fois pour ce thread."""
        try:
            # check_same_thread=False est nécessaire car cette connexion est
            # utilisée exclusivement par ce thread, qui est différent du thread principal.
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        except Exception as e:
            logging.error(f"Impossible de se connecter à la BDD SQLite dans le worker {self.logger_name}: {e}")

    def _write_log_to_backend(self, log_item: dict):
        """Réutilise la connexion existante pour insérer un log."""
        if not self.conn:
            logging.error(f"Aucune connexion BDD disponible pour {self.logger_name}.")
            return

        try:
            cursor = self.conn.cursor()
            details_json = json.dumps(log_item['details']) if log_item['details'] else None
            cursor.execute(
                f"INSERT INTO {self.table_name} (timestamp, event_type, details_json) VALUES (?, ?, ?)",
                (log_item['timestamp'], log_item['event_type'], details_json)
            )
            self.conn.commit()
        except Exception as e:
            logging.error(f"Erreur d'écriture dans SQLite pour {self.logger_name}: {e}")

    def _shutdown_backend(self):
        """Ferme la connexion de manière explicite à la fin."""
        if self.conn:
            self.conn.close()


sqlite_business_logger = SqliteBusinessLogger()
