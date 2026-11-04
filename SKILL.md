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

## Valores válidos (no hace falta leer el código)

| Campo | Valores |
|---|---|
| `status` | 1 Nuevo, 2 En curso (asignado), 3 En curso (planificado), 4 En espera, 5 Resuelto, 6 Cerrado. Acepta el número o el nombre |
| `urgency` / `impact` | 1 Muy baja, 2 Baja, 3 Media, 4 Alta, 5 Muy alta. Acepta el número o el nombre ("alta") |
| `priority` | 1 a 6 (6 = Mayor). GLPI la recalcula con la matriz urgencia x impacto |

Los IDs son enteros (`10` o `"10"`); un ID no numérico o inexistente lanza `GlpiDataError` con un mensaje claro.
Un valor fuera de rango, un estado desconocido o un campo que no existe en el ticket también lanzan `GlpiDataError`; no se envía nada a GLPI.

## Capacidad 1 — Crear ticket

`create_ticket(title, content, urgency=3, impact=3, priority=3, **extra_fields)` devuelve el ticket creado completo (`id`, `status`, `urgency`, `priority`...).

```python
ticket = client.create_ticket("Error de acceso", "El usuario no puede iniciar sesión", urgency="alta")
print(ticket["id"], ticket["status"])
```

## Capacidad 2 — Actualizar ticket

`update_ticket(ticket_id, fields)` devuelve el ticket tal como quedó tras el cambio.

```python
updated = client.update_ticket(10, {"status": "En curso (asignado)"})
updated = client.update_ticket(10, {"status": 5})  # Resuelto
print(updated["status"])
```

## Capacidad 3 — Consultar ticket

```python
ticket = client.get_ticket(10)
print(ticket["name"], ticket["status"], ticket["urgency"], ticket["priority"])
```

## Capacidad 4 — Agregar seguimiento

`add_followup(ticket_id, content, is_private=False)`. Con `is_private=True` el seguimiento solo lo ven los técnicos.

```python
client.add_followup(10, "Se contactó al usuario y se escaló a N2")
client.add_followup(10, "Nota interna para el equipo", is_private=True)
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
6. No cambies el estado de otros tickets para "restaurarlos" si el usuario no lo pidió.
