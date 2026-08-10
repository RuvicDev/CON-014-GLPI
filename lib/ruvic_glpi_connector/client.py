"""Cliente para GLPI REST API.

Capacidades:
- create_ticket(): crear ticket.
- update_ticket(): actualizar ticket.
- get_ticket(): consultar ticket.
- add_followup(): agregar seguimiento a un ticket.

Autenticación estándar GLPI: App-Token + Authorization user_token para initSession,
y luego App-Token + Session-Token para las operaciones.
"""
from __future__ import annotations
from typing import Any
import requests
from requests import Response
from .config import GlpiConfig
from .exceptions import GlpiAuthError, GlpiDataError, GlpiNetworkError
from .logging_utils import get_logger

class GlpiClient:
    """Cliente para gestión de tickets en GLPI.

    Args:
        config: configuración opcional. Si se omite, lee RUVIC_GLPI_*.

    Ejemplo:
        >>> client = GlpiClient()
        >>> client.get_ticket(1)
        {'id': 1, 'name': 'Ticket de prueba'}
    """
    def __init__(self, config: GlpiConfig | None = None) -> None:
        self.config = config or GlpiConfig.from_env()
        self._logger = get_logger()
        self._session = requests.Session()
        self._session_token: str | None = None

    def _url(self, path: str) -> str:
        clean = path if path.startswith("/") else f"/{path}"
        return self.config.api_url + clean

    def _headers(self, authenticated: bool = True) -> dict[str, str]:
        headers = {"App-Token": self.config.app_token, "Accept": "application/json", "Content-Type": "application/json"}
        if authenticated:
            if not self._session_token:
                self.init_session()
            headers["Session-Token"] = self._session_token or ""
        else:
            headers["Authorization"] = f"user_token {self.config.user_token}"
        return headers

    def _handle_response(self, response: Response) -> Any:
        if response.status_code in {401, 403}:
            raise GlpiAuthError(f"GLPI rechazó autenticación o permisos ({response.status_code}). Revisa App Token, User Token, API habilitada y perfil del usuario.")
        if response.status_code == 404:
            raise GlpiDataError("Recurso GLPI no encontrado. Verifica ticket_id o endpoint.")
        if response.status_code == 429:
            raise GlpiDataError("GLPI aplicó rate limiting (429). Espera y reintenta más tarde.")
        if response.status_code >= 400:
            raise GlpiDataError(f"GLPI retornó HTTP {response.status_code}: {response.text[:500]}")
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise GlpiDataError("GLPI respondió contenido no JSON cuando se esperaba JSON.") from exc

    def _request(self, method: str, path: str, json_body: dict[str, Any] | None = None, params: dict[str, Any] | None = None, authenticated: bool = True) -> Any:
        try:
            response = self._session.request(method=method.upper(), url=self._url(path), json=json_body, params={k: v for k, v in (params or {}).items() if v is not None}, headers=self._headers(authenticated=authenticated), timeout=self.config.timeout, verify=self.config.verify_ssl)
        except requests.exceptions.SSLError as exc:
            raise GlpiNetworkError("Error SSL conectando con GLPI. Verifica certificado o RUVIC_GLPI_VERIFY_SSL.") from exc
        except requests.exceptions.Timeout as exc:
            raise GlpiNetworkError(f"Timeout conectando con GLPI ({self.config.timeout}s).") from exc
        except requests.exceptions.RequestException as exc:
            raise GlpiNetworkError(f"No se pudo conectar con GLPI: {exc}.") from exc
        return self._handle_response(response)

    def init_session(self) -> str:
        """Inicia sesión en GLPI y obtiene Session-Token.

        Returns:
            Session token de GLPI.
        Ejemplo:
            >>> token = client.init_session()
            >>> bool(token)
            True
        """
        data = self._request("GET", "/initSession", authenticated=False)
        token = data.get("session_token") if isinstance(data, dict) else None
        if not token:
            raise GlpiAuthError("GLPI no retornó session_token en initSession. Revisa tokens y API habilitada.")
        self._session_token = token
        self._logger.info("Sesión GLPI iniciada")
        return token

    def close(self) -> None:
        """Cierra la sesión GLPI si existe.

        Ejemplo:
            >>> client.close()
        """
        if self._session_token:
            try:
                self._request("GET", "/killSession")
            finally:
                self._session_token = None
                self._logger.info("Sesión GLPI cerrada")

    def ping(self) -> bool:
        """Verifica conexión iniciando sesión y consultando datos del usuario activo.

        Returns:
            True si GLPI responde correctamente.
        Ejemplo:
            >>> client.ping()
            True
        """
        self.init_session()
        self._request("GET", "/getFullSession")
        self._logger.info("Ping exitoso a GLPI")
        return True

    def create_ticket(self, title: str, content: str, urgency: int = 3, impact: int = 3, priority: int = 3, **extra_fields: Any) -> dict[str, Any]:
        """Crea un ticket en GLPI.

        Args:
            title: título del ticket (`name` en GLPI).
            content: descripción/contenido del ticket.
            urgency: urgencia GLPI, normalmente 1 a 5.
            impact: impacto GLPI, normalmente 1 a 5.
            priority: prioridad GLPI, normalmente 1 a 5.
            extra_fields: otros campos GLPI soportados.
        Returns:
            Ticket creado o respuesta GLPI.
        Ejemplo:
            >>> client.create_ticket('Error login', 'Usuario no puede entrar')
            {'id': 10, ...}
        """
        if not title.strip(): raise GlpiDataError("title no puede estar vacío.")
        if not content.strip(): raise GlpiDataError("content no puede estar vacío.")
        payload = {"input": {"name": title, "content": content, "urgency": int(urgency), "impact": int(impact), "priority": int(priority), **extra_fields}}
        data = self._request("POST", "/Ticket", json_body=payload)
        self._logger.info("Ticket GLPI creado")
        return dict(data) if isinstance(data, dict) else {"response": data}

    def update_ticket(self, ticket_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        """Actualiza un ticket GLPI.

        Args:
            ticket_id: ID numérico del ticket.
            fields: campos a actualizar.
        Returns:
            Respuesta GLPI.
        Ejemplo:
            >>> client.update_ticket(10, {'priority': 4})
            {'id': 10, ...}
        """
        if int(ticket_id) <= 0: raise GlpiDataError("ticket_id debe ser mayor que cero.")
        if not fields: raise GlpiDataError("fields no puede estar vacío.")
        data = self._request("PUT", f"/Ticket/{int(ticket_id)}", json_body={"input": fields})
        self._logger.info("Ticket GLPI actualizado")
        return dict(data) if isinstance(data, dict) else {"response": data}

    def get_ticket(self, ticket_id: int) -> dict[str, Any]:
        """Consulta un ticket GLPI por ID.

        Args:
            ticket_id: ID numérico del ticket.
        Returns:
            Ticket como dict.
        Ejemplo:
            >>> client.get_ticket(10)
            {'id': 10, 'name': 'Error login'}
        """
        if int(ticket_id) <= 0: raise GlpiDataError("ticket_id debe ser mayor que cero.")
        data = self._request("GET", f"/Ticket/{int(ticket_id)}")
        self._logger.info("Ticket GLPI consultado")
        return dict(data) if isinstance(data, dict) else {"response": data}

    def add_followup(self, ticket_id: int, content: str, is_private: bool = False) -> dict[str, Any]:
        """Agrega un seguimiento a un ticket GLPI.

        Args:
            ticket_id: ID numérico del ticket.
            content: contenido del seguimiento.
            is_private: si el seguimiento es privado.
        Returns:
            Respuesta GLPI.
        Ejemplo:
            >>> client.add_followup(10, 'Se contactó al usuario')
            {'id': 20, ...}
        """
        if int(ticket_id) <= 0: raise GlpiDataError("ticket_id debe ser mayor que cero.")
        if not content.strip(): raise GlpiDataError("content no puede estar vacío.")
        payload = {"input": {"items_id": int(ticket_id), "itemtype": "Ticket", "content": content, "is_private": int(bool(is_private))}}
        data = self._request("POST", f"/Ticket/{int(ticket_id)}/ITILFollowup", json_body=payload)
        self._logger.info("Seguimiento agregado a ticket GLPI")
        return dict(data) if isinstance(data, dict) else {"response": data}
