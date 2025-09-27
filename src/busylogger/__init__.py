"""
Une librairie simple et robuste pour enregistrer des événements métier
de manière asynchrone, non-bloquante et thread-safe.
"""
from .json_business_logger import json_business_logger
from .sqlite_business_logger import sqlite_business_logger

__version__ = "0.2.0"

__all__ = [
    "sqlite_business_logger",
    "json_business_logger"
]