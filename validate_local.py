"""Validación local del conector GLPI contra GLPI real.

Requiere RUVIC_GLPI_* apuntando a una instancia GLPI local/Docker o de prueba.
Crea un ticket real, lo consulta, lo actualiza y agrega un seguimiento.
"""
from __future__ import annotations
from ruvic_glpi_connector import GlpiClient, setup_logging
setup_logging("INFO")
client = GlpiClient()
try:
    print("== Ping =="); print(client.ping())
    print("== Crear ticket =="); created = client.create_ticket("Prueba local Ruvic GLPI", "Ticket creado por validate_local.py", urgency=3, impact=3, priority=3); print(created)
    ticket_id = int(created.get("id") or created.get("input", {}).get("id") or created.get("response", {}).get("id"))
    print("== Consultar ticket =="); print(client.get_ticket(ticket_id))
    print("== Actualizar ticket =="); print(client.update_ticket(ticket_id, {"priority": 4}))
    print("== Agregar seguimiento =="); print(client.add_followup(ticket_id, "Seguimiento agregado por validate_local.py", is_private=False))
    print("Validación GLPI completa. Ticket de prueba creado:", ticket_id)
finally:
    client.close()
