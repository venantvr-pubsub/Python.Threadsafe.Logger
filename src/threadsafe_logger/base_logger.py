import logging
import os
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

class BaseBusinessLogger(ABC):
    _instances = {}
    _lock = threading.Lock()
    _GREEN = "\033[92m"
    _RESET = "\033[0m"

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = False
        self.is_enabled = False
        self._init_lock = threading.Lock()
        self.backend = None

    @property
    @abstractmethod
    def logger_name(self) -> str:
        pass

    @property
    @abstractmethod
    def enabled_env_var(self) -> str:
        pass

    @property
    @abstractmethod
    def db_file_env_var(self) -> str:
        pass

    @staticmethod
    @abstractmethod
    def _create_backend(file_path: str):
        pass

    @abstractmethod
    def _on_backend_ready(self):
        pass

    @abstractmethod
    def log(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        pass

    def _lazy_initialize(self):
        with self._init_lock:
            if self._initialized: return
            enabled = os.getenv(self.enabled_env_var, "false").lower() in ("true", "1", "yes")
            db_file = os.getenv(self.db_file_env_var)
            if enabled and db_file:
                self.backend = self.__class__._create_backend(db_file)
                self.backend.start()
                if self.backend.wait_for_ready():
                    self.is_enabled = True
                    self._on_backend_ready()
                    print(f"✅ {self.logger_name} configured. Logs will be in '{db_file}'.")
                else:
                    logging.error(f"The backend for {self.logger_name} failed to start.")
            self._initialized = True

    def _ensure_initialized(self):
        if not self._initialized: self._lazy_initialize()

    def shutdown(self):
        self._ensure_initialized()
        if self.is_enabled and self.backend:
            self.backend.stop()
            print(f"✅ {self.logger_name} shut down cleanly.")

    def __enter__(self):
        self._ensure_initialized()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    # =================================================================
    # MÉTHODE CORRIGÉE / AJOUTÉE
    # =================================================================
    def _reset_for_testing(self):
        """
        Réinitialise l'état interne du logger pour les tests.
        Cette méthode arrête le backend, réinitialise les flags et supprime
        l'instance singleton pour garantir l'isolation des tests.
        """
        # 1. Arrête le backend s'il est actif
        if self.is_enabled and self.backend:
            self.shutdown()

        # 2. Réinitialise les attributs d'état de l'instance
        self._initialized = False
        self.is_enabled = False
        self.backend = None

        # 3. Supprime l'instance du cache singleton de la classe
        with self.__class__._lock:
            if self.__class__ in self.__class__._instances:
                del self.__class__._instances[self.__class__]
