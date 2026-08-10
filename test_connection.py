"""Prueba de conexión estándar del conector GLPI."""
from __future__ import annotations

def test_connection() -> tuple[bool, str]:
    """Prueba App Token/User Token e initSession."""
    try:
        from ruvic_glpi_connector import GlpiAuthError, GlpiClient, GlpiConfigError, GlpiDataError, GlpiNetworkError, GlpiSecurityError
    except ImportError:
        return False, "La librería ruvic-glpi-connector no está instalada. Instala con: pip install git+https://github.com/tu-org/conector-glpi.git#subdirectory=lib"
    client = None
    try:
        client = GlpiClient(); client.ping()
    except ValueError as exc:
        return False, str(exc)
    except GlpiConfigError as exc:
        return False, f"Configuración inválida: {exc}"
    except GlpiAuthError as exc:
        return False, f"Autenticación o permisos GLPI inválidos: {exc}"
    except GlpiNetworkError as exc:
        return False, f"Error de red hacia GLPI: {exc}"
    except GlpiSecurityError as exc:
        return False, f"Bloqueo de seguridad: {exc}"
    except GlpiDataError as exc:
        return False, f"GLPI rechazó la solicitud: {exc}"
    except Exception as exc:
        return False, f"Error inesperado probando GLPI: {exc}"
    finally:
        if client:
            try: client.close()
            except Exception: pass
    return True, f"Conexión exitosa a GLPI en {client.config.api_url}."
if __name__ == "__main__":
    ok, message = test_connection(); print(f"{'OK' if ok else 'FALLO'}: {message}"); raise SystemExit(0 if ok else 1)
