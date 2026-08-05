# Master Spec — notificaciones v2

## Problema / Objetivo
Publicar y consumir el evento de notificación entre los dos servicios.

## Alcance
- **Incluye:** el emisor, el receptor y el acuerdo del evento.
- **No incluye:** los avisos por correo.

## Criterios de aceptación
- **AC-1 [repo-local]:** Given el emisor, When se crea una notificación, Then publica el evento.
- **AC-2 [repo-local]:** Given el receptor, When llega el evento, Then lo procesa.
- **AC-5 [repo-local]:** Given el panel, When se consulta el histórico, Then lista las notificaciones.
- **AC-3 [integration]:** Given los dos servicios arriba, When se crea una notificación, Then el receptor la procesa y responde 200.
- **AC-4 [integration]:** Given el acuerdo publicado, When se valida el esquema del evento, Then emisor y receptor coinciden.

## Contratos entre servicios
- **servicio-a expone:** evento `notificacion.creada {id, destinatario}`.
- **servicio-b consume:** `notificacion.creada` desde el bus.

## Anclas versionadas
- `acuerdo-evento: v3`
- `wiki-acuerdo: v1`
- `catalogo: v1`

## Reparto
| AC | Repo(s) | Tipo |
|---|---|---|
| AC-1 | servicio-a | repo-local |
| AC-2 | servicio-b | repo-local |
| AC-5 | servicio-c | repo-local |
| AC-3 | servicio-a + servicio-b | integration |
| AC-4 | servicio-a | integration |
