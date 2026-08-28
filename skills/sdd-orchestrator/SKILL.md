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
5. **Trazabilidad cross-repo.** Todo `AC-n` global tiene cobertura declarada, y declarada donde corresponde según su etiqueta; ninguna sub-task referencia un AC inexistente. Se valida antes de salir de Fase 1 (cross-artifact check). Sus cláusulas exactas, abajo en "Regla 5 — trazabilidad cross-repo".
6. **Lock cooperativo.** Antes de tocar un repo, verificar que no esté retenido por otra orquestación activa (otro `.sdd/*/manifest.yml`). Nunca hacer checkout de un repo tomado sin resolver el conflicto.
7. **Nada de lo que genera el orquestador se trackea.** `.sdd/` es local, igual que los `.plans/`/`.specify/` de `sdd-flow`. La skill nunca los stagea, comitea ni los agrega a un `.gitignore` compartido.
8. **Degradación elegante.** Si falta un MCP/CLI (tracker, navegador, host de Git) o `sdd-flow` no está disponible, avisar y continuar con lo que haya, o detenerse explicando el bloqueo. Descubrir por capacidad, no por nombre de tool.

### Regla 5 — trazabilidad cross-repo

Cobertura del **100 %** de los `AC-n` de la `master-spec.md`, con la **misma** cardinalidad que valida el cross-artifact check de la Fase 1: si acá dijera "≥1" para los de integración, la regla admitiría duplicados que el check rechaza, y lo escrito contradiría a lo que se ejecuta.

- Cada AC `[repo-local]` está cubierto por ≥1 repo, en su `covers_ac`.
- Cada AC `[integration]` está cubierto por exactamente una tarea de cierre.
- Un AC `[integration]` en el `covers_ac` de un repo es un error.
- Un AC `[repo-local]` en el `covers_ac` de una tarea de orquestación es un error.

Las dos últimas cláusulas son el mismo defecto de ubicación en sentidos opuestos, y por eso se declaran las dos: un AC cubierto en el lugar equivocado no está cubierto. Un `[integration]` anotado en un repo lo cerraría el `verify` local, que es lo que prohíbe la ley fundamental de "Red flags"; un `[repo-local]` anotado en una tarea de orquestación se lo saca de las manos al único que puede probarlo. Ninguna sub-task referencia un AC inexistente, y todo esto se valida antes de salir de Fase 1.

<!-- inventario-familias:inicio -->
### Inventario de familias

Antes de cualquier preflight, la **raíz** de la corrida resuelve una vez la selección de workers
despachables. El conductor conduce y no entra en `families`; cada worker es un proceso aparte en
sesión fresca. Si el contrato de invocación trae `family_inventory`, **no se resuelve nada**: se
heredan `families` y `selection`, no se relee config y no se vuelve a avisar.

| Paso | Regla |
|---|---|
| 1 — workers **declarados** | comprobar el CLI en PATH de cada familia de `families`, **la del conductor incluida**. Que el conductor esté corriendo por construcción no exime del preflight de su worker |
| 2 — **sin declaración** | solo si no hay declaración, detectar qué CLIs están en PATH para proponer la selección. POSIX: `command -v codex` / `command -v claude`. PowerShell: `Get-Command codex -ErrorAction SilentlyContinue`. Nada más cuenta |

Los dos pasos miden el CLI porque es **condición necesaria de todas las vías**: el runtime del subagente
resuelve su disponibilidad corriendo `codex --version` y `codex app-server --help`, así que exige el
CLI y algo más. No es la intersección restrictiva, es el piso común.

La auditoría **no comprueba versión, auth, aislamiento ni lanzamiento**, y **no afirma capacidad
operativa**: una familia presente puede fallar igual su preflight, y eso sigue siendo un fallo real.

`selection` conserva cómo se resolvió la lista: `full` abarca todas las familias presentes y
`user_choice` declara menos. Se persiste con `families`, se hereda y nunca se reconstruye sondeando.

**Declarado ↔ disponible:**

| Caso | Resultado |
|---|---|
| no declara una familia presente | preferencia válida; no se sondea ni se despacha ese worker |
| declara una familia cuyo CLI está ausente | **error**: nombra la familia y que la auditoría no la encuentra |

`families: []` sigue siendo error. La allowlist admite solo `claude | codex`, sin duplicados y
canonizada a minúsculas.
<!-- inventario-familias:fin -->

Cuando el manifest declara `families`, el orquestador compara primero las declaraciones locales y
aplica esta matriz por presencia de la clave:

| `families` en el manifest | `families` en el repo | Resultado |
|---|---|---|
| presente | presente e igual, o ausente | manda el manifest; la selección se propaga |
| presente | presente y distinta | **error**: contradicción entre allowlists de workers |
| ausente | — | el orquestador resuelve y persiste la selección antes de despachar |

Sin `families` en el manifest, la raíz sigue cinco pasos en orden: (1) propone la selección, (2)
detecta las familias con CLI despachable, (3) si hay otra presente pregunta si se suma, (4) abre un
STOP para persistir la respuesta y (5) aplica el ruteo de cada skill y recién entonces despacha:
**ningún worker sale antes**. Si solo está instalada una familia, el mismo STOP ofrece persistir
`[<familia-del-conductor>]` con `selection: full`.

El STOP muestra el **delta exacto** y hace un merge **no destructivo** en el `manifest.yml`: preserva
el resto, crea `cross_model` si falta y emite `schema_version: 1` cuando nace. El destino equivalente
de una raíz `sdd-flow` es `.specify/config.yml`, creando `.specify/` si falta. Ninguno se escribe sin
permiso explícito.

Una declaración vigente de `families` sin `selection` **no declara cómo se resolvió**. Antes del
primer despacho, abrir un STOP único que nombre la lista, ofrezca `full` y `user_choice` y persista
la respuesta con las mismas garantías. **No se infiere un default** ni se sondea para elegirlo:
preguntar una vez por una clave ausente no es descubrir familias. Desde la respuesta no se vuelve a
preguntar.

Solo después de esa resolución y comparación se entrega el mismo `family_inventory`, con
`families`, `source`, `selection` y `root`, al agente delegado o al camino inline. La skill anidada
**hereda la elección**: no la recalcula, no redetecta y no vuelve a avisar.

## Corridas delegadas en vuelo

Antes del primer despacho, comprobar en la raíz efectiva si existe
`.cross-model/conmutacion.lock`. Si existe, detener la corrida antes de crear o escribir el sobre e
informar `conmutación en curso`. No inferir que está huérfano por su PID ni borrarlo automáticamente.

Todo agente que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`, y
mientras el sobre siga activo cada turno del conductor cierra informando su estado. El punto de
despacho propio es uno:

- el **fan-out por repo** de la Fase 2.3: un agente por repo elegible y libre, corriendo la Vía B de
  `sdd-flow`

El orden es fijo y no se altera: **bitácora** → **sobre** → **despacho**. Primero se registra el
intento de la transición en la bitácora, después se escribe el sobre bajo `.cross-model/active/`, y
recién entonces se hace la tool call que lanza al agente. Es la única skill donde los tres registros
existen a la vez, y por eso es la única que los ordena: la bitácora registra el intento aunque el
despacho no llegue a ocurrir, y el sobre no puede nacer después de un worker que ya está corriendo.

Campos del sobre, transiciones, sonda por turno, cosecha y condiciones del retiro:
`skills/cross-review/corridas-en-vuelo.md`, la **sede única** del contrato. Es la regla normativa; acá solo se enumera dónde
aplica.

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos del flujo multi-repo. Ley fundamental:

> **NINGÚN AC `[integration]` SE DA POR CUMPLIDO EN UN REPO — SOLO EN LA FASE 3.** Un repo verde no cierra una integración; eso es trabajo cross-repo con evidencia propia.

Si reconoces alguno de estos pensamientos, detente y vuelve al paso correspondiente.

| Racionalización | Realidad |
|---|---|
| "Los dos repos del contrato están verdes, doy la integración por cumplida" | Un AC `[integration]` solo se verifica en Fase 3 con evidencia cross-repo (regla 5; Fase 3.3). Verde por-repo ≠ integración probada. |
| "Los AC de integración los verifico al final, no hace falta anotarlos" | Un AC `[integration]` sin tarea que lo cubra no tiene dueño: nadie lo ejecuta y nadie lo prueba. |
| "Este repo parece involucrado, le creo la rama y arranco" | No se delega a un repo no confirmado por el usuario (regla 3). La propuesta se confirma en la selección de repos. |
| "Un repo falló pero los demás siguen igual, sigo todos" | El fallo bloquea **a sus dependientes** en el DAG (`blocked`); arrancarlos igual rompe la cascada (Fase 2.4). |
| "El repo aparece en otra orquestación pero entro igual, total es rápido" | Lock cooperativo (regla 6): un repo en `status` no terminal está tomado; resolver el conflicto antes de tocarlo. |
| "Commiteo los verdes yo mismo para terminar antes" | El commit/push es de Fase 3, bajo control del usuario, con el mecanismo de `sdd-flow` (regla 4). |
| "Re-reviso cada plan por repo además del reparto, por las dudas" | El reparto ya cubrió los `plan.md`/`tasks.md`; re-revisar duplica (la Fase 2 delega con `cross_review.mode: off`). |
| "Anuncio el fan-out y cierro el turno para arrancarlo después" | Anunciar no es despachar: las tool calls del fan-out van en el **mismo turno** que las anuncias. Un turno que solo dice "voy a despachar" es un turno muerto que estanca la orquestación (Fase 2.3). |
| "El CLI de `cross` no está, lo re-chequeo repo por repo" | Si el preflight confirma que el binario no está (o auth/versión rota), es una **pared run-wide**: se degrada toda la orquestación, no se re-diagnostica por repo. Un **flake transitorio** de lanzamiento sí admite reintento acotado y no condena a los demás repos (Fase 2.3). |

## Compatibilidad con Plan Mode / modos no mutantes

Si el entorno prohíbe mutaciones: ejecutar solo pasos read-only (detección de repos, `gather-context`, análisis, propuesta conversacional de `master-spec.md`), **no** escribir `.sdd/` ni `.plans/`, **no** crear ramas ni delegar implementación. Avisar que el flujo real queda bloqueado y que al salir se retoma desde escribir `master-spec.md`.

## Dependencia de `sdd-flow`

Esta skill **requiere** `sdd-flow` instalada en el entorno. Antes de la Fase 2, verificar que existe (buscar la skill por capacidad: un flujo SDD por-repo con bootstrap `implement <ruta>`). Si no está, avisar y detener: el orquestador no implementa por su cuenta.

## Revisión cross-model (segunda opinión, opcional)

En la Fase 1, antes de los gates de `master-spec.md` y de reparto, si está disponible la skill
**`cross-review`** se puede correr una **segunda opinión de un modelo de otra familia que el
autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) sobre
esos artefactos, en read-only. Es el candidato más fuerte de todo el flujo SDD: los **contratos
entre servicios** y los **AC `[integration]`** son justo donde un segundo modelo caza
inconsistencias que un humano pasa por alto. **Augmenta el gate, no lo reemplaza.**

- **Dependencia blanda.** Si `cross-review` no está instalada, omitir la revisión y seguir con
  el gate humano normal. Detectarla por capacidad (regla 8). Si está instalada, invocarla con el
  **Skill tool** (`cross-review`; esa skill sí es invocable por el modelo). (Distinta de
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
  gate humano. Misma filosofía que la regla 8. **Si el retorno trae `aplicaciones_pendientes` mayor
  que cero, declararlo con sus `ids_pendientes` antes de liberar el gate:** una degradación no abre
  checkpoint, así que es la única oportunidad de decir que quedaron ediciones sin observar.
- **El paso previo: arbitrar las disputas, en los dos gates de Fase 1.** Si la revisión devuelve
  findings **`en-disputa`**, el humano los resuelve **antes** de elegir opción, dentro del mismo STOP
  y sin gate extra. Dos destinos: **resolver a favor del finding** (`aplicado`, y el conductor aplica
  la corrección) o **sostener el rechazo sobre el mérito** (`cerrado`). La decisión puede agruparse
  por motivo, pero **cada finding lleva su fila**. Se escribe **en este orden**: una `transicion` por
  finding con `actor: humano` y su rationale, y luego **una** `control-corrida` con
  `evento_corrida: arbitraje-disputas` y `finding_id` nulo —**también si no se arbitró ninguna**—,
  todas con la **`ronda` acumulada al abrir el checkpoint**. Por finding la secuencia es **decidir →
  editar → registrar**: la fila hacia `aplicado` se escribe **después** de aplicar la corrección,
  nunca antes. Y esa `control-corrida` cierra **ese acto**, no la posibilidad de arbitrar: un
  checkpoint posterior abre otro, con la suya. **Y si la opción elegida no concede**, los rechazos sin responder que ese paso deja `en-disputa` se arbitran en el mismo STOP, antes de cerrar: es la única oportunidad que van a tener, porque esas dos opciones cierran la corrida. Mecánica completa en
  `cross-review/reference.md` → "El paso previo: arbitrar las disputas".
- **Las cinco opciones del checkpoint, en los dos gates de Fase 1.** Si la revisión devuelve
  `tandas_concedibles`, los STOPs de `master-spec` (gate 1.3) y de `reparto` (gate 1.4) ofrecen
  —sin gate extra— **continuar así** · **conceder una tanda** · **seguir hasta `APPROVED`** ·
  **ronda de cierre con artefacto congelado** · **cerrar la revisión**. El presentador solo muestra
  el retorno, sin inferir, recalcular ni reordenar —salvo lo que el arbitraje de este STOP haya
  invalidado, que se re-deriva—: `serie` → `advertencia_bucle` →
  `aplicaciones_pendientes` con sus `ids_pendientes` → `opciones` con la `recomendada` marcada. Las
  cinco se ofrecen siempre: la recomendación advierte, no deshabilita, igual que `disponibles:
  false`. **El paso previo no las cambia:** no agrega una sexta ni altera sus postcondiciones.
  **Si `aplicaciones_pendientes` es mayor que cero, mostrarlo con sus `ids_pendientes`
  dentro de ese orden**: "continuar así" aprueba el
  artefacto, y quien elige tiene que saber que hay ediciones que ninguna ronda observó. **Tras
  arbitrar, ese conteo se re-deriva del ledger** —junto con sus IDs, los tres inventarios y todo
  campo derivado que el arbitraje mueva (`presupuesto`, `advertencia_bucle`, `recomendada`)—
  porque el valor del retorno es anterior al arbitraje; `causa_corte` y `disponibles` **no** se
  re-derivan, son históricos, y `disponibles` deja de usarse como advertencia una vez que hubo
  arbitraje. Con el modo automático activo, el fin de tanda es una
  **frontera interna** y la barrera del gate sigue marcada. Tras el gate, la llamadora **reanuda la
  misma corrida por su `run_id`** si el humano concede, o **finaliza el único manifest** si eligió
  una salida terminal; y su `resume` **consulta el descriptor durable** antes de iniciar otra
  revisión. Postcondiciones y descriptor en `cross-review/reference.md` → "Tandas y salida de
  rondas" y "Checkpoint durable".
  Si el retorno trae `contract_version: 1`, ofrece exactamente las cuatro de esa versión y omite
  serie, presupuesto y recomendación.
- **El fan-out de Fase 2 queda fuera:** delega con `cross_review.mode: off`, así que ahí no hay
  revisión que gobernar. Los gates de Fase 1 **sí** son interactivos, y por eso la excepción de
  "donde no hay gate no se pregunta" no los alcanza.

> Detalle del loop, el contrato con el revisor (Codex o Claude según quién conduzca) y el formato del log viven en la propia
> `cross-review`. Acá el orquestador solo decide **cuándo** invocarla y **presenta** su salida.

## Co-exploración cross-model (opcional)

Mismo patrón que `sdd-flow` (ver su sección "Co-exploración cross-model" en
`skills/sdd-flow/SKILL.md`), aplicado a los dos artefactos de Fase 1 — que ya se revisan como
`complex`. Si está disponible la skill **`co-explore`**, un modelo de otra familia que el
autor explora el mismo terreno **cross-repo** en paralelo, antes de que el conductor escriba
`master-spec.md` o el reparto. Contrato completo (formato del informe, independencia, degradación)
en la propia `co-explore`; acá solo cuándo se despacha y qué contexto recibe.

- **`explore` (pre-`master-spec`).** Corre **después de 1.2** (selección de repos confirmada — el
  revisor necesita saber dónde mirar) y antes de 1.3: se arma el paquete de contexto global y se
  invoca `co-explore` con los repos confirmados como `working_dir`s. El foco del informe se
  corre a nivel sistema: contratos entre servicios existentes, superficies de integración, riesgos
  `[integration]`. El conductor **no explora**: arbitra desde los índices de los dos workers y sintetiza igual que en `sdd-flow` (guía en
  `co-explore` → "La síntesis"). **Si el informe sugiere que un repo no confirmado está
  involucrado** (en Riesgos/Incógnitas), re-abrir la selección de repos con el usuario antes de
  escribir `master-spec.md`.
- **`counter-plan` (pre-reparto).** Con `master-spec.md` aprobada, antes de 1.4: el revisor
  propone su propio **reparto tentativo** (qué repo cubre qué AC, `depends_on`, orden) que el
  conductor contrasta antes de escribir el reparto real. Errores de DAG y cobertura AC↔repo son el
  objetivo.
- **Artefactos.** `.sdd/<id>/co-explore/` (mismos nombres que en `sdd-flow`), local y untracked
  como el resto de `.sdd/` (regla 7). Los artefactos de orquestación (`master-spec.md`, el
  reparto / `manifest.yml`) no citan la co-exploración ni sus informes — misma regla que en
  `sdd-flow` ("Los artefactos no citan la co-exploración").
- **Config.** Clave **top-level** `co_explore` en el `manifest.yml` de la orquestación
  (hermana de `cross_review`, no anidada — son ortogonales; ver "Esquema de `manifest.yml`").
  Default `auto` = **on**: los artefactos de orquestación son el caso complejo por definición,
  igual que su cross-review. Deadlines: usar los de `complexity: complex` (600 s) como piso.
- **Crítica informada.** Los informes se pasan como `context_paths` adicionales a
  `cross-review` en la revisión de `master-spec` (gate 1.3) y de `reparto` (gate 1.4).
- **Sin doble co-exploración.** La Fase 2 delega con `cross_review.mode: off` **y**
  `co_explore.mode: off` explícitos (son ortogonales: apagar uno no apaga el otro) — la
  exploración global ya cubrió ese terreno, así que los `sdd-flow` por-repo no re-exploran.

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

**La búsqueda de antecedentes se hereda de `sdd-flow` y corre en `1.2`, no acá:** su entrada es el universo de repos, que se enumera en el paso 1 de esa sección. Este paso solo fija el objetivo y el `<id>`.

### 1.2 Selección de repos
1. **Universo:** enumerar los subdirectorios de la carpeta contenedora que son repos git (probar `git rev-parse --is-inside-work-tree` dentro de cada uno, o detectar `.git`). Detalle en `reference.md` → "Matriz de detección de repos". **Si el universo queda vacío —ningún repo git bajo la carpeta—, avisar y detener acá** (no inventar): el paso frena antes de crear ningún artefacto y antes de buscar, porque no hay dónde hacerlo.
2. **Buscar antecedentes sobre todo el universo:** crear `<contenedora>/.sdd/<id>/` y correr ahí, repo por repo, el mismo procedimiento de repo único —`sdd-flow/reference.md` → "Búsqueda de antecedentes"—, dejando el resultado en `<contenedora>/.sdd/<id>/antecedentes.md`.
   - **Se busca antes de confirmar, y ese costo se declara:** se recorren repos que el humano puede descartar en el paso 4. Se paga porque buscar después dejaría la propuesta ciega justamente sobre los repos que se omitieron — que es el modo en que este defecto se reproduce a escala de sistema.
   - **Las seis fuentes corren sobre todo el universo, y el `fetch` también.** Es la única parte del procedimiento que **muta estado de git** —refs locales, nunca el working tree— y que **no se revierte**, así que alcanza a repos que el usuario puede sacar del reparto en el paso 4. **Ese costo se declara en el checkpoint**, con los repos tocados a la vista.
     Diferirlo a los repos confirmados se evaluó y **se descartó**, por dos razones medibles: dejaría las refs remotas de todo repo no confirmado en la foto de la última sincronización —el verde falso que la rama (b) de `sdd-flow` describe al decir que el `fetch` **no es opcional**—, y obligaría a inventar una cuarta causa de `no comprobada` —"repo todavía no confirmado"— que no es ninguna de las tres ramas disjuntas heredadas. Un efecto acotado a refs y declarado en un checkpoint cuesta menos que una evidencia falsamente vacía y un enum ampliado a escondidas.
   - **El esquema es el de repo único, extendido.** Su bloque de estado lleva además el **universo enumerado** y **cuáles se confirmaron**, más una entrada `repos` por repo —`repo` (ruta relativa a la contenedora), `busqueda`, `fuentes_terminadas`, `terminos` y `fingerprints`—: el estado de repo único replicado por repo. Su bloque declarativo lleva **cada campo con su dimensión `repo`**, más el residual global.
   - **La agregación tiene cuatro salidas, y ninguna se promedia:**

     | Qué pasó en el conjunto | Qué produce |
     |---|---|
     | **total global** — todos los repos cubiertos | ofrece **cerrar** la orquestación |
     | **cobertura parcial repartida** | el **residual por repo**, que es la resta exacta de lo acreditado |
     | **flujo activo en un repo** | abre la decisión de cuál de los dos sigue |
     | **fuentes no comprobadas en algunos repos** | **cualifica** el resultado global; nunca se lee como "examinado" |

   - **Ningún repo sale del reparto sin checkpoint humano.** En esta fase todavía no hay AC ni contratos —nacen en `1.3`, con la spec madre—, así que lo único retirable acá es un repo del universo; los AC y contratos se retiran más tarde, con su propio gate.
3. **Propuesta:** a partir del objetivo **y de los candidatos del paso 2**, proponer qué repos parecen involucrados (por nombre, por los contratos mencionados, por búsqueda en código si el alcance lo amerita). Un repo con hallazgo entra a la propuesta **aunque su nombre no lo sugiriera**: es justamente lo que el paso 2 aporta y ninguna heurística de nombres ve.
4. **Confirmación (checkpoint):** mostrar la lista propuesta —con los hallazgos de cada repo a la vista— y dejar que el usuario agregue/saque repos. **Nunca** se trabaja un repo no confirmado (regla 3). Confirmar los repos **no** es explorar: es acotar el `working_dir` del fan-out, y es un carve-out declarado de "el conductor no explora" (ver `co-explore/reference.md` → "Carve-outs de la regla del conductor").
5. **Despacho del `explore` global:** con co-exploración activa, se despacha acá, ya con los repos confirmados (ver "Co-exploración cross-model"). Su paquete de contexto lleva los **hechos crudos** del paso 2 —términos, estado por fuente y coincidencias con su ref, ruta y SHA— y **ninguna** clasificación resuelta.

### 1.3 `master-spec.md` → GATE
1. `<contenedora>/.sdd/<id>/` **ya existe**: lo creó el paso 2 de `1.2` junto con su ledger de búsqueda. Si faltara —una orquestación heredada, anterior a ese paso—, crearlo (POSIX: `mkdir -p`; PowerShell: `New-Item -ItemType Directory -Force`).
2. Escribir `master-spec.md` con la plantilla de `reference.md` → "Plantilla de `master-spec.md`". Mínimo: problema/objetivo global, alcance (in/out) a nivel sistema, **criterios de aceptación `AC-1..N`** cada uno etiquetado `[repo-local]` o `[integration]`, **contratos entre servicios** (qué expone cada uno y qué consume), y el **reparto** (qué repo cubre qué AC). **Promover acá el resultado de la búsqueda:** proyectar **únicamente el bloque declarativo** de `<contenedora>/.sdd/<id>/antecedentes.md` a la sección `### Antecedentes` de la plantilla, con su dimensión por repo y el residual global. El ledger **sobrevive** con su bloque de estado intacto, y **ninguna** de sus claves máquina se copia acá.
3. **STOP** — si la **revisión cross-model** está activa (ver "Revisión cross-model"), ejecutar `cross-review` sobre `master-spec.md` (foco en contratos entre servicios y AC `[integration]`; con co-exploración corrida, sumar los **índices + la síntesis** de la co-exploración como `context_paths` adicional — nunca los `detail-*` completos — ver "Co-exploración cross-model") antes de presentar. Presentar la spec madre (con el resumen de crítica, si lo hubo) y pedir aprobación. No avanzar sin ella.

### 1.4 Reparto → GATE
Con co-exploración activa, antes del punto 1 se despacha el `counter-plan` (ver "Co-exploración cross-model"): el revisor propone su **reparto tentativo**, que el conductor contrasta antes de escribir el reparto real.

**El reparto se materializa entero, de una vez.** Los artefactos que produce esta fase nacen en el mismo acto y ninguno queda para más adelante:

- Manifest, referencias por repo y contrato completo se producen en una sola materialización, con `v1` congelado.

Dejar el contrato de integración para después no es otro orden sino un reparto incompleto: sus tareas quedarían sin dónde probar su cierre y el check del punto 4 —que cruza cada tarea contra su fila— no tendría contra qué correr, así que el gate aprobaría un reparto cuya mitad de orquestación nadie validó. El congelamiento del `v1` exige el mismo gate del contrato que rige antes de ejecutar evidencia (`reference.md` → "Gate de la Fase 3 y agregación"): cobertura bidireccional, campos obligatorios y baseline resuelto en toda fila.

La enumeración inmediata no es exhaustiva; manda el conjunto canónico completo de `cross-implement/contrato-verificacion.md` → «El gate previo al dispatch».

1. Por cada repo confirmado, crear `<repo>/.plans/<id>/` como un flujo `sdd-flow` completo:
   - **`spec.md`** — la fuente de los AC que el agente delegado verificará en Fase 2 (sin ella, el `verify` de `sdd-flow` no tiene contra qué chequear). Contenido: problema/objetivo recortado a lo que aporta el repo, los AC de su `covers_ac` copiados **textuales** de la master-spec (manteniendo los IDs globales `AC-n` para trazabilidad), los contratos que el repo expone/consume, y una nota explícita de que los AC `[integration]` en los que participa **no** se verifican en el repo (los cierra la tarea de orquestación dueña de su fila; nunca darlos por cumplidos localmente). Su fila vive en el **contrato de integración** de la orquestación y el contrato del repo solo la **referencia en solo-lectura**, con evidencia `N/A: orchestration-owned` — ni `NOT_APPLICABLE` ni pendiente (`reference.md` → "Contrato de integración"). Mini-plantilla en `reference.md` → "Spec por repo".
   - **`plan.md`** con el **header YAML de `sdd-flow`** (`id`, `branch`, `base_commit`, `change_type`, `complexity`, `status: planned`, `created_at`) + las secciones de enfoque/archivos/tests, y su `## Verification` con el **contrato de verificación obligatorio**: el mismo esquema normativo que `sdd-flow`, heredado por puntero (`sdd-flow/reference.md` → "Plantilla de plan"), nunca una plantilla propia. Sin esa herencia los planes multi-repo nacen sin contrato y `implement_mode: cross` se rompe solo acá. La **`complexity` por repo la asigna el orquestador** en el reparto (default `normal`; `trivial` solo si el cambio del repo es trivial → spec y tasks embebidas en `plan.md`, igual que `sdd-flow`). `base_commit` = HEAD actual de la rama base del repo; la rama todavía no existe — la crea `sdd-flow` en Fase 2 (su `resume` la recrea desde `base_commit` cuando no la encuentra).
   - **`tasks.md`** (salvo *trivial*) con el **formato detallado** de `sdd-flow` (cada task con Por qué / Archivos / Pasos / Verificar / `AC-n`).

   El `branch` se nombra con la convención de `sdd-flow` (`<prefijo>/{id}-{slug}`), resolviendo el `<prefijo>` (el `{type}`) por repo con esta **precedencia**: (1) `branch_prefix` del `<repo>/.specify/config.yml` si lo tiene (su CI/CD manda) → (2) `branch_prefix` de la orquestación (del `manifest.yml`) → (3) prefijo **semántico** del cambio. Normalizar quitando la barra final si la trae. (Ese `<repo>/.specify/config.yml` se puede generar con `/sdd-flow init` dentro del repo; hace el reparto más determinista.)
2. Escribir/actualizar `manifest.yml` (esquema en `reference.md`): por repo, `path`, `branch`, `status`, `depends_on` (el DAG) y `covers_ac`; y en `orchestration_tasks`, el trabajo que no vive en ningún repo —una entrada por tarea, con su `phase`, `what`, `owner`, `status`, `depends_on`, `covers_ac`, `done_when`, y `blocks_repos` / `participating_repos` donde correspondan (campo por campo en `reference.md` → "Campos de `orchestration_tasks`")—.
3. Escribir el **contrato de integración** completo en `<contenedora>/.sdd/<id>/integracion.md` —una fila por cada entrada de `orchestration_tasks`, cubra AC `[integration]` o sea auxiliar— y **congelar su `v1`** acá, con el baseline de cada fila resuelto (`reference.md` → "Contrato de integración"). Al escribir cada fila, aplicar `cross-implement/contrato-verificacion.md` → «Pertinencia: poder discriminante por fila». El `done_when` de cada tarea referencia el ID de su fila en vez de reescribir su criterio, y la referencia solo-lectura del punto 1 de cada repo participante apunta a esa misma fila.
4. **Cross-artifact check (regla 5), ampliado a la orquestación:**

   - El cross-artifact check falla ante cobertura, ubicación o invariantes inválidos.

   Validar la cobertura solo contra el `covers_ac` de los **repos** deja fuera justo a los AC `[integration]`, que por la regla 5 no se declaran ahí: uno sin nadie que lo cubra pasaría el gate en verde. Los cinco grupos:

   - **Cobertura.** Cada AC `[repo-local]` está en el `covers_ac` de ≥1 repo, y cada AC `[integration]` en el de **exactamente una** tarea de orquestación. Un AC `[integration]` que ninguna tarea declare es **huérfano** y el check falla **nombrándolo**.
   - **Ubicación, en los dos sentidos.** Falla igual un AC `[integration]` declarado en el `covers_ac` de un repo que un `[repo-local]` declarado en el de una tarea de orquestación: un AC cubierto en el lugar equivocado no está cubierto.
   - **Cardinalidad, validada por separado.** Tarea ↔ fila del contrato: exactamente una fila por tarea, y ninguna fila huérfana. AC `[integration]` ↔ tarea de cierre: exactamente una tarea, y ningún AC cubierto por dos. Son dos coberturas distintas y una puede cerrar con la otra rota.
   - **Invariantes estructurales del grafo.** Sin ciclos en `depends_on`; sin `id` duplicado; `depends_on` y `blocks_repos` referenciando algo que existe (otra tarea y un `path` de `repos`, respectivamente); `phase` y `status` dentro de su enum; `owner` y `done_when` presentes y no vacíos; `blocks_repos` ausente en toda tarea de `phase: closeout`; y ninguna tarea de `phase: gate` que dependa de una de `phase: closeout` — el grafo sería acíclico e inejecutable igual, porque un gate corre antes del fan-out y un closeout después.
   - **Participación.** `participating_repos` es un mapa AC → repos, y ausente o `{}` es válido mientras la tarea no cubra ningún AC `[integration]`. Fallan: claves duplicadas; claves que no sean **exactamente** el conjunto de `covers_ac` —falta la de un AC cubierto, o sobra la de uno que la tarea no cubre—; repos que no existen en `repos`; y AC que no estén etiquetados `[integration]`.

   Y sigue valiendo lo de siempre: ninguna sub-task referencia un AC inexistente. Reportar todo lo que no cierre antes del gate, nombrando el AC, la tarea o la fila involucrada.

   **El dueño pendiente se reporta, no bloquea.**

   - Una tarea con `owner: UNASSIGNED` se reporta sin bloquear el gate.

   Es una tarea todavía sin dueño, no un manifest inválido: bloquear acá impediría declarar el trabajo que aún no se asignó, que es exactamente lo que el centinela existe para permitir. Va en el reporte del gate junto con las demás observaciones, para que el usuario le ponga dueño al aprobar o decida seguir sin él; lo que no puede es cerrarse mientras siga así, y eso se controla al cerrar la tarea, no acá.
5. **STOP** — si la **revisión cross-model** está activa, ejecutar `cross-review` sobre el `reparto` (artefacto: `manifest.yml`; contexto: `master-spec.md` + los `plan.md` por repo + los índices + la síntesis de `counter-plan`, si co-exploración corrió; foco en cobertura AC↔repo, `depends_on` y ciclos del DAG) antes de presentar. Presentar el reparto (tabla repo · branch · AC cubiertos · dependencias, con el resumen de crítica si lo hubo) y pedir aprobación. Al aprobar, promover a `status: tasks-ready` **solo** los repos que ningún gate abierto bloquea —los bloqueados quedan en `planned`— y escribir ese estado tanto en el `manifest.yml` como en el header del `plan.md` del repo (Fase 2, paso 1).

---

## Fase 2 · Ejecución (delegada, paralela)

Precondición: reparto aprobado y `sdd-flow` disponible (ver "Dependencia de `sdd-flow`").

1. **Resolver la elegibilidad.** Un repo tiene dos condiciones que cumplir, no una: el DAG entre repos y los gates de la orquestación.

   - Un repo es elegible cuando sus `depends_on` están en terminal verde y ninguna tarea `phase: gate` que lo incluya en `blocks_repos` está fuera de `done`.
   - La aprobación del reparto promueve solo los repos no bloqueados; los bloqueados permanecen en `planned`.
   - El estado del repo vale lo mismo en `manifest.yml` y en el header de su `plan.md`, en las dos transiciones.
   - Al cerrarse el último gate que lo bloquea, el repo se promueve y se despacha; dejarlo en `planned` es un error.
   - Cada despacho, cada promoción y cada liberación de lock registra su intento en la bitácora antes de materializarse.

   Terminal verde son `verified`, `committed`, `pushed`, `pr-open` y `done`; los demás repos esperan. La segunda condición es la que agrega el trabajo propio del orquestador: una tarea de `gate` existe justo para frenar el fan-out de los repos que nombra, así que un repo con un gate abierto no es elegible aunque todo su DAG esté verde. `pending`, `in-progress` y `blocked` cuentan por igual como fuera de `done`: lo que habilita el despacho es el cierre de la tarea, no que alguien la haya empezado.

   Las **dos transiciones** son la promoción inicial al aprobar el reparto (1.4) y la promoción posterior al cierre del último gate que bloqueaba al repo; en las dos, el estado se escribe en los dos artefactos. El resume los lee a ambos, así que un manifest en `planned` con un `plan.md` en `tasks-ready` no es una divergencia cosmética: deja el punto del repo indeterminado y el retome elige uno de los dos sin saber cuál manda. El defecto simétrico es un repo que sigue en `planned` con su gate ya cerrado —trabajo listo que nadie despacha—, y por eso cerrar un gate reabre la elegibilidad en el acto en vez de esperar a la próxima vuelta del DAG.

   Y el intento se registra **antes** de materializarse, nunca después (`reference.md` → "Bitácora de transiciones"). Un snapshot no distingue el repo que esperó a que su gate cerrara del que se despachó igual; lo único que los separa es el evento, y registrar después pierde justo el intento **rechazado**, que por definición no cambia nada y no dejaría rastro.
2. **Lock cooperativo previo (regla 6).** Antes de tocar cada repo elegible, leer los **otros** `.sdd/*/manifest.yml`. Si el repo aparece en otra orquestación con `status` **no terminal** (≠ `pushed`/`pr-open`/`done`), está **tomado**: aplicar el protocolo del lock (ver "Orquestaciones concurrentes"). No arrancarlo hasta resolver.
3. **Fan-out.** Por cada repo elegible y libre, despachar un agente que ejecute la **Vía B de `sdd-flow`** (`implement .plans/<id>/`) **parado en `<repo>/`**, con la corrida en `cross_review.mode: off` y `co_explore.mode: off` (ortogonales; se apagan ambos explícitos): los `plan.md`/`tasks.md` por repo ya quedaron cubiertos por la revisión del reparto y la exploración global ya cubrió ese terreno. Si el `manifest.yml` fija `implement_mode` (global o por repo — ver "Esquema de `manifest.yml`"), el agente delegado lo hereda como modo de ejecución de su `implement` (incluido `cross`: la implementación del repo la hace el modelo de la otra familia vía `cross-implement` y el agente delegado revisa el diff — exige esa capacidad en su contexto; sin ella, degrada al modo disponible con aviso, como en `sdd-flow`). **Un manifest heredado que declare `implement_mode: subagent` detiene la orquestación acá, con un error de migración** que nombra el valor retirado y exige elegir `inline` o `cross`: ese modo ya no existe y **no hay fallback silencioso** — ni se degrada a `inline` ni se ignora la clave, porque un fan-out entero corriendo en un modo que nadie eligió es peor que un abort. Los working trees son disjuntos, así que `cross` convive con el fan-out; el tope de concurrencia ya existente aplica igual a los implementadores delegados. **Cómo se delega:** `sdd-flow` es solo-slash (`disable-model-invocation`), así que el subagente **no** puede invocarla con el Skill tool — el prompt del agente le indica **leer** `sdd-flow/SKILL.md` (y `reference.md` si lo necesita) desde el directorio de skills y ejecutar su Vía B siguiendo ese contrato. Tras comparar la declaración local, ese prompt recibe el `family_inventory` resuelto si el manifest declaró `families`; sin esa clave no se agrega carrier. Plantilla del prompt y contrato de retorno en `reference.md` → "Prompt del agente delegado". El agente hereda toda la Vía B: crea rama, implementa task por task (con el **debugging sistemático** ante un test/AC en rojo), corre tests+build, verifica los AC `repo-local` con la **gate function**, y **FRENA antes de commitear** (regla 4). Usar el patrón de subagentes en paralelo (cada repo es un working tree disjunto → sin colisión de archivos) con un **tope de concurrencia**; los repos en exceso quedan en cola. Descubrir la capacidad de paralelismo por entorno, no por nombre de tool. **Despacho en el mismo turno (sin turnos muertos):** emitir las tool calls del fan-out en el **mismo turno** en que las anuncias; anunciar el despacho y cerrar el turno sin la tool call estanca la orquestación (el turno termina sin que nada se despache y hace falta un empujón para seguir). **Preflight de capacidad para `cross` (una vez, no por repo):** si el `implement_mode` resuelto es `cross`, chequear la capacidad del CLI de la otra familia **una sola vez** (preflight portable: POSIX `command -v`, PowerShell `Get-Command`) antes del fan-out. Si el preflight confirma que el binario **no está** (o auth rechazada / versión incompatible), es una **pared confirmada run-wide**: marcarla no disponible para toda la orquestación y degradar los repos restantes al modo disponible con un aviso, en vez de re-diagnosticar en cada repo. Distinto son (a) un **flake transitorio de lanzamiento** con el binario presente —admite 2-3 reintentos con backoff corto por despacho, y no condena a los demás repos— y (b) un repo que **arrancó** `cross` y falló la tarea (fallo del repo, no de la capacidad; cascada normal del paso 4).

   **Modo inline (opcional).** Con `execution_mode: inline` en el `manifest.yml` o a pedido del usuario ("ejecuta `<repo>` acá", "modo inline"), el orquestador ejecuta la Vía B de ese repo **en su propia sesión**, parado en `<repo>/` — mismo contrato que el agente delegado (incluido **FRENAR antes de commitear**) y mismo update del manifest. Después de comparar la declaración local, el camino inline hereda el mismo `family_inventory` cuando el manifest declaró `families`; no relee el config del repo. Los repos van **de a uno** (sin paralelismo inline). Útil cuando queda un solo repo elegible o el usuario quiere seguir la implementación de cerca. Trade-off: carga el contexto del orquestador — para fan-outs grandes, seguir con agentes. El default es y sigue siendo `fanout`; el repo ejecutado inline hereda el `implement` de `sdd-flow` con sus propios modos.
4. **Recolección + cascada de fallos.** Al volver cada agente, leer su reporte estructurado (contrato en `reference.md` → "Prompt del agente delegado"; si el reporte falta o no parsea, **releer el `status` que `sdd-flow` persistió** en `<repo>/.plans/<id>/plan.md` y tratar la ausencia de `verified` como fallo) y actualizar el `status` del repo en `manifest.yml`:
   - Verde (`verified`): queda listo para el cierre.
   - **Fallo** (tests/build rojos o AC no cumplido): marcar `failed`, **no commitear**, y **bloquear solo a sus dependientes** en el DAG (marcarlos `blocked`). Los repos independientes siguen. Detalle en `reference.md` → "Cascada de fallos (DAG)".
   - Recalcular la elegibilidad con los repos recién liberados y los gates recién cerrados, y volver al paso 1 hasta que no queden elegibles.

> **Reconciliar antes de declarar un fallo de conteo.** Si el reporte de un agente delegado trae un conteo de tests y quieres verificarlo, vuelve a correr el **mismo comando, mismo set de archivos y mismo commit** que reportó, y lee el conteo del **propio runner**: un test parametrizado/table-driven explota en varios casos colectados, así que contar funciones a mano (`grep -c 'def test_'`) no es un oráculo. No registres `miscount`/over-report en el `manifest.yml` sin esa recolección fresca sobre el mismo gate.

`failed` y `blocked` son estados **propios del manifest** del orquestador (no del ciclo de `sdd-flow`).

### Gate bloqueado

Una tarea de `phase: gate` en `status: blocked` no es un manifest inválido: es trabajo frenado que hay que reportar sin adivinar qué hacer con él. La salida es determinista y termina en una decisión del usuario.

- Expone la causa del bloqueo y no despacha los repos de su `blocks_repos`.
- Exige una decisión explícita —suspender, excluir el repo o abortar— antes de liberar su lock.
- Al retomar un repo cuyo lock se liberó, revalida su `base_commit` antes de seguir.

La causa va en el reporte de estado junto al `id` de la tarea, su `owner` y la lista de repos que quedan esperando: un estado agregado que diga solo "bloqueado" obliga a reconstruir a mano por qué, y el `what` de la tarea ya lo dice.

El lock es lo que no se resuelve solo, y las dos automatizaciones posibles fallan en direcciones opuestas. Liberarlo apenas la tarea se bloquea le abre el repo a otra orquestación, que puede moverlo y dejar obsoleto el `base_commit` con el que este reparto se escribió. No liberarlo nunca deja el repo tomado en silencio para todas las demás features, sin que nadie sepa hasta cuándo. Por eso la elige el usuario, entre tres: **suspender** la orquestación (el lock se conserva y el repo sigue reservado), **excluir** el repo de esta feature (se libera su lock y sale del reparto) o **abortar** la orquestación entera (se liberan todos, con el mecanismo del sub-paso `abort`).

La liberación se registra como cualquier otra transición: primero el evento con su resultado, después el efecto sobre el lock. Un intento de liberar sin una decisión previa en la bitácora se **rechaza**, y ese rechazo es el comportamiento correcto y no una falla; lo inválido es una liberación consumada sin decisión que la preceda. La diferencia entre las dos no está en el estado final del lock —en un caso quedó tomado, en el otro libre— sino en el orden de los eventos, que es lo único que la vuelve observable.

Retomar después no es continuar donde se dejó. Entre la liberación y el retome, cualquier otra orquestación pudo mover la rama base del repo, así que antes de seguir se revalida el `base_commit` del `plan.md` contra el HEAD actual de esa rama. Si cambió, se replantea con el usuario en vez de implementar sobre un punto de partida que ya no existe.

### Cierre de una tarea de orquestación

Marcar `done` una `orchestration_task` es una transición con su propio gate, y rige para **las dos fases**: el primer cierre es el de una tarea de `gate`, que ocurre acá, y las de `closeout` cierran en la Fase 3. Una precondición escrita en una sola de las dos deja la otra sin control.

- Una tarea con `owner: UNASSIGNED` no pasa a `done` en ninguna fase; en el reparto solo se reporta.
- Antes de materializar `done` se exige: `depends_on` en `done`, evidencia fresca de su fila, `Esperado` satisfecho y `done_when` referenciando esa fila.
- Ningún dueño ni ninguna evidencia se reutiliza entre dos tareas.
- Para una acción externa o manual, el dueño de ejecución la realiza y el orquestador registra y verifica la evidencia.
- El intento de cierre y la ejecución de su evidencia se registran en la bitácora antes de materializarse, en cualquiera de las dos fases.

El centinela vive dos momentos distintos y se comporta distinto en cada uno: en el gate del reparto se reporta sin bloquear —declarar trabajo todavía sin asignar es justo para lo que existe—, pero al cerrar sí bloquea, porque una tarea que nadie ejecutó no la cierra nadie. Vale igual cubra AC `[integration]` o sea auxiliar, y sea `gate` o `closeout`.

Las cuatro precondiciones se comprueban juntas, y ninguna suple a otra. La frescura se juzga contra la bitácora, no contra el estado (`reference.md` → "Bitácora de transiciones"): que la fila figure ejecutada no dice cuándo, ni sobre qué versión del contrato, ni sobre qué SHA de cada repo relevante. Y `done_when` referencia el ID de su fila en vez de reescribir el criterio, para que no queden dos criterios divergentes del mismo cierre. Si algo no cierra, la transición se **rechaza**: `status: done` no es un campo que alguien marca a mano.

Ni el dueño ni la evidencia se comparten. Cada tarea posee exactamente una fila del contrato y responde por su propia ejecución, así que dos tareas que declaren la misma fila —o el mismo dueño de ejecución para el mismo cierre— no son dos cierres sino uno contado dos veces. Distinto es repetir el ID de un AC, que es legítimo y obligatorio: vive a la vez en la `master-spec.md`, el manifest, el contrato de integración y la referencia solo-lectura de cada repo participante.

Cuando el cierre depende de una acción externa o manual —un despliegue, un acuerdo entre equipos, la publicación de un contrato— el reparto de responsabilidades no cambia: la ejecuta el dueño y el orquestador registra el evento (con el dueño como `actor`) y verifica la evidencia contra el `Esperado` de su fila. El orquestador no ejecuta acciones de infraestructura, y tampoco da por cumplido lo que no puede verificar.

Y el orden vale acá igual que en el despacho: primero el evento con su resultado, después el efecto. Un cierre rechazado —por un `depends_on` abierto, por evidencia vencida, por un `Esperado` que no se satisface o por un dueño pendiente— deja su registro y no toca el `status`.

---

## Fase 3 · Cierre (centralizada, el usuario al mando)

1. **Reporte consolidado.** Tabla por repo: `repo · status · AC repo-local cumplidos · verde/fallido/bloqueado`. Listar aparte los AC `integration` pendientes.
2. **Commit/push centralizado.** Para cada repo en `verified`, ofrecer (controlado por el usuario): revisión → commit → push, **siguiendo el mecanismo de commit de `sdd-flow`** (leído de sus archivos — no vía Skill tool, que su flag bloquea): staging selectivo + mensaje convencional construido **inline** (`sdd-flow/reference.md` → "Construcción del mensaje de commit"; sdd-flow no depende de ninguna skill externa para commitear). Soportar lote ("commitea todos los verdes"). Mostrar siempre, antes de ejecutar, los archivos staged + mensaje + comando. Actualizar `status` a `committed`/`pushed` en el manifest. El scope del commit por defecto es el `<id>` global (override por repo si el servicio tiene su propia clave de ticket).
3. **Gate de apertura del contrato de integración.** Antes de ejecutar ninguna evidencia, validar el contrato de `<contenedora>/.sdd/<id>/integracion.md` con el **mismo gate** que `cross-implement` aplica antes de delegar (`cross-implement/contrato-verificacion.md` → "El gate previo al dispatch"): esquema canónico, cobertura bidireccional contra los AC `[integration]`, campos obligatorios y baseline resuelto en toda fila, ninguna en `BLOCKED`.

   La enumeración inmediata no es exhaustiva; manda el conjunto canónico completo de la sede enlazada.

   - La Fase 3 revalida la versión vigente del contrato antes de ejecutar evidencia.

   El contrato nació **completo y congelado en la Fase 1** (1.4), así que acá no hay nada que congelar: lo que se hace es revalidar la versión vigente. La revalidación **no emite una versión que agregue o quite IDs** —el conjunto es invariante entre versiones, y por eso el contrato se materializa entero de una vez—; si el gate no pasa, se corrige por el versionado canónico heredado y no se corre ninguna fila hasta que pase. Sacar estas filas del contrato de cada repo sin este gate las dejaría sin ningún gate, en vez de moverlas a otro.
4. **AC de integración.** Los AC `[integration]` no los cierra un agente aislado. Aplicarles la **gate function** del `verify` de `sdd-flow`, a nivel cross-repo: CARGAR la fila del contrato de integración que prueba este AC (no elegir la evidencia acá: ya está congelada) → CORRERLA fresca → LEER salida + exit code → VERIFICAR contra su `Esperado`. Si no hay comando ejecutable, la fila lo declara como evidencia `manual` y queda como **verificación manual** pendiente. Nunca darlos por cumplidos sin esa evidencia (ley de la sección "Red flags").

   - Cada ejecución de evidencia y cada cierre de tarea registra su intento en la bitácora antes de materializarse.

   Las tareas de `closeout` cierran acá, con el mismo gate de "Cierre de una tarea de orquestación" que rige en la Fase 2, y el orden es el mismo que en el despacho: primero el evento con su resultado, después el efecto. Una evidencia que se corrió y falló, o un cierre rechazado, dejan su registro igual: es lo único que después distingue la fila que nunca se ejecutó de la que se ejecutó y no satisfizo su `Esperado`.
5. **Agregación.** El estado global no se lee a ojo de los estados sueltos: lo produce una tabla de precedencia declarada, que ante varias condiciones a la vez emite **una sola** y siempre la más grave.

   - Una tabla de precedencia produce el estado agregado como `ESTADO:<valor>` y nunca oculta el más grave.

   | # | Estado agregado | Cuándo |
   |---|---|---|
   | 1 | `ESTADO:no-verificado:repo-failed` | algún repo quedó en `failed` |
   | 2 | `ESTADO:no-verificado:repo-blocked` | algún repo quedó en `blocked` por la cascada del DAG |
   | 3 | `ESTADO:no-verificado:gate-blocked` | alguna tarea `phase: gate` quedó en `blocked` |
   | 4 | `ESTADO:en-curso` | algún repo sigue en marcha y ninguno falló ni está bloqueado |
   | 5 | `ESTADO:no-verificado:integracion-pendiente` | queda una `orchestration_task` sin cerrar, o una fila del contrato ausente, `BLOCKED` o `manual` pendiente |
   | 6 | `ESTADO:done` | todos los repos en terminal verde y todas las tareas en `done` |

   La primera columna es el **rango**: gana el número más bajo de todas las condiciones que se cumplen. Un repo en `failed` conviviendo con integración pendiente se reporta como `repo-failed`, no como integración pendiente — reportar la condición menos grave satisface la letra de "hay una tabla" y miente sobre el estado real.

   El veredicto sigue siendo **no verificado**, acompañado de su causa: es el mismo vocabulario del resto de la skill y no se duplica con un término paralelo. El estado global solo puede ser verde con **todas** las filas del contrato de integración resueltas y ninguna ausente ni `BLOCKED`. Una fila que falta no es una fila que pasa: si el contrato quedó incompleto, el flujo global se reporta como no verificado, no como verde con salvedades.

---

## Resume global (retomar una orquestación)

Punto de entrada cuando vuelves a una orquestación ya empezada (sesión nueva, o tras cambiar de contexto).

1. Si el usuario nombró un `<id>`, usar ese; si fue genérico ("¿en qué quedé?"), **listar** las orquestaciones activas leyendo cada `.sdd/*/manifest.yml` **y cada `.sdd/*/antecedentes.md`** (excluir `.sdd/archived/`) y mostrar `id · #repos · estado agregado`. Que elija.
   - **Los dos se listan porque una pausa temprana no tiene manifest todavía** —lo escribe el paso 2 de **`1.4`**, no `1.3`—, así que mirando solo el manifest ninguna orquestación pausada en `1.2`, en `1.3` o antes de ese paso de `1.4` aparecería en ningún listado.
   - **Una sola entrada por `<id>`, con precedencia declarada:** con manifest presente, el resumen sale del manifest y el ledger de la búsqueda solo aporta su estado; sin manifest, el ledger **es** la entrada completa. Sin esta precedencia, después de `1.3` existen los dos y la misma orquestación produciría dos filas.
   - Una orquestación con `busqueda: terminal` y sin manifest **no se ofrece como reanudable**: es un cierre pre-master deliberado. Sigue visible con ese estado, sin "siguiente paso".
2. **Si hay `manifest.yml`**, leerlo junto con el `status` de cada `<repo>/.plans/<id>/plan.md`. **Si no lo hay**, no hay reparto todavía, y dónde retomar lo decide **qué artefacto está presente** —no la sola ausencia del manifest, que rutearía juntas tres pausas distintas y descartaría una spec madre ya escrita:
   - **sin `master-spec.md`** → `1.2`, retomando la búsqueda desde su ledger.
   - **con `master-spec.md` y sin ningún `<repo>/.plans/<id>/plan.md`** → `1.3`: la spec madre existe pero el reparto no empezó, así que se presenta su gate. Repetirlo es barato; saltearlo aprueba lo que nadie aprobó.
   - **con `master-spec.md` y con al menos un `<repo>/.plans/<id>/plan.md`** → `1.4`, **desde su punto 2**: el punto 1 ya corrió y **no se repite**, porque volvería a crear artefactos que existen. Se completan los repos que falten y se sigue con el manifest.
   En las dos últimas **no se re-corre la búsqueda ni se reabre la selección de repos**: los confirmados salen de `confirmados`, en el bloque `## estado` del ledger, que es su única sede mientras no haya manifest. Si `<repo>/.plans/<id>/` no existe, buscar `<repo>/.plans/archived/<id>/` (el flujo del repo fue archivado por `sdd-flow` → tratarlo como `done`). **Anunciar el punto de cada repo** antes de actuar. Si el manifest **no** trae `orchestration_tasks`, resolver acá cuál de los dos casos es antes de seguir (ver "Orquestación sin el bloque"): este camino no re-corre el cross-artifact check, así que nada más adelante lo va a detectar.
3. Por repo, retomar siguiendo el `resume` de `sdd-flow` (mismo mecanismo que el fan-out: el agente lee los archivos de `sdd-flow`, hace el checkout seguro a la rama del repo y salta al paso según su `status`). **No** re-crear `master-spec.md` ni duplicar `.plans/<id>/`.
4. Recalcular el DAG y continuar en la fase que corresponda (típicamente Fase 2 para los repos `tasks-ready`/`implementing`, o Fase 3 para los `verified`/`committed`).

### Orquestación sin el bloque

Un `manifest.yml` sin `orchestration_tasks` es válido (`reference.md` → "Esquema de `manifest.yml`"), pero significa dos cosas distintas y tratarlas igual rompe una de las dos. Lo que las separa es la `master-spec.md`, no el manifest.

- Sin AC `[integration]`: es compatibilidad real y sigue verde, sin advertencias.
- Con AC `[integration]` y sin `orchestration_tasks`: el resume se detiene.
- El mensaje indica que requiere actualización manual del reparto y materialización completa del contrato.
- Se preserva todo el progreso existente: ramas, planes y estados.

Una orquestación de repos independientes no necesita trabajo de orquestador: no hay nada que los repos no cierren solos, el bloque sobra, y advertir ahí convertiría el caso normal en ruido permanente. El otro caso no es compatibilidad sino **formato insuficiente**: hay AC que por la regla 5 no se declaran en ningún repo y no existe la tarea que debería cubrirlos, así que quedan sin dueño —nadie los ejecuta y nadie los prueba—. Seguir avanzando los daría por cumplidos por omisión, que es justo lo que prohíbe la ley fundamental de "Red flags".

Detenerse no cuesta el trabajo ya hecho: no se toca ninguna rama, ningún `<repo>/.plans/<id>/` ni ningún `status` del manifest. Se frena para que el usuario actualice el reparto, no para hacerlo empezar de nuevo. Modelo del mensaje:

> Esta orquestación tiene AC `[integration]` en su `master-spec.md` y su `manifest.yml` no declara `orchestration_tasks`: ninguna tarea los cierra. Me detengo acá — sin esas tareas, avanzar los daría por cumplidos sin evidencia.
>
> Para retomarla faltan dos cosas, y las decides tú:
> 1. **Actualizar el reparto a mano**: agregar `orchestration_tasks` al `manifest.yml`, con una tarea de cierre por cada AC `[integration]` (`id`, `phase`, `what`, `owner`, `status`, `covers_ac`, `done_when` y su `participating_repos`).
> 2. **Materializar el contrato de integración completo** en `<contenedora>/.sdd/<id>/integracion.md`: una fila por tarea, con su baseline resuelto, y congelar esa versión.
>
> Nada de lo avanzado se pierde ni se rehace: las ramas, los `<repo>/.plans/<id>/` y los `status` del manifest quedan como están. Cuando el reparto esté completo, el retome sigue desde el mismo punto y pasa por el cross-artifact check.

El texto es un modelo, no un literal. Lo que no puede es decir solo que algo falló: un mensaje que no nombre las dos cosas que faltan deja al usuario reconstruyendo el reparto a ciegas, y uno que no aclare que el progreso se conserva lo empuja a rehacer trabajo intacto.

---

## Sub-pasos `archive` / `abort` (cerrar o cancelar una orquestación)

**`archive`** — solo cuando el usuario confirma explícitamente que el cambio global está probado y correcto (decisión del usuario, nunca automática). Requiere todos los repos en `pushed`/`pr-open`/`done` (`pr-open` es el estado opcional de `sdd-flow` cuando se abrió el PR del repo desde su flujo).

- `archive` se rechaza si alguna `orchestration_task` no está en `done`.

Los repos no son la única condición. Una tarea auxiliar que nadie cerró y un `closeout` a medias son trabajo pendiente igual que un repo en `failed`, así que la exigencia vale para **toda** tarea del bloque: sea su `phase` `gate` o `closeout`, y esté vacío o no su `covers_ac`. Al rechazar, el mensaje **nombra** las tareas que faltan por su `id` — decir solo que quedan pendientes obliga a recorrer el manifest a mano para saber cuáles, y archivar con tareas abiertas las da por cumplidas por omisión.

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
