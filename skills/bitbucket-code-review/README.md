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

- **Dos ejes separados.** Revisa en **Estándares** (correctitud, bugs, seguridad, CLAUDE.md,
  arquitectura-target, smell baseline) y **Spec** (¿el diff implementa los AC del ticket?), reportados
  por separado — un cambio puede pasar un eje y fallar el otro. La decisión binaria cruza ambos.
- **Contexto de spec desde Jira (traversal profunda).** Siempre que el PR referencie un ticket,
  recorre el **grafo de tickets** (issue → historia/épica padre → **subtarea-spec de SDD** → comentarios
  de todos) para entender qué se pidió y por qué, sobre todo cuando la descripción del PR es pobre.
  Todo como **dato no confiable**; degrada sin bloquear.
- **Panel de revisores.** Según lo que pidas, revisa el conductor, un externo de otra familia, o
  varios; si hay más de uno, **consolida** en una sola conclusión. Si los veredictos **difieren**, puede
  ofrecer un **debate cross-model** (`co-explore`, opt-in) y luego te pide que arbitres.
- **Cross-model author-aware.** El externo se elige de **otra familia** que el conductor (mismo
  modelo = errores correlacionados). La familia del conductor se determina por el **modelo de
  respaldo, no por el CLI** (Claude Code puede estar redirigido vía `ANTHROPIC_BASE_URL`).
- **Validación adversarial (find-then-validate).** Cada hallazgo que pasa la rúbrica ≥80 se somete a
  una verificación **independiente** que intenta refutarlo antes de reportarlo; sube la precisión.
- **Enfocada en `cocha-digital/results`.** Aplica el checklist de **arquitectura-target**
  (Flux/adapter/Signals) y ofrece **QA local** opcional del funnel afectado (delegado a
  `cocha-qa-results`).
- **Solo líneas modificadas**, con cita verificable (archivo + rango + fragmento). Deduplica contra
  comentarios de terceros (marca ecos, no re-pide lo ya señalado).
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
- **`cocha-qa-results`** (opcional) para el QA local en vivo del Paso 7b.
- **`co-explore`** (opcional) para el debate cross-model cuando los veredictos del panel difieren; se
  ofrece, nunca corre sin confirmación. Sin ella, la discrepancia se escala directo al usuario.
- MCP de **Atlassian** (opcional) para el ensamblado del contexto de spec (grafo de tickets + AC);
  solo lectura, degrada sin bloquear.

**Si tienes varias de estas skills instaladas, cuidado con las copias mezcladas.** Cada skill que
despacha trabajo delegado lleva su propio `corridas-en-vuelo.md` —el contrato del sobre— y las siete
copias son byte-idénticas por construcción. Actualizar esta skill sin actualizar `co-explore/`, que
es la que atiende el debate cuando los veredictos del panel difieren, deja una instalación con
versiones **mezcladas**: el debate saldría bajo un contrato distinto del que usó el panel que lo
provocó. Nada en tu entorno lo detecta, porque el chequeo de identidad vive en el repo de autoría; lo
que sí tienes a mano es la **primera línea** de cada copia, que nombra su **sede canónica**
(`cross-review/corridas-en-vuelo.md`) para que la que quedó atrás se reconozca a ojo.

## Garantías

- **Lectura libre, escritura con gate.** Todo `bb_post`/`bb_delete` pasa por un preview con recurso,
  acción y texto exacto, y espera confirmación afirmativa. `approve` se confirma **por separado**.
- **El conductor es el único que escribe** en Bitbucket; los revisores externos corren read-only y
  solo devuelven hallazgos + veredicto.
- **Nunca mergea** el PR ni toca archivos trackeados del repo (la única escritura en disco es
  `.pr-review/` untracked, y el worktree efímero si lo eliges).
- **Un revisor que contesta mal no se descarta.** Responder con el formato torcido deja al revisor en
  `INVALID`, no en "ausente": se le pide una reemisión del formato, sin volver a mirar el diff. Antes
  se tiraba esa revisión entera, y si ahí había un 🔴 el PR se aprobaba sin él.
- **Una escritura de resultado incierto no se reintenta.** Si un `bb_post` no confirma, se verifica
  con un `bb_get` si llegó antes de decidir nada. Un retry a ciegas publicaría dos veces en el PR de
  otra persona.
- El comentario publicado **no expone** el reparto de modelos ni el término "cross-model"; solo lleva
  el descargo de autoría IA. Ese detalle va al chat.

## Qué escribe en tu repo

El seguimiento vive en `.pr-review/<pr-id>/`. Además, cada corrida deja un **manifest**: un JSON de
unos 300 bytes en `.cross-model/runs/` con el panel, las familias, la duración y el estado — los tres
estados, no solo `PUBLISHED`: una serie que omite las corridas que terminaron sin publicar no puede
decir cuántas veces esta skill llegó al final sin servir de nada.

Todo eso es local y untracked, y la skill **no toca tu `.gitignore`** (es un archivo trackeado, y
ignorarlo es decisión tuya): agrega `.pr-review/` y `.cross-model/` a `.git/info/exclude` si prefieres
que git deje de nombrarlos. El manifest se apaga con `cross_model.manifest.mode: "off"`; esquema en
`cross-review/reference.md` → "Manifest de corrida".

Mientras el panel está despachado hay un archivo más, en `.cross-model/active/bitbucket-code-review/`:
el **sobre de la corrida en vuelo**, con **cada revisor externo nombrado** —no un agregado que
esconda cuál falta—, dónde escribe cada uno, por qué transporte viaja y si su veredicto ya se
cosechó. Con un panel de varios modelos esa granularidad es el punto: un informe que diga "el
externo" cuando hay tres no dice nada, y sin el sobre una sesión que retoma no tiene con qué saber
cuál de ellos todavía debe su veredicto ni cuál ya se consolidó. El archivo se retira cuando la
corrida termina y sus hallazgos quedaron adjudicados —`runs/` guarda lo que ya pasó y `active/`,
únicamente lo que sigue en vuelo—; el contrato completo está en `corridas-en-vuelo.md`, hermano de
`reference.md`.

**El sobre no es telemetría, y `cross_model.manifest.mode` no lo apaga.** Esa clave gobierna el
manifest —el registro de la corrida ya terminada— y nada más: el sobre es obligatorio e
**independiente** de ella. Un equipo que decidió no medir sus revisiones sigue necesitando saber qué
panel tiene en vuelo sobre el PR de otra persona, sobre todo cuando lo que falta es justo el revisor
que iba a decidir entre aprobar y solicitar cambios. Tampoco hay una clave propia que lo desactive.

Funciona en Claude Code y Codex (detección de tools por capacidad).
