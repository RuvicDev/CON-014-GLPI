---
name: glpi
description: "Usa la librería ruvic_glpi_connector para gestionar tickets en GLPI: crear tickets, actualizar tickets, consultar tickets y agregar seguimientos. Úsala cuando el usuario pida operar tickets GLPI o ITSM."
triggers:
- glpi
- ticket glpi
- itsm
- helpdesk
- crear ticket
- seguimiento
---

# Conector GLPI (ruvic_glpi_connector)

## Regla crítica de credenciales

El código generado NUNCA hardcodea credenciales. Siempre se leen de variables de entorno:

| Variable | Contenido |
|---|---|
| `RUVIC_GLPI_BASE_URL` | URL base de GLPI |
| `RUVIC_GLPI_APP_TOKEN` | App Token de GLPI |
| `RUVIC_GLPI_USER_TOKEN` | User Token de GLPI |
| `RUVIC_GLPI_VERIFY_SSL` | Verificación SSL opcional |
| `RUVIC_GLPI_TIMEOUT` | Timeout opcional |
| `RUVIC_GLPI_MAX_RESULTS` | Máximo de resultados |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en Settings → Conectores. Nunca uses variables con alias `_DEFAULT_`, `_TEST_` o `_PRODUCCION_`.

## Conexión

```python
from ruvic_glpi_connector import GlpiClient
client = GlpiClient()
```

## Capacidad 1 — Crear ticket

```python
ticket = client.create_ticket("Error de acceso", "El usuario no puede iniciar sesión")
print(ticket)
```

## Capacidad 2 — Actualizar ticket

```python
updated = client.update_ticket(10, {"priority": 4})
print(updated)
```

## Capacidad 3 — Consultar ticket

```python
ticket = client.get_ticket(10)
print(ticket)
```

## Capacidad 4 — Agregar seguimiento

```python
followup = client.add_followup(10, "Se contactó al usuario y se escaló a N2")
print(followup)
```

## Manejo de errores

```python
from ruvic_glpi_connector import GlpiAuthError, GlpiConfigError, GlpiDataError, GlpiNetworkError
try:
    ticket = client.get_ticket(10)
except GlpiConfigError as exc:
    print(f"Configuración inválida: {exc}")
except GlpiAuthError:
    print("App Token, User Token o permisos GLPI inválidos")
except GlpiNetworkError:
    print("No se pudo alcanzar GLPI")
except GlpiDataError as exc:
    print(f"GLPI rechazó la solicitud: {exc}")
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de `RUVIC_GLPI_*`.
2. Nunca imprimas App Token, User Token ni Session Token.
3. Cierra sesión con `client.close()` al finalizar scripts largos.
4. Confirma con el usuario antes de crear o actualizar tickets reales.
5. No implementes eliminación de tickets; no está soportada en este conector.
