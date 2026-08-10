"""Excepciones propias del conector GLPI."""

class GlpiConnectorError(Exception):
    """Error base del conector GLPI."""

class GlpiConfigError(GlpiConnectorError):
    """Falta configuración requerida o algún valor de configuración es inválido."""

class GlpiAuthError(GlpiConnectorError):
    """Credenciales GLPI inválidas, sesión rechazada o permisos insuficientes."""

class GlpiNetworkError(GlpiConnectorError):
    """Error de red, DNS, SSL, timeout o GLPI no alcanzable."""

class GlpiDataError(GlpiConnectorError):
    """Solicitud inválida, ticket inexistente, payload inválido o error de datos GLPI."""

class GlpiSecurityError(GlpiConnectorError):
    """Operación bloqueada por reglas de seguridad del conector."""
