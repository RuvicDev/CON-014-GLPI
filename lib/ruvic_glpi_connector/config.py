"""Configuración del conector leída desde variables de entorno.

Prefijo: RUVIC_GLPI_
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from .exceptions import GlpiConfigError

ENV_PREFIX = "RUVIC_GLPI_"

def _to_bool(value: str, default: bool) -> bool:
    raw = (value or "").strip().lower()
    if raw == "": return default
    if raw in {"true", "1", "yes", "y", "on"}: return True
    if raw in {"false", "0", "no", "n", "off"}: return False
    raise GlpiConfigError("Configuración inválida: VERIFY_SSL debe ser true/false.")

@dataclass(frozen=True)
class GlpiConfig:
    """Parámetros para autenticar y usar GLPI REST API."""
    base_url: str
    app_token: str
    user_token: str
    verify_ssl: bool = True
    timeout: int = 20
    max_results: int = 100

    @property
    def api_url(self) -> str:
        """URL base de la API REST GLPI."""
        base = self.base_url.rstrip("/")
        if base.endswith("/apirest.php"):
            return base
        return f"{base}/apirest.php"

    @classmethod
    def from_env(cls) -> "GlpiConfig":
        """Construye la configuración desde variables RUVIC_GLPI_*.

        Raises:
            ValueError: si faltan variables requeridas.
            GlpiConfigError: si un valor opcional es inválido.
        """
        base_url = os.environ.get(f"{ENV_PREFIX}BASE_URL", "").strip().rstrip("/")
        app_token = os.environ.get(f"{ENV_PREFIX}APP_TOKEN", "").strip()
        user_token = os.environ.get(f"{ENV_PREFIX}USER_TOKEN", "").strip()
        missing = [n for n, v in ((f"{ENV_PREFIX}BASE_URL", base_url), (f"{ENV_PREFIX}APP_TOKEN", app_token), (f"{ENV_PREFIX}USER_TOKEN", user_token)) if not v]
        if missing:
            raise ValueError("Faltan variables de entorno del conector glpi: " + ", ".join(missing) + ". Configura el conector en Settings → Conectores.")
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise GlpiConfigError("RUVIC_GLPI_BASE_URL debe iniciar por http:// o https://.")
        try:
            timeout = int(os.environ.get(f"{ENV_PREFIX}TIMEOUT", "20").strip() or "20")
            max_results = int(os.environ.get(f"{ENV_PREFIX}MAX_RESULTS", "100").strip() or "100")
            verify_ssl = _to_bool(os.environ.get(f"{ENV_PREFIX}VERIFY_SSL", "true"), default=True)
        except ValueError as exc:
            raise GlpiConfigError("RUVIC_GLPI_TIMEOUT y RUVIC_GLPI_MAX_RESULTS deben ser enteros.") from exc
        if timeout <= 0 or timeout > 120:
            raise GlpiConfigError("RUVIC_GLPI_TIMEOUT debe estar entre 1 y 120 segundos.")
        if max_results <= 0 or max_results > 1000:
            raise GlpiConfigError("RUVIC_GLPI_MAX_RESULTS debe estar entre 1 y 1000.")
        return cls(base_url=base_url, app_token=app_token, user_token=user_token, verify_ssl=verify_ssl, timeout=timeout, max_results=max_results)
