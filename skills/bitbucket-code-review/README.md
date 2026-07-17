# bitbucket-code-review

Hace **code review de un Pull Request de Bitbucket** usando el MCP de Bitbucket y entrega una
**decisión consolidada**. La revisión la puede hacer el **modelo que conduce la sesión**, uno o más
**modelos de otra familia** (Codex/Claude, estilo cross-model, para romper la correlación de errores
del mismo modelo), o ambos. Con confirmación explícita, **publica** la decisión como comentario en el
PR, puede **aprobar** o **solicitar cambios**, y en una re-pasada **responde y resuelve su propio
comentario**.

Es la versión Bitbucket de la skill oficial de code review (atada a GitHub vía `gh`). Aquí: MCP de
Bitbucket + panel cross-model + escritura con gate + seguimiento local en `.pr-review/`.

## Qué hace

- **Panel de revisores.** Según lo que pidas, revisa el conductor, un externo de otra familia, o
  varios; si hay más de uno, **consolida** en una sola conclusión y, si los veredictos difieren, te
  pide que arbitres.
- **Cross-model author-aware.** El externo se elige de **otra familia** que el conductor (mismo
  modelo = errores correlacionados). La familia del conductor se determina por el **modelo de
  respaldo, no por el CLI** (Claude Code puede estar redirigido vía `ANTHROPIC_BASE_URL`).
- **Enfocada en `cocha-digital/results`.** Además de correctitud, aplica el checklist de
  **arquitectura-target** (Flux/adapter/Signals), cruza **criterios de aceptación de Jira** y ofrece
  **QA local** opcional del funnel afectado (delegado a `local-qa-playwright`).
- **Solo líneas modificadas**, con cita verificable (archivo + rango + fragmento) y rúbrica de
  confianza ≥80. Deduplica contra comentarios de terceros (marca ecos, no re-pide lo ya señalado).
- **Seguimiento local.** `.pr-review/<pr-id>/` (untracked) registra `sha`, veredicto y `comment-id`
  propio por pasada, para re-pasadas sin re-revisar.

## Cuándo usarla

Cuando el usuario pida "code review", "revisa el PR", "review del PR \<id\>", "review con
codex/claude", "segunda opinión del PR", "aprueba el PR" o "solicita cambios" de Bitbucket.

No es `sdd-pr-feedback`: esta skill **produce** el review (propone comentarios); `sdd-pr-feedback`
**reacciona** a los comentarios ya publicados. Tampoco resuelve/responde comentarios de terceros.

## Invocación

```
code review del PR 1234            # panel = solo el conductor
haz el code review con codex       # delegado a Codex (el conductor solo orquesta)
revisa tú y que codex también      # conductor + Codex, consolidado
segunda opinión del PR             # suma un externo de otra familia
aprueba el PR / solicita cambios   # acción de estado (con gate separado)
```

Sin PR id, detecta el PR **OPEN** de la rama actual.

## Requisitos

- **MCP de Bitbucket** (`mcp__bitbucket__bb_get` / `bb_post` / `bb_delete`). Sin capacidad de
  escritura, degrada a **solo proponer** el comentario. Sin lectura, avisa y se detiene.
- **Revisor Codex** (subagente `codex:codex-rescue` o CLI `codex exec -s read-only`) y/o **revisor
  Claude** (CLI `claude -p`) — **opcionales**; si faltan, ese revisor queda `UNAVAILABLE` y sigue con
  los disponibles.
- **`local-qa-playwright`** (opcional) para el QA local en vivo del Paso 7b.
- MCP de **Atlassian** (opcional) para cruzar los AC de Jira; degrada sin bloquear.

## Garantías

- **Lectura libre, escritura con gate.** Todo `bb_post`/`bb_delete` pasa por un preview con recurso,
  acción y texto exacto, y espera confirmación afirmativa. `approve` se confirma **por separado**.
- **El conductor es el único que escribe** en Bitbucket; los revisores externos corren read-only y
  solo devuelven hallazgos + veredicto.
- **Nunca mergea** el PR ni toca archivos trackeados del repo (la única escritura en disco es
  `.pr-review/` untracked, y el worktree efímero si lo elegís).
- El comentario publicado **no expone** el reparto de modelos ni el término "cross-model"; solo lleva
  el descargo de autoría IA. Ese detalle va al chat.

Funciona en Claude Code y Codex (detección de tools por capacidad).
