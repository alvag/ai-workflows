# Sesiones reales Claude ↔ Codex para los flujos cross-model

**Estado:** investigación y diseño propuesto, todavía no implementado

**Fecha:** 2026-07-17

**Repositorio:** `ai-workflows`

## Resumen ejecutivo

Las skills `co-explore`, `cross-review` y `cross-implement` ya cruzan las dos familias de
modelos: cuando conduce Claude delegan en Codex, y cuando conduce Codex delegan en Claude.
Sin embargo, hoy invocan al secundario como un proceso nuevo mediante `codex exec`, el
subagente `codex:codex-rescue` o `claude -p`.

Ese mecanismo es portable y seguro, pero no equivale a usar una sesión interactiva real ya
abierta:

- el secundario no hereda la conversación del conductor;
- Claude se inicia con `--safe-mode`, que desactiva `CLAUDE.md`, skills, plugins, hooks y MCP;
- las herramientas se restringen según el rol;
- el proceso queda sujeto a deadlines y rondas acotadas;
- el modelo secundario no puede avisar directamente a una sesión principal independiente: el
  conductor observa archivos o espera al proceso hijo.

La propuesta es agregar un transporte opcional **`orca-session`**. Cuando dos terminales reales
de Claude y Codex están abiertos dentro de Orca, `sdd-flow` conserva su entrypoint habitual:

```text
/sdd-flow <ticket o descripción>
```

La sesión donde se ejecuta el comando es el **principal**. En los puntos cross-model que ya
existen, `sdd-flow` despacha una tarea acotada a un terminal real de la otra familia mediante
Orca orchestration. El secundario trabaja con la configuración completa de su propia sesión y
termina enviando `worker_done`. El principal recibe esa señal, lee el informe y continúa el
flujo.

El mecanismo actual no se elimina. Queda como fallback portable cuando Orca no está disponible:

```yaml
cross_model:
  transport: auto # auto | orca-session | cli
```

`auto` intentaría primero una sesión real de Orca y degradaría a `codex exec` / `claude -p`.

## Pregunta investigada

El objetivo es determinar si podemos:

1. abrir una sesión real de Claude Code y otra de Codex;
2. definir cuál conduce y cuál actúa como secundaria;
3. iniciar el flujo normalmente con `/sdd-flow ...`;
4. entregar contexto y artefactos al secundario sin perder independencia;
5. permitir que el secundario use MCP, hooks, skills y herramientas de su sesión;
6. hacer que el secundario notifique al principal cuando termina;
7. conservar gates, trazabilidad, seguridad y degradación portable.

La respuesta es **sí**, con modificaciones en las skills. Orca ya ofrece el transporte y el
protocolo de finalización necesarios, pero las skills actuales todavía no los usan.

## Fuentes y verificaciones

### Implementación actual del repositorio

Se revisaron:

- `skills/sdd-flow/SKILL.md`
- `skills/sdd-flow/reference.md`
- `skills/co-explore/SKILL.md`
- `skills/co-explore/reference.md`
- `skills/cross-review/SKILL.md`
- `skills/cross-review/reference.md`
- `skills/cross-implement/SKILL.md`
- `skills/cross-implement/reference.md`
- `skills/bitbucket-code-review/SKILL.md`
- `skills/bitbucket-code-review/reference.md`

### Capacidades locales verificadas

Durante la investigación:

- Codex CLI instalado: `codex-cli 0.144.5`.
- Claude Code instalado: `2.1.214`.
- Configuración activa de Codex:
  - modelo: `gpt-5.6-sol`;
  - esfuerzo de razonamiento: `high`.
- Codex reportó la feature `hooks` como `stable` y activa.
- `codex app-server` ofrece transporte por `stdio`, Unix socket y WebSocket, pero no es necesario
  para una primera implementación basada en terminales Orca.
- Claude admite sesiones persistentes con `--session-id`, `--resume` y entrada/salida
  `stream-json`.
- Orca CLI expone:
  - `orca orchestration task-create`;
  - `orca orchestration dispatch --inject`;
  - `orca orchestration send --type worker_done`;
  - `orca orchestration check --wait`;
  - terminales dirigibles por handle concreto.

En esta corrida, `orca status --json` devolvió `stale_bootstrap` y `app.running: false`. Por eso
se verificó la interfaz del CLI, pero no se ejecutó un ciclo real extremo a extremo.

### Hooks de Codex

Codex soporta lifecycle hooks desde `hooks.json` o tablas `[hooks]` en `config.toml`, tanto a
nivel usuario como proyecto. Los hooks de proyecto requieren que el proyecto sea trusted.
Actualmente se ejecutan handlers de comando; handlers de prompt o agente se parsean, pero se
omiten.

Documentación oficial:

- [Advanced Configuration — Hooks](https://developers.openai.com/codex/config-advanced#hooks)
- [Configuration Reference](https://developers.openai.com/codex/config-reference)

Los hooks son útiles como protección adicional, pero no son el transporte recomendado entre
sesiones. Son callbacks reactivos: no constituyen por sí solos un bus de mensajes ni garantizan
que una sesión principal inactiva inicie un nuevo turno.

## Estado actual

### Flujo actual cuando conduce Claude

| Skill | Secundario | Invocación actual | Capacidades |
|---|---|---|---|
| `co-explore` | Codex | `codex exec -s read-only` | Repo en read-only, config de Codex |
| `cross-review` | Codex | `codex:codex-rescue` o `codex exec -s read-only` | Revisión read-only |
| `cross-implement` | Codex | `codex exec -s workspace-write` | Escritura acotada al workspace |

Codex no recibe un `-m` explícito: hereda el modelo configurado. La skill tampoco impone un
límite adicional de tokens o turnos. Sí aplica sandbox, deadlines y contratos de salida.

### Flujo actual cuando conduce Codex

| Skill | Secundario | Invocación actual | Capacidades |
|---|---|---|---|
| `co-explore` | Claude Opus | `claude -p --safe-mode` | `Read,Grep,Glob` |
| `cross-review` | Claude Opus | `claude -p --safe-mode` | `Read,Grep,Glob` |
| `cross-implement` | Claude Sonnet | `claude -p --safe-mode` | Read/Edit/Write acotado + prueba permitida |

`--safe-mode` desactiva personalizaciones de Claude: `CLAUDE.md`, skills, plugins, hooks, MCP,
comandos y agentes personalizados. No se fija `--effort`, por lo que se usa el default del CLI.
En implementación se elige Sonnet deliberadamente por velocidad.

### Qué significa “usar el 100%”

No existe una garantía absoluta de “100%”: toda sesión sigue limitada por el modelo contratado,
su ventana de contexto, las políticas del workspace, el sandbox y los permisos del usuario.

En este diseño, “máxima capacidad” significa:

- usar la sesión interactiva real elegida por el usuario;
- conservar el modelo y esfuerzo con los que se inició esa sesión;
- conservar sus MCP autenticados;
- conservar hooks, skills, plugins y archivos de instrucciones;
- conservar su historial conversacional;
- no introducir `--safe-mode` ni una allowlist artificial desde la skill;
- mantener únicamente las restricciones funcionales necesarias para el rol.

Una revisión debe seguir siendo read-only sobre código aunque el agente tenga más herramientas.
Más capacidad no implica acceso irrestricto.

## Arquitectura propuesta

### Principio central

`sdd-flow` sigue siendo el coordinador y la única autoridad del flujo. La sesión secundaria no
ejecuta otro `/sdd-flow`; recibe tareas acotadas en los puntos de extensión cross-model ya
existentes.

```text
Usuario
  │
  ▼
/sdd-flow <prompt> en la sesión principal
  │
  ├─ gather-context
  ├─ co-explore ─────────► terminal real de la otra familia
  │                           │
  │                           └─ worker_done + reportPath
  ├─ specify
  ├─ cross-review ───────► mismo terminal real
  │                           │
  │                           └─ worker_done + review-log/report
  ├─ plan / tasks
  ├─ cross-implement ─────► mismo terminal real, si se eligió modo cross
  │                           │
  │                           └─ worker_done + diff/report
  └─ verify / gate humano / commit / push
```

### Responsabilidades

#### Principal

- recibe `/sdd-flow ...`;
- lee configuración y tracker;
- clasifica complejidad;
- prepara los paquetes de contexto;
- crea y despacha tareas Orca;
- realiza su propia exploración antes de leer la del secundario;
- decide qué findings aplicar o rechazar;
- edita `spec.md`, `plan.md` y `tasks.md`;
- conserva todos los gates humanos;
- revisa diffs;
- ejecuta pruebas y `verify`;
- commitea y pushea tras confirmación.

#### Secundario

- recibe una tarea concreta, no el control del flujo;
- trabaja con su sesión real y sus capacidades configuradas;
- respeta el contrato del modo: explore, review o implement;
- escribe solamente el informe o código autorizado;
- no aprueba gates;
- no commitea ni pushea;
- envía exactamente un `worker_done` por dispatch.

### Transporte

El transporte debería resolverse de forma compartida por las tres skills:

```yaml
cross_model:
  transport: auto # auto | orca-session | cli
```

- `orca-session`: exige runtime Orca y una sesión real compatible.
- `cli`: fuerza el mecanismo actual.
- `auto`: prefiere `orca-session`; si no puede resolverla, usa `cli`.

Los bloques existentes siguen decidiendo **cuándo** y **con qué política** se ejecuta cada
capacidad:

```yaml
co_explore:
  mode: auto
  deadline: 600

cross_review:
  mode: auto
  execution: auto
  max_rounds: 3

implement_mode: ask

cross_implement:
  execution: auto
  max_fix_rounds: 2
  deadline: 1800
```

`cross_model.transport` decide **cómo contactar** a la otra familia. No reemplaza esos bloques.

## Experiencia de usuario

### Preparación

1. Abrir el repo o worktree en Orca.
2. Levantar una sesión real de Claude y otra de Codex.
3. Dejar idle la sesión que actuará como secundaria.
4. Iniciar el flujo desde la sesión que se desea como principal.

### Invocación normal

```text
/sdd-flow PQTCH-123 implementar el cambio descrito en el ticket
```

No se agrega un comando obligatorio. La sesión actual es el principal.

El checkpoint inicial de `sdd-flow` debería anunciar:

```text
config: cross_model transport orca-session · principal Claude · secundario Codex
· co_explore on · cross_review on
```

### Override conversacional

Si existen varios terminales candidatos:

```text
/sdd-flow PQTCH-123 ... usando el terminal codex-review como secundario
```

Los handles de Orca son efímeros. No deberían persistirse como preferencia permanente en
`.specify/config.yml`. Un handle puede guardarse en el scratch de una corrida como dato de
auditoría, pero al retomar debe validarse y resolverse otra vez.

## Descubrimiento de sesiones

Algoritmo propuesto:

1. Verificar que `orca` existe.
2. Ejecutar `orca status --json`.
3. Exigir runtime alcanzable y orchestration activa.
4. Resolver el handle del terminal actual.
5. Determinar la familia del principal.
6. Listar terminales del mismo worktree.
7. Filtrar terminales:
   - reconocidos como Claude o Codex;
   - de la familia opuesta;
   - idle;
   - no asociados a otro dispatch activo incompatible.
8. Si queda uno, seleccionarlo.
9. Si quedan varios, hacer una sola pregunta al usuario.
10. Si no queda ninguno:
    - con `transport: auto`, degradar a CLI;
    - con `transport: orca-session`, devolver `UNAVAILABLE`.

El dispatch siempre debe usar el **handle concreto**. No debe enviarse a `@codex`, `@claude` ni
otro grupo: `worker_done` requiere identidad exacta para tener autoridad de finalización.

## Protocolo de trabajo

### Crear y despachar una tarea

El principal crea una tarea que contiene:

- modo (`explore`, `counter-plan`, `debate`, `review`, `implement`, `fix`);
- objetivo;
- paths del contexto;
- working directory;
- restricciones;
- output contract;
- ruta permitida para el informe;
- deadline global;
- instrucción de `worker_done`.

Ejemplo conceptual:

```bash
orca orchestration task-create \
  --spec "Cross-review de .plans/ABC-123/spec.md; solo lectura sobre código; escribe el informe en .plans/ABC-123/cross-review/spec-r1.md" \
  --json

orca orchestration dispatch \
  --task <task_id> \
  --to <secondary_handle> \
  --inject \
  --json
```

`--inject` entrega el task spec y el preámbulo de coordinación a un CLI reconocido.

### Finalización del secundario

El secundario escribe su resultado y envía:

```bash
orca orchestration send \
  --to <principal_handle> \
  --type worker_done \
  --subject "Cross-review terminada" \
  --task-id <task_id> \
  --dispatch-id <dispatch_id> \
  --report-path ".plans/ABC-123/cross-review/spec-r1.md" \
  --json
```

El payload debe incluir como mínimo:

- `taskId`;
- `dispatchId`;
- `reportPath`;
- estado lógico (`done`, `revise`, `approved`, `failed`);
- archivos modificados cuando el rol permite escritura;
- resumen corto.

### Espera del principal

```bash
orca orchestration check \
  --wait \
  --types worker_done,escalation,decision_gate \
  --timeout-ms 120000 \
  --json
```

El timeout de cada `check --wait` es una ventana de espera, no el deadline completo. Si devuelve
cero mensajes, el principal revisa el deadline global y vuelve a esperar. Solo al vencer el
deadline de la skill se declara `UNAVAILABLE`.

Así se reconcilian dos reglas:

- Orca: una ventana vacía no significa que el worker falló.
- Skills cross-model: ningún proceso espera indefinidamente.

### ¿El principal queda “despierto”?

En el flujo recomendado, sí:

- durante `co-explore`, el principal realiza su propia exploración y luego espera;
- durante `cross-review`, espera el resultado antes del gate;
- durante `cross-implement`, espera para revisar el diff.

El turno del principal permanece activo. `worker_done` desbloquea la espera y permite continuar.

Si se quisiera cerrar por completo el turno principal y reactivarlo después, haría falta un
coordinador persistente que ejecute `check --wait --inject`. Eso puede añadirse más adelante, pero
no es necesario para integrar el mecanismo con `sdd-flow`.

## Acople exacto con `sdd-flow`

### Inicio

El usuario mantiene:

```text
/sdd-flow <prompt>
```

En el checkpoint inicial, `sdd-flow`:

1. lee `.specify/config.yml`;
2. resuelve `cross_model.transport`;
3. registra la familia y handle del principal;
4. descubre el secundario;
5. anuncia el transporte resuelto;
6. continúa con `gather-context`.

El secundario no ejecuta `sdd-flow`. Esto también evita el problema de
`disable-model-invocation: true`: únicamente el principal activa la skill slash.

### `co-explore` — modo `explore`

Después de `gather-context`:

1. el principal arma el `context_package`;
2. crea un task Orca;
3. despacha al secundario;
4. el principal explora sin leer la salida secundaria;
5. escribe `findings-<familia-principal>.md`;
6. espera `worker_done`;
7. valida `reportPath`;
8. escribe o incorpora `findings-<familia-secundaria>.md`;
9. produce `synthesis.md`;
10. continúa con `specify`.

Se conserva la independencia: el secundario no ve el mapa del principal y el principal no lee el
informe secundario hasta cerrar el suyo.

### `cross-review` — gates de spec, plan y tasks

Antes de cada gate activo:

1. el principal escribe el artefacto;
2. crea el task de revisión;
3. despacha al mismo terminal secundario;
4. espera `worker_done`;
5. lee findings;
6. verifica cada finding;
7. aplica, rechaza o escala con rationale;
8. si hay otra ronda, crea un nuevo dispatch al mismo terminal;
9. presenta artefacto + crítica en el gate humano.

Para una primera implementación, cada ronda debería ser un dispatch separado. El terminal real
conserva su contexto conversacional, mientras Orca mantiene una autoridad `worker_done` clara por
dispatch.

### `co-explore` — modo `counter-plan`

Con la spec aprobada:

1. se despacha otra tarea al mismo secundario;
2. recibe la spec y su propio informe de `explore`;
3. prepara un contra-enfoque;
4. envía `worker_done`;
5. el principal contrasta enfoques y escribe `plan.md`.

### `co-explore` — modo `debate`

Cada ronda de cruce puede representarse como un dispatch nuevo al mismo terminal:

1. ronda 0: postura independiente;
2. principal forma su postura sin leer la secundaria;
3. rondas 1..N: intercambio de deltas;
4. `worker_done` por ronda;
5. síntesis final neutral;
6. decisión del usuario.

### `cross-implement`

Si el usuario elige `implement_mode: cross`:

1. el principal confirma el work order congelado;
2. verifica clean tree;
3. despacha la implementación completa;
4. el secundario escribe código, pero no `.plans/`, commits ni pushes;
5. envía `worker_done` con `filesModified`, reporte y prueba ejecutada;
6. el principal revisa el diff completo;
7. el principal ejecuta `proof_cmd` de nuevo;
8. cada fix round se despacha al mismo terminal;
9. el principal conserva `verify`, gate manual, commit y push.

En este modo debe existir un único propietario de escritura: mientras el secundario implementa,
el principal no edita código.

## Archivos de trabajo y trazabilidad

Los artefactos actuales deberían conservarse. Solo cambia el transporte.

Ejemplo extendido:

```text
.plans/<id>/
├─ spec.md
├─ plan.md
├─ tasks.md
├─ review-log.md
├─ co-explore/
│  ├─ findings-claude.md
│  ├─ findings-codex.md
│  ├─ counter-plan-codex.md
│  ├─ synthesis.md
│  └─ session.json
├─ cross-review/
│  ├─ spec-r1.md
│  ├─ plan-r1.md
│  └─ tasks-r1.md
└─ cross-implement/
   └─ implement-log.md
```

`co-explore/session.json` puede extenderse:

```json
{
  "transport": "orca-session",
  "family": "codex",
  "terminal_handle": "codex-review",
  "task_id": "task-...",
  "dispatch_id": "dispatch-...",
  "mode": "explore",
  "created_at": "2026-07-17T00:00:00Z"
}
```

`terminal_handle` sirve como pista auditable, no como binding durable. Al retomar:

1. validar que el runtime siga siendo el mismo;
2. comprobar que el handle existe y está idle;
3. si no, volver a descubrir;
4. si no hay reemplazo, degradar a CLI.

## Seguridad y aislamiento

### Review y explore

“Sesión completa” no debe significar permiso para editar producto.

El contrato debe indicar:

- código del repo en solo lectura;
- MCP de lectura permitidos;
- navegador permitido si la tarea lo requiere;
- escritura limitada al informe local asignado;
- no tocar `.plans/` fuera de la ruta de salida;
- no ejecutar commit, push ni operaciones destructivas.

Además, el principal debe comparar `git status` antes y después. Si el secundario cambió código
en un rol read-only, se informa como violación y no se revierte automáticamente: una reversión
ciega podría destruir cambios legítimos del usuario.

### Implementación

- un solo escritor;
- clean-tree gate antes del dispatch;
- scope del working directory;
- sin commit ni push;
- diff completo revisado por el principal;
- prueba ejecutada otra vez por el principal;
- fix loop acotado;
- takeover al agotar rondas.

### MCP con escritura

Una sesión real puede tener MCP que modifican Jira, Bitbucket, Drive u otros sistemas. El
contrato del secundario debe prohibir escrituras externas salvo pedido explícito y confirmado.
Tener acceso no equivale a estar autorizado a usarlo.

## Papel de los hooks

### Lo que sí pueden aportar

- registrar `SessionStart`;
- validar que existe un dispatch activo;
- adjuntar `taskId` y `dispatchId` al contexto;
- emitir telemetría;
- comprobar al terminar que existe un informe;
- enviar `worker_done` como safety net si el agente no lo hizo.

### Lo que no deberían hacer

- ser el bus principal de mensajes;
- seleccionar por sí solos principal y secundario;
- iniciar tareas sin un dispatch auditable;
- ejecutar escrituras amplias;
- despertar arbitrariamente una sesión cerrada;
- marcar una revisión como válida solo porque ocurrió `Stop`.

Un hook `Stop` automático solo debería enviar `worker_done` cuando:

1. existe un archivo de dispatch activo;
2. el `taskId` y `dispatchId` coinciden;
3. el informe esperado existe;
4. aún no se envió `worker_done`;
5. el estado no es ambiguo.

De lo contrario debe limitarse a registrar el cierre.

## Cambios propuestos por archivo

### `skills/sdd-flow/SKILL.md`

- agregar `cross_model.transport` al checkpoint inicial;
- resolver principal y secundario una vez por corrida;
- anunciar el transporte efectivo;
- pasar el binding runtime a `co-explore`, `cross-review` y `cross-implement`;
- mantener todos los gates en el principal;
- re-resolver el secundario en `resume` si el handle quedó stale;
- documentar degradación `orca-session → cli`.

### `skills/sdd-flow/reference.md`

- extender el esquema de `.specify/config.yml`;
- documentar detección de Orca;
- documentar selección por familia, worktree y estado idle;
- agregar comandos POSIX y PowerShell donde aplique;
- extender `handoff.md` con el transporte resuelto como información, no como autoridad durable;
- agregar matriz de fallos y fallback.

### `skills/sdd-flow/README.md`

- explicar que `/sdd-flow` no cambia;
- documentar requisito de abrir dos terminales para `orca-session`;
- incluir un ejemplo Claude principal / Codex secundario y el inverso;
- aclarar que el mecanismo actual sigue disponible.

### `skills/co-explore/SKILL.md`

- aceptar `transport` y `secondary_handle`;
- mantener el algoritmo de independencia;
- despachar vía Orca cuando se resuelva `orca-session`;
- esperar `worker_done` en el punto de encuentro;
- usar `reportPath` como fuente del informe;
- conservar la vía CLI como fallback.

### `skills/co-explore/reference.md`

- agregar “Vía D — terminal real Orca”;
- definir task spec por modo;
- definir `worker_done`;
- extender `session.json`;
- documentar ventanas de espera versus deadline global;
- documentar rondas de debate como dispatches sucesivos;
- agregar casos de terminal desaparecido, ocupado o familia incorrecta.

### `skills/co-explore/README.md`

- documentar el nuevo transporte;
- explicar qué capacidades se conservan;
- aclarar que el rol sigue siendo read-only sobre código.

### `skills/cross-review/SKILL.md`

- aceptar `transport` y `secondary_handle`;
- usar un dispatch por ronda;
- mantener triage y arbitraje en el principal;
- aceptar el informe señalado por `worker_done`;
- no confundir la finalización del worker con `APPROVED`.

### `skills/cross-review/reference.md`

- agregar vía Orca antes de los fallbacks CLI;
- definir el task spec y output contract;
- definir el comportamiento de cada ronda;
- registrar terminal/familia/transporte en `review-log.md`;
- validar que `worker_done` pertenece al task/dispatch esperado;
- documentar degradación a CLI.

### `skills/cross-review/README.md`

- documentar sesiones reales y requisitos;
- aclarar que el gate humano no cambia.

### `skills/cross-implement/SKILL.md`

- aceptar transporte Orca;
- exigir propietario único de escritura;
- tratar `worker_done` como reporte advisory;
- conservar revisión de diff y prueba propia;
- ejecutar cada fix round en el mismo terminal secundario.

### `skills/cross-implement/reference.md`

- agregar vía de implementación en terminal real;
- definir preflight de clean tree y estado idle;
- definir payload `filesModified` y `reportPath`;
- documentar fix rounds como dispatches sucesivos;
- documentar qué ocurre si el terminal desaparece con un diff parcial.

### `skills/cross-implement/README.md`

- documentar el transporte y su trade-off;
- mantener explícito que el secundario nunca commitea.

### `skills/sdd-orchestrator/*`

Debe heredar el transporte para los subflujos, pero no compartir un único secundario entre
repos simultáneos sin coordinación. Cada dispatch necesita:

- repo/worktree correcto;
- terminal concreto;
- ownership de escritura claro;
- task/dispatch independientes.

La integración debería hacerse después de estabilizar el caso de un solo repo.

### `skills/bitbucket-code-review/*`

Usa las mismas vías `codex exec` / `claude -p`. Puede adoptar el resolver compartido más adelante,
pero no debería entrar en el primer alcance: primero hay que validar el ciclo SDD.

### Posible helper compartido

Para evitar duplicar comandos y reglas, conviene agregar una referencia o script común que
resuelva:

- disponibilidad de Orca;
- terminal principal;
- candidatos secundarios;
- creación de task;
- dispatch;
- espera;
- validación de `worker_done`;
- fallback.

Debe cuidarse la portabilidad del formato Agent Skills. Un script compartido agrega una
dependencia de layout; una referencia canónica en `cross-review/reference.md`, como ocurre hoy con
el descubrimiento de familia, puede ser una primera implementación menos invasiva.

## Pseudocódigo del resolver

```text
resolve_cross_model_transport(request):
  desired = request.override
         ?? config.cross_model.transport
         ?? "auto"

  if desired in ["auto", "orca-session"]:
    orca = detect_orca_runtime()

    if orca.available:
      principal = resolve_current_terminal()
      candidates = list_terminals(
        worktree = principal.worktree,
        family = opposite(principal.family),
        state = idle
      )

      if request.secondary_handle:
        candidate = validate_explicit_candidate(request.secondary_handle)
      else if candidates.count == 1:
        candidate = candidates[0]
      else if candidates.count > 1:
        candidate = ask_user_once(candidates)
      else:
        candidate = null

      if candidate:
        return OrcaSession(principal, candidate)

    if desired == "orca-session":
      return UNAVAILABLE

  return resolve_current_cli_transport()
```

## Pseudocódigo de un dispatch

```text
run_cross_task(contract):
  binding = resolve_cross_model_transport(contract)

  if binding.transport == "cli":
    return run_existing_cli_path(contract)

  task = orca.task_create(contract.render())
  dispatch = orca.dispatch(task.id, binding.secondary.handle, inject=true)

  deadline = now + contract.deadline

  while now < deadline:
    message = orca.check_wait(
      terminal = binding.principal.handle,
      types = [worker_done, escalation, decision_gate],
      timeout = min(120s, deadline - now)
    )

    if message.type == decision_gate:
      resolve_or_escalate(message)
      continue

    if message.type == escalation:
      return UNAVAILABLE_WITH_CONTEXT

    if message.type == worker_done:
      validate(message.taskId == task.id)
      validate(message.dispatchId == dispatch.id)
      validate(message.sender == binding.secondary.handle)
      validate_report_path(message.reportPath)
      return parse_result(message.reportPath)

  return UNAVAILABLE_TIMEOUT
```

## Fallos y degradación

| Falla | Comportamiento recomendado |
|---|---|
| Orca no está instalado | `auto` usa CLI; `orca-session` devuelve `UNAVAILABLE` |
| Runtime Orca no está activo | mismo comportamiento |
| No hay terminal de la otra familia | fallback CLI o `UNAVAILABLE` |
| Hay varios candidatos | una sola pregunta al usuario |
| Terminal no está idle | no despachar; buscar otro o fallback |
| `dispatch --inject` falla | registrar y fallback solo si no hubo ejecución parcial |
| Secundario desaparece | conservar artefactos parciales, no asumir éxito |
| Vence una ventana de `check --wait` | continuar mientras no venza el deadline global |
| Vence el deadline global | `UNAVAILABLE`; no esperar indefinidamente |
| `worker_done` con IDs incorrectos | ignorar como finalización no autorizada |
| Informe no existe o no parsea | revisar texto disponible; no marcar aprobado |
| Secundario cambia código en review | detener y reportar violación |
| Runtime reiniciado durante `resume` | re-resolver terminal; el handle guardado es solo una pista |
| CLI fallback tampoco está disponible | degradación normal al flujo de una sola familia |

## Riesgos

### Dependencia de Orca

El repo busca ser portable. Hacer Orca obligatorio rompería esa propiedad. Por eso el transporte
debe ser una capacidad opcional y `auto` debe conservar el camino actual.

### Sesiones con contexto contaminado

Una sesión real puede traer conversaciones anteriores irrelevantes. Para reducirlo:

- usar un terminal dedicado por flujo cuando el cambio sea complejo;
- incluir un contrato completo en cada dispatch;
- pedir que el secundario trate el task spec como autoridad;
- registrar supuestos;
- no confiar en memoria tácita.

### Herramientas poderosas

MCP y hooks aumentan capacidad y también superficie de riesgo. Los contratos deben distinguir
acceso disponible de acción autorizada.

### Colisiones en el working tree

En review/explore, el principal no debe mutar source mientras el secundario lee un checkout que se
supone estable. En implementación, solo el secundario escribe hasta devolver el control.

### Finalización falsa

`Stop` no equivale a éxito. La autoridad se compone de:

```text
sender handle + taskId + dispatchId + informe válido
```

### Portabilidad POSIX / PowerShell

Los comandos Orca no dependen de redirecciones complejas como los CLIs actuales, pero toda
documentación nueva debe mantener ejemplos válidos en ambos shells cuando haya diferencias.

## Plan de implementación recomendado

### Fase 1 — resolver y transportar

1. agregar `cross_model.transport`;
2. implementar detección de Orca y selección de terminal;
3. definir task/dispatch/worker_done;
4. adaptar solo `co-explore explore`;
5. mantener fallback CLI;
6. validar Claude principal → Codex secundario y la inversa.

### Fase 2 — cross-review

1. agregar un dispatch por ronda;
2. validar IDs y reportPath;
3. conservar triage, logs y gate humano;
4. probar resume lógico en el mismo terminal;
5. probar timeout, terminal caído y salida inválida.

### Fase 3 — counter-plan y debate

1. reutilizar el terminal de `explore`;
2. probar independencia de ronda 0;
3. probar múltiples dispatches;
4. verificar que la decisión final sigue siendo humana.

### Fase 4 — cross-implement

1. agregar clean-tree gate;
2. imponer escritor único;
3. validar `filesModified`;
4. revisar diff y repetir prueba en el principal;
5. implementar fix rounds;
6. probar caída con diff parcial y takeover.

### Fase 5 — sdd-orchestrator y otras skills

1. extender a multi-repo;
2. evitar compartir un terminal ocupado entre repos;
3. evaluar `bitbucket-code-review`;
4. considerar hooks de safety net;
5. documentar operación y troubleshooting.

## Estrategia de pruebas

### Matriz mínima

| Principal | Secundario | Modo | Resultado esperado |
|---|---|---|---|
| Claude | Codex | `co-explore explore` | dos mapas independientes + `worker_done` |
| Codex | Claude | `co-explore explore` | MCP/skills de Claude disponibles |
| Claude | Codex | `cross-review` | findings + gate en principal |
| Codex | Claude | `cross-review` | Opus/config real, sin `--safe-mode` |
| Claude | Codex | `cross-implement` | diff revisado, sin commit secundario |
| Codex | Claude | `cross-implement` | mismo contrato |

### Casos negativos

- Orca apagado con `transport: auto`;
- Orca apagado con `transport: orca-session`;
- cero candidatos;
- dos candidatos;
- candidato ocupado;
- familia incorrecta;
- `worker_done` duplicado;
- `worker_done` con task equivocado;
- informe ausente;
- timeout;
- terminal cerrado;
- cambio de código durante review;
- MCP de escritura disponible pero no autorizado;
- restart del runtime entre fases;
- `resume` de `sdd-flow` en una sesión principal distinta.

### Criterios de aceptación del cambio

1. `/sdd-flow <prompt>` mantiene la misma sintaxis.
2. El principal se identifica por la sesión donde se invoca.
3. `auto` usa una sesión real opuesta cuando hay exactamente una válida.
4. El secundario conserva su configuración de sesión.
5. `worker_done` reactiva el punto de espera del principal.
6. El principal conserva todos los gates.
7. `co-explore` mantiene independencia de mapas.
8. `cross-review` no confunde finalización con aprobación.
9. `cross-implement` mantiene escritor único, revisión y prueba propia.
10. Sin Orca, el comportamiento actual sigue funcionando.

## Decisión recomendada

Implementar el transporte como una **capa opcional compartida**, no reescribir los flujos:

```text
cross-model contract
        │
        ├─ orca-session ──► terminal real + worker_done
        └─ cli fallback ──► codex exec / claude -p
```

La primera entrega debe limitarse a `co-explore explore` dentro de `sdd-flow`. Es el caso más
seguro para validar:

- descubrimiento de sesiones;
- despacho;
- independencia;
- notificación;
- lectura de informe;
- degradación.

Una vez estable, el mismo transporte puede extenderse a `cross-review` y finalmente a
`cross-implement`, donde los riesgos de escritura son mayores.

## Conclusión

La idea es viable y encaja con la arquitectura existente. No requiere cambiar la forma en que el
usuario inicia SDD: el comando sigue siendo `/sdd-flow <prompt>`.

Sí requiere modificar las skills porque actualmente ninguna descubre ni despacha a terminales
reales de Orca. El cambio correcto no es reemplazar los contratos existentes, sino separar:

- **qué trabajo** se pide: responsabilidad de `co-explore`, `cross-review` y `cross-implement`;
- **cuándo se pide**: responsabilidad de `sdd-flow`;
- **cómo llega al secundario**: nueva capa de transporte `orca-session | cli`;
- **cómo vuelve el resultado**: `worker_done` validado por task, dispatch y terminal.

Con esta separación, el secundario puede usar la capacidad configurada de su sesión real y el
ecosistema mantiene portabilidad, auditabilidad y degradación segura.
