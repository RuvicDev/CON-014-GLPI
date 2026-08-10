# Conector GLPI para Ruvic

Conector Ruvic para gestión de tickets en GLPI: crear ticket, actualizar ticket, consultar ticket y agregar seguimiento.

## Capacidades

1. `create_ticket(...)`.
2. `update_ticket(ticket_id, fields)`.
3. `get_ticket(ticket_id)`.
4. `add_followup(ticket_id, content, is_private=False)`.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ./lib
```

Desde Git:

```bash
pip install git+https://github.com/tu-org/conector-glpi.git#subdirectory=lib
```

## Variables de entorno

| Variable | Obligatoria | Descripción | Default |
|---|---:|---|---|
| `RUVIC_GLPI_BASE_URL` | Sí | URL base de GLPI | — |
| `RUVIC_GLPI_APP_TOKEN` | Sí | App Token GLPI | — |
| `RUVIC_GLPI_USER_TOKEN` | Sí | User Token GLPI | — |
| `RUVIC_GLPI_VERIFY_SSL` | No | Verificar SSL | `true` |
| `RUVIC_GLPI_TIMEOUT` | No | Timeout | `20` |
| `RUVIC_GLPI_MAX_RESULTS` | No | Máximo resultados | `100` |

## Pruebas locales

GLPI puede probarse con Docker levantando una instancia local con base de datos. Luego se debe activar la API REST, generar App Token y User Token.

```bash
python test_connection.py
python validate_local.py
```

`validate_local.py` crea un ticket real de prueba, lo consulta, lo actualiza y agrega un seguimiento.

## Seguridad

- Nunca subas App Token, User Token ni Session Token al repositorio.
- Usa una instancia GLPI local o de prueba.
- No se implementa eliminación de tickets.
