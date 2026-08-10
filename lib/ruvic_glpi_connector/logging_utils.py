"""Logging configurable del conector GLPI. Nada de print() en la librería."""
from __future__ import annotations
import logging
_LOGGER_NAME = "ruvic_glpi_connector"

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configura y retorna el logger del conector.

    Args:
        level: Nivel de logging.
    Returns:
        Logger configurado.
    Ejemplo:
        >>> setup_logging("INFO").name
        'ruvic_glpi_connector'
    """
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger

def get_logger() -> logging.Logger:
    """Retorna el logger del conector."""
    return logging.getLogger(_LOGGER_NAME)
