import datetime
import os
import queue
import threading
from typing import Optional, Dict, Any

from tinydb import TinyDB


class JsonBusinessLogger:
    """
    Équivalent du BusinessLogger mais utilisant un fichier JSON comme stockage via TinyDB.
    Même fonctionnement : auto-configurable, thread-safe et non-bloquant.
    """
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
            self.db: Optional[TinyDB] = None

    def _lazy_initialize(self):
        """Effectue l'initialisation une seule fois à partir des variables d'environnement."""
        with self._init_lock:
            if self._initialized_flag:
                return

            enabled = os.getenv("JSON_BUSINESS_LOGGER_ENABLED", "false").lower() in ("true", "1", "yes")
            db_file = os.getenv("JSON_BUSINESS_LOGGER_DB_FILE")

            if enabled and db_file:
                try:
                    path_dirname = os.path.dirname(db_file)
                    if len(path_dirname) > 0:
                        os.makedirs(path_dirname, exist_ok=True)
                    # os.makedirs(os.path.dirname(db_file), exist_ok=True)
                    self.db = TinyDB(db_file, indent=2, ensure_ascii=False)
                    self.is_enabled = True
                    self.log_queue = queue.Queue()
                    self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
                    self.worker_thread.start()
                    print(f"✅ JsonBusinessLogger auto-configuré. Logs dans '{db_file}'.")
                except Exception as e:
                    print(f"❌ Erreur lors de l'initialisation de JsonBusinessLogger : {e}")
                    self.is_enabled = False

            self._initialized_flag = True

    def _process_queue(self):
        """Méthode du thread de travail qui insère les documents dans le fichier JSON."""
        while True:
            try:
                log_item = self.log_queue.get()
                if log_item is None:
                    break

                if self.db:
                    self.db.insert(log_item)
                self.log_queue.task_done()
            except Exception as e:
                print(f"❌ Erreur dans le worker JsonBusinessLogger : {e}")

    def log(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """Enregistre un événement. Imprime en console et met en file pour écriture."""
        if not self._initialized_flag:
            self._lazy_initialize()

        if not self.is_enabled:
            return

        # Impression console en vert
        details_str = f"- {details}" if details else ""
        console_output = f"[EVENT-JSON] {event_type} {details_str}"
        print(f"{self._GREEN}{console_output}{self._RESET}")

        # Création du document et mise en file d'attente
        log_document = {
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'event_type': event_type,
            'details': details
        }
        self.log_queue.put(log_document)

    def shutdown(self, wait=True):
        """Arrête proprement le logger."""
        if not self._initialized_flag:
            self._lazy_initialize()

        if not self.is_enabled or not hasattr(self, 'log_queue'):
            return

        if wait:
            self.log_queue.join()

        self.log_queue.put(None)
        if hasattr(self, 'worker_thread'):
            self.worker_thread.join(timeout=5)

        if self.db:
            self.db.close()
        print("✅ JsonBusinessLogger arrêté proprement.")


# Instance singleton qui sera importée dans le reste de l'application.
json_business_logger = JsonBusinessLogger()
