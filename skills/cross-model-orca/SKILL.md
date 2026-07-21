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

### Cómo se corre: UN comando (no improvisar Orca a mano)

El flujo de arriba lo ejecuta el conductor con **un** comando — el entrypoint
`assets/run-orca-session.mjs` —, que encadena `createOwnedSession → createDispatch → awaitDone`
con la misma degradación a `cli`. El prompt/spec va **por archivo** (nunca inline: el markdown con
backticks rompe el quoting del shell):

```sh
node <skill>/assets/run-orca-session.mjs \
  --family <codex|claude> --role <read-only|write> --mode <attended|unattended> \
  --worktree <abspath-registrado-en-orca> --spec-file <path> \
  --report <relpath-a-root> --root <dir> [--deadline-ms <n>] [--boot-timeout-ms <n>]
```

**Precondición del destino:** el conductor crea antes el directorio padre de `--report`
(`mkdir -p` / `New-Item -ItemType Directory -Force`), pero deja el archivo destino inexistente.
El runner no hace `mkdir -p`: necesita que el padre ya exista para canonicalizarlo con `realpath`
y rechazar symlinks que escapen de `--root`. Si falta, devuelve `code:2` **antes** de crear una
sesión Orca, con un error sobre el directorio padre.

Devuelve una línea JSON en stdout: `{ transport:"orca-session", code, reportPath?, reason? }`.
`code:0` = cosechado (`reportPath` es el informe); `code!=0` = **degradar a `cli`** leyendo
`reason` (4 = no se pudo crear/localizar la sesión propia; 2/3 = fallo de cosecha/invocación).

> **Red flag — NUNCA improvisar `orca terminal create --command 'codex exec … < prompt > out'`.**
> Eso NO es este transporte: es la rama `cli` metida a mano en una terminal Orca, y se salta las
> dos garantías del adaptador — el **boot-wait (`tui-idle`)** antes de inyectar (sin él, el comando
> se teclea mientras el shell todavía sourcea `.zshrc` y el prompt se pierde en la carrera de boot)
> y la **cosecha por `nonce`** del transcript propio. Si el runtime de Orca es alcanzable,
> `orca-session` se corre SOLO por `run-orca-session.mjs`; si no, se corre la rama `cli` de
> siempre. No hay un punto intermedio a mano.
>
> El transporte se llama **`orca-session`** (una sesión interactiva propia), no "orca-cli": "usar
> la CLI de Orca" no significa teclear comandos `orca …` sueltos, sino correr el entrypoint que
> abre esa sesión y la cosecha con autoridad.

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
**autoridad**, lo que un secundario no puede forjar, es la **propiedad de la sesión**: el conductor
**creó él mismo** la terminal fresca y lee el transcript/rollout de **esa** sesión exacta — para
Claude, fijando un `--session-id` propio; para Codex, localizando el rollout por `cwd`+timestamp de creación+
`source` y desambiguando a **exactamente 1** candidato. El `nonce` (único por dispatch) selecciona
el mensaje correcto dentro de ese transcript propio. Vale para **ambas familias**: es el mismo
modelo.

**Por qué no se usa `worker_done`.** El E2E real (Fase 7, primer contacto con Orca vivo) mostró que
un Codex **sandboxeado** no puede reportar `worker_done` de forma confiable: dentro del sandbox
`read-only` el `orca orchestration send` falla de forma **intermitente** con "Orca is not running"
(el `ORCA_CLI_SOCKET` viene vacío y no alcanza el runtime). La señal que el conductor **siempre**
observa —porque él no está sandboxeado— es el `nonce`+sentinel apareciendo en el transcript propio,
que `harvest()` sondea hasta el deadline: **esa** es la detección de fin. `taskId`/`dispatchId` no
sumarían autoridad (serían un eco forjable de datos que el conductor ya conoce); el parser los
tolera por compatibilidad, pero el dispatch `orca-session` solo pide `nonce`. Como el preamble de
Orca igualmente menciona `worker_done`, la tarea inyectada le ordena explícitamente al secundario
no ejecutar `orca` ni intentar enviarlo.

El parseo exacto del envelope, la desambiguación por `nonce` y el algoritmo de cosecha
crash-idempotente están en `reference.md` (consumen `assets/harvest-core.mjs` y
`assets/harvest-from-transcript.mjs`).

## 3. Tres capas de control

Sin las tres activas, no se despacha:

1. **Sandbox/toolset** — qué puede tocar el proceso. Codex: `-s read-only` / `-s
   workspace-write`. Claude: **siempre** toolset cerrado `--tools "Read,Grep,Glob"` (Bash queda
   fuera del toolset → read-only duro, inmune a un `allow:["Bash"]` heredado de otro scope).
   El fin de turno **no** se detecta por una señal que emita el secundario: para **ambas familias**
   el conductor sondea el transcript propio esperando el `nonce`+sentinel (sección 2). `tui-idle`
   solo se usa como barrera de **boot** antes de inyectar (para no perder el prompt) y en la
   recuperación, no como detección de fin.
2. **MCP** — qué tools remotas están disponibles. El comportamiento **depende de la familia y el
   rol**:
   - **read-only Claude → MCP OFF por default.** `--tools "Read,Grep,Glob"` cierra los built-ins
     (sin Bash), pero **no** las tools MCP: un read-only con los MCP del entorno podía alcanzar una
     tool MCP de **ejecución** (p. ej. la terminal del IDE del usuario) y correr comandos fuera del
     worktree — gatillado por el `worker_done` que le pide el preamble de `dispatch --inject`
     (hallazgo del E2E de Fase 7, gateado por aprobación manual pero fuera de lo esperado para un
     read-only). Por eso el read-only combina `--strict-mcp-config --mcp-config
     claude-readonly.mcp.json` vacío con `--disallowedTools "mcp__*"` y `--permission-mode dontAsk`.
     El config vacío evita heredar servidores configurados; el deny explícito también cubre tools
     publicadas por plugins/connectors y `dontAsk` impide que una negación deje la TUI esperando.
   - **Codex → MCP OFF por override dinámico, en ambos roles.** El adaptador enumera
     `[mcp_servers.*]` del `config.toml` vigente (`configDir('codex')`, respeta `CODEX_HOME`) **al
     momento de lanzar** y agrega un `-c mcp_servers.<name>.enabled=false` por server — la lista
     nunca se fija: altas/bajas en el config quedan cubiertas en la próxima sesión. Motivo doble:
     latencia (los MCP dominan el boot de la TUI — medido ~2x — y en Windows llegaron a colgarlo
     en "MCP startup incomplete") y que el secundario no los necesita: todo su contexto viaja en
     el prompt del dispatch. Cobertura parcial asumida: MCP publicados por plugins y servers con
     nombre quoted no son overrideables y arrancan igual (costo menor). Best-effort: config
     ilegible → sin overrides, boot completo. `-c features.apps=false` y `--disable hooks` siguen
     activos.
   - **write Claude → vigilancia manual (P4).** El secundario ve los MCP del entorno y el humano
     aprueba/rechaza en la TUI cualquier acción sensible; no hay inventario ni allowlist que
     mantener. Ver `assets/launch/mcp-inventory.md`.
3. **Hooks** — qué automatización local puede dispararse. `disableAllHooks: true` (Claude) /
   `--disable hooks` (Codex), siempre, en los dos roles.

El detalle verificado de cada capa (perfiles concretos, validación real contra el CLI, namespacing
de tools MCP por cómo está instalado el servidor) vive en `assets/launch/profiles.md` y
`assets/launch/mcp-inventory.md`. El cierre MCP **fail-closed** corresponde a Claude read-only;
en Codex el apagado es best-effort por override dinámico (fail-open ante config ilegible).

## 4. Matriz de lanzamiento

Resumen familia × rol × modo — comandos completos POSIX+PowerShell en `assets/launch/profiles.md`:

| Familia | Rol | Atendido | Desatendido |
|---|---|---|---|
| Claude | read-only | `--tools "Read,Grep,Glob"` + `--disallowedTools "mcp__*"` + `--permission-mode dontAsk` + config MCP estricto vacío | mismo comando (sin superficie de ejecución ni prompts) |
| Claude | write (cross-implement) | `--permission-mode manual` | `--permission-mode dontAsk` (`acceptEdits` solo en worktree hermano aislado) |
| Codex | read-only | `-c features.apps=false` + overrides MCP-off dinámicos + `-s read-only -a untrusted --disable hooks` | `-a never` en vez de `untrusted` |
| Codex | write (cross-implement) | `-c features.apps=false` + overrides MCP-off dinámicos + `-s workspace-write -a on-request --disable hooks` | `-a never` en vez de `on-request` |

No copies los comandos completos desde acá: `assets/launch/profiles.md` tiene cada celda con su
bloque POSIX y PowerShell verificado. Los perfiles Codex son un endurecimiento **opcional** y no
forman parte del lanzamiento default del adaptador.

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

En perfiles **write atendidos**, v1 trata la aprobación de acciones sensibles como vigilancia
manual: no hay surfacing programático del `PermissionRequest` hacia el conductor. Si una acción
escala, se aprueba a mano en la TUI. Claude read-only no usa P4: su toolset y namespace MCP están
cerrados y `dontAsk` rechaza cualquier desvío sin bloquear.

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
