import datetime
import logging
import os
import queue
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

# Configuration du logging de base pour voir les erreurs et avertissements de la librairie
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


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
    def _initialize_backend_for_worker(self):
        """Initialise les ressources (ex: connexion BDD) pour le thread de travail."""
        pass

    @abstractmethod
    def _write_log_to_backend(self, log_item: Any):
        """Écrit un seul item de log dans le backend."""
        pass

    @abstractmethod
    def _shutdown_backend(self):
        """Ferme proprement les connexions au backend (ex: db.close())."""
        pass

    def _lazy_initialize(self):
        with self._init_lock:
            if self._initialized_flag:
                return

            enabled = os.getenv(self.enabled_env_var, "false").lower() in ("true", "1", "yes")
            db_file = os.getenv(self.db_file_env_var)

            if enabled and db_file:
                if self._setup_backend(db_file):
                    self.is_enabled = True
                    # Utilisation d'une file de taille limitée pour éviter une surconsommation de mémoire
                    self.log_queue = queue.Queue(maxsize=1000)
                    self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
                    self.worker_thread.start()
                    print(f"✅ {self.logger_name} auto-configuré. Logs dans '{db_file}'.")

            self._initialized_flag = True

    def _process_queue(self):
        # Initialisation spécifique au thread (ex: connexion BDD)
        self._initialize_backend_for_worker()

        while True:
            try:
                log_item = self.log_queue.get()
                if log_item is None: break
                self._write_log_to_backend(log_item)
                self.log_queue.task_done()
            except Exception as e:
                # Utiliser le logging standard pour les erreurs internes
                logging.error(f"Erreur dans le worker {self.logger_name} : {e}")

    def log(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        if not self._initialized_flag: self._lazy_initialize()
        if not self.is_enabled: return

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        details_str = f"- {details}" if details else ""
        console_output = f"[{self.logger_name}] {event_type} {details_str}"
        print(f"{self._GREEN}{console_output}{self._RESET}")

        log_data = {
            'timestamp': timestamp,
            'event_type': event_type,
            'details': details
        }

        try:
            # Ne pas bloquer l'application si la file est pleine
            self.log_queue.put(log_data, block=False)
        except queue.Full:
            logging.warning(f"File d'attente du logger '{self.logger_name}' pleine. Le log a été ignoré.")

    def shutdown(self, wait=True):
        if not self._initialized_flag: self._lazy_initialize()
        if not self.is_enabled or not hasattr(self, 'log_queue'): return
        if wait: self.log_queue.join()
        self.log_queue.put(None)
        if hasattr(self, 'worker_thread'): self.worker_thread.join(timeout=5)
        self._shutdown_backend()
        print(f"✅ {self.logger_name} arrêté proprement.")

    def __enter__(self):
        self._lazy_initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.shutdown()

    def _reset_for_testing(self):
        """Réinitialise l'état interne du logger. POUR LES TESTS UNIQUEMENT."""
        # S'assure que le thread est bien arrêté s'il est en cours
        if hasattr(self, 'worker_thread') and self.worker_thread.is_alive():
            # CORRIGÉ : On attend la fin du traitement de la file.
            self.shutdown(wait=True)

        # Réinitialise les flags d'état
        self._initialized_flag = False
        self.is_enabled = False

        # Vide la queue au cas où un test précédent aurait échoué en laissant des items
        if hasattr(self, 'log_queue'):
            while not self.log_queue.empty():
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    continue
