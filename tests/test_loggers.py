import json
import os
import sqlite3

import pytest

from busylogger import sqlite_business_logger, json_business_logger


# noinspection PyProtectedMember
@pytest.fixture
def setup_env_vars(tmp_path, monkeypatch):
    """
    Prépare un environnement de test propre.
    """
    # ÉTAPE 1: On réinitialise l'état AVANT de configurer l'environnement.
    # noinspection PyProtectedMember
    sqlite_business_logger._reset_for_testing()
    # noinspection PyProtectedMember
    json_business_logger._reset_for_testing()

    db_file = tmp_path / "test_events.db"
    json_file = tmp_path / "test_events.jsonl"

    monkeypatch.setenv("SQLITE_BUSINESS_LOGGER_ENABLED", "true")
    monkeypatch.setenv("SQLITE_BUSINESS_LOGGER_DB_FILE", str(db_file))
    monkeypatch.setenv("JSON_BUSINESS_LOGGER_ENABLED", "true")
    monkeypatch.setenv("JSON_BUSINESS_LOGGER_DB_FILE", str(json_file))

    yield db_file, json_file

    sqlite_business_logger._reset_for_testing()
    json_business_logger._reset_for_testing()


def test_singleton_pattern():
    """Vérifie que l'on obtient bien la même instance du logger à chaque fois."""
    from busylogger import sqlite_business_logger as instance1
    from busylogger import sqlite_business_logger as instance2
    assert instance1 is instance2


def test_loggers_are_disabled_by_default():
    """Vérifie que sans variables d'environnement, les loggers sont inactifs."""
    # On s'assure que l'état est propre avant ce test aussi.
    sqlite_business_logger._reset_for_testing()

    sqlite_business_logger.log("SHOULD_NOT_BE_LOGGED", {})

    assert not sqlite_business_logger.is_enabled
    assert not os.path.exists("./logs/business_events.db")


def test_sqlite_logger_writes_data_correctly(setup_env_vars):
    """
    Teste le cycle complet : log -> shutdown -> vérification des données en BDD.
    """
    db_file, _ = setup_env_vars

    event_data = {"order_id": "XYZ-123", "amount": 99.99}

    with sqlite_business_logger:
        sqlite_business_logger.log("ORDER_CREATED", event_data)

    assert os.path.exists(db_file)

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT event_type, details_json FROM business_events")
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == "ORDER_CREATED"
        assert json.loads(row[1]) == event_data


def test_json_logger_with_context_manager(setup_env_vars):
    """
    Teste l'écriture dans le fichier JSONL en utilisant le gestionnaire de contexte 'with'.
    """
    _, json_file = setup_env_vars

    event_data = {"user_id": "usr-456", "action": "login"}

    with json_business_logger:
        json_business_logger.log("USER_AUTHENTICATION", event_data)

    assert os.path.exists(json_file)

    # MODIFIÉ : Lecture d'un fichier au format JSON Lines (une ligne = un JSON)
    with open(json_file, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        assert first_line  # S'assure que la ligne n'est pas vide

        data = json.loads(first_line)

        assert data['event_type'] == "USER_AUTHENTICATION"
        assert data['details'] == event_data
