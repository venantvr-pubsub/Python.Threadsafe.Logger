import time

from dotenv import load_dotenv

# Charger la configuration depuis le fichier .env à la racine
load_dotenv()

# Importer les loggers depuis la librairie (avec le nouveau nom de package)
from busylogger import sqlite_business_logger, json_business_logger


def run_app():
    """Une fonction qui simule l'activité de votre application."""
    print("Début de l'application...")
    for i in range(3):
        print(f"Opération #{i + 1}")
        sqlite_business_logger.log("SQL_EVENT", {"iteration": i, "status": "processing"})
        time.sleep(0.5)
        json_business_logger.log("JSON_EVENT", {"iteration": i, "details": "some data"})
        time.sleep(1)
    print("Fin des opérations.")


if __name__ == "__main__":
    print("Lancement de l'exemple avec gestion automatique des loggers...")

    # Le bloc 'with' garantit que shutdown() sera appelé pour les deux loggers
    # à la fin, même si une erreur se produit à l'intérieur.
    with sqlite_business_logger, json_business_logger:
        run_app()

    print("\nApplication terminée. Les loggers ont été arrêtés proprement.")