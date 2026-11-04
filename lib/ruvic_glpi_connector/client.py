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

# Estados de ticket en GLPI. Se acepta el código o el nombre (español/inglés).
TICKET_STATUSES = {
    1: "Nuevo",
    2: "En curso (asignado)",
    3: "En curso (planificado)",
    4: "En espera",
    5: "Resuelto",
    6: "Cerrado",
}
_STATUS_ALIASES = {
    "nuevo": 1, "new": 1,
    "en curso (asignado)": 2, "en curso": 2, "asignado": 2, "processing (assigned)": 2, "assigned": 2,
    "en curso (planificado)": 3, "planificado": 3, "processing (planned)": 3, "planned": 3,
    "en espera": 4, "pendiente": 4, "pending": 4, "waiting": 4,
    "resuelto": 5, "solucionado": 5, "solved": 5, "resolved": 5,
    "cerrado": 6, "closed": 6,
}
# Escalas de GLPI: 1 = Muy baja ... 5 = Muy alta (prioridad admite 6 = Mayor).
_SCALE_ALIASES = {"muy baja": 1, "very low": 1, "baja": 2, "low": 2, "media": 3, "medium": 3,
                  "alta": 4, "high": 4, "muy alta": 5, "very high": 5, "mayor": 6, "major": 6}
_SCALE_RANGES = {"urgency": (1, 5), "impact": (1, 5), "priority": (1, 6)}

# Códigos de error de GLPI que indican problema de credenciales o sesión.
_AUTH_ERROR_CODES = (
    "ERROR_WRONG_APP_TOKEN_PARAMETER",
    "ERROR_APP_TOKEN_PARAMETERS_MISSING",
    "ERROR_GLPI_LOGIN_USER_TOKEN",
    "ERROR_GLPI_LOGIN",
    "ERROR_LOGIN_PARAMETERS_MISSING",
    "ERROR_SESSION_TOKEN_INVALID",
    "ERROR_SESSION_TOKEN_MISSING",
    "ERROR_NOT_ALLOWED_IP",
)


def _parse_id(value: Any, name: str = "ticket_id") -> int:
    """Convierte un ID a entero positivo con un error claro si no lo es."""
    try:
        number = int(str(value).strip().lstrip("#"))
    except (TypeError, ValueError):
        raise GlpiDataError(f"{name} debe ser un número entero positivo; se recibió '{value}'.") from None
    if number <= 0:
        raise GlpiDataError(f"{name} debe ser mayor que cero; se recibió '{value}'.")
    return number


def _parse_status(value: Any) -> int:
    text = str(value).strip()
    code = _STATUS_ALIASES.get(text.lower())
    if code is None:
        try:
            code = int(text)
        except ValueError:
            code = None
    if code not in TICKET_STATUSES:
        valid = ", ".join(f"{k} ({v})" for k, v in TICKET_STATUSES.items())
        raise GlpiDataError(f"Estado '{value}' no válido para un ticket GLPI. Valores válidos: {valid}.")
    return code


def _parse_scale(field: str, value: Any) -> int:
    low, high = _SCALE_RANGES[field]
    text = str(value).strip()
    number = _SCALE_ALIASES.get(text.lower())
    if number is None:
        try:
            number = int(text)
        except ValueError:
            number = None
    if number is None or not low <= number <= high:
        raise GlpiDataError(
            f"{field} debe estar entre {low} y {high} (1 = muy baja, 5 = muy alta"
            f"{', 6 = mayor' if high == 6 else ''}); se recibió '{value}'."
        )
    return number


def _normalize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        if key == "status":
            normalized[key] = _parse_status(value)
        elif key in _SCALE_RANGES:
            normalized[key] = _parse_scale(key, value)
        else:
            normalized[key] = value
    return normalized


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

    @staticmethod
    def _glpi_error(response: Response) -> str:
        """Devuelve el código y mensaje de error de GLPI (formato ["ERROR_X", "mensaje"])."""
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500]
        if isinstance(payload, list) and payload:
            return " ".join(str(part) for part in payload[:2])
        return str(payload)[:500]

    def _handle_response(self, response: Response) -> Any:
        if response.status_code >= 400:
            detail = self._glpi_error(response)
            if response.status_code in {401, 403} or any(code in detail for code in _AUTH_ERROR_CODES):
                raise GlpiAuthError(
                    f"GLPI rechazó autenticación o permisos ({response.status_code}): {detail}. "
                    "Revisa App Token, User Token, que la API esté habilitada y el perfil del usuario."
                )
            if response.status_code == 404:
                raise GlpiDataError(f"Recurso GLPI no encontrado: {detail}")
            if response.status_code == 429:
                raise GlpiDataError("GLPI aplicó rate limiting (429). Espera y reintenta más tarde.")
            raise GlpiDataError(f"GLPI retornó HTTP {response.status_code}: {detail}")
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

    def create_ticket(self, title: str, content: str, urgency: int | str = 3, impact: int | str = 3, priority: int | str = 3, **extra_fields: Any) -> dict[str, Any]:
        """Crea un ticket en GLPI.

        Args:
            title: título del ticket (`name` en GLPI).
            content: descripción/contenido del ticket.
            urgency: urgencia 1 a 5 (1 = muy baja, 5 = muy alta). También acepta "alta", "media"...
            impact: impacto 1 a 5.
            priority: prioridad 1 a 6 (6 = mayor).
            extra_fields: otros campos GLPI soportados (por ejemplo `status`, `type`, `itilcategories_id`).
        Returns:
            Ticket creado tal como queda en GLPI (incluye `id`, `status`, `urgency`, `priority`).
        Ejemplo:
            >>> client.create_ticket('Error login', 'Usuario no puede entrar', urgency=4)
            {'id': 10, 'name': 'Error login', 'status': 1, ...}
        """
        if not title.strip(): raise GlpiDataError("title no puede estar vacío.")
        if not content.strip(): raise GlpiDataError("content no puede estar vacío.")
        fields = _normalize_fields({"urgency": urgency, "impact": impact, "priority": priority, **extra_fields})
        payload = {"input": {"name": title, "content": content, **fields}}
        data = self._request("POST", "/Ticket", json_body=payload)
        ticket_id = data.get("id") if isinstance(data, dict) else None
        self._logger.info("Ticket GLPI creado")
        if ticket_id:
            ticket = self.get_ticket(ticket_id)
            self._check_ignored_fields(ticket, extra_fields)
            return ticket
        return dict(data) if isinstance(data, dict) else {"response": data}

    def update_ticket(self, ticket_id: int | str, fields: dict[str, Any]) -> dict[str, Any]:
        """Actualiza un ticket GLPI y devuelve el ticket tal como quedó.

        Args:
            ticket_id: ID numérico del ticket.
            fields: campos a actualizar. `status` acepta 1-6 o el nombre del estado
                ("Nuevo", "En curso (asignado)", "En curso (planificado)", "En espera",
                "Resuelto", "Cerrado"); `urgency`/`impact` 1-5; `priority` 1-6.
        Returns:
            Ticket actualizado (mismo formato que get_ticket).
        Ejemplo:
            >>> client.update_ticket(10, {'status': 'Resuelto'})
            {'id': 10, 'status': 5, ...}
        """
        ticket_id = _parse_id(ticket_id)
        if not fields: raise GlpiDataError("fields no puede estar vacío.")
        fields = _normalize_fields(fields)
        current = self.get_ticket(ticket_id)
        unknown = [k for k in fields if not k.startswith("_") and k not in current]
        if unknown:
            raise GlpiDataError(
                f"Campos inexistentes en un ticket GLPI: {', '.join(unknown)}. "
                "Usa nombres técnicos de GLPI como name, content, status, urgency, impact, priority."
            )
        self._request("PUT", f"/Ticket/{ticket_id}", json_body={"input": fields})
        self._logger.info("Ticket GLPI actualizado")
        updated = self.get_ticket(ticket_id)
        self._check_ignored_fields(updated, fields)
        return updated

    @staticmethod
    def _check_ignored_fields(ticket: dict[str, Any], fields: dict[str, Any]) -> None:
        """Avisa si GLPI aceptó la petición pero no guardó status/urgency/impact.

        priority no se comprueba: GLPI la recalcula con la matriz urgencia x impacto.
        """
        ignored = [
            k for k in ("status", "urgency", "impact")
            if k in fields and k in ticket and str(ticket[k]) != str(fields[k])
        ]
        if ignored:
            detail = ", ".join(f"{k}: pedido {fields[k]}, quedó {ticket[k]}" for k in ignored)
            raise GlpiDataError(
                f"GLPI aceptó la petición pero no aplicó todos los cambios ({detail}). "
                "Puede deberse a reglas de negocio, a la matriz de prioridad o a permisos del perfil."
            )

    def get_ticket(self, ticket_id: int | str) -> dict[str, Any]:
        """Consulta un ticket GLPI por ID.

        Args:
            ticket_id: ID numérico del ticket.
        Returns:
            Ticket como dict. `status` es un código 1-6 (ver TICKET_STATUSES).
        Ejemplo:
            >>> client.get_ticket(10)
            {'id': 10, 'name': 'Error login', 'status': 1, ...}
        """
        ticket_id = _parse_id(ticket_id)
        try:
            data = self._request("GET", f"/Ticket/{ticket_id}")
        except GlpiDataError as exc:
            if "no encontrado" in str(exc) or "ERROR_ITEM_NOT_FOUND" in str(exc):
                raise GlpiDataError(f"No existe el ticket {ticket_id} en GLPI.") from None
            raise
        self._logger.info("Ticket GLPI consultado")
        return dict(data) if isinstance(data, dict) else {"response": data}

    def add_followup(self, ticket_id: int | str, content: str, is_private: bool = False) -> dict[str, Any]:
        """Agrega un seguimiento a un ticket GLPI.

        Args:
            ticket_id: ID numérico del ticket.
            content: contenido del seguimiento.
            is_private: True para un seguimiento privado (solo visible para técnicos).
        Returns:
            Respuesta GLPI con el `id` del seguimiento creado.
        Ejemplo:
            >>> client.add_followup(10, 'Se contactó al usuario')
            {'id': 20, 'message': ''}
        """
        ticket_id = _parse_id(ticket_id)
        if not content.strip(): raise GlpiDataError("content no puede estar vacío.")
        self.get_ticket(ticket_id)  # error claro si el ticket no existe
        payload = {"input": {"items_id": ticket_id, "itemtype": "Ticket", "content": content, "is_private": int(bool(is_private))}}
        data = self._request("POST", f"/Ticket/{ticket_id}/ITILFollowup", json_body=payload)
        self._logger.info("Seguimiento agregado a ticket GLPI")
        return dict(data) if isinstance(data, dict) else {"response": data}
