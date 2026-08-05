# Master Spec — notificaciones v2

## Problema / Objetivo
Publicar y consumir el evento de notificación entre los dos servicios.

## Alcance
- **Incluye:** el emisor, el receptor y el acuerdo del evento.
- **No incluye:** los avisos por correo.

## Criterios de aceptación
- **AC-1 [repo-local]:** Given el emisor, When se crea una notificación, Then publica el evento.
- **AC-2 [repo-local]:** Given el receptor, When llega el evento, Then lo procesa.

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
