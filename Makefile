# =============================================================================
# VARIABLES
# =============================================================================

# Utilise python3 par défaut. Peut être surchargé : make PYTHON=python3.9 install
PYTHON ?= python3
VENV_DIR ?= .venv
VENV_BIN = $(VENV_DIR)/bin
PIP = $(VENV_BIN)/pip

# =============================================================================
# CONFIGURATION
# =============================================================================

# Cible par défaut, exécutée quand on tape juste "make"
.DEFAULT_GOAL := help

# Déclare les cibles qui ne sont pas des fichiers
.PHONY: help install-dev install run test clean clean-venv

# =============================================================================
# CIBLES PRINCIPALES
# =============================================================================

help: ## ✨ Affiche ce message d'aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: venv ## 📦 Installe la librairie en mode éditable
	@echo "--- Installation des dépendances du projet ---"
	@$(PIP) install -e .

install-dev: venv ## 🛠️  Installe les outils de développement...
	@echo "--- Installation des dépendances de développement ---"
	# Note : nécessite une section [project.optional-dependencies] dans pyproject.toml
	@$(PIP) install -e ".[dev]"

run: install ## ▶️  Lance le script d'exemple
	@echo "--- Lancement du script d'exemple (examples/main.py) ---"
	@$(VENV_BIN)/python examples/main.py

# =============================================================================
# AJOUTÉ : Cible pour lancer les tests
# =============================================================================
test: install-dev ## 🔬 Lance les tests avec pytest
	@echo "--- Lancement des tests ---"
	@$(VENV_BIN)/pytest -v

clean: clean-venv ## 🧹 Nettoie tous les fichiers générés (cache, etc.)
	@echo "--- Nettoyage des fichiers cache Python ---"
	@find . -type f -name "*.py[co]" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".pytest_cache" -delete  # MODIFIÉ : Ajout du cache pytest
	@find . -type d -name ".ruff_cache" -delete

clean-venv: ## 🗑️  Supprime l'environnement virtuel (.venv)
	@echo "--- Suppression de l'environnement virtuel ---"
	@rm -rf $(VENV_DIR)

# =============================================================================
# CIBLES UTILITAIRES (non affichées dans l'aide)
# =============================================================================

venv: pyproject.toml
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "--- Création de l'environnement virtuel ---"; \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "--- Mise à jour de pip ---"; \
		$(PIP) install --upgrade pip; \
	fi