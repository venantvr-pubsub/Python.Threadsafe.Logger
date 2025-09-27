import json
import logging
import os

from .base_logger import BaseBusinessLogger


class JsonBusinessLogger(BaseBusinessLogger):
    @property
    def logger_name(self) -> str:
        return "EVENT-JSONL"  # Nom mis à jour pour refléter le format

    @property
    def enabled_env_var(self) -> str:
        return "JSON_BUSINESS_LOGGER_ENABLED"

    @property
    def db_file_env_var(self) -> str:
        return "JSON_BUSINESS_LOGGER_DB_FILE"

    def _setup_backend(self, db_file: str) -> bool:
        """Prépare le chemin et s'assure que le répertoire existe."""
        self.db_file = db_file
        self.file_handle = None
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la création du répertoire pour {self.logger_name}: {e}")
            return False

    def _initialize_backend_for_worker(self):
        """Ouvre le fichier en mode 'append' dans le thread de travail."""
        try:
            self.file_handle = open(self.db_file, 'a', encoding='utf-8')
        except Exception as e:
            logging.error(f"Erreur d'ouverture du fichier de log dans le worker {self.logger_name}: {e}")

    def _write_log_to_backend(self, log_item: dict):
        """Écrit une ligne JSON dans le fichier et force l'écriture sur le disque."""
        if self.file_handle:
            try:
                # Convertit le dict en chaîne JSON et ajoute un retour à la ligne
                json_line = json.dumps(log_item, ensure_ascii=False)
                self.file_handle.write(json_line + '\n')
                # Force l'écriture sur le disque, équivalent du 'commit' de SQLite
                self.file_handle.flush()
            except Exception as e:
                logging.error(f"Erreur d'écriture dans le fichier pour {self.logger_name}: {e}")

    def _shutdown_backend(self):
        """Ferme le fichier proprement."""
        if self.file_handle:
            self.file_handle.close()

json_business_logger = JsonBusinessLogger()