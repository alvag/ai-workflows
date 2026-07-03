---
name: sdd-orchestrator
description: >-
  Orquesta un cambio con un objetivo común repartido entre varios repos git que
  viven bajo una carpeta contenedora (que puede no ser un repo). Arma una spec
  madre con criterios de aceptación globales y contratos entre servicios, reparte
  el trabajo en un sub-plan por repo (con dependencias declarables), implementa en
  paralelo delegando cada repo a la skill `sdd-flow`, y cierra de forma centralizada
  (revisión, commit, push) bajo control del usuario. Soporta varias features a la
  vez con lock cooperativo. Usar cuando un mismo objetivo cruza 2+ repos bajo una
  carpeta contenedora. Para un solo repo, usar `sdd-flow` directamente. Invocación
  explícita: "/sdd-orchestrator" parado en la carpeta contenedora.
argument-hint: "[<objetivo|ticket multi-repo> | retoma <id> | estado | cierra <id>]"
# disable-model-invocation es una clave REAL de Claude Code: bloquea la invocación
# vía Skill tool (la skill queda solo-slash: /sdd-orchestrator). Se mantiene a
# propósito: invocación explícita, sin competir por el auto-trigger. Nada invoca a
# esta skill programáticamente, así que el bloqueo no afecta integraciones.
disable-model-invocation: true
---

# sdd-orchestrator — SDD multi-repo

Capa de **orquestación** sobre `sdd-flow`. Coordina un cambio con **un objetivo común que se reparte entre varios repos git** ubicados bajo una carpeta contenedora (típicamente no es un repo git: un `backend/` con microservicios).

**Restricción de diseño: no reimplementa SDD.** Toda la mecánica por-repo (crear rama, implementar, tests/build, verificar AC, frenar antes de commitear, commit selectivo) la ejecuta `sdd-flow` vía su **Vía B** (`/sdd-flow implement <ruta-carpeta>`). Esta skill solo aporta: contexto global, spec madre, selección de repos, reparto, fan-out paralelo y cierre. **Nunca modifica `sdd-flow`.**

El ciclo, en tres fases:

```
FASE 1 · DISEÑO (centralizada, en la carpeta contenedora, con gates humanos)
  gather-context global
   → análisis cross-repo: propone repos involucrados   ──► el usuario confirma
   → master-spec.md (AC globales + contratos entre servicios)     [GATE]
   → reparto: sub-plan + sub-tasks por repo, con dependencias     [GATE]
   → se escribe .plans/<id>/ aprobado dentro de cada repo

FASE 2 · EJECUCIÓN (delegada, paralela, respetando el DAG)
  por cada repo elegible y libre:  /sdd-flow implement .plans/<id>/   (Vía B)
   → crea rama · implementa · tests+build · verifica AC · FRENA antes de commitear
  fallo de un repo → cascada: bloquea solo a sus dependientes; los demás siguen

FASE 3 · CIERRE (centralizada, el usuario al mando)
  reporte consolidado (verdes / fallidos / bloqueados)
   → revisión + commit + push por repo, aprobados desde el orquestador
   → verificación de AC de integración (cross-repo, manual salvo comando dado)
```

Artefactos en disco (modelo híbrido):

```
<contenedora>/             # p. ej. backend/ — puede NO ser repo git
├─ .sdd/                   # capa orquestadora, LOCAL (nunca se trackea ni commitea)
│  ├─ <id>/
│  │  ├─ master-spec.md    # QUÉ global + AC-1..N + contratos entre servicios
│  │  └─ manifest.yml      # estado de la orquestación (repos, status, deps, AC)
│  └─ archived/<id>/       # orquestaciones cerradas (archive/abort); fuera del lock y del listado
├─ servicio-a/             # repo git autónomo
│  └─ .plans/<id>/         # flujo sdd-flow normal (plan.md + spec.md + tasks.md; tasks.md salvo en trivial)
├─ servicio-b/
│  └─ .plans/<id>/
└─ gateway/
   └─ .plans/<id>/
```

Como `.sdd/` y los `.plans/<id>/` son **locales (untracked)**, conviven N features sin pisarse: todo está namespaced por `<id>` (clave del ticket o slug del título). Cada `.plans/<id>/` por repo es un flujo `sdd-flow` común y **autónomo**: se puede entrar a un repo solo y retomarlo con el `/sdd-flow` estándar.

## Reglas no negociables

1. **La spec madre manda.** No se reparte trabajo (sub-planes) sin un `master-spec.md` aprobado. La verificación final chequea contra sus criterios de aceptación.
2. **Gates de diseño, una sola vez y centralizados.** Los gates de `master-spec.md` y de reparto ocurren con el usuario antes de delegar, y nunca silenciosos: se anuncia y se espera confirmación explícita en cada uno.
3. **No se delega a un repo no confirmado.** La lista de repos involucrados la confirma el usuario (Fase 1). Nunca se crea rama ni se implementa en un repo que el usuario no eligió.
4. **Los agentes frenan antes de commitear.** La Fase 2 implementa y verifica, pero el commit/push de cada repo se decide en la Fase 3, bajo control del usuario.
5. **Trazabilidad cross-repo.** Cada `AC-n` global lo cubre ≥1 repo (`covers_ac` en el manifest); ninguna sub-task referencia un AC inexistente. Se valida antes de salir de Fase 1 (cross-artifact check).
6. **Lock cooperativo.** Antes de tocar un repo, verificar que no esté retenido por otra orquestación activa (otro `.sdd/*/manifest.yml`). Nunca hacer checkout de un repo tomado sin resolver el conflicto.
7. **Nada de lo que genera el orquestador se trackea.** `.sdd/` es local, igual que los `.plans/`/`.specify/` de `sdd-flow`. La skill nunca los stagea, comitea ni los agrega a un `.gitignore` compartido.
8. **Degradación elegante.** Si falta un MCP/CLI (tracker, navegador, host de Git) o `sdd-flow` no está disponible, avisar y continuar con lo que haya, o detenerse explicando el bloqueo. Descubrir por capacidad, no por nombre de tool.

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos del flujo multi-repo. Ley fundamental:

> **NINGÚN AC `[integration]` SE DA POR CUMPLIDO EN UN REPO — SOLO EN LA FASE 3.** Un repo verde no cierra una integración; eso es trabajo cross-repo con evidencia propia.

Si reconoces alguno de estos pensamientos, detente y vuelve al paso correspondiente.

| Racionalización | Realidad |
|---|---|
| "Los dos repos del contrato están verdes, doy la integración por cumplida" | Un AC `[integration]` solo se verifica en Fase 3 con evidencia cross-repo (regla 5; Fase 3.3). Verde por-repo ≠ integración probada. |
| "Este repo parece involucrado, le creo la rama y arranco" | No se delega a un repo no confirmado por el usuario (regla 3). La propuesta se confirma en la selección de repos. |
| "Un repo falló pero los demás siguen igual, sigo todos" | El fallo bloquea **a sus dependientes** en el DAG (`blocked`); arrancarlos igual rompe la cascada (Fase 2.4). |
| "El repo aparece en otra orquestación pero entro igual, total es rápido" | Lock cooperativo (regla 6): un repo en `status` no terminal está tomado; resolver el conflicto antes de tocarlo. |
| "Commiteo los verdes yo mismo para terminar antes" | El commit/push es de Fase 3, bajo control del usuario, con el mecanismo de `sdd-flow` (regla 4). |
| "Re-reviso cada plan por repo además del reparto, por las dudas" | El reparto ya cubrió los `plan.md`/`tasks.md`; re-revisar duplica (la Fase 2 delega con `cross_review.mode: off`). |

## Compatibilidad con Plan Mode / modos no mutantes

Si el entorno prohíbe mutaciones: ejecutar solo pasos read-only (detección de repos, `gather-context`, análisis, propuesta conversacional de `master-spec.md`), **no** escribir `.sdd/` ni `.plans/`, **no** crear ramas ni delegar implementación. Avisar que el flujo real queda bloqueado y que al salir se retoma desde escribir `master-spec.md`.

## Dependencia de `sdd-flow`

Esta skill **requiere** `sdd-flow` instalada en el entorno. Antes de la Fase 2, verificar que existe (buscar la skill por capacidad: un flujo SDD por-repo con bootstrap `implement <ruta>`). Si no está, avisar y detener: el orquestador no implementa por su cuenta.

## Revisión cross-model (segunda opinión, opcional)

En la Fase 1, antes de los gates de `master-spec.md` y de reparto, si está disponible la skill
**`sdd-cross-review`** se puede correr una **segunda opinión de un modelo de otra familia que el
autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) sobre
esos artefactos, en read-only. Es el candidato más fuerte de todo el flujo SDD: los **contratos
entre servicios** y los **AC `[integration]`** son justo donde un segundo modelo caza
inconsistencias que un humano pasa por alto. **Augmenta el gate, no lo reemplaza.**

- **Dependencia blanda.** Si `sdd-cross-review` no está instalada, omitir la revisión y seguir con
  el gate humano normal. Detectarla por capacidad (regla 8). Si está instalada, invocarla con el
  **Skill tool** (`sdd-cross-review`; esa skill sí es invocable por el modelo). (Distinta de
  `sdd-flow`, que **sí** es dependencia dura: sin ella no hay Fase 2.)
- **Qué se revisa y dónde:** `master-spec` (foco en contratos y AC `[integration]`) en el gate 1.3,
  y `reparto` (foco en cobertura AC↔repo, `depends_on` y ciclos del DAG) en el gate 1.4. El
  `review-log.md` queda en `.sdd/<id>/review-log.md` (local, untracked).
- **Defaults del orquestador:** `cross_review.mode: auto` equivale a **on** para estos dos gates, y
  la revisión se invoca con `complexity: complex` (los artefactos de orquestación son, por
  definición, el caso complejo — eso fija el presupuesto de tiempo del revisor).
- **Review en capas, sin redundancia.** Los `plan.md`/`tasks.md` por-repo se generan en el reparto
  (1.4) y quedan cubiertos por la revisión del **reparto**. Por eso, cuando la Fase 2 delega a
  `sdd-flow` (Vía B) sobre un plan ya escrito, **no se re-revisa** por defecto: pasar la corrida
  con `cross_review.mode: off` al `sdd-flow` delegado para no duplicar la segunda opinión (override
  si quieres revisión por-repo adicional).
- **Modo de ejecución.** `cross_review.execution` (en `manifest.yml`, heredado por la revisión)
  controla cómo se espera al revisor: `auto` (default; sync si el conductor puede fijar un timeout
  largo, background+poll acotado si su exec es corto), `sync` o `background`. En todos los modos la
  skill garantiza un **tope duro** → `UNAVAILABLE`, nunca espera indefinida.
- **Degradación (nunca bloquea).** Sin revisor, invocación de la skill fallida, fallo en runtime,
  timeout/`poll_deadline` vencido, o `cross_review.mode: off` → avisar en una línea y seguir con el
  gate humano. Misma filosofía que la regla 8.

> Detalle del loop, el contrato con el revisor (Codex o Claude según quién conduzca) y el formato del log viven en la propia
> `sdd-cross-review`. Acá el orquestador solo decide **cuándo** invocarla y **presenta** su salida.

## Co-exploración cross-model (opcional)

Mismo patrón que `sdd-flow` (ver su sección "Co-exploración cross-model" en
`skills/sdd-flow/SKILL.md`), aplicado a los dos artefactos de Fase 1 — que ya se revisan como
`complex`. Si está disponible la skill **`sdd-co-explore`**, un modelo de otra familia que el
autor explora el mismo terreno **cross-repo** en paralelo, antes de que el conductor escriba
`master-spec.md` o el reparto. Contrato completo (formato del informe, independencia, degradación)
en la propia `sdd-co-explore`; acá solo cuándo se despacha y qué contexto recibe.

- **`explore` (pre-`master-spec`).** Corre **después de 1.2** (selección de repos confirmada — el
  revisor necesita saber dónde mirar) y antes de 1.3: se arma el paquete de contexto global y se
  invoca `sdd-co-explore` con los repos confirmados como `working_dir`s. El foco del informe se
  corre a nivel sistema: contratos entre servicios existentes, superficies de integración, riesgos
  `[integration]`. El conductor explora en paralelo y sintetiza igual que en `sdd-flow` (guía en
  `sdd-co-explore` → "La síntesis"). **Si el informe sugiere que un repo no confirmado está
  involucrado** (en Riesgos/Incógnitas), re-abrir la selección de repos con el usuario antes de
  escribir `master-spec.md`.
- **`counter-plan` (pre-reparto).** Con `master-spec.md` aprobada, antes de 1.4: el revisor
  propone su propio **reparto tentativo** (qué repo cubre qué AC, `depends_on`, orden) que el
  conductor contrasta antes de escribir el reparto real. Errores de DAG y cobertura AC↔repo son el
  objetivo.
- **Artefactos.** `.sdd/<id>/co-explore/` (mismos nombres que en `sdd-flow`), local y untracked
  como el resto de `.sdd/` (regla 7).
- **Config.** Sub-clave `cross_review.co_explore` en el `manifest.yml` de la orquestación
  (ver "Esquema de `manifest.yml`"). Default `auto` = **on**: los artefactos de orquestación
  son el caso complejo por definición, igual que su cross-review. Deadlines: usar los de
  `complexity: complex` (600 s) como piso.
- **Crítica informada.** Los informes se pasan como `context_paths` adicionales a
  `sdd-cross-review` en la revisión de `master-spec` (gate 1.3) y de `reparto` (gate 1.4).
- **Sin doble co-exploración.** La Fase 2 ya delega con `cross_review.mode: off`; dejar explícito
  que eso también apaga `co_explore` en los `sdd-flow` por-repo — la exploración global ya cubrió
  ese terreno.

## Router de intención (alias coloquiales → fase / sub-paso)

| El usuario dice (ej.) | Paso |
|---|---|
| "/sdd-orchestrator", "tengo un cambio que toca varios servicios", pega objetivo + carpeta | Fase 1 desde `gather-context` global → **STOP en cada gate** |
| "qué repos toca esto", "cuáles servicios entran" | Fase 1 · selección de repos (análisis propone, usuario confirma) |
| "arma la spec global", "define el objetivo y los contratos" | Fase 1 · `master-spec.md` → **GATE** |
| "reparte el trabajo", "arma los planes por repo" | Fase 1 · reparto + cross-artifact check → **GATE** |
| "sin cross-review", "salta la segunda opinión" / "con cross-review" | override de revisión cross-model de la orquestación (off/on; ver "Revisión cross-model") |
| "con co-exploración" / "sin co-exploración" | override de co-exploración de la orquestación (on/off; ver "Co-exploración cross-model") |
| "ejecuta `<repo>` acá", "modo inline" / "vuelve al fan-out" | override del **modo de ejecución** de la Fase 2 (inline/fanout; ver Fase 2 → "Modo inline") |
| "implementa todo", "dale", "ejecuta" (con reparto aprobado) | Fase 2 · fan-out a `sdd-flow` |
| "cómo viene", "estado", "qué falta" | leer `manifest.yml` y reportar |
| "retoma", "sigue la orquestación `<id>`", "¿en qué quedó?" | Resume global |
| "cierra", "commitea los verdes", "publica" | Fase 3 · cierre (revisión/commit/push) |
| "verifica la integración" | Fase 3 · AC de integración |
| "archiva la orquestación `<id>`", "ya está todo probado, ciérrala" | sub-paso `archive` |
| "aborta/cancela la orquestación `<id>`" | sub-paso `abort` |

---

## Fase 1 · Diseño (centralizada, con gates)

### 1.1 `gather-context` global
Consolidar el objetivo del cambio desde el ticket (si hay clave de tracker y MCP/CLI disponible) + el prompt del usuario, a nivel **sistema** (no de un repo). Mismo criterio que `sdd-flow gather-context`, pero el alcance es el conjunto de servicios. Fijar el `<id>` (clave del ticket, o slug del título si no hay tracker). Si el usuario indicó un **prefijo de rama** para la orquestación (p. ej. "con prefijo de rama feature/"), registrarlo para guardarlo luego en `manifest.yml` (`branch_prefix`).

### 1.2 Selección de repos
1. **Universo:** enumerar los subdirectorios de la carpeta contenedora que son repos git (probar `git rev-parse --is-inside-work-tree` dentro de cada uno, o detectar `.git`). Detalle en `reference.md` → "Matriz de detección de repos".
2. **Propuesta:** a partir del objetivo, proponer qué repos parecen involucrados (por nombre, por los contratos mencionados, por búsqueda en código si el alcance lo amerita).
3. **Confirmación (checkpoint):** mostrar la lista propuesta y dejar que el usuario agregue/saque repos. **Nunca** se trabaja un repo no confirmado (regla 3). Con co-exploración activa, acá se despacha el `explore` global (ver "Co-exploración cross-model").
4. Si no hay ningún repo git bajo la carpeta, **avisar y detener** (no inventar).

### 1.3 `master-spec.md` → GATE
1. Crear `<contenedora>/.sdd/<id>/` (POSIX: `mkdir -p`; PowerShell: `New-Item -ItemType Directory -Force`).
2. Escribir `master-spec.md` con la plantilla de `reference.md` → "Plantilla de `master-spec.md`". Mínimo: problema/objetivo global, alcance (in/out) a nivel sistema, **criterios de aceptación `AC-1..N`** cada uno etiquetado `[repo-local]` o `[integration]`, **contratos entre servicios** (qué expone cada uno y qué consume), y el **reparto** (qué repo cubre qué AC).
3. **STOP** — si la **revisión cross-model** está activa (ver "Revisión cross-model"), ejecutar `sdd-cross-review` sobre `master-spec.md` (foco en contratos entre servicios y AC `[integration]`; con co-exploración corrida, sumar `co-explore/findings-<familia>.md` como `context_paths` adicional — ver "Co-exploración cross-model") antes de presentar. Presentar la spec madre (con el resumen de crítica, si lo hubo) y pedir aprobación. No avanzar sin ella.

### 1.4 Reparto → GATE
Con co-exploración activa, antes del punto 1 se despacha el `counter-plan` (ver "Co-exploración cross-model"): el revisor propone su **reparto tentativo**, que el conductor contrasta antes de escribir el reparto real.

1. Por cada repo confirmado, crear `<repo>/.plans/<id>/` como un flujo `sdd-flow` completo:
   - **`spec.md`** — la fuente de los AC que el agente delegado verificará en Fase 2 (sin ella, el `verify` de `sdd-flow` no tiene contra qué chequear). Contenido: problema/objetivo recortado a lo que aporta el repo, los AC de su `covers_ac` copiados **textuales** de la master-spec (manteniendo los IDs globales `AC-n` para trazabilidad), los contratos que el repo expone/consume, y una nota explícita de que los AC `[integration]` en los que participa **no** se verifican en el repo (van a Fase 3; nunca darlos por cumplidos localmente). Mini-plantilla en `reference.md` → "Spec por repo".
   - **`plan.md`** con el **header YAML de `sdd-flow`** (`id`, `branch`, `base_commit`, `change_type`, `complexity`, `status: planned`, `created_at`) + las secciones de enfoque/archivos/tests/verification. La **`complexity` por repo la asigna el orquestador** en el reparto (default `normal`; `trivial` solo si el cambio del repo es trivial → spec y tasks embebidas en `plan.md`, igual que `sdd-flow`). `base_commit` = HEAD actual de la rama base del repo; la rama todavía no existe — la crea `sdd-flow` en Fase 2 (su `resume` la recrea desde `base_commit` cuando no la encuentra).
   - **`tasks.md`** (salvo *trivial*) con el **formato detallado** de `sdd-flow` (cada task con Por qué / Archivos / Pasos / Verificar / `AC-n`).

   El `branch` se nombra con la convención de `sdd-flow` (`<prefijo>/{id}-{slug}`), resolviendo el `<prefijo>` (el `{type}`) por repo con esta **precedencia**: (1) `branch_prefix` del `<repo>/.specify/config.yml` si lo tiene (su CI/CD manda) → (2) `branch_prefix` de la orquestación (del `manifest.yml`) → (3) prefijo **semántico** del cambio. Normalizar quitando la barra final si la trae. (Ese `<repo>/.specify/config.yml` se puede generar con `/sdd-flow init` dentro del repo; hace el reparto más determinista.)
2. Escribir/actualizar `manifest.yml` (esquema en `reference.md`): por repo, `path`, `branch`, `status`, `depends_on` (el DAG) y `covers_ac`.
3. **Cross-artifact check (regla 5):** validar que cada `AC-n` global está cubierto por ≥1 repo y que ninguna sub-task referencia un AC inexistente. Reportar huérfanos antes del gate.
4. **STOP** — si la **revisión cross-model** está activa, ejecutar `sdd-cross-review` sobre el `reparto` (artefacto: `manifest.yml`; contexto: `master-spec.md` + los `plan.md` por repo + el reparto tentativo del revisor, si co-exploración corrió; foco en cobertura AC↔repo, `depends_on` y ciclos del DAG) antes de presentar. Presentar el reparto (tabla repo · branch · AC cubiertos · dependencias, con el resumen de crítica si lo hubo) y pedir aprobación. Al aprobar, poner cada repo en `status: tasks-ready`.

---

## Fase 2 · Ejecución (delegada, paralela)

Precondición: reparto aprobado y `sdd-flow` disponible (ver "Dependencia de `sdd-flow`").

1. **Resolver el orden por DAG.** Repos elegibles = aquellos cuyos `depends_on` están todos en estado terminal verde (`verified`/`committed`/`pushed`/`pr-open`/`done`). Los demás esperan.
2. **Lock cooperativo previo (regla 6).** Antes de tocar cada repo elegible, leer los **otros** `.sdd/*/manifest.yml`. Si el repo aparece en otra orquestación con `status` **no terminal** (≠ `pushed`/`pr-open`/`done`), está **tomado**: aplicar el protocolo del lock (ver "Orquestaciones concurrentes"). No arrancarlo hasta resolver.
3. **Fan-out.** Por cada repo elegible y libre, despachar un agente que ejecute la **Vía B de `sdd-flow`** (`implement .plans/<id>/`) **parado en `<repo>/`**, con la corrida en `cross_review.mode: off` (que apaga también `co_explore`): los `plan.md`/`tasks.md` por repo ya quedaron cubiertos por la revisión del reparto y la exploración global ya cubrió ese terreno. **Cómo se delega:** `sdd-flow` es solo-slash (`disable-model-invocation`), así que el subagente **no** puede invocarla con el Skill tool — el prompt del agente le indica **leer** `sdd-flow/SKILL.md` (y `reference.md` si lo necesita) desde el directorio de skills y ejecutar su Vía B siguiendo ese contrato. Plantilla del prompt y contrato de retorno en `reference.md` → "Prompt del agente delegado". El agente hereda toda la Vía B: crea rama, implementa task por task (con el **pre-flight scan** y el **reviewer por-task** del modo subagent de `sdd-flow`, si su entorno los soporta; y el **debugging sistemático** ante un test/AC en rojo), corre tests+build, verifica los AC `repo-local` con la **gate function**, y **FRENA antes de commitear** (regla 4). Usar el patrón de subagentes en paralelo (cada repo es un working tree disjunto → sin colisión de archivos) con un **tope de concurrencia**; los repos en exceso quedan en cola. Descubrir la capacidad de paralelismo por entorno, no por nombre de tool.

   **Modo inline (opcional).** Con `execution_mode: inline` en el `manifest.yml` o a pedido del usuario ("ejecuta `<repo>` acá", "modo inline"), el orquestador ejecuta la Vía B de ese repo **en su propia sesión**, parado en `<repo>/` — mismo contrato que el agente delegado (incluido **FRENAR antes de commitear**) y mismo update del manifest; los repos van **de a uno** (sin paralelismo inline). Útil cuando queda un solo repo elegible o el usuario quiere seguir la implementación de cerca. Trade-off: carga el contexto del orquestador — para fan-outs grandes, seguir con agentes. El default es y sigue siendo `fanout`; el repo ejecutado inline hereda el `implement` de `sdd-flow` con sus propios modos.
4. **Recolección + cascada de fallos.** Al volver cada agente, leer su reporte estructurado (contrato en `reference.md` → "Prompt del agente delegado"; si el reporte falta o no parsea, **releer el `status` que `sdd-flow` persistió** en `<repo>/.plans/<id>/plan.md` y tratar la ausencia de `verified` como fallo) y actualizar el `status` del repo en `manifest.yml`:
   - Verde (`verified`): queda listo para el cierre.
   - **Fallo** (tests/build rojos o AC no cumplido): marcar `failed`, **no commitear**, y **bloquear solo a sus dependientes** en el DAG (marcarlos `blocked`). Los repos independientes siguen. Detalle en `reference.md` → "Cascada de fallos".
   - Recalcular el DAG con los repos recién liberados y volver al paso 1 hasta que no queden elegibles.

`failed` y `blocked` son estados **propios del manifest** del orquestador (no del ciclo de `sdd-flow`).

---

## Fase 3 · Cierre (centralizada, el usuario al mando)

1. **Reporte consolidado.** Tabla por repo: `repo · status · AC repo-local cumplidos · verde/fallido/bloqueado`. Listar aparte los AC `integration` pendientes.
2. **Commit/push centralizado.** Para cada repo en `verified`, ofrecer (controlado por el usuario): revisión → commit → push, **siguiendo el mecanismo de commit de `sdd-flow`** (leído de sus archivos — no vía Skill tool, que su flag bloquea): staging selectivo + mensaje convencional construido **inline** (su `reference.md` → "Construcción del mensaje de commit"; sdd-flow no depende de ninguna skill externa para commitear). Soportar lote ("commitea todos los verdes"). Mostrar siempre, antes de ejecutar, los archivos staged + mensaje + comando. Actualizar `status` a `committed`/`pushed` en el manifest. El scope del commit por defecto es el `<id>` global (override por repo si el servicio tiene su propia clave de ticket).
3. **AC de integración.** Los AC `[integration]` no los cierra un agente aislado. Aplicarles la **gate function** del `verify` de `sdd-flow`, a nivel cross-repo: IDENTIFICAR el comando/observación que prueba la integración → CORRERLO fresco → LEER salida + exit code → VERIFICAR que confirma el AC. Si el usuario proveyó un comando de integración (p. ej. `docker compose up` + smoke test), ejecutarlo y reportar la **evidencia**; si no, listarlos como **verificación manual** pendiente. Nunca darlos por cumplidos sin esa evidencia (ley de la sección "Red flags").

---

## Resume global (retomar una orquestación)

Punto de entrada cuando vuelves a una orquestación ya empezada (sesión nueva, o tras cambiar de contexto).

1. Si el usuario nombró un `<id>`, usar ese; si fue genérico ("¿en qué quedé?"), **listar** las orquestaciones activas leyendo cada `.sdd/*/manifest.yml` (excluir `.sdd/archived/`) y mostrar `id · #repos · estado agregado`. Que elija.
2. Leer `manifest.yml` + el `status` de cada `<repo>/.plans/<id>/plan.md`. Si `<repo>/.plans/<id>/` no existe, buscar `<repo>/.plans/archived/<id>/` (el flujo del repo fue archivado por `sdd-flow` → tratarlo como `done`). **Anunciar el punto de cada repo** antes de actuar.
3. Por repo, retomar siguiendo el `resume` de `sdd-flow` (mismo mecanismo que el fan-out: el agente lee los archivos de `sdd-flow`, hace el checkout seguro a la rama del repo y salta al paso según su `status`). **No** re-crear `master-spec.md` ni duplicar `.plans/<id>/`.
4. Recalcular el DAG y continuar en la fase que corresponda (típicamente Fase 2 para los repos `tasks-ready`/`implementing`, o Fase 3 para los `verified`/`committed`).

---

## Sub-pasos `archive` / `abort` (cerrar o cancelar una orquestación)

**`archive`** — solo cuando el usuario confirma explícitamente que el cambio global está probado y correcto (decisión del usuario, nunca automática). Requiere todos los repos en `pushed`/`pr-open`/`done` (`pr-open` es el estado opcional de `sdd-flow` cuando se abrió el PR del repo desde su flujo).

1. Ofrecer delegar el `archive` de `sdd-flow` por repo (mueve `<repo>/.plans/<id>/` a `<repo>/.plans/archived/<id>/` y pone `status: done`).
2. Mover `.sdd/<id>/` a `.sdd/archived/<id>/` (`mv` plano; sigue siendo local — regla 7).
3. Confirmar que salió del listado de activas y que **liberó sus locks** (el algoritmo del lock ignora `.sdd/archived/`).

**`abort`** — cancelar una orquestación a medias (también decisión del usuario, nunca automática).

1. Por cada repo en curso, preguntar qué hacer: **pausar** (delegar el `pause` de `sdd-flow` → WIP commit en la rama del repo) o **descartar** el trabajo del repo — nunca descartar sin confirmación explícita por repo.
2. Anotar en el `manifest.yml` que la orquestación terminó abortada (`outcome: aborted`; ver esquema en `reference.md`) y mover `.sdd/<id>/` a `.sdd/archived/<id>/` para **liberar los locks**.
3. Reportar qué quedó en cada repo (ramas creadas, WIP commits, `.plans/<id>/` remanentes) para limpieza manual si se desea.

---

## Orquestaciones concurrentes (varias features a la vez)

El modelo soporta **N features simultáneas** porque todo está namespaced por `<id>`: `.sdd/<id-1>/` y `.sdd/<id-2>/`, y `<repo>/.plans/<id-1>/` y `<repo>/.plans/<id-2>/`. Lo que **no** se puede compartir es el working tree de un repo (git tiene un solo HEAD por repo).

- **Features sobre repos disjuntos:** conviven y se ejecutan en paralelo sin problema.
- **Features que comparten un repo:** se resuelve con el **lock cooperativo**. Antes de tocar el repo compartido, el orquestador detecta que otra orquestación lo retiene (su `manifest.yml` lo tiene en `status` no terminal) y ofrece:
  1. **Esperar / saltar** ese repo por ahora (sigue con los demás).
  2. **Pausar** el flujo de ese repo en la otra feature (`pause` de `sdd-flow` → WIP commit) y tomarlo.
  3. **Excluir** ese repo de esta feature.
  Los repos no compartidos siguen en paralelo; solo se serializa el repo en disputa. Algoritmo en `reference.md` → "Algoritmo del lock cooperativo".

> **Fuera de v1:** dar a cada feature su propio `git worktree` del repo compartido (paralelismo real). Queda anotado como evolución futura; rompe el supuesto de `.plans/` untracked por working tree.

## Reporte final

- Objetivo y `<id>`; repos involucrados.
- Tabla por repo: `status` · AC repo-local cumplidos · commit/push.
- AC de integración: verificados manualmente / pendientes.
- Fallidos y bloqueados (con el motivo).
- Estado agregado de la orquestación.

## Referencias internas

- `reference.md` — esquema de `manifest.yml`, plantilla de `master-spec.md`, spec por repo, formato de contratos, matriz de detección de repos, prompt del agente delegado (con contrato de retorno), algoritmo del lock cooperativo, cascada de fallos, ejemplos.
- `README.md` — qué es, cuándo usarla, requisitos, instalación y ejemplos.
