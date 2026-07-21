# cross-model-orca

Skill-librería que aloja el protocolo común del transporte cross-model `orca-session` y el único
artefacto ejecutable del repo: un módulo Node del lado del conductor que abre una sesión
interactiva real de la otra familia (Codex cuando conduce Claude; Claude cuando conduce Codex) vía
[Orca](https://orca.dev), la deja trabajar, y cosecha su resultado con autoridad. Es la alternativa
a `codex exec`/`claude -p` (el CLI headless de hoy) cuando el usuario tiene Orca disponible; sin
Orca, el comportamiento de las skills que la consumen no cambia.

Esta librería no ejecuta nada por sí misma sobre un pedido del usuario: no tiene una tarea propia
que "hacer". Aloja el protocolo (envelope con autoridad, tres capas de control, matriz de
lanzamiento, matriz de raíces de persistencia, privacidad v1) y los módulos Node que las skills que
sí hacen algo consumen desde su propio paso "resolver transporte".

## Cuándo se usa / quién la consume

El usuario no invoca `cross-model-orca` directo. La consumen, leyendo sus archivos, las cinco
skills del ecosistema que ya delegan en la otra familia:

- `co-explore` — para su rama `orca-session` al explorar/investigar/debatir en paralelo.
- `cross-review` — para su rama `orca-session` al pedir una segunda opinión sobre un artefacto de
  diseño (reutiliza sesión entre rondas).
- `cross-implement` — para su rama `orca-session` al delegar la implementación de un work order
  congelado (sesión write-capable).
- `sdd-flow` / `sdd-orchestrator` — propagan la clave `cross_model.transport` a las skills
  anteriores cuando `co_explore`/cross-review/cross-implement están activos dentro del flujo SDD.

Cada skill llamadora conserva su rama `cli` intacta: `orca-session` es aditiva, nunca un
reemplazo obligatorio.

## Modelo mental

1. El conductor crea una sesión **fresca** de la otra familia vía Orca (nunca reutiliza una sesión
   ajena que no haya creado el propio flujo).
2. El secundario trabaja — read-only o write-capable, según el rol — y cierra su turno con un
   envelope con autoridad (`X-CMO: taskId=… dispatchId=… nonce=…` + `STATUS: done`). El secundario
   **no cosecha ni escribe su propio informe**.
3. El **conductor** detecta el fin del turno, lee el transcript/rollout de su propia sesión,
   valida el envelope (autoridad + `nonce` del dispatch en curso) y persiste el informe en la ruta
   que le corresponde a la skill llamadora.
4. Ante cualquier incertidumbre (Orca no alcanzable, locator ambiguo, sesión no propia, falta un
   binario/MCP), el transporte degrada de forma transparente al CLI headless de siempre.

El detalle completo de cada paso — envelope, tres capas de control, matriz de lanzamiento, matriz
de raíces por skill, privacidad v1, vigilancia manual (P4) y degradación — está en `SKILL.md`; el
resolver de transporte, la recuperación y la espera bloqueante están en `reference.md`.

## Instalación

Instalar es, en esencia, **copiar la skill-librería** (y las skills que la consumen) a
`~/.claude/skills/`: los módulos Node resuelven su raíz **solos** (autolocalización vía
`import.meta.url`), así que no hace falta setear nada. Ver [`install.md`](./install.md) para el
detalle: verificación de Node ≥18, la variable de entorno **opcional** `CROSS_MODEL_ORCA` (solo
como override, para correr los módulos desde una ubicación distinta de su propio `assets`), e
instalación reproducible de `skills-ref` (el validador de formato de skills) como checkpoint
manual. No se duplica acá.

## Estructura de archivos

```
skills/cross-model-orca/
  SKILL.md          # protocolo, cargado al activar la skill (agente en ejecución)
  reference.md      # resolver de transporte, recuperación, espera — detalle pesado
  README.md          # este archivo, documentación para humanos
  install.md         # contrato de instalación (Node, CROSS_MODEL_ORCA, skills-ref)
  assets/
    run-orca-session.mjs           # ENTRYPOINT CLI (guardless): parsea argv y corre el flujo (lo que invoca el conductor)
    orca-session.mjs               # librería: runOrcaSession = createOwnedSession→createDispatch→awaitDone (la importan el CLI y los tests)
    dispatch-adapter.mjs           # librería: sesión, dispatch, espera, recuperación (createOwnedSession/createDispatch/awaitDone)
    harvest-core.mjs               # funciones puras: envelope, contención, parser, dedup-FSM
    harvest-from-transcript.mjs    # ENTRY conductor: espera + cosecha del transcript
    lib/platform.mjs               # rutas por plataforma, preflight de Node
    launch/
      profiles.md                 # matriz de lanzamiento familia×rol×modo (POSIX+PowerShell)
      mcp-inventory.md             # inventario MCP fail-closed + namespacing de tools
      claude-readonly.settings.json / claude-write.settings.json
      codex-readonly.config.toml / codex-write.config.toml
    test/                         # tests de los módulos de arriba + fixtures
  spikes/
    RESULTS.md                    # bitácora de los spikes que fijan locator y señal
```

`README.md` es solo documentación para humanos: el agente en ejecución no lo lee. Lo que el agente
carga al activar la skill es `SKILL.md`, y `reference.md` solo cuando `SKILL.md` lo indica
explícitamente.
