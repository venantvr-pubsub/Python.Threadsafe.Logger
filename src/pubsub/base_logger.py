import datetime
import os
import queue
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseBusinessLogger(ABC):
    """
    Classe de base abstraite pour les loggers métier.
    Gère toute la logique commune : singleton, initialisation paresseuse,
    file d'attente, thread de travail, et gestion de contexte 'with'.
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

    # --- Méthodes et propriétés abstraites à implémenter par les enfants ---

    @property
    @abstractmethod
    def logger_name(self) -> str:
        """Nom du logger pour les messages console."""
        pass

    @property
    @abstractmethod
    def enabled_env_var(self) -> str:
        """Clé de la variable d'environnement pour activer le logger."""
        pass

    @property
    @abstractmethod
    def db_file_env_var(self) -> str:
        """Clé de la variable d'environnement pour le fichier de BDD."""
        pass

    @abstractmethod
    def _setup_backend(self, db_file: str) -> bool:
        """Prépare le backend de stockage (crée le fichier, la table, etc.). Retourne True si succès."""
        pass

    @abstractmethod
    def _write_log_to_backend(self, log_item: Any):
        """Écrit un seul item de log dans le backend."""
        pass

    @abstractmethod
    def _shutdown_backend(self):
        """Ferme proprement les connexions au backend (ex: db.close())."""
        pass

    # --- Logique commune ---

    def _lazy_initialize(self):
        with self._init_lock:
            if self._initialized_flag:
                return

            enabled = os.getenv(self.enabled_env_var, "false").lower() in ("true", "1", "yes")
            db_file = os.getenv(self.db_file_env_var)

            if enabled and db_file:
                if self._setup_backend(db_file):
                    self.is_enabled = True
                    self.log_queue = queue.Queue()
                    self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
                    self.worker_thread.start()
                    print(f"✅ {self.logger_name} auto-configuré. Logs dans '{db_file}'.")

            self._initialized_flag = True

    def _process_queue(self):
        while True:
            try:
                log_item = self.log_queue.get()
                if log_item is None: break
                self._write_log_to_backend(log_item)
                self.log_queue.task_done()
            except Exception as e:
                print(f"❌ Erreur dans le worker {self.logger_name} : {e}")

    def log(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        if not self._initialized_flag: self._lazy_initialize()
        if not self.is_enabled: return

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        details_str = f"- {details}" if details else ""
        console_output = f"[{self.logger_name}] {event_type} {details_str}"
        print(f"{self._GREEN}{console_output}{self._RESET}")

        self.log_queue.put({
            'timestamp': timestamp,
            'event_type': event_type,
            'details': details
        })

    def shutdown(self, wait=True):
        if not self._initialized_flag: self._lazy_initialize()
        if not self.is_enabled or not hasattr(self, 'log_queue'): return
        if wait: self.log_queue.join()
        self.log_queue.put(None)
        if hasattr(self, 'worker_thread'): self.worker_thread.join(timeout=5)
        self._shutdown_backend()
        print(f"✅ {self.logger_name} arrêté proprement.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.shutdown()
