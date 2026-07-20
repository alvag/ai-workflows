---
name: cross-model-orca
description: >-
  Skill-librería que aloja el protocolo común del transporte cross-model
  `orca-session` y el único artefacto ejecutable del repo: un módulo Node del
  lado del conductor que crea una sesión fresca de la otra familia (Codex
  cuando conduce Claude; Claude cuando conduce Codex) vía Orca, detecta el fin
  de su turno y cosecha el transcript con autoridad (envelope `X-CMO` +
  `STATUS: done`), con degradación transparente al CLI headless cuando Orca no
  está disponible. No es una skill que el usuario invoque para "hacer algo":
  co-explore explora/hipotetiza, cross-review revisa artefactos de diseño,
  cross-implement escribe código, y esta librería solo provee el transporte
  (tres capas de control, matriz de lanzamiento, matriz de raíces de
  persistencia, privacidad v1) que esas skills y sdd-flow/sdd-orchestrator
  consumen leyendo sus archivos. No se invoca espontáneamente: es una
  librería de referencia que consumen co-explore, cross-review,
  cross-implement, sdd-flow y sdd-orchestrator.
disable-model-invocation: true
---

# cross-model-orca — protocolo y artefacto del transporte `orca-session`

`disable-model-invocation: true` está puesto a propósito: el contenido de esta skill es genérico
(protocolo de transporte, no una tarea puntual) y competiría por el auto-trigger con las skills
que sí hacen algo. Consecuencia asumida: nadie invoca `cross-model-orca` por el Skill tool —
`co-explore`, `cross-review`, `cross-implement`, `sdd-flow` y `sdd-orchestrator` la consumen
**leyendo sus archivos** (`SKILL.md`, `reference.md`, `install.md`, `assets/**`) desde su propio
paso "resolver transporte".

## 1. Qué es / arquitectura en breve

`orca-session` es un transporte alternativo al CLI headless de hoy (`codex exec` / `claude -p`)
para el mismo patrón cross-model del repo: el conductor delega en un modelo de **la otra
familia**. En vez de un subproceso efímero, el conductor usa Orca para abrir una **sesión
interactiva fresca** de la otra familia, la deja trabajar, y luego **cosecha** su resultado.

Flujo en breve:

1. El conductor crea una sesión **fresca** (nunca reutiliza una sesión ajena) de la otra familia
   vía Orca, con una de las tres capas de control activas.
2. El secundario trabaja de forma read-only o write-capable según el rol, y termina su turno
   emitiendo el envelope con autoridad (sección 2) como última salida.
3. El secundario **no cosecha ni escribe su propio informe**: solo produce el envelope en su
   transcript. Es el **conductor** quien detecta el fin del turno, lee el transcript/rollout de
   **su propia sesión fresca**, valida el envelope y persiste el informe en la ruta que le
   corresponde a la skill llamadora (sección 5).
4. Ante cualquier incertidumbre — el binario/MCP falta, el runtime de Orca está `stale_bootstrap`,
   el locator del transcript es ambiguo, la sesión no es propia — el transporte **degrada al CLI
   headless** sin cambios de comportamiento observables (sección 8).

El resolver que decide `orca-session` vs `cli` (`override ?? config ?? auto`), la recuperación
ante fallas del secundario y la espera bloqueante con backoff están en `reference.md` → secciones
"Resolver de transporte", "Recuperación" y "Espera y backoff" (no en este archivo).

## 2. Envelope con autoridad

El secundario cierra su turno con:

```
<salida propia del modo (findings/veredicto/diff, según la skill llamadora)>
X-CMO: nonce=<..>
STATUS: done
```

`STATUS: done` debe ser la **última línea no vacía**. El conductor cosecha **solo** el mensaje que
trae el `nonce` del dispatch en curso — una sesión reutilizada (p. ej. `cross-review` entre
rondas) puede tener mensajes de dispatches previos con `nonce` viejo, y esos se descartan.

**Correlación vs. autoridad.** El texto del envelope lo produce el modelo secundario, así que es
**falsificable**: no sirve como credencial. Por eso lleva un único campo, el `nonce`, que es solo
un **token de correlación** — para qué mensaje del transcript corresponde a este dispatch. La
**autoridad**, lo que un secundario no puede forjar, vive **fuera del texto** y la valida el
conductor **antes** de cosechar: para Codex, el `payload={taskId, dispatchId}` del `worker_done`
más la garantía de Orca de que el `sender` coincide con el `assignee` del dispatch; para Claude
(que no emite `worker_done`), la **propiedad de la sesión** — el conductor la creó con un
`--session-id` propio y lee ese transcript exacto. Agregar `taskId`/`dispatchId` al texto no
sumaría autoridad (serían un eco forjable de datos que el conductor ya conoce); el parser los
tolera por compatibilidad, pero el dispatch `orca-session` solo pide `nonce`.

El parseo exacto del envelope, la desambiguación por `nonce` y el algoritmo de cosecha
crash-idempotente están en `reference.md` (consumen `assets/harvest-core.mjs` y
`assets/harvest-from-transcript.mjs`).

## 3. Tres capas de control

Sin las tres activas, no se despacha:

1. **Sandbox/toolset** — qué puede tocar el proceso. Codex: `-s read-only` / `-s
   workspace-write`. Claude: **siempre** toolset cerrado `--tools "Read,Grep,Glob"` (Bash queda
   fuera del toolset → read-only duro, inmune a un `allow:["Bash"]` heredado de otro scope).
   Consecuencia: **Claude no señaliza por comando** — su fin de turno se detecta por la
   transición `tui-idle` posterior al dispatch, nunca por una señal propia. La señal
   `worker_done` por comando es **solo Codex**.
2. **MCP** — qué tools remotas están disponibles. En el **default atendido**, MCP se controla por
   **vigilancia manual** (P4): el secundario ve los MCP del entorno y el humano aprueba/rechaza en
   la TUI cualquier acción sensible. No hay inventario ni allowlist que configurar. `--tools` acota
   solo los built-ins, no las tools MCP (`claude --help`: "from the built-in set"), por eso el gate
   de MCP es el humano, no el toolset. Para una corrida **desatendida** (sin gate humano), un gate
   declarativo **opcional**: `--strict-mcp-config --mcp-config claude-readonly.mcp.json` (deja solo
   los servidores del allowlist; vacío = cero MCP). Codex: perfil instalado en
   `$CODEX_HOME/<nombre>.config.toml`, invocado con `-p <nombre>` (server-scoped, nunca `-c`). Ver
   `assets/launch/mcp-inventory.md` para el modelo completo.
3. **Hooks** — qué automatización local puede dispararse. `disableAllHooks: true` (Claude) /
   `--disable hooks` (Codex), siempre, en los dos roles.

El detalle verificado de cada capa (perfiles concretos, validación real contra el CLI, namespacing
de tools MCP por cómo está instalado el servidor) vive en `assets/launch/profiles.md` y
`assets/launch/mcp-inventory.md` — **fail-closed**: un servidor/tool que no aparece en el
inventario bloquea el despacho, no se habilita solo porque exista en el entorno.

## 4. Matriz de lanzamiento

Resumen familia × rol × modo — comandos completos POSIX+PowerShell en `assets/launch/profiles.md`:

| Familia | Rol | Atendido | Desatendido |
|---|---|---|---|
| Claude | read-only | `--tools "Read,Grep,Glob"` + `--settings claude-readonly.settings.json` | mismo comando (el toolset cerrado ya excluye todo prompt) |
| Claude | write (cross-implement) | `--permission-mode manual` | `--permission-mode dontAsk` (`acceptEdits` solo en worktree hermano aislado) |
| Codex | read-only | `-p cmo-readonly -s read-only -a untrusted --disable hooks` | `-a never` en vez de `untrusted` |
| Codex | write (cross-implement) | `-p cmo-write -s workspace-write -a on-request --disable hooks` | `-a never` en vez de `on-request` |

No copies los comandos completos desde acá: `assets/launch/profiles.md` tiene cada celda con su
bloque POSIX y PowerShell verificado, más la instalación previa obligatoria de los perfiles Codex
(`cp`/`Copy-Item` a `$CODEX_HOME/<nombre>.config.toml` antes de invocar `-p`).

## 5. Matriz de raíces por skill/modo

Dónde persiste cada skill el informe que el conductor cosecha. Cada raíz se **canonicaliza**
(`realpath`) antes de escribir, y la escritura es **exclusiva** (`wx`) contra un destino
inexistente — el algoritmo de contención robusta y el detalle de reconstrucción/promoción
atómica para destinos acumulativos están en `reference.md`.

| Skill | Modo SDD | Standalone |
|---|---|---|
| `co-explore` | `.plans/<id>/co-explore/` o `.sdd/<id>/co-explore/` | `.co-explore/<slug>/` |
| `cross-review` | `.plans/<id>/…` o `.sdd/<id>/…` | `.cross-review/<slug>/` (con `review-log.md` acumulativo por rondas) |
| `cross-implement` | scratch de su propio worktree | — |

Para destinos **acumulativos** (el `review-log.md` de `cross-review`, que crece ronda a ronda) la
cosecha nunca sobrescribe el archivo canónico directo con `wx`: escribe un **raw único e
inmutable por ronda/dispatch** y luego reconstruye + promueve el canónico de forma atómica
(`rename`). El algoritmo exacto queda en `reference.md`.

## 6. Privacidad (v1)

El conductor cosecha **exclusivamente transcripts de sesiones frescas que el propio flujo creó**.
Una sesión **ajena** — una ya abierta por el usuario o por otro flujo — **nunca** se cosecha en
v1: no existe una rama de consentimiento que lo habilite. Si no se puede garantizar que la sesión
es propia y fresca, el transporte fuerza crear una sesión nueva o **degrada a `cli`**. Sin
excepciones.

## 7. P4 = vigilancia manual declarada

v1 trata la aprobación de acciones sensibles como **vigilancia manual atendida**: no hay
surfacing programático del `PermissionRequest` del secundario hacia el conductor. Si un `send` o
una tool escala a aprobación durante el turno del secundario, se aprueba **a mano en la TUI** de
esa sesión — es responsabilidad de quien está mirando la corrida, no algo que esta librería
automatice.

## 8. Degradación (fallback CLI)

El transporte `cli` (`codex exec -s read-only` / `claude -p`, ya usado por las skills hoy) es el
**status quo y el fallback por defecto**. `orca-session` degrada a `cli` sin cambios de
comportamiento observables ante cualquiera de estos casos:

- El runtime de Orca está `stale_bootstrap` desde el proceso del conductor.
- El locator del transcript/rollout de la sesión es ambiguo (más de un candidato, o ninguno).
- La sesión a cosechar no es una sesión fresca propia del flujo (ver sección 6).
- Falta el binario de Orca, el binario de la otra familia, o un MCP requerido por el perfil.

La skill llamadora nunca queda bloqueada por la ausencia de Orca: si algo de lo anterior falla,
sigue con `cli` y lo reporta como degradación, igual que hoy hace la ausencia de un binario o MCP.

## Ver también

- `install.md` — Node ≥18, `CROSS_MODEL_ORCA`, instalación reproducible de `skills-ref`.
- `reference.md` — resolver de transporte, recuperación con interrupt/close, espera
  bloqueante/backoff, algoritmo de contención y promoción atómica.
- `assets/launch/profiles.md` — matriz de lanzamiento completa (POSIX+PowerShell).
- `assets/launch/mcp-inventory.md` — inventario MCP y namespacing real de tools.
- `spikes/RESULTS.md` — contratos de locator y señal con evidencia.
