# sdd-orchestrator — Referencia

Detalle operativo de la skill `sdd-orchestrator`. El `SKILL.md` apunta acá cuando necesita esquemas, plantillas, la matriz de detección o los algoritmos del lock y la cascada.

## Tabla de contenidos

- [Matriz de detección de repos](#matriz-de-detección-de-repos)
- [Esquema de `manifest.yml`](#esquema-de-manifestyml)
- [Plantilla de `master-spec.md`](#plantilla-de-master-specmd)
- [Spec por repo](#spec-por-repo)
- [Formato de contratos entre servicios](#formato-de-contratos-entre-servicios)
- [Prompt del agente delegado](#prompt-del-agente-delegado)
- [Algoritmo del lock cooperativo](#algoritmo-del-lock-cooperativo)
- [Cascada de fallos (DAG)](#cascada-de-fallos-dag)
- [Ejemplos de `manifest.yml`](#ejemplos-de-manifestyml)

---

## Matriz de detección de repos

La carpeta contenedora puede o no ser un repo git. El orquestador descubre los repos **hijos**:

| Qué | Cómo | Notas |
|---|---|---|
| Universo de repos | Para cada subdirectorio inmediato de la contenedora, probar `git -C <sub> rev-parse --is-inside-work-tree` (o detectar `<sub>/.git`). | Solo el primer nivel; no descender en monorepos anidados salvo que el usuario lo pida. |
| ¿La contenedora es git? | `git -C <contenedora> rev-parse --is-inside-work-tree`. | Si lo es y además tiene sub-repos, preguntar al usuario si quiere tratarla como contenedora (multi-repo) o como repo único (entonces usar `sdd-flow`). |
| Repos involucrados | El análisis del objetivo propone un subconjunto (por nombre del servicio, por los contratos mencionados, por búsqueda en código si el alcance lo amerita). | **Siempre** confirmar con el usuario (regla 3). |
| Rama base por repo | Delegado a `sdd-flow` (cada repo la detecta con `git symbolic-ref refs/remotes/origin/HEAD`). | El orquestador no la hardcodea. |

Si no hay ningún repo git bajo la contenedora, avisar y detener.

## Esquema de `manifest.yml`

Vive en `<contenedora>/.sdd/<id>/manifest.yml`. Es la fuente de verdad de la coordinación. Local, nunca se trackea.

```yaml
id: ABC-123                    # clave del ticket o slug del título
master_spec: .sdd/ABC-123/master-spec.md
created_at: 2026-06-03T12:00:00-03:00
branch_prefix: ""              # opcional; prefijo único de la orquestación; vacío → semántico por repo (features: feature/, nunca feat/)
execution_mode: fanout         # fanout (agentes paralelos, default) | inline (en la sesión del orquestador, de a un repo) — opcional
implement_mode: ""             # opcional; modo de implementación que heredan los sdd-flow delegados: inline | cross (vacío → cada sdd-flow resuelve el suyo: config del repo > default). `cross` exige la capacidad (skill cross-implement + CLI de la otra familia) en el contexto del agente delegado. Un manifest heredado con el modo retirado detiene la orquestación con error de migración (ver `SKILL.md` → "Fan-out")
# outcome: aborted             # solo si la orquestación terminó abortada (sub-paso `abort`)
cross_model:                   # opcional; inventario común de familias para toda la orquestación
  schema_version: 1            # obligatorio si el bloque existe; esta obligación se introduce aquí y no se hereda de otra superficie
  families: [claude, codex]    # claude | codex — allowlist de workers; el conductor no entra
  selection: full              # full | user_choice — obligatorio con families; sin default
cross_review:                  # opcional; segunda opinión cross-model EN LOS GATES (ver skill cross-review)
  mode: auto                   # auto | "on" | "off"  (entre comillas: sin ellas YAML los parsea como booleanos)
  execution: auto              # auto (por capacidad del conductor) | sync | background
  artifacts: [master-spec, reparto]
  max_rounds: 3                # rondas POR TANDA, no de la corrida entera; al agotarse se abre el checkpoint
  reviewer: auto               # auto (familia opuesta dentro de la allowlist) | claude | codex; fuera de families → error canónico de cross-review
co_explore: {mode: auto, deadline: 600}  # co-exploración cross-repo ANTES del reparto; ORTOGONAL a cross_review (bloque hermano, no anidado); default on en orquestación; ver SKILL.md → Co-exploración cross-model
repos:
  - path: servicio-a          # relativo a la contenedora
    branch: feature/ABC-123-trace-id
    status: tasks-ready        # ver "Valores de status"
    depends_on: []             # lista de paths de los que depende (DAG)
    covers_ac: [AC-1, AC-2]    # qué AC globales cubre este repo
    # implement_mode: cross    # opcional; override por repo del implement_mode de la orquestación
  - path: servicio-b
    branch: feature/ABC-123-consume-health
    status: planned
    depends_on: [servicio-a]
    covers_ac: [AC-3]
orchestration_tasks:           # opcional; el trabajo del orquestador, que no vive en ningún repo
  - id: G1
    phase: gate                # gate (antes del fan-out) | closeout (después de la Fase 2)
    what: acordar el nombre del header de trazas entre los dos equipos
    owner: UNASSIGNED          # centinela: la tarea existe y todavía no tiene dueño
    status: pending            # pending | in-progress | done | blocked
    depends_on: []             # solo IDs de otras orchestration_tasks
    covers_ac: []              # AC [integration] que cierra; vacía es válida
    done_when: V-G1            # ID de la fila del contrato de integración que la cierra
    blocks_repos: [servicio-b] # solo en phase: gate; esos repos no se despachan hasta cerrarla
  - id: C1
    phase: closeout
    what: correr el flujo end-to-end con los dos servicios desplegados
    owner: equipo-plataforma
    status: pending
    depends_on: [G1]
    covers_ac: [AC-4]
    done_when: V-C1
    participating_repos:       # mapa AC → repos, una clave por cada AC de covers_ac
      AC-4: [servicio-a, servicio-b]
```

`families` nombra **workers despachables**; el **conductor no entra en** la lista y siempre conserva
la conducción. Cada worker es un proceso aparte en **sesión fresca**, incluso si comparte familia
con el conductor. Declarar menos familias que las presentes es una preferencia válida. Cada familia
declarada —la del conductor incluida— debe superar el preflight de su CLI en PATH: que el conductor
esté corriendo por construcción **no exime del preflight** de su worker. Los tokens admitidos son
`claude | codex`; una lista vacía, un escalar, un duplicado o cualquier otro token es error, y el
eco canoniza a minúsculas.

`selection` persiste cómo se resolvió la allowlist: `full` abarca todas las familias presentes y
`user_choice` declara menos. Es obligatorio con `families`, no tiene default y viaja sin
reconstruirse en `family_inventory`.

Si un `manifest.yml` vigente declara `families` pero **no declara cómo se resolvió**, abrir un STOP
único que muestre la lista, ofrezca `full` y `user_choice` y enseñe el **delta exacto** antes de hacer
un merge **no destructivo**. **No se infiere un default** ni se sondea el entorno: preguntar una vez
por la clave ausente no es descubrir familias.

El `branch` de cada repo se computa al hacer el reparto resolviendo el prefijo con precedencia **`branch_prefix` local del repo (`<repo>/.specify/config.yml`) > `branch_prefix` de la orquestación (este `manifest.yml`) > prefijo semántico**. Por eso dos repos de la misma orquestación pueden tener prefijos distintos (uno con config local, otro no).

### Valores de `status`

Lo que el `manifest.yml` escribe por repo: el ciclo de `sdd-flow` menos el valor que este
orquestador nunca emite (`plan-approved`, ver abajo), más dos estados **propios del orquestador**:

```
planned → tasks-ready → implementing → verified → committed → pushed → (pr-open) → done
                                   ↘ failed        (propio del orquestador)
                                   ↘ blocked       (propio del orquestador: dependía de un failed)
```

- `planned … done` — idénticos a `sdd-flow` (el `plan.md` del repo es la fuente fina). Incluye el
  opcional `pr-open` (el usuario abrió el PR del repo vía `sdd-flow`): cuenta como **terminal verde**
  para el lock, la elegibilidad del DAG y el `archive`.
- `plan-approved` — existe en el ciclo de `sdd-flow` pero **el `manifest.yml` nunca lo escribe**: el
  gate de reparto es único y pone cada repo en `tasks-ready` de una (`SKILL.md` → Fase 1, punto 4).
  Puede aparecer en el `plan.md` de un repo cuyo `sdd-flow` delegado quedó entre sus dos gates; ahí
  se lee con el significado que le da `sdd-flow`.
- `failed` — el agente del repo no logró dejarlo verde (tests/build rojos o AC no cumplido). No se commitea.
- `blocked` — el repo no arrancó porque un `depends_on` quedó `failed`.

`failed`/`blocked` viven solo en el `manifest.yml`; `sdd-flow` no los conoce.

### Campos de `orchestration_tasks`

`orchestration_tasks` declara el trabajo que **no pertenece a ningún repo**: lo que hay que cerrar
antes de despachar el fan-out (`phase: gate`) y lo que solo tiene sentido con todos los servicios
arriba (`phase: closeout`). El bloque es opcional; una orquestación sin trabajo propio del
orquestador simplemente no lo lleva.

Cada campo fija su tipo, sus valores admitidos, su obligatoriedad y a qué puede referenciar:

- `orchestration_tasks`: lista opcional de tareas; un manifest sin ella es válido.
- `id`: cadena obligatoria, única dentro del manifest.
- `phase`: enum obligatorio, admite solo `gate` o `closeout`.
- `what`: cadena obligatoria y no vacía que describe la tarea.
- `owner`: cadena obligatoria y no vacía; `UNASSIGNED` es su centinela.
- `status`: enum obligatorio, admite solo `pending`, `in-progress`, `done` o `blocked`.
- `depends_on`: lista opcional que solo referencia otras `orchestration_tasks`.
- `covers_ac`: lista obligatoria que solo admite AC etiquetados `[integration]`; puede ser vacía.
- `done_when`: cadena obligatoria y no vacía; referencia el ID de la fila del contrato que cierra la tarea.
- `blocks_repos`: lista opcional, solo válida en `phase: gate`, que solo referencia un `path` de `repos`.
- `participating_repos`: mapa obligatorio cuando `covers_ac` no está vacía; una clave por cada AC de `covers_ac`, y cada valor una lista que solo referencia un `path` de `repos`.

El `status` de una tarea es un enum **propio**: una tarea no se implementa ni se commitea, así que no
atraviesa el ciclo de un repo. Y `UNASSIGNED` no es un `owner` ausente sino uno declarado como
pendiente: la tarea existe, se reporta en el reparto y nadie la cierra hasta que tenga dueño real.

`participating_repos` es un **mapa**, no una lista plana. Sus claves son exactamente el conjunto de
`covers_ac` —ni falta la de un AC cubierto ni sobra la de un AC que la tarea no cubre— y cada valor
lista los repos que participan de ese AC. Una tarea puede cubrir varios AC en una sola entrada, y los
repos que participan en cada uno no tienen por qué ser los mismos: una lista plana no sabría de cuál
de ellos participa cada repo. Con `covers_ac` vacía el mapa sobra: ausente o `{}` es lo correcto.

### Participación y custodia

Alrededor de una tarea de orquestación hay cuatro preguntas distintas —quién interviene, quién la
ejecuta, qué prueba su cierre y quién mantiene el contrato—, y llamar "dueño" a más de una las
confunde. Cada una tiene su término y su lugar:

- Participación: qué repos intervienen en un AC `[integration]`. Se declara en `participating_repos`, dentro de cada `orchestration_task`, y es la fuente autoritativa de la relación AC → repos.
- Dueño de ejecución: quién ejecuta la tarea de orquestación y responde por su cierre. Se declara en `owner`.
- Evidencia autoritativa: la fila del contrato que prueba el cierre de la tarea. Es única y no se duplica.
- Custodia del contrato: quién mantiene el contrato de integración. Es el orquestador.
- Los cuatro son conceptos distintos y no comparten término.

La tabla de **Reparto** de la `master-spec.md` sigue mostrando qué repos tocan cada AC, pero es una
vista humana derivada: ante una discrepancia manda `participating_repos`, que es lo que leen las
validaciones. Un AC `[integration]` no se declara en el `covers_ac` de ningún repo, así que sin este
mapa no habría forma de distinguir un repo que participa de uno que no.

### Bitácora de transiciones

El `manifest.yml` guarda **estados**; la bitácora guarda los **intentos** de cambiarlos. Un snapshot
no distingue el repo que esperó a que se cerrara su gate del que se despachó igual, ni dice quién
cerró una tarea ni en qué orden pasó cada cosa. La bitácora instancia el patrón de
`cross-implement/contrato-verificacion.md` —una línea por paso, con su actor y su timestamp, y el
orden decidido por los datos y no por la posición del renglón— y le agrega lo que la coordinación
multi-repo necesita: identidad por evento y un resultado que separa el intento consumado del
rechazado.

**El evento.** Es la unidad de la bitácora y no admite huecos: los seis campos que declara son
**obligatorios**, y un evento al que le falte cualquiera invalida la bitácora. Ninguno se completa
por defecto ni se da por sobreentendido.

- Cada intento de transición registra un evento con identidad propia y orden inequívoco respecto de los demás.
- El orden no se deriva solo del timestamp, que admite empates.
- Cada evento lleva paso, actor, objeto afectado, resultado y timestamp.
- `resultado` es un enum cerrado que distingue el intento consumado del rechazado.

El `id` cubre las dos primeras cláusulas a la vez: es un entero **estrictamente creciente** en el
orden de registro, así que su valor identifica el evento y su comparación lo ordena. Por eso un `id`
repetido y un `id` que no admite comparación son defectos distintos: el primero rompe la identidad,
el segundo deja el orden indeterminable. El `timestamp` es ISO-8601 con huso y dice **cuándo** pasó
algo, no **después de qué**: dos eventos pueden compartirlo porque la resolución del reloj es finita,
y ordenar por él dejaría ese empate sin resolver.

`paso` es también un enum cerrado, con un valor por camino instrumentado: `cerrar-tarea`,
`despachar-repo`, `promover-repo`, `liberar-lock` y `ejecutar-evidencia`. `actor` es quien intentó la
transición —el orquestador, o el dueño de ejecución de la tarea cuando la acción es externa o
manual—. `objeto` es qué se intentó mover: el `id` de la tarea, el `path` del repo o el recurso del
lock. Una línea por evento:

```markdown
- `id: 7` · `paso: despachar-repo` · `actor: orquestador` · `objeto: servicio-b` · `resultado: consumado` · `timestamp: 2026-06-03T14:22:31-03:00`
```

**El resultado y su efecto.** `resultado` admite exactamente dos valores, `consumado` y `rechazado`.

- Solo un resultado exitoso materializa la transición; un intento rechazado es un registro legítimo.

Un rechazo no es una violación del modelo sino su funcionamiento normal: es lo que deja constancia
del repo que **no** se despachó porque su gate seguía abierto, o del cierre que **no** se materializó
porque su evidencia estaba vencida. Sin ese registro, ese repo es indistinguible de uno que nadie
intentó despachar. Las tres formas de romper la correspondencia son inválidas por igual: un evento
`consumado` sin su cambio de estado, un evento `rechazado` cuyo estado cambió igual, y un cambio de
estado que ningún evento consumó.

**Dónde vive.**

- La bitácora es local y untracked, sobrevive al `resume` y se archiva con la orquestación.

Es `<contenedora>/.sdd/<id>/bitacora.md`, junto al `manifest.yml` y la `master-spec.md`, y con las
mismas reglas que ellos: local, nunca se trackea ni se commitea en ningún repo. Es **acumulativa**:
un `resume` la continúa y jamás la reinicia —perder los eventos previos borraría justo lo que hace
verificable el progreso ya hecho—, y el `archive` la conserva con el resto del directorio de la
orquestación. Una bitácora ausente o incompleta produce el mismo veredicto que una transición
inválida, nunca un verde por omisión.

**Qué la escribe y cuándo.**

- Los caminos instrumentados son cerrar una tarea, despachar un repo, promoverlo tras un gate, liberar un lock y ejecutar evidencia.
- El intento se registra antes de materializar la transición, nunca después.

El orden no es decorativo. Registrar después solo puede dejar constancia de lo que efectivamente
ocurrió, así que pierde exactamente el caso que la bitácora existe para probar: el intento
**rechazado**, que por definición no materializa nada y no dejaría rastro. La secuencia es siempre la
misma: se evalúan las precondiciones, se registra el evento con el resultado del intento, y **recién
entonces** se aplica el cambio de estado que un `consumado` habilita, sobre el `manifest.yml`, sobre
el `plan.md` del repo o sobre el lock. Un rechazo termina en el registro y no toca nada más.

**La frescura de una evidencia.**

- La frescura de una evidencia ata la tarea, su fila, la versión vigente del contrato y el SHA de cada repo relevante.
- Para evidencia no ligada a código, la frescura usa un ancla versionada equivalente declarada.

El evento de ejecución de evidencia lleva, además de los seis obligatorios, el anclaje que permite
juzgarla: la fila del contrato que ejecutó, la versión del contrato vigente en ese momento y —para
evidencia ligada a código— un SHA por **cada** repo relevante. No existe un "commit vigente"
singular: una tarea cuyo `participating_repos` nombra dos repos se mide contra dos SHA, y si uno de
ellos se movió después, la evidencia está vencida aunque el otro siga igual. Con un SHA de menos la
evidencia no es juzgable, y no juzgable cuenta como vencida.

Cuando la evidencia no está ligada a código —un acuerdo entre equipos, una configuración de entorno,
la publicación de un contrato— el SHA no aplica, pero la vara no baja: el evento declara el ancla
versionada equivalente que haga las veces —la versión del documento acordado, el identificador del
despliegue, la revisión de la configuración— y esa ancla se revalida igual que un SHA. Una evidencia
sin ancla, o con un ancla que ya no es la vigente, se trata igual que una medida sobre un repo que
después se movió.

```markdown
- `id: 12` · `paso: ejecutar-evidencia` · `actor: equipo-plataforma` · `objeto: C1` · `resultado: consumado` · `timestamp: 2026-06-03T18:04:09-03:00` · `fila: V-C1` · `contrato: v3` · `sha: servicio-a=4f2a9c1, servicio-b=9b1e77d`
- `id: 13` · `paso: cerrar-tarea` · `actor: orquestador` · `objeto: C1` · `resultado: rechazado` · `timestamp: 2026-06-03T18:04:11-03:00`
```

**Este esquema mezcla estado de corrida (`id`, `created_at`, `master_spec`, `repos`,
`orchestration_tasks`) con configuración.** Las claves de configuración son propias de esta skill (`branch_prefix`,
`execution_mode`, `implement_mode`, `cross_model.*`) salvo `cross_review.*` y `co_explore.*`, cuyo enum lo define su
dueño: `cross_review.*` en `cross-review/SKILL.md` → "Configuración" y `co_explore.*` en
`co-explore/SKILL.md` → "Configuración". Solo esas 12 claves, listas para
copiar y con la misma vista que `config-ejemplo.md` de `sdd-flow`, están en `manifest-ejemplo.md`.

## Plantilla de `master-spec.md`

`<contenedora>/.sdd/<id>/master-spec.md` — el QUÉ global. Sin detalles de implementación por repo (eso va en cada `plan.md`).

```markdown
# Master Spec — <título corto del objetivo>

## Problema / Objetivo
<por qué existe este cambio, a nivel sistema — del ticket + prompt>

## Alcance
- **Incluye:** <qué entra, a nivel sistema>
- **No incluye:** <qué queda afuera>

## Criterios de aceptación
- **AC-1 [repo-local]:** Given <contexto>, When <acción>, Then <resultado observable en un repo>.
- **AC-2 [repo-local]:** <...>
- **AC-3 [integration]:** Given <varios servicios arriba>, When <flujo end-to-end>, Then <resultado observable cross-repo>.

## Contratos entre servicios
<ver "Formato de contratos entre servicios">

## Reparto
| AC | Repo(s) | Tipo |
|---|---|---|
| AC-1 | servicio-a | repo-local |
| AC-2 | servicio-a | repo-local |
| AC-3 | servicio-a + servicio-b | integration |
```

Cada AC lleva la etiqueta `[repo-local]` (lo verifica el agente del repo en Fase 2) o `[integration]` (verificación manual en Fase 3, salvo comando de integración dado).

## Spec por repo

`<repo>/.plans/<id>/spec.md` — la fuente de los AC que el agente delegado verifica (la Vía B de `sdd-flow` la lee igual que una spec propia; sin ella, su paso `verify` no tiene contra qué chequear). Se escribe en el reparto (Fase 1.4), derivada de la master-spec:

```markdown
# Spec — <título corto> (parte de <id>, repo <repo>)

## Problema / Objetivo
<el objetivo global recortado a lo que este repo aporta>
Master-spec de la orquestación: <contenedora>/.sdd/<id>/master-spec.md

## Criterios de aceptación
<los AC de covers_ac, copiados TEXTUALES de la master-spec, con sus IDs globales>
- **AC-1 [repo-local]:** Given <contexto>, When <acción>, Then <resultado observable>.

## Fuera del alcance de este repo
- Los AC [integration] en los que participa (<AC-n, …>) se verifican en la Fase 3 de la
  orquestación, no acá. El agente del repo NUNCA los da por cumplidos localmente.

## Contratos que tocan a este repo
- <qué expone / qué consume, copiado de la master-spec>
```

Mantener los IDs globales `AC-n` (no renumerar): la trazabilidad cross-repo del `manifest.yml` (`covers_ac`) y el cross-artifact check dependen de eso.

> **Self-review del reparto (antes del gate 1.4).** Los `plan.md`/`tasks.md` por repo heredan el formato y la disciplina de `sdd-flow` (ver su `reference.md` → "Plantilla de plan" y "Plantilla de tasks", bloque "Self-review (antes del gate)"). Además de la cobertura AC↔repo (cross-artifact check, regla 5), correr sobre cada `plan.md`/`tasks.md` generado: la **cobertura AC↔fila del contrato de verificación** (bidireccional, ni AC sin fila ni fila sin AC), el **scan anti-placeholder** (sin `TBD`/`TODO`/"etc." colgados) y la **consistencia de contratos** entre servicios — lo que un repo `expone` coincide en firma con lo que el otro `consume` (mismo criterio que `Produce`/`Consume` entre tasks). Reportarlo en una línea antes del gate.

### Contrato de verificación por repo

El `## Verification` de cada `plan.md` generado lleva el **mismo esquema normativo** que en un flujo
`sdd-flow` de un solo repo: la tabla de seis columnas y su bloque de baseline por versión. Se hereda
**por puntero** (`sdd-flow/reference.md` → "Plantilla de plan"), y esta skill **no** mantiene una
plantilla propia: dos plantillas del mismo contrato se desincronizan en la primera corrección, y el
gate de `cross-implement` valida una sola forma.

Lo único propio del multi-repo es qué filas entran, y eso lo decide la etiqueta del AC:

| AC | Dónde vive su fila | Qué lleva el contrato del repo |
|---|---|---|
| `[repo-local]` | en el contrato del repo | la fila completa, con su baseline medido en ese repo |
| `[integration]` | en el **contrato de integración** de la orquestación | una referencia **solo-lectura** (ver "Contrato de integración") |

### Contrato de integración

Las filas de los AC `[integration]` **no viven en el contrato de ningún repo**. Viven en un contrato
de integración propio, en `<contenedora>/.sdd/<id>/integracion.md`, con el mismo esquema normativo y
un dueño único: el orquestador.

Es la forma contractual de la regla no negociable que ya rige —ningún AC `[integration]` se da por
cumplido en un repo—: si su fila viviera en el contrato del repo, el `verify` local la ejecutaría y
la cerraría, que es exactamente lo prohibido. Y si viviera en **dos** repos, cada uno la cerraría con
media evidencia.

**Qué cubre y cuándo nace.**

- Es el contrato de cierre de toda tarea de orquestación, auxiliares incluidas.
- Su versión inicial se materializa completa y se congela en la Fase 1.
- La Fase 3 revalida la versión vigente sin agregar ni quitar IDs.
- El baseline de toda fila se resuelve al congelarla: `NOT_APPLICABLE` cuando medirlo es inaplicable y `BLOCKED` cuando falta entorno, y con `BLOCKED` no se despacha.

Toda entrada de `orchestration_tasks` tiene su fila: el cierre de un `gate`, el de un `closeout` y el
de una tarea auxiliar con `covers_ac` vacío, por igual. Una auxiliar no cubre ningún AC y aun así
necesita dónde probar su cierre; su `done_when` referencia esa fila como cualquier otra.

Que el contrato nazca completo no es una preferencia de orden. El esquema canónico declara
**invariante el conjunto de `ID` entre versiones** (`cross-implement/contrato-verificacion.md` → "Qué
es invariante entre versiones"), así que materializar solo las filas de los gates volvería
**imposible** añadir después las de los cierres: toda versión posterior que las estrenara se
rechazaría. Las seis columnas y el bloque de baseline se heredan por puntero de ese mismo documento;
esta skill no mantiene una forma propia.

Congelar en la Fase 1 fija **cuándo nace** el contrato completo, no prohíbe repararlo: el versionado
canónico sigue admitiendo versiones nuevas mientras conserven IDs, `Requisito` y `Esperado`. Por eso
la Fase 3 no vuelve a congelar nada —el conjunto de filas ya está decidido— y lo que hace es
revalidar la vigente antes de ejecutar las que le quedan.

Un baseline resuelto es condición de ese congelamiento, y sus dos casos límite no significan lo mismo.
`NOT_APPLICABLE` es un veredicto sobre la medición: no hay nada que medir antes del cambio, y la fila
queda igual de exigible. `BLOCKED` no es un veredicto sino una falta de entorno, y mientras dure el
repo **no se despacha**: despachar contra una fila cuyo baseline nadie pudo medir deja el resultado
final sin nada contra qué compararse, que es el falso verde que el contrato existe para impedir.

El contrato del repo **referencia** la fila en modo solo-lectura, con su ID global y una evidencia que
no es un estado del enum:

- La referencia solo-lectura del repo lleva `N/A: orchestration-owned`.

```markdown
| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |
|---|---|---|---|---|---|
| V3 | AC-7 [integration] — el checkout confirma contra el servicio de pagos | N/A: orchestration-owned | ver V-C2 de integracion.md | se verifica en el contrato de integración | N/A: orchestration-owned |
```

La observación `ver V-<id-tarea> de integracion.md` nombra la fila **autoritativa**: la de la tarea
cuyo `covers_ac` incluye ese AC. Sin ella la referencia diría que el AC se cierra en otro lado sin
decir dónde, y dos repos participantes podrían apuntar a filas distintas para el mismo AC.

El valor de la evidencia declara **de quién es la fila**, no en qué momento se ejecuta, y es
deliberadamente **ninguno de los dos atajos** que parecen naturales:

- **no es `NOT_APPLICABLE`**, que significa "medir un baseline es semánticamente inaplicable" y
  borraría una obligación global: el AC sí se verifica, en otro lado;
- **no es una fila pendiente ni `BLOCKED`**, que bloquearía el gate del repo por algo que no le toca
  resolver y dejaría el flujo local trabado para siempre.

Nombrar al dueño en vez del momento tampoco es cosmético: la tarea que cierra un AC `[integration]`
puede ser un `gate`, y entonces su evidencia se ejecuta **antes** del fan-out. Una referencia que
anunciara una fase fija sería falsa justo en ese caso, y el repo la leería como permiso para dar el
AC por diferido hasta el final.

La referencia es obligatoria y no opcional: sin ella, el contrato del repo tendría un AC en alcance
sin fila y la cobertura bidireccional no cerraría. Eliminarla para "simplificar" rompe el gate.

### Gate de la Fase 3 y agregación

El contrato de integración pasa por un gate **equivalente** al que `cross-implement` aplica antes de
delegar (`cross-implement/contrato-verificacion.md` → "El gate previo al dispatch"): versión vigente
identificada, cobertura bidireccional contra los AC `[integration]`, campos obligatorios presentes y
baseline resuelto en toda fila, ninguna en `BLOCKED`. Ese gate corre dos veces con el mismo criterio
y distinto efecto: en la Fase 1 es lo que habilita el congelamiento de la versión inicial, y en la
Fase 3 revalida esa misma versión antes de la primera evidencia. La segunda pasada no emite ninguna
versión ni toca el conjunto de filas: si algo no cierra, la Fase 3 se detiene en vez de reparar el
contrato sobre la marcha.

La enumeración inmediata no es exhaustiva; manda el conjunto canónico completo de la sede enlazada.

El gate no es un trámite copiado: es lo que hace que sacar estas filas del contrato de cada repo sea
**moverlas a otro gate** y no dejarlas sin ninguno. Sin él, la separación las volvería invisibles —
que es peor que el problema original de cerrarlas localmente con media evidencia.

**La agregación final no puede producir verde con filas ausentes.** El estado global es verde solo
si toda fila del contrato de integración está resuelta; una ausente, una `BLOCKED` o una `manual`
pendiente producen **no verificado**. Un agregador que ignora lo que falta reporta el subconjunto que
miró, y ese número siempre da mejor que la realidad.

## Formato de contratos entre servicios

La sección que permite implementar en paralelo contra un acuerdo, aunque en runtime un servicio dependa de otro:

```markdown
## Contratos entre servicios
- **servicio-a expone:** `GET /health` → `200 { "status": "ok" }`.
- **servicio-b consume:** `GET servicio-a/health` al arrancar; si != 200, log de warning y retry.
- **evento (si aplica):** `servicio-a` publica `user.created {id, email}` en el bus; `gateway` lo consume.
```

Cada contrato nombra **quién expone** y **quién consume**, con el shape (endpoint/payload/evento). El `depends_on` del manifest refleja estas relaciones.

## Prompt del agente delegado

`sdd-flow` es solo-slash (`disable-model-invocation`): un subagente **no** puede invocarla con el
Skill tool. El fan-out (Fase 2.3) le pasa el contrato por prompt. Plantilla:

```
Trabaja ÚNICAMENTE en el repo <ruta-absoluta-al-repo> (todo comando y ruta, relativos a él).
Lee <directorio-de-skills>/sdd-flow/SKILL.md (y su reference.md si lo necesitas) y ejecuta su
Vía B: "implement .plans/<id>/", siguiendo ese contrato al pie de la letra.
Override de esta corrida: cross_review.mode: off (el plan ya fue revisado en el reparto).
Inventario heredado, solo si el manifest declaró `families` y ya se comparó con el repo:
family_inventory:
  families: <lista canonizada>
  source: declared
  selection: <full | user_choice>
  root: sdd-orchestrator
Reglas duras:
- FRENA antes de commitear (nada de git commit/push); no toques nada fuera del repo.
- Eres un agente sin usuario: NO hagas los checkpoints conversacionales de la Vía B (no
  confirmes resúmenes ni preguntes el modo de implementación — usa inline, salvo que tu
  entorno permita despachar subagentes). Ante un bloqueo real, devuelve STATUS: failed con la razón.
- La rama del header todavía no existe (esta orquestación nunca la creó): créala desde
  base_commit sin preguntar (git checkout -b <branch> <base_commit>).

Tu mensaje final debe ser EXACTAMENTE este reporte (sin prosa extra):
STATUS: verified | failed
FAILURE_REASON: <1-3 líneas si failed; omitir si verified>
AC: <una línea por AC-n: cumplido | no cumplido — evidencia breve>
FILES: <una línea por archivo tocado>
```

El orquestador parsea `STATUS` para actualizar el `manifest.yml` (Fase 2.4). Red de seguridad: si
el reporte falta o no parsea, releer el `status` persistido en `<repo>/.plans/<id>/plan.md`
(fuente de verdad que `sdd-flow` mantiene) y tratar la ausencia de `verified` como fallo.

## Algoritmo del lock cooperativo

Antes de tocar un repo en Fase 2 (o de hacer checkout en un resume), evitar pisar otra orquestación activa:

```
para cada repo R que esta feature (id_actual) va a tocar:
    tomado_por = null
    para cada manifest M en .sdd/*/manifest.yml  (excepto el de id_actual; .sdd/archived/ no cuenta):
        si R.path está en M.repos con status ∉ {pushed, pr-open, done}:
            tomado_por = (M.id, status de R en M)
            break
    si tomado_por:
        AVISAR: "<R> está retenido por la orquestación <M.id> (status <status>)"
        OFRECER, sin hacer checkout de R:
          1. esperar / saltar R por ahora (seguir con los otros repos)
          2. pausar R en M  → delegar `pause` de sdd-flow en <R> (WIP commit), luego tomarlo
          3. excluir R de id_actual
    si no:
        proceder a delegar `/sdd-flow implement` en R
```

Es **cooperativo** (basado en leer manifests), no un lock de archivo del SO. Reusa `pause`/`resume` de `sdd-flow` para liberar y retomar. Los repos no compartidos no se ven afectados.

> **Limitación conocida:** al ser cooperativo no es atómico — dos sesiones orquestando exactamente a la vez pueden leerse antes de escribirse y no verse. Ante la duda (p. ej. el repo está en una rama inesperada o con working tree sucio), tratarlo como tomado y preguntar.

## Cascada de fallos (DAG)

Cuando un agente vuelve con fallo:

```
al marcar R como failed:
    no commitear nada en R
    para cada repo D tal que R ∈ D.depends_on (directa o transitivamente):
        si D aún no arrancó o no terminó:
            D.status = blocked   (motivo: depende de R, que falló)
    los repos sin R en su cierre transitiva de depends_on NO se tocan: siguen su curso
recalcular elegibles (depends_on satisfechos en verde) y continuar el fan-out
```

El reporte final distingue `verified`/`committed`/`pushed` (verdes), `failed` (con el error) y `blocked` (con el repo del que dependían).

## Ejemplos de `manifest.yml`

**E1 — dos repos independientes (paralelo puro):**

```yaml
id: trace-id-rollout
master_spec: .sdd/trace-id-rollout/master-spec.md
created_at: 2026-06-03T10:00:00-03:00
repos:
  - path: servicio-a
    branch: feature/trace-id-rollout-a
    status: tasks-ready
    depends_on: []
    covers_ac: [AC-1]
  - path: servicio-b
    branch: feature/trace-id-rollout-b
    status: tasks-ready
    depends_on: []
    covers_ac: [AC-2]
```

**E2 — dependencia A→B (DAG):**

```yaml
id: health-contract
master_spec: .sdd/health-contract/master-spec.md
created_at: 2026-06-03T10:00:00-03:00
repos:
  - path: servicio-a
    branch: feature/health-contract-expose
    status: tasks-ready
    depends_on: []
    covers_ac: [AC-1]
  - path: servicio-b
    branch: feature/health-contract-consume
    status: planned
    depends_on: [servicio-a]
    covers_ac: [AC-2]
```

**E3 — con trabajo propio del orquestador (gate, cierre y auxiliar):**

```yaml
id: notificaciones-v2
master_spec: .sdd/notificaciones-v2/master-spec.md
created_at: 2026-06-03T10:00:00-03:00
repos:
  - path: servicio-a
    branch: feature/notificaciones-v2-emisor
    status: planned
    depends_on: []
    covers_ac: [AC-1]
  - path: servicio-b
    branch: feature/notificaciones-v2-receptor
    status: planned
    depends_on: []
    covers_ac: [AC-2]
orchestration_tasks:
  - id: G1
    phase: gate
    what: acordar el esquema del evento entre los dos equipos
    owner: UNASSIGNED
    status: pending
    depends_on: []
    covers_ac: []
    done_when: V-G1
    blocks_repos: [servicio-a, servicio-b]
  - id: C1
    phase: closeout
    what: correr el flujo end-to-end con los dos servicios desplegados
    owner: equipo-plataforma
    status: pending
    depends_on: [G1]
    covers_ac: [AC-3]
    done_when: V-C1
    participating_repos:
      AC-3: [servicio-a, servicio-b]
  - id: X1
    phase: closeout
    what: archivar el acuerdo del evento en la wiki del equipo
    owner: equipo-plataforma
    status: pending
    depends_on: [C1]
    covers_ac: []
    done_when: V-X1
```

Las tres entradas muestran los tres casos que la cardinalidad distingue. `G1` es un gate: retiene el
fan-out de los dos repos —por eso ambos arrancan en `planned`— y no cubre ningún AC. `C1` es el
cierre que cubre el AC `[integration]` y declara en `participating_repos` qué repos participan de él.
`X1` es auxiliar: no cubre AC ni bloquea a nadie, y aun así lleva `owner`, `done_when` y su fila en
el contrato de integración, porque el contrato cierra **toda** tarea.

## Bloques de validación de la integración

Predicados sobre el reparto y el contrato de integración. Cada bloque declara su **predicado**, y esa
línea es idéntica en las dos variantes de shell.

Los escenarios contra los que corren esos predicados los materializa una **fábrica única**,
`@bloque:fixtures-orquestacion`: recibe el nombre de un escenario, deja sus artefactos en el
directorio actual y escribe `env.sh` y `env.ps1` con las entradas que cada bloque declara en su
`# Entradas:`. Es un solo bloque POSIX y **no** tiene gemelo `-ps`: la rama PowerShell lo invoca con
`bash fab.sh <NOMBRE>` como proceso hijo y consume el `env.ps1` que produce, así que un solo cuerpo
decide qué es cada escenario y los dos gemelos de cada guarda ven exactamente el mismo material.

```bash
# @bloque:fixtures-orquestacion
# Fábrica de escenarios de orquestación. Materializa en el cwd el manifest, la master-spec, un
# plan.md por repo, el contrato de integración, la bitácora y una copia del SKILL.md, más `env.sh` y
# `env.ps1` con las entradas que declaran las guardas.
#
# Uso: `. ./fab.sh <NOMBRE>` (sourced, como la corre el runner POSIX) y `bash fab.sh <NOMBRE>`
# (proceso hijo, como la corre la rama PowerShell). Tiene que andar de las dos formas, así que todo
# vive dentro de _fx_main: `return` en el nivel superior de un script NO sourceado es un error, y
# `exit` cortaría el arnés antes de la guarda dejando la fila verde sin haber corrido nada.
#
# Un fixture válido base y UNA sola mutación por caso rojo (decisión 4 del plan). La mutación se
# propaga a los artefactos que la vuelven coherente —estado y su evento de bitácora van juntos—
# pero nunca introduce un segundo defecto: un fixture con dos defectos puede ponerse rojo por el
# equivocado y entonces su fila no prueba su invariante.
#
# Precedencias que las guardas deben respetar para que cada fixture emita UN solo diagnóstico. No
# son opcionales: son la contracara de la mutación única, y sin ellas dos comprobaciones correctas
# se pisan sobre el mismo defecto.
#   modelo:    ubicación de AC → mapa ausente/vacío → clave ajena → clave sin AC → AC no integration
#   contrato:  clase closeout ausente → clase auxiliar ausente → cardinalidad por tarea → fila huérfana
#   estado:    despacho consumado con gate abierto → promoción indebida; evidencia duplicada →
#              evidencia de otra fila; correspondencia objeto↔fila del evento → evidencia ausente
#   El repo libre que sigue en `planned` solo es defecto si el reparto se aprobó, y esa señal es la
#   existencia de un evento `promover-repo` (de cualquier resultado): sin él, todo en `planned` es
#   el estado correcto de una orquestación que todavía no repartió.
#   Un repo cuya fila local tiene baseline BLOCKED no arrastra la obligación de despachar.
_fx_main() {
  local n="${1:-}"
  _fx_defaults
  case "$n" in

  # ── modelo: manifest + master-spec ───────────────────────────────────────
  MODELO_VALIDO|PARTICIPACION_AUSENTE_SIN_INTEG) ;;
  PARTICIPACION_VACIA_SIN_INTEG)   FX_X1_PART=@empty@ ;;
  AC_INTEGRATION_HUERFANO)         FX_C1_COVERS="AC-4"; FX_C1_PART="AC-4=servicio-a"
                                   FX_A_REFS="AC-4=V-C1=ok"; FX_B_REFS="" ;;
  AC_MAL_UBICADO_INTEG_EN_REPO)    FX_A_COVERS="AC-1, AC-3" ;;
  AC_MAL_UBICADO_LOCAL_EN_TAREA)   FX_C1_COVERS="AC-3, AC-4, AC-1"
                                   FX_C1_PART="AC-3=servicio-a,servicio-b;AC-4=servicio-a;AC-1=servicio-a" ;;
  CARDINALIDAD_DOS_TAREAS)         FX_X1_COVERS="AC-3"; FX_X1_PART="AC-3=servicio-a,servicio-b" ;;
  CICLO)                           FX_C1_DEPS="G1, X1"; FX_X1_DEPS="C1" ;;
  ID_DUPLICADO)                    FX_TAREAS="G1 C1 X1 D1" ;;
  REF_MUERTA_DEPENDS)              FX_C1_DEPS="G9" ;;
  REF_MUERTA_BLOCKS)               FX_G1_BLOCKS="servicio-z" ;;
  ENUM_PHASE)                      FX_C1_PHASE=cierre ;;
  ENUM_STATUS)                     FX_C1_ST=pendiente ;;
  OWNER_AUSENTE)                   FX_C1_OWNER=@none@ ;;
  OWNER_VACIO)                     FX_C1_OWNER=@empty@ ;;
  DONE_WHEN_AUSENTE)               FX_X1_DW=@none@ ;;
  DONE_WHEN_VACIO)                 FX_X1_DW=@empty@ ;;
  BLOCKS_EN_CLOSEOUT)              FX_C1_BLOCKS="servicio-b" ;;
  GATE_DEPENDE_CLOSEOUT)           FX_G1_DEPS="X1" ;;
  PARTICIPACION_CLAVE_DUP)         FX_C1_PART="AC-3=servicio-a,servicio-b;AC-3=servicio-a;AC-4=servicio-a" ;;
  PARTICIPACION_REPO_INEXISTENTE)  FX_C1_PART="AC-3=servicio-a,servicio-z;AC-4=servicio-a" ;;
  PARTICIPACION_AC_NO_INTEG)       FX_C1_COVERS="AC-3, AC-4, AC-7"
                                   FX_C1_PART="AC-3=servicio-a,servicio-b;AC-4=servicio-a;AC-7=servicio-a" ;;
  PARTICIPACION_AC_SIN_CLAVE)      FX_C1_PART="AC-3=servicio-a,servicio-b" ;;
  PARTICIPACION_CLAVE_EXTRA)       FX_C1_PART="AC-3=servicio-a,servicio-b;AC-4=servicio-a;AC-9=servicio-b" ;;
  PARTICIPACION_AUSENTE_CON_INTEG) FX_C1_PART=@none@ ;;
  PARTICIPACION_VACIA_CON_INTEG)   FX_C1_PART=@empty@ ;;

  # ── contrato de integración ──────────────────────────────────────────────
  CONTRATO_COMPLETO|BASELINE_NOT_APPLICABLE) ;;
  SOLO_GATES)                      FX_FILAS="G1" ;;
  SIN_AUXILIAR)                    FX_FILAS="G1 C1" ;;
  CARDINALIDAD_TAREA_SIN_FILA)     FX_FILAS="G1 X1" ;;
  CARDINALIDAD_FILA_HUERFANA)      FX_FILA_HUERFANA=1 ;;
  CARDINALIDAD_DOS_FILAS)          FX_FILA_DUP=1 ;;
  BASELINE_SIN_RESOLVER)           FX_X1_BASE=TBD ;;
  V2_AGREGA_ID)                    FX_V2=agrega ;;
  V2_QUITA_ID)                     FX_V2=quita ;;

  # ── ownership de la referencia por repo ──────────────────────────────────
  REF_CLOSEOUT) ;;
  REF_GATE)                        _fx_gate_cubre ;;
  CIERRE_LOCAL_PROHIBIDO)          FX_A_REFS="AC-3=V-C1=local AC-4=V-C1=ok" ;;
  CIERRE_LOCAL_NOT_APPLICABLE)     FX_A_REFS="AC-3=V-C1=na AC-4=V-C1=ok" ;;
  REF_ESPERADA_AUSENTE)            FX_A_REFS="AC-3=V-C1=ok" ;;
  REF_EN_NO_PARTICIPANTE)          FX_B_REFS="AC-3=V-C1=ok AC-4=V-C1=ok" ;;
  REF_CON_LITERAL_VIEJO)           FX_A_REFS="AC-3=V-C1=viejo AC-4=V-C1=ok" ;;
  REF_A_FILA_EQUIVOCADA)           FX_B_REFS="AC-3=V-X1=ok" ;;

  # ── compatibilidad ───────────────────────────────────────────────────────
  RETROCOMPAT)                     _fx_retro ;;
  MIXTO_2P_1NP)                    FX_USA_C=1 ;;

  # ── gate de la Fase 3 ────────────────────────────────────────────────────
  FASE3_SIN_REVALIDAR)             FX_SKILL_REVALIDA=0 ;;

  # ── reparto y asignación inicial ─────────────────────────────────────────
  ASIGNACION_INICIAL)              _fx_reparto ;;
  REPARTO_OWNER_UNASSIGNED)        _fx_reparto; FX_C1_OWNER=UNASSIGNED ;;
  ASIGNACION_LIBRE_AUN_PLANNED)    _fx_reparto; FX_A_ST=planned ;;
  ASIGNACION_BLOQUEADO_YA_READY)   _fx_reparto; FX_B_ST=tasks-ready; FX_B_DESPACHO=no ;;
  DIVERGENCIA_MANIFEST_PLAN)       _fx_reparto; FX_A_PLANST=planned ;;

  # ── gate abierto / cerrado ───────────────────────────────────────────────
  GATE_ABIERTO_REPO_PLANNED)       _fx_reparto; FX_B_DESPACHO=no ;;
  GATE_ABIERTO_DESPACHO_RECHAZADO) _fx_reparto ;;
  GATE_ABIERTO_DESPACHO_EXITOSO)   _fx_reparto; FX_B_ST=implementing ;;
  GATE_CERRADO_REPO_READY|PROMOCION_TRAS_GATE)
                                   _fx_reparto; FX_G1_ST=done; FX_B_ST=implementing ;;
  GATE_CERRADO_REPO_AUN_PLANNED)   _fx_reparto; FX_G1_ST=done ;;
  GATE_CERRADO_SIN_DESPACHO)       _fx_reparto; FX_G1_ST=done; FX_B_ST=tasks-ready; FX_B_DESPACHO=no ;;

  # ── baseline BLOCKED y despacho ──────────────────────────────────────────
  BASELINE_BLOCKED_SIN_DESPACHO)   _fx_baseline_blocked ;;
  DESPACHO_CON_BASELINE_BLOCKED)   _fx_baseline_blocked; FX_A_ST=implementing ;;

  # ── gate bloqueado y lock ────────────────────────────────────────────────
  LOCK_LIBERADO_TRAS_DECISION)     _fx_lock; FX_LOCK=con-decision ;;
  LOCK_LIBERACION_RECHAZADA_SIN_DECISION) _fx_lock; FX_LOCK=rechazado ;;
  LOCK_LIBERADO_SIN_DECISION)      _fx_lock; FX_LOCK=sin-decision ;;

  # ── cierre de tareas ─────────────────────────────────────────────────────
  CIERRE_LEGITIMO|BITACORA_TRANSICION_CONSUMADA|FRESCURA_VALIDA_MULTIREPO) ;;
  FRESCURA_VALIDA_ANCLA_NO_CODIGO) ;;
  DONE_GATE_UNASSIGNED_SINAC)      FX_G1_OWNER=UNASSIGNED ;;
  DONE_GATE_UNASSIGNED_CONAC)      _fx_gate_cubre; FX_G1_OWNER=UNASSIGNED ;;
  DONE_CLOSEOUT_UNASSIGNED_CONAC)  FX_C1_OWNER=UNASSIGNED ;;
  DONE_CLOSEOUT_UNASSIGNED_SINAC)  FX_X1_OWNER=UNASSIGNED ;;
  DEPS_INSATISFECHAS)              FX_X1_DEPS="C1"; FX_C1_ST=in-progress ;;
  EVIDENCIA_OBSOLETA)              FX_C1_EVIDENCIA=no ;;
  ESPERADO_FALLIDO)                FX_C1_OBSERVADO="el receptor descarta el evento y responde 500" ;;
  DONE_WHEN_DIVERGENTE)            FX_C1_DW=V-C9 ;;
  DUENO_DUPLICADO)                 FX_X1_OWNER=equipo-plataforma ;;
  EVIDENCIA_DUPLICADA)             FX_X1_DW=V-C1; FX_X1_EVFILA=V-C1 ;;

  # ── frescura de la evidencia ─────────────────────────────────────────────
  FRESCURA_FILA_EQUIVOCADA)        FX_C1_EVFILA=V-Z9 ;;
  FRESCURA_TAREA_EQUIVOCADA)       FX_C1_EVOBJ=X1 ;;
  FRESCURA_VERSION_ANTERIOR)       FX_V2=igual ;;
  FRESCURA_REPO_MOVIDO)            FX_B_SHA=bbb9999 ;;
  FRESCURA_REPO_AUSENTE)           FX_C1_SHAS="servicio-a=aaa1111" ;;
  FRESCURA_ANCLA_AUSENTE)          FX_G1_ANCLA=@none@ ;;
  FRESCURA_ANCLA_OBSOLETA)         FX_G1_ANCLA="acuerdo-evento=v2" ;;

  # ── bitácora ─────────────────────────────────────────────────────────────
  BITACORA_INTENTO_RECHAZADO)      _fx_reparto ;;
  BITACORA_AUSENTE)                FX_BIT_VACIA=1 ;;
  BITACORA_ID_DUPLICADO)           FX_BIT_DIR='$'; FX_BIT_SED="s/id: [0-9][0-9]*/id: 1/" ;;
  BITACORA_ORDEN_AMBIGUO)          FX_BIT_DIR='$'; FX_BIT_SED="s/id: [0-9][0-9]*/id: ultimo/" ;;
  BITACORA_RESULTADO_INVALIDO)     FX_BIT_DIR="/cerrar-tarea.*objeto: C1./"
                                   FX_BIT_SED="s/resultado: consumado/resultado: ok/" ;;
  BITACORA_EXITO_SIN_EFECTO)       FX_X1_ST=pending; FX_X1_CIERRE=forzado ;;
  BITACORA_RECHAZO_CON_EFECTO)     FX_BIT_DIR="/cerrar-tarea.*objeto: X1./"
                                   FX_BIT_SED="s/resultado: consumado/resultado: rechazado/" ;;
  BITACORA_TRANSICION_SIN_EVENTO)  FX_BIT_DIR="/cerrar-tarea.*objeto: X1./"; FX_BIT_SED=d ;;
  BITACORA_EVENTO_SIN_ID)          _fx_sin_campo id ;;
  BITACORA_EVENTO_SIN_PASO)        _fx_sin_campo paso ;;
  BITACORA_EVENTO_SIN_ACTOR)       _fx_sin_campo actor ;;
  BITACORA_EVENTO_SIN_OBJETO)      _fx_sin_campo objeto ;;
  BITACORA_EVENTO_SIN_RESULTADO)   _fx_sin_campo resultado ;;
  BITACORA_EVENTO_SIN_TIMESTAMP)   _fx_sin_campo timestamp ;;

  # ── precedencia del estado agregado ──────────────────────────────────────
  PRECEDENCIA_TODO_DONE)           ;;
  PRECEDENCIA_REPO_FAILED)         FX_A_ST=failed ;;
  PRECEDENCIA_REPO_BLOCKED)        FX_B_ST=blocked ;;
  PRECEDENCIA_GATE_BLOCKED)        _fx_lock ;;
  PRECEDENCIA_EN_CURSO)            FX_B_ST=implementing ;;
  PRECEDENCIA_INTEGRACION_PENDIENTE) FX_C1_ST=pending ;;
  PRECEDENCIA_FAILED_MAS_INTEG_PENDIENTE)  FX_A_ST=failed; FX_C1_ST=pending ;;
  PRECEDENCIA_GATE_BLOCKED_MAS_EN_CURSO)   _fx_lock; FX_A_ST=implementing ;;
  PRECEDENCIA_FAILED_MAS_REPO_BLOCKED)     FX_A_ST=failed; FX_B_ST=blocked ;;
  PRECEDENCIA_REPO_BLOCKED_MAS_GATE_BLOCKED) _fx_lock; FX_B_ST=blocked ;;
  PRECEDENCIA_EN_CURSO_MAS_INTEG_PENDIENTE) FX_B_ST=implementing; FX_C1_ST=pending ;;

  # ── archive ──────────────────────────────────────────────────────────────
  ARCHIVE_CIERRE_PENDIENTE)        FX_OUTCOME=archived; FX_C1_ST=pending ;;
  ARCHIVE_VARIAS_PENDIENTES)       FX_OUTCOME=archived; FX_REPARTO=0
                                   FX_G1_ST=pending; FX_C1_ST=pending; FX_X1_ST=pending
                                   FX_A_ST=planned; FX_B_ST=planned ;;

  *) printf 'ARNES:escenario desconocido: %s\n' "$n" >&2; return 1 ;;
  esac
  _fx_emitir
  return 0
}

# ── presets de fase ────────────────────────────────────────────────────────
# El reparto recién aprobado: el gate abierto retiene servicio-b, ninguna tarea cerró.
_fx_reparto() {
  FX_G1_ST=pending; FX_C1_ST=pending; FX_X1_ST=pending
  FX_A_ST=tasks-ready; FX_B_ST=planned
}
# El AC de integración lo cubre un GATE: su evidencia se ejecuta antes del fan-out.
_fx_gate_cubre() {
  FX_G1_COVERS="AC-3"; FX_G1_PART="AC-3=servicio-a,servicio-b"
  FX_G1_SHAS="servicio-a=aaa1111, servicio-b=bbb2222"; FX_G1_ANCLA=@none@
  FX_C1_COVERS="AC-4"; FX_C1_PART="AC-4=servicio-a"; FX_C1_SHAS="servicio-a=aaa1111"
  FX_A_REFS="AC-3=V-G1=ok AC-4=V-C1=ok"; FX_B_REFS="AC-3=V-G1=ok"
}
# Un repo con el baseline de su fila local sin medir: mientras dure, no se despacha.
_fx_baseline_blocked() {
  FX_A_LOCALBASE=BLOCKED; FX_A_ST=tasks-ready; FX_A_DESPACHO=rechazado
  FX_C1_ST=pending; FX_X1_ST=pending
}
# Gate bloqueado que retiene a servicio-b: es el contexto donde se libera un lock.
_fx_lock() {
  FX_G1_ST=blocked; FX_C1_ST=pending; FX_X1_ST=pending
  FX_A_ST=done; FX_B_ST=planned
}
# Un campo obligatorio de menos en el evento de cierre de C1.
_fx_sin_campo() {
  FX_BIT_DIR="/cerrar-tarea.*objeto: C1./"
  case "$1" in
    id) FX_BIT_SED="s/^- ${FX_BQ}id: [^${FX_BQ}]*${FX_BQ} · /- /" ;;
    *)  FX_BIT_SED="s/ · ${FX_BQ}$1: [^${FX_BQ}]*${FX_BQ}//" ;;
  esac
}
# El caso retrocompatible: ni AC [integration] ni orchestration_tasks.
_fx_retro() {
  FX_RETRO=1; FX_TAREAS=""; FX_FILAS=""
  FX_A_REFS=""; FX_B_REFS=""
}

# ── valores del escenario válido base ──────────────────────────────────────
_fx_defaults() {
  FX_BQ='`'
  FX_ID=notificaciones-v2
  FX_DIR=".sdd/$FX_ID"
  FX_OUTCOME=""; FX_RETRO=0; FX_USA_C=0; FX_REPARTO=1
  FX_SKILL_REVALIDA=1
  FX_V2=""; FX_FILA_HUERFANA=0; FX_FILA_DUP=0
  FX_BIT_VACIA=0; FX_BIT_DIR=""; FX_BIT_SED=""
  FX_LOCK=""

  FX_A_ST=done; FX_B_ST=done; FX_C_ST=done
  FX_A_PLANST=""; FX_B_PLANST=""; FX_C_PLANST=""
  FX_A_SHA=aaa1111; FX_B_SHA=bbb2222; FX_C_SHA=ccc3333
  FX_A_LOCALBASE=RED; FX_B_LOCALBASE=RED; FX_C_LOCALBASE=RED
  FX_A_DESPACHO=auto; FX_B_DESPACHO=auto; FX_C_DESPACHO=auto
  FX_A_COVERS="AC-1"; FX_B_COVERS="AC-2"; FX_C_COVERS="AC-5"
  FX_A_REFS="AC-3=V-C1=ok AC-4=V-C1=ok"; FX_B_REFS="AC-3=V-C1=ok"; FX_C_REFS=""

  FX_TAREAS="G1 C1 X1"
  FX_FILAS="G1 C1 X1"

  FX_G1_ID=G1; FX_G1_PHASE=gate; FX_G1_OWNER=equipo-arquitectura; FX_G1_ST=done
  FX_G1_WHAT="acordar el esquema del evento entre los dos equipos"
  FX_G1_DEPS=@empty@; FX_G1_COVERS=@empty@; FX_G1_DW=V-G1
  FX_G1_BLOCKS="servicio-b"; FX_G1_PART=@none@; FX_G1_BASE=NOT_APPLICABLE
  FX_G1_ANCLA="acuerdo-evento=v3"; FX_G1_SHAS=""; FX_G1_EVFILA=""; FX_G1_EVOBJ=""
  FX_G1_ESPERADO="el acuerdo declara el esquema del evento"
  FX_G1_OBSERVADO="el acuerdo declara el esquema del evento"
  FX_G1_EVIDENCIA=si; FX_G1_CIERRE=auto

  FX_C1_ID=C1; FX_C1_PHASE=closeout; FX_C1_OWNER=equipo-plataforma; FX_C1_ST=done
  FX_C1_WHAT="correr el flujo end-to-end con los dos servicios desplegados"
  FX_C1_DEPS="G1"; FX_C1_COVERS="AC-3, AC-4"; FX_C1_DW=V-C1
  FX_C1_BLOCKS=@none@; FX_C1_PART="AC-3=servicio-a,servicio-b;AC-4=servicio-a"; FX_C1_BASE=RED
  FX_C1_ANCLA=@none@; FX_C1_SHAS="servicio-a=aaa1111, servicio-b=bbb2222"
  FX_C1_EVFILA=""; FX_C1_EVOBJ=""
  FX_C1_ESPERADO="el receptor procesa el evento y responde 200"
  FX_C1_OBSERVADO="el receptor procesa el evento y responde 200"
  FX_C1_EVIDENCIA=si; FX_C1_CIERRE=auto

  FX_X1_ID=X1; FX_X1_PHASE=closeout; FX_X1_OWNER=equipo-datos; FX_X1_ST=done
  FX_X1_WHAT="archivar el acuerdo del evento en la wiki del equipo"
  FX_X1_DEPS=@empty@; FX_X1_COVERS=@empty@; FX_X1_DW=V-X1
  FX_X1_BLOCKS=@none@; FX_X1_PART=@none@; FX_X1_BASE=NOT_APPLICABLE
  FX_X1_ANCLA="wiki-acuerdo=v1"; FX_X1_SHAS=""; FX_X1_EVFILA=""; FX_X1_EVOBJ=""
  FX_X1_ESPERADO="el acuerdo quedó archivado en la wiki"
  FX_X1_OBSERVADO="el acuerdo quedó archivado en la wiki"
  FX_X1_EVIDENCIA=si; FX_X1_CIERRE=auto

  # Entrada extra que solo usa ID_DUPLICADO: repite un id ya tomado, y nada más.
  FX_D1_ID=C1; FX_D1_PHASE=closeout; FX_D1_OWNER=equipo-redes; FX_D1_ST=done
  FX_D1_WHAT="publicar el acuerdo en el catálogo interno"
  FX_D1_DEPS=@empty@; FX_D1_COVERS=@empty@; FX_D1_DW=V-D1
  FX_D1_BLOCKS=@none@; FX_D1_PART=@none@; FX_D1_BASE=NOT_APPLICABLE
  FX_D1_ANCLA="catalogo=v1"; FX_D1_SHAS=""; FX_D1_EVFILA=""; FX_D1_EVOBJ=""
  FX_D1_ESPERADO="el acuerdo figura en el catálogo"
  FX_D1_OBSERVADO="el acuerdo figura en el catálogo"
  FX_D1_EVIDENCIA=no; FX_D1_CIERRE=no
}

# ── materialización ────────────────────────────────────────────────────────
_fx_get() { eval "printf '%s' \"\${FX_${1}_${2}}\""; }
_fx_sed() { local f="$1"; shift; sed "$@" "$f" > "$f.fxtmp" && mv "$f.fxtmp" "$f"; }
# Lista YAML en línea a partir de una lista separada por comas, con sus dos centinelas.
_fx_lista() { case "$1" in @none@) return 1 ;; @empty@) printf '[]' ;; *) printf '[%s]' "$1" ;; esac; }
_fx_ts() { printf '2026-06-03T%02d:%02d:00-03:00' $((10 + FX_N / 60)) $((FX_N % 60)); }
_fx_repos_activos() { if [ "$FX_USA_C" = 1 ]; then printf 'a b c'; else printf 'a b'; fi; }
_fx_path() { case "$1" in a) printf 'servicio-a' ;; b) printf 'servicio-b' ;; c) printf 'servicio-c' ;; esac; }
_fx_plan() { printf '%s/%s/.plans/%s/plan.md' "$PWD" "$(_fx_path "$1")" "$FX_ID"; }

_fx_emitir() {
  FX_MANIFEST="$PWD/$FX_DIR/manifest.yml"
  FX_SPEC="$PWD/$FX_DIR/master-spec.md"
  FX_CONTRATO="$PWD/$FX_DIR/integracion.md"
  FX_BITACORA="$PWD/$FX_DIR/bitacora.md"
  FX_SKILL="$PWD/skill/SKILL.md"
  mkdir -p "$PWD/$FX_DIR" "$PWD/skill"
  local r
  for r in $(_fx_repos_activos); do mkdir -p "$PWD/$(_fx_path "$r")/.plans/$FX_ID"; done
  _fx_emitir_manifest > "$FX_MANIFEST"
  _fx_emitir_spec     > "$FX_SPEC"
  _fx_emitir_contrato > "$FX_CONTRATO"
  _fx_emitir_bitacora > "$FX_BITACORA"
  for r in $(_fx_repos_activos); do _fx_emitir_plan "$r" > "$(_fx_plan "$r")"; done
  _fx_emitir_skill    > "$FX_SKILL"
  [ -z "$FX_BIT_SED" ] || _fx_sed "$FX_BITACORA" "$FX_BIT_DIR $FX_BIT_SED"
  _fx_emitir_env
}

_fx_emitir_manifest() {
  local r t v
  printf 'id: %s\n' "$FX_ID"
  printf 'master_spec: %s/master-spec.md\n' "$FX_DIR"
  printf 'created_at: 2026-06-03T09:00:00-03:00\n'
  [ -z "$FX_OUTCOME" ] || printf 'outcome: %s\n' "$FX_OUTCOME"
  printf 'repos:\n'
  for r in $(_fx_repos_activos); do
    printf '  - path: %s\n' "$(_fx_path "$r")"
    printf '    branch: feature/%s-%s\n' "$FX_ID" "$(_fx_path "$r")"
    printf '    status: %s\n' "$(_fx_get "$(_fx_up "$r")" ST)"
    printf '    depends_on: []\n'
    printf '    covers_ac: [%s]\n' "$(_fx_get "$(_fx_up "$r")" COVERS)"
  done
  [ -n "$FX_TAREAS" ] || return 0
  printf 'orchestration_tasks:\n'
  for t in $FX_TAREAS; do
    printf '  - id: %s\n' "$(_fx_get "$t" ID)"
    printf '    phase: %s\n' "$(_fx_get "$t" PHASE)"
    printf '    what: %s\n' "$(_fx_get "$t" WHAT)"
    v=$(_fx_get "$t" OWNER)
    case "$v" in @none@) ;; @empty@) printf '    owner: ""\n' ;; *) printf '    owner: %s\n' "$v" ;; esac
    printf '    status: %s\n' "$(_fx_get "$t" ST)"
    v=$(_fx_lista "$(_fx_get "$t" DEPS)") && printf '    depends_on: %s\n' "$v"
    v=$(_fx_lista "$(_fx_get "$t" COVERS)") && printf '    covers_ac: %s\n' "$v"
    v=$(_fx_get "$t" DW)
    case "$v" in @none@) ;; @empty@) printf '    done_when: ""\n' ;; *) printf '    done_when: %s\n' "$v" ;; esac
    v=$(_fx_lista "$(_fx_get "$t" BLOCKS)") && printf '    blocks_repos: %s\n' "$v"
    _fx_emitir_participacion "$(_fx_get "$t" PART)"
  done
}
# El mapa AC → repos, con sus dos centinelas: ausente (sin la clave) y vacío, que en un mapa se
# escribe {} y no []. Las claves salen en el orden declarado, repetidas incluidas.
_fx_emitir_participacion() {
  local par ac repos
  case "$1" in
    @none@) return 0 ;;
    @empty@) printf '    participating_repos: {}\n'; return 0 ;;
  esac
  printf '    participating_repos:\n'
  local IFS=';'
  for par in $1; do
    ac=${par%%=*}; repos=${par#*=}
    printf '      %s: [%s]\n' "$ac" "$(printf '%s' "$repos" | sed 's/,/, /g')"
  done
}

_fx_emitir_spec() {
  printf '# Master Spec — notificaciones v2\n\n'
  printf '## Problema / Objetivo\nPublicar y consumir el evento de notificación entre los dos servicios.\n\n'
  printf '## Alcance\n- **Incluye:** el emisor, el receptor y el acuerdo del evento.\n'
  printf -- '- **No incluye:** los avisos por correo.\n\n'
  printf '## Criterios de aceptación\n'
  printf -- '- **AC-1 [repo-local]:** Given el emisor, When se crea una notificación, Then publica el evento.\n'
  printf -- '- **AC-2 [repo-local]:** Given el receptor, When llega el evento, Then lo procesa.\n'
  [ "$FX_USA_C" = 1 ] && printf -- '- **AC-5 [repo-local]:** Given el panel, When se consulta el histórico, Then lista las notificaciones.\n'
  if [ "$FX_RETRO" = 0 ]; then
    printf -- '- **AC-3 [integration]:** Given los dos servicios arriba, When se crea una notificación, Then el receptor la procesa y responde 200.\n'
    printf -- '- **AC-4 [integration]:** Given el acuerdo publicado, When se valida el esquema del evento, Then emisor y receptor coinciden.\n'
  fi
  printf '\n## Contratos entre servicios\n'
  printf -- '- **servicio-a expone:** evento `notificacion.creada {id, destinatario}`.\n'
  printf -- '- **servicio-b consume:** `notificacion.creada` desde el bus.\n\n'
  printf '## Anclas versionadas\n'
  printf -- '- `acuerdo-evento: v3`\n'
  printf -- '- `wiki-acuerdo: v1`\n'
  printf -- '- `catalogo: v1`\n\n'
  printf '## Reparto\n| AC | Repo(s) | Tipo |\n|---|---|---|\n'
  printf '| AC-1 | servicio-a | repo-local |\n| AC-2 | servicio-b | repo-local |\n'
  [ "$FX_USA_C" = 1 ] && printf '| AC-5 | servicio-c | repo-local |\n'
  if [ "$FX_RETRO" = 0 ]; then
    printf '| AC-3 | servicio-a + servicio-b | integration |\n| AC-4 | servicio-a | integration |\n'
  fi
  return 0
}

# El contrato de cierre de TODA tarea, con el esquema normativo de cross-implement: seis columnas y
# un registro de baseline por fila. El Requisito lleva la gramática del enlace tarea ↔ fila:
# `<id-tarea> — <what> [AC-n, AC-m]`, y `[—]` cuando la tarea no cubre ningún AC.
_fx_emitir_contrato() {
  printf '# Contrato de integración — %s\n\n' "$FX_ID"
  _fx_version_contrato v1 "$FX_FILAS"
  case "$FX_V2" in
    igual)  printf '\n'; _fx_version_contrato v2 "$FX_FILAS" ;;
    agrega) printf '\n'; _fx_version_contrato v2 "$FX_FILAS Z9" ;;
    quita)  printf '\n'; _fx_version_contrato v2 "$(printf '%s' "$FX_FILAS" | sed 's/ X1//')" ;;
  esac
}
_fx_version_contrato() {
  local ver="$1" filas="$2" t cov
  printf '## %s\n\n' "$ver"
  printf '| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |\n|---|---|---|---|---|---|\n'
  for t in $filas; do
    if [ "$t" = Z9 ]; then
      printf '| V-Z9 | Z9 — revisar el tablero de la orquestación [—] | inspección | `grep -c tablero notas.md` | `1` | NOT_APPLICABLE |\n'
      continue
    fi
    cov=$(_fx_get "$t" COVERS)
    case "$cov" in @empty@|@none@) cov='—' ;; esac
    printf '| V-%s | %s — %s [%s] | %s | %s | %s | %s |\n' \
      "$(_fx_get "$t" ID)" "$(_fx_get "$t" ID)" "$(_fx_get "$t" WHAT)" "$cov" \
      "$(_fx_evidencia_de "$t")" "$(_fx_comando_de "$t")" "$(_fx_get "$t" ESPERADO)" \
      "$(_fx_base_de "$t")"
    if [ "$FX_FILA_DUP" = 1 ] && [ "$t" = X1 ]; then
      printf '| V-X1-bis | X1 — %s [—] | inspección | `grep -c acuerdo wiki.md` | `1` | NOT_APPLICABLE |\n' \
        "$(_fx_get X1 WHAT)"
    fi
  done
  [ "$FX_FILA_HUERFANA" = 1 ] && \
    printf '| V-H9 | H9 — publicar el changelog de la orquestación [—] | inspección | `grep -c changelog notas.md` | `1` | NOT_APPLICABLE |\n'
  printf '\n### Baseline de %s\n' "$ver"
  printf '`hash_previo:` · `hash: 9b1c04e2`\n\n'
  for t in $filas; do
    if [ "$t" = Z9 ]; then
      printf -- '- `id: V-Z9` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00` · `justificación: la fila mira un tablero que este cambio no produce`\n'
      continue
    fi
    _fx_registro_baseline "V-$(_fx_get "$t" ID)" "$(_fx_base_de "$t")"
    if [ "$FX_FILA_DUP" = 1 ] && [ "$t" = X1 ]; then _fx_registro_baseline V-X1-bis NOT_APPLICABLE; fi
  done
  [ "$FX_FILA_HUERFANA" = 1 ] && _fx_registro_baseline V-H9 NOT_APPLICABLE
  return 0
}
_fx_registro_baseline() {
  printf -- '- `id: %s` · `commit: 4f2a9c1` · `timestamp: 2026-06-03T09:10:00-03:00`' "$1"
  case "$2" in
    NOT_APPLICABLE) printf ' · `justificación: la evidencia es un acuerdo entre equipos; no hay comando que ejecutar contra el código`' ;;
    GREEN_ALREADY)  printf ' · `adjudicación: already_satisfied`' ;;
  esac
  printf '\n'
}
_fx_base_de()      { local v; v=$(_fx_get "$1" BASE); printf '%s' "$v"; }
_fx_evidencia_de() { case "$1" in C1) printf 'manual' ;; *) printf 'inspección' ;; esac; }
_fx_comando_de()   {
  case "$1" in
    C1) printf 'desplegar los dos servicios y publicar una notificación' ;;
    G1) printf '`grep -c "^evento:" acuerdo.md`' ;;
    *)  printf '`grep -c acuerdo wiki.md`' ;;
  esac
}

# La bitácora se DERIVA del estado: cada transición materializada tiene su evento y ninguna otra.
# Así una mutación de estado no arrastra de regalo un `exito-sin-transicion`, y los fixtures que sí
# quieren romper esa correspondencia lo hacen con una edición explícita y visible (FX_BIT_SED).
_fx_emitir_bitacora() {
  [ "$FX_BIT_VACIA" = 1 ] && return 0
  local r p st t
  FX_N=0
  printf '# Bitácora de transiciones — %s\n\n' "$FX_ID"
  if [ "$FX_REPARTO" = 1 ]; then
    for r in $(_fx_repos_activos); do
      p=$(_fx_path "$r"); st=$(_fx_get "$(_fx_up "$r")" ST)
      case "$st" in
        planned) _fx_evento promover-repo orquestador "$p" rechazado ;;
        *)       _fx_evento promover-repo orquestador "$p" consumado ;;
      esac
    done
    for r in $(_fx_repos_activos); do
      p=$(_fx_path "$r"); st=$(_fx_get "$(_fx_up "$r")" ST)
      case "$(_fx_get "$(_fx_up "$r")" DESPACHO)" in
        no) continue ;;
        rechazado)  _fx_evento despachar-repo orquestador "$p" rechazado; continue ;;
        consumado)  _fx_evento despachar-repo orquestador "$p" consumado; continue ;;
      esac
      case "$st" in
        planned|blocked) _fx_evento despachar-repo orquestador "$p" rechazado ;;
        tasks-ready) ;;
        *)           _fx_evento despachar-repo orquestador "$p" consumado ;;
      esac
    done
  fi
  case "$FX_LOCK" in
    con-decision)  _fx_evento liberar-lock orquestador servicio-b consumado 'decision: excluir-repo' ;;
    sin-decision)  _fx_evento liberar-lock orquestador servicio-b consumado ;;
    rechazado)     _fx_evento liberar-lock orquestador servicio-b rechazado ;;
  esac
  for t in $FX_TAREAS; do
    [ "$(_fx_get "$t" ST)" = done ] || [ "$(_fx_get "$t" CIERRE)" = forzado ] || continue
    [ "$(_fx_get "$t" CIERRE)" = no ] && continue
    [ "$(_fx_get "$t" EVIDENCIA)" = si ] && _fx_evento_evidencia "$t"
    _fx_evento cerrar-tarea orquestador "$(_fx_get "$t" ID)" consumado
  done
  return 0
}
# La evidencia ata la tarea, su fila, la versión vigente del contrato y —según de qué esté hecha— el
# SHA de cada repo relevante o el ancla versionada equivalente.
_fx_evento_evidencia() {
  local t="$1" obj fila extra_sha extra_ancla ver actor
  obj=$(_fx_get "$t" EVOBJ); [ -n "$obj" ] || obj=$(_fx_get "$t" ID)
  # Un `owner` mutado a ausente o vacío es un defecto del manifest y no del evento: el actor de la
  # bitácora cae al orquestador para no arrastrar un segundo defecto a otro artefacto.
  actor=$(_fx_get "$t" OWNER)
  case "$actor" in @none@|@empty@|UNASSIGNED) actor=orquestador ;; esac
  fila=$(_fx_get "$t" EVFILA); [ -n "$fila" ] || fila="V-$(_fx_get "$t" ID)"
  # El evento SIEMPRE ancla a v1: cuando el contrato tiene una v2, la vigente dejó de ser la que
  # midió la evidencia, y esa es toda la diferencia entre FRESCURA_VERSION_ANTERIOR y su verde.
  ver=v1
  extra_sha=$(_fx_get "$t" SHAS); extra_ancla=$(_fx_get "$t" ANCLA)
  set -- "fila: $fila" "contrato: $ver"
  [ -n "$extra_sha" ] && set -- "$@" "sha: $extra_sha"
  [ "$extra_ancla" = @none@ ] || [ -z "$extra_ancla" ] || set -- "$@" "ancla: $extra_ancla"
  set -- "$@" "observado: $(_fx_get "$t" OBSERVADO)"
  _fx_evento ejecutar-evidencia "$actor" "$obj" consumado "$@"
}
_fx_evento() {
  local paso="$1" actor="$2" objeto="$3" res="$4" l x
  shift 4
  FX_N=$((FX_N + 1))
  l=$(printf -- '- %sid: %s%s · %spaso: %s%s · %sactor: %s%s · %sobjeto: %s%s · %sresultado: %s%s · %stimestamp: %s%s' \
        "$FX_BQ" "$FX_N" "$FX_BQ" "$FX_BQ" "$paso" "$FX_BQ" "$FX_BQ" "$actor" "$FX_BQ" \
        "$FX_BQ" "$objeto" "$FX_BQ" "$FX_BQ" "$res" "$FX_BQ" "$FX_BQ" "$(_fx_ts)" "$FX_BQ")
  for x in "$@"; do l="$l · $FX_BQ$x$FX_BQ"; done
  printf '%s\n' "$l"
}
_fx_up() { case "$1" in a) printf 'A' ;; b) printf 'B' ;; c) printf 'C' ;; esac; }

# El plan.md del repo: su contrato local lleva la fila de cada AC [repo-local] y, por cada AC
# [integration] en el que el repo participa, una referencia SOLO-LECTURA a la fila autoritativa.
_fx_emitir_plan() {
  local r="$1" u p st n ref ac fila modo
  u=$(_fx_up "$r"); p=$(_fx_path "$r")
  st=$(_fx_get "$u" PLANST); [ -n "$st" ] || st=$(_fx_get "$u" ST)
  printf -- '---\n'
  printf 'id: %s\nrepo: %s\nbranch: feature/%s-%s\n' "$FX_ID" "$p" "$FX_ID" "$p"
  printf 'base_commit: 0000000\nhead_sha: %s\nstatus: %s\n' "$(_fx_get "$u" SHA)" "$st"
  printf -- '---\n\n'
  printf '# Plan — %s (parte de %s)\n\n## Verification\n\n### v1\n\n' "$p" "$FX_ID"
  printf '| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |\n|---|---|---|---|---|---|\n'
  printf '| V1 | %s [repo-local] — el repo cumple su parte | test | `npm test` | 1 test, verde | %s |\n' \
    "$(_fx_get "$u" COVERS)" "$(_fx_get "$u" LOCALBASE)"
  n=1
  for ref in $(_fx_get "$u" REFS); do
    n=$((n + 1)); ac=${ref%%=*}; fila=${ref#*=}; modo=${fila##*=}; fila=${fila%%=*}
    case "$modo" in
      local) printf '| V%s | %s [integration] — el repo lo verifica de su lado | test | `npm test -- integracion` | 1 test, verde | RED |\n' "$n" "$ac" ;;
      na)    printf '| V%s | %s [integration] — cerrado en el contrato de integración | NOT_APPLICABLE | ver %s de integracion.md | se verifica en el contrato de integración | NOT_APPLICABLE |\n' "$n" "$ac" "$fila" ;;
      viejo) printf '| V%s | %s [integration] — cerrado en el contrato de integración | N/A: Fase 3 | ver %s de integracion.md | se verifica en el contrato de integración | N/A: Fase 3 |\n' "$n" "$ac" "$fila" ;;
      *)     printf '| V%s | %s [integration] — cerrado en el contrato de integración | N/A: orchestration-owned | ver %s de integracion.md | se verifica en el contrato de integración | N/A: orchestration-owned |\n' "$n" "$ac" "$fila" ;;
    esac
  done
  printf '\n#### Baseline de v1\n`hash_previo:` · `hash: 3c7f1ab0`\n\n'
  printf -- '- `id: V1` · `commit: 0000000` · `timestamp: 2026-06-03T09:20:00-03:00`\n'
  # Un registro por fila, también para las referencias: la asimetría entre tabla y baseline impide
  # congelar, y una fila de referencia sin registro dejaría el contrato del repo sin poder cerrarse.
  local i=1
  for ref in $(_fx_get "$u" REFS); do
    i=$((i + 1))
    printf -- '- `id: V%s` · `commit: 0000000` · `timestamp: 2026-06-03T09:20:00-03:00` · `justificación: la fila se cierra en el contrato de integración de la orquestación`\n' "$i"
  done
  return 0
}

# La copia del SKILL.md que consume `gate-fase-3`. Lleva la Fase 3 con su cláusula de revalidación,
# su tabla de precedencia y el vocabulario de `no verificado`; el único escenario rojo la reemplaza
# por la redacción vieja, que anclaba el congelado a la Fase 3.
_fx_emitir_skill() {
  printf '# sdd-orchestrator\n\n## Fase 3 · Cierre (centralizada, el usuario al mando)\n\n'
  printf -- '- Gate de apertura del contrato de integración: el contrato pasa su gate antes de la primera evidencia.\n'
  # La única diferencia entre el escenario válido y su rojo: la cláusula de revalidación contra la
  # redacción vieja, que anclaba el congelado a la Fase 3. Todo lo demás del documento es idéntico.
  if [ "$FX_SKILL_REVALIDA" = 1 ]; then
    printf -- '- La Fase 3 revalida la versión vigente del contrato antes de ejecutar evidencia.\n'
  else
    printf -- '- Congelarlo **antes** de ejecutar la primera evidencia.\n'
  fi
  printf -- '- Una tabla de precedencia produce el estado agregado como `ESTADO:<valor>` y nunca oculta el más grave.\n'
  printf -- '- Cada ejecución de evidencia y cada cierre de tarea registra su intento en la bitácora antes de materializarse.\n\n'
  printf '| # | Estado agregado | Cuándo |\n|---|---|---|\n'
  printf '| 1 | `ESTADO:no-verificado:repo-failed` | algún repo quedó en `failed` |\n'
  printf '| 2 | `ESTADO:no-verificado:repo-blocked` | algún repo quedó en `blocked` |\n'
  printf '| 3 | `ESTADO:no-verificado:gate-blocked` | alguna tarea `gate` quedó en `blocked` |\n'
  printf '| 4 | `ESTADO:en-curso` | algún repo sigue en marcha |\n'
  printf '| 5 | `ESTADO:no-verificado:integracion-pendiente` | queda una tarea de orquestación sin cerrar |\n'
  printf '| 6 | `ESTADO:done` | todo cerrado |\n\n'
  printf 'Una fila ausente, `BLOCKED` o `manual` pendiente produce no verificado.\n'
}

# Las seis entradas que declaran las guardas, en los dos dialectos. `$repos` va separado por
# espacios en POSIX y como ARREGLO en PowerShell.
_fx_emitir_env() {
  local r lista=""
  for r in $(_fx_repos_activos); do lista="$lista $(_fx_plan "$r")"; done
  lista=${lista# }
  { printf 'export repos="%s"\n' "$lista"
    printf 'export manifest="%s"\n' "$FX_MANIFEST"
    printf 'export master_spec="%s"\n' "$FX_SPEC"
    printf 'export contrato="%s"\n' "$FX_CONTRATO"
    printf 'export bitacora="%s"\n' "$FX_BITACORA"
    printf 'export skill_orq="%s"\n' "$FX_SKILL"
  } > "$PWD/env.sh"
  { printf '$repos = @('
    local sep=""
    for r in $(_fx_repos_activos); do printf "%s'%s'" "$sep" "$(_fx_plan "$r")"; sep=","; done
    printf ')\n'
    printf "\$manifest = '%s'\n" "$FX_MANIFEST"
    printf "\$master_spec = '%s'\n" "$FX_SPEC"
    printf "\$contrato = '%s'\n" "$FX_CONTRATO"
    printf "\$bitacora = '%s'\n" "$FX_BITACORA"
    printf "\$skill_orq = '%s'\n" "$FX_SKILL"
  } > "$PWD/env.ps1"
}

_fx_main "$@"
# @fin:fixtures-orquestacion
```

`@bloque:orchestration-model` valida el reparto contra la master-spec: es la guarda que caza el AC
`[integration]` sin dueño. Lee dos artefactos —el `manifest.yml` y la `master-spec.md`— y emite **un
solo diagnóstico por corrida**: el primero del orden en que están escritas sus comprobaciones, que
va de la identidad de la tarea a los enums, de ahí al grafo, después a la ubicación de cada AC y al
final al mapa de participación. Ese orden no es cosmético. Dos comprobaciones correctas pueden ver
el mismo defecto —un AC `[repo-local]` en el `covers_ac` de una tarea es, a la vez, una clave de
participación que no es `[integration]`— y emitir las dos convierte un defecto en dos hallazgos, sin
decir cuál de los dos es el que hay que arreglar.

```bash
# @bloque:orchestration-model
# Predicado: el modelo de orquestación cierra contra la master-spec: cada AC [integration] lo cubre
# exactamente una tarea, cada AC vive del lado que dice su etiqueta, el grafo de `depends_on` es
# acíclico y ejecutable, los campos obligatorios están con valores de su enum, y el mapa de
# participación tiene por claves exactamente el `covers_ac` de su tarea, con repos que existen.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica.
# Entradas: $manifest (el manifest.yml) y $master_spec (la master-spec.md)
for f in "$manifest" "$master_spec"; do
  [ -f "$f" ] || { printf 'ARNES:no existe %s\n' "$f" >&2; exit 99; }
done
awk -v mf="$manifest" '
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
# Un escalar YAML puede venir entrecomillado; `owner: ""` es un owner VACIO y no uno de dos
# caracteres. El apostrofo se arma con sprintf: el programa entero vive entre comillas simples.
function desnudo(s,   c) {
  s = trim(s)
  if (length(s) >= 2) {
    c = substr(s, 1, 1)
    if ((c == "\"" || c == Q) && substr(s, length(s), 1) == c) s = substr(s, 2, length(s) - 2)
  }
  return trim(s)
}
# El comentario de fin de línea NO es parte del valor. El esquema declara sus campos opcionales
# justamente así —`status: pending  # pending | in-progress | done | blocked`—, y sin esto ese
# manifest da un status fuera de enum y un `orchestration_tasks:` comentado desaparece entero: la
# guarda pasaría en verde sin haber leído una sola tarea. Un `#` abre comentario solo si arranca la
# línea o viene tras un espacio, que es la regla de YAML. En un valor entrecomillado el comentario
# empieza recién tras la comilla de cierre: cortar antes dejaba `owner: "" # sin dueño` como un
# owner con texto, y el owner vacío que el esquema prohíbe pasaba en verde.
function sincom(s,   c, i, n) {
  s = trim(s); c = substr(s, 1, 1)
  if (c == "\"" || c == Q) {
    n = length(s)
    for (i = 2; i <= n; i++) if (substr(s, i, 1) == c) return substr(s, 1, i)
    return s
  }
  if (match(s, /[ \t]#/)) s = substr(s, 1, RSTART - 1)
  return trim(s)
}
# Lista YAML en línea. `[]` es la lista vacía y no un elemento llamado "[]".
function lista(v, arr,   n, i, x, tmp) {
  delete arr
  v = trim(v); sub(/^\[/, "", v); sub(/\]$/, "", v); v = trim(v)
  if (v == "") return 0
  n = split(v, tmp, ","); x = 0
  for (i = 1; i <= n; i++) if (desnudo(tmp[i]) != "") arr[++x] = desnudo(tmp[i])
  return x
}
# Registra el PRIMER hallazgo y descarta los demás. Cada fixture rojo lleva una sola mutación, así
# que dos diagnósticos en una corrida significan que dos comprobaciones se pisaron sobre el mismo
# defecto — y el arnés exige exactamente una línea GUARD:, así que emitirlos todos pone en rojo la
# fila de cada uno.
function falla(m, ctx) { if (G == "") { G = m; CTX = ctx } }
function esc(t, c) { return has[t, c] ? raw[t, c] : "" }
function idlista(t, c,   s, i) {
  s = ""
  for (i = 1; i <= ln[t, c]; i++) s = s (i > 1 ? ", " : "") lv[t, c, i]
  return s
}

BEGIN { Q = sprintf("%c", 39) }

# ── master-spec: la etiqueta de cada AC ───────────────────────────────────────
# La etiqueta se lee del criterio, no de la tabla de Reparto: la tabla es una vista humana derivada
# y el propio documento dice que ante una discrepancia manda el manifest.
FNR == NR {
  if (match($0, /^-[ \t]*\*\*AC-[0-9]+[ \t]*\[[a-z-]+\]/)) {
    s = substr($0, RSTART, RLENGTH)
    ac = s; sub(/^-[ \t]*\*\*/, "", ac); sub(/[ \t]*\[.*$/, "", ac)
    tp = s; sub(/^.*\[/, "", tp); sub(/\].*$/, "", tp)
    tag[ac] = tp
    if (tp == "integration") intac[++nint] = ac
  }
  next
}

# Una línea entera de comentario no abre ni cierra nada: si reseteara la sección, un comentario en
# columna 0 partiría el manifest en dos y la mitad de abajo dejaría de leerse.
/^[ \t]*#/ { next }

# ── manifest: clave de primer nivel ───────────────────────────────────────────
/^[^ \t]/ {
  sec = ""
  if ($0 ~ /^repos:[ \t]*(#.*)?$/) sec = "repos"
  else if ($0 ~ /^orchestration_tasks:[ \t]*(#.*)?$/) sec = "tasks"
  next
}

sec == "repos" {
  if (match($0, /^[ \t]*-[ \t]*path:[ \t]*/)) {
    rpath[++nrep] = desnudo(sincom(substr($0, RSTART + RLENGTH))); esrepo[rpath[nrep]] = 1
    rcampo = "path"; next
  }
  if (!nrep) next
  if (match($0, /^[ \t]*covers_ac:[ \t]*/)) {
    rcampo = "covers_ac"
    rcovn[nrep] = lista(sincom(substr($0, RSTART + RLENGTH)), tmpa)
    for (i = 1; i <= rcovn[nrep]; i++) rcov[nrep, i] = tmpa[i]
    next
  }
  # Una lista en bloque es YAML igual de válido que una en línea, y acá no es cosmético: si el
  # `covers_ac` del repo se leyera vacío, el AC [integration] declarado del lado equivocado dejaría
  # de verse y la guarda daría verde sobre el defecto que existe para cazar.
  if (rcampo == "covers_ac" && $0 ~ /^[ \t]*-[ \t]/) {
    match($0, /^[ \t]*-[ \t]*/)
    rcov[nrep, ++rcovn[nrep]] = desnudo(sincom(substr($0, RSTART + RLENGTH))); next
  }
  if (match($0, /^[ \t]*[A-Za-z_][A-Za-z0-9_]*:/)) rcampo = "otro"
  next
}

# ── manifest: una entrada de orchestration_tasks ──────────────────────────────
# La columna manda: un campo de la tarea está a la altura de su `id:`, y todo lo que cuelgue más a
# la derecha pertenece al último campo abierto. Sin eso, una clave del mapa de participación es
# indistinguible de un campo de la tarea.
sec == "tasks" {
  ind = match($0, /[^ \t]/); if (ind == 0) next
  if (match($0, /^[ \t]*-[ \t]*id:[ \t]*/)) {
    nt++; indcampo = index($0, "id:"); campo = ""; enmapa = 0
    tid[nt] = desnudo(sincom(substr($0, RSTART + RLENGTH))); porid[tid[nt]]++
    pmodo[nt] = "none"
    next
  }
  if (!nt) next
  if (ind > indcampo) {
    if (enmapa) {
      if ($0 ~ /^[ \t]*-[ \t]/) {                                  # repo de la clave abierta
        match($0, /^[ \t]*-[ \t]*/)
        if (pn[nt] > 0) { j = pn[nt]; pv[nt, j, ++pvn[nt, j]] = desnudo(sincom(substr($0, RSTART + RLENGTH))) }
      } else if (match($0, /^[ \t]*[^ \t:]+:[ \t]*/)) {            # una clave del mapa
        k = substr($0, RSTART, RLENGTH); sub(/:[ \t]*$/, "", k)
        pk[nt, ++pn[nt]] = desnudo(k)
        pvn[nt, pn[nt]] = lista(sincom(substr($0, RSTART + RLENGTH)), tmpa)
        for (i = 1; i <= pvn[nt, pn[nt]]; i++) pv[nt, pn[nt], i] = tmpa[i]
      }
    } else if (campo != "" && $0 ~ /^[ \t]*-[ \t]/) {              # ítem de una lista en bloque
      match($0, /^[ \t]*-[ \t]*/)
      lv[nt, campo, ++ln[nt, campo]] = desnudo(sincom(substr($0, RSTART + RLENGTH)))
    }
    next
  }
  if (ind != indcampo) next
  if (!match($0, /^[ \t]*[A-Za-z_][A-Za-z0-9_]*:/)) next
  campo = substr($0, RSTART, RLENGTH); sub(/:$/, "", campo); campo = trim(campo)
  v = sincom(substr($0, RSTART + RLENGTH))
  has[nt, campo] = 1; raw[nt, campo] = desnudo(v); enmapa = 0
  if (campo == "participating_repos") {
    if (v == "") { pmodo[nt] = "map"; enmapa = 1 } else if (v ~ /^\{[ \t]*\}$/) pmodo[nt] = "empty"
    else pmodo[nt] = "map"
    next
  }
  if (campo == "depends_on" || campo == "covers_ac" || campo == "blocks_repos") {
    ln[nt, campo] = lista(v, tmpa)
    for (i = 1; i <= ln[nt, campo]; i++) lv[nt, campo, i] = tmpa[i]
  }
  next
}

END {
  # ── identidad ───────────────────────────────────────────────────────────────
  for (t = 1; t <= nt; t++)
    if (porid[tid[t]] > 1)
      falla("id-duplicado", "el id " tid[t] " abre " porid[tid[t]] " entradas de orchestration_tasks")

  # ── enums y campos obligatorios ─────────────────────────────────────────────
  for (t = 1; t <= nt; t++) {
    p = esc(t, "phase")
    if (p != "gate" && p != "closeout")
      falla("phase-fuera-de-enum", "la tarea " tid[t] " declara phase=[" p "], fuera de {gate, closeout}")
  }
  for (t = 1; t <= nt; t++) {
    st = esc(t, "status")
    if (st != "pending" && st != "in-progress" && st != "done" && st != "blocked")
      falla("status-fuera-de-enum", "la tarea " tid[t] " declara status=[" st "], fuera de {pending, in-progress, done, blocked}")
  }
  for (t = 1; t <= nt; t++) if (!has[t, "owner"])   falla("owner-ausente", "la tarea " tid[t] " no declara owner")
  for (t = 1; t <= nt; t++) if (has[t, "owner"] && esc(t, "owner") == "") falla("owner-vacio", "la tarea " tid[t] " declara owner vacío")
  for (t = 1; t <= nt; t++) if (!has[t, "done_when"]) falla("done_when-ausente", "la tarea " tid[t] " no declara done_when")
  for (t = 1; t <= nt; t++) if (has[t, "done_when"] && esc(t, "done_when") == "") falla("done_when-vacio", "la tarea " tid[t] " declara done_when vacío")

  # ── grafo: ejecutabilidad antes que forma ───────────────────────────────────
  for (t = 1; t <= nt; t++)
    if (has[t, "blocks_repos"] && esc(t, "phase") != "gate")
      falla("blocks_repos-en-closeout", "la tarea " tid[t] " es phase=" esc(t, "phase") " y declara blocks_repos: [" idlista(t, "blocks_repos") "]")
  for (t = 1; t <= nt; t++)
    for (i = 1; i <= ln[t, "depends_on"]; i++)
      if (!(lv[t, "depends_on", i] in porid))
        falla("depends_on-inexistente", "la tarea " tid[t] " depende de " lv[t, "depends_on", i] ", que ninguna orchestration_task declara")
  for (t = 1; t <= nt; t++)
    for (i = 1; i <= ln[t, "blocks_repos"]; i++)
      if (!(lv[t, "blocks_repos", i] in esrepo))
        falla("blocks_repos-inexistente", "la tarea " tid[t] " bloquea " lv[t, "blocks_repos", i] ", que no es un path de repos")
  # Un gate corre antes del fan-out y un closeout después: el grafo es acíclico y aun así inejecutable.
  for (t = 1; t <= nt; t++) {
    if (esc(t, "phase") != "gate") continue
    for (i = 1; i <= ln[t, "depends_on"]; i++)
      for (u = 1; u <= nt; u++)
        if (tid[u] == lv[t, "depends_on", i] && esc(u, "phase") == "closeout")
          falla("gate-depende-de-closeout", "el gate " tid[t] " depende de " tid[u] ", que es phase=closeout")
  }
  # Ciclo por eliminación sucesiva: lo que nunca queda sin dependencias vivas está en un ciclo. Las
  # referencias muertas no cuentan como arista — si no, una ref inexistente se leería como ciclo.
  for (t = 1; t <= nt; t++) vivo[t] = 1
  cambio = 1
  while (cambio) {
    cambio = 0
    for (t = 1; t <= nt; t++) {
      if (!vivo[t]) continue
      atado = 0
      for (i = 1; i <= ln[t, "depends_on"]; i++) {
        d = lv[t, "depends_on", i]
        if (d == tid[t]) { atado = 1; continue }
        for (u = 1; u <= nt; u++) if (vivo[u] && tid[u] == d) atado = 1
      }
      if (!atado) { vivo[t] = 0; cambio = 1 }
    }
  }
  ciclo = ""
  for (t = 1; t <= nt; t++) if (vivo[t]) ciclo = ciclo (ciclo == "" ? "" : ", ") tid[t]
  if (ciclo != "") falla("ciclo-en-depends_on", "estas tareas no llegan a ejecutarse nunca: " ciclo)

  # ── ubicación de cada AC, en los dos sentidos ───────────────────────────────
  for (r = 1; r <= nrep; r++)
    for (i = 1; i <= rcovn[r]; i++)
      if (tag[rcov[r, i]] == "integration")
        falla("integration-en-covers_ac-de-repo", "el repo " rpath[r] " declara " rcov[r, i] ", que la master-spec etiqueta [integration]")
  for (t = 1; t <= nt; t++)
    for (i = 1; i <= ln[t, "covers_ac"]; i++)
      if (tag[lv[t, "covers_ac", i]] == "repo-local")
        falla("repo-local-en-covers_ac-de-tarea", "la tarea " tid[t] " declara " lv[t, "covers_ac", i] ", que la master-spec etiqueta [repo-local]")

  # ── cardinalidad AC [integration] ↔ tarea de cierre ─────────────────────────
  nh = 0
  for (k = 1; k <= nint; k++) {
    ac = intac[k]; cub = ""; ncub = 0
    for (t = 1; t <= nt; t++)
      for (i = 1; i <= ln[t, "covers_ac"]; i++)
        if (lv[t, "covers_ac", i] == ac) { ncub++; cub = cub (cub == "" ? "" : ", ") tid[t]; break }
    if (ncub == 0) huerf[++nh] = ac
    if (ncub > 1) falla("ac-cubierto-por-dos-tareas", ac " lo cubren " ncub " tareas de cierre: " cub)
  }
  if (nh > 0 && G == "") {
    lst = ""
    for (i = 1; i <= nh; i++) lst = lst (i > 1 ? ", " : "") huerf[i]
    falla("ac-integration-huerfano", "ninguna orchestration_task cubre " lst)
    condetalle = 1
  }

  # ── participación: el mapa AC → repos ──────────────────────────────────────
  for (t = 1; t <= nt; t++) {
    if (ln[t, "covers_ac"] == 0) continue
    if (pmodo[t] == "none")
      falla("participacion-ausente-con-covers_ac", "la tarea " tid[t] " cubre [" idlista(t, "covers_ac") "] y no declara participating_repos")
    else if (pmodo[t] == "empty" || pn[t] == 0)
      falla("participacion-vacia-con-covers_ac", "la tarea " tid[t] " cubre [" idlista(t, "covers_ac") "] con participating_repos vacío")
  }
  for (t = 1; t <= nt; t++)
    for (j = 1; j <= pn[t]; j++)
      for (k = j + 1; k <= pn[t]; k++)
        if (pk[t, j] == pk[t, k])
          falla("participacion-clave-duplicada", "la tarea " tid[t] " repite la clave " pk[t, j] " en participating_repos")
  # Las dos direcciones de la misma cláusula: las claves son EXACTAMENTE el conjunto de covers_ac.
  # Una clave de más cuelga la participación de una tarea que no es su dueña; una de menos deja la
  # relación AC → repos indefinida, y ahí ninguna otra guarda la reclama.
  for (t = 1; t <= nt; t++)
    for (j = 1; j <= pn[t]; j++) {
      esta = 0
      for (i = 1; i <= ln[t, "covers_ac"]; i++) if (lv[t, "covers_ac", i] == pk[t, j]) esta = 1
      if (!esta) falla("participacion-clave-ajena", "la tarea " tid[t] " declara la clave " pk[t, j] ", que no está en su covers_ac [" idlista(t, "covers_ac") "]")
    }
  for (t = 1; t <= nt; t++) {
    if (pmodo[t] != "map") continue
    for (i = 1; i <= ln[t, "covers_ac"]; i++) {
      esta = 0
      for (j = 1; j <= pn[t]; j++) if (pk[t, j] == lv[t, "covers_ac", i]) esta = 1
      if (!esta) falla("participacion-ac-sin-clave", "la tarea " tid[t] " cubre " lv[t, "covers_ac", i] " y no le declara clave en participating_repos")
    }
  }
  for (t = 1; t <= nt; t++)
    for (j = 1; j <= pn[t]; j++)
      if (tag[pk[t, j]] != "integration")
        falla("participacion-ac-no-integration", "la clave " pk[t, j] " de la tarea " tid[t] " no es un AC [integration] de la master-spec")
  for (t = 1; t <= nt; t++)
    for (j = 1; j <= pn[t]; j++)
      for (i = 1; i <= pvn[t, j]; i++)
        if (!(pv[t, j, i] in esrepo))
          falla("participacion-repo-inexistente", "la clave " pk[t, j] " de la tarea " tid[t] " nombra " pv[t, j, i] ", que no es un path de repos")

  if (G == "") exit 0
  # El marcador va SOLO en su línea: el arnés lo compara entero, así que el dato medido vive abajo.
  print "GUARD:model " G
  print "  " CTX
  print "  manifest: " mf
  if (condetalle) for (i = 1; i <= nh; i++) print "DETALLE:" huerf[i]
  exit 1
}
' "$master_spec" "$manifest" >&2
exit $?
# @fin:orchestration-model
```

```powershell
# @bloque:orchestration-model-ps
# Predicado: el modelo de orquestación cierra contra la master-spec: cada AC [integration] lo cubre
# exactamente una tarea, cada AC vive del lado que dice su etiqueta, el grafo de `depends_on` es
# acíclico y ejecutable, los campos obligatorios están con valores de su enum, y el mapa de
# participación tiene por claves exactamente el `covers_ac` de su tarea, con repos que existen.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica.
# Entradas: $manifest (el manifest.yml) y $master_spec (la master-spec.md)
foreach ($f in @($manifest, $master_spec)) {
  if (-not (Test-Path -LiteralPath $f)) { [Console]::Error.WriteLine("ARNES:no existe $f"); exit 99 }
}
$Q = [char]39
# Un escalar YAML puede venir entrecomillado; `owner: ""` es un owner VACIO y no uno de dos
# caracteres.
function Desnudo($s) {
  $s = "$s".Trim()
  if ($s.Length -ge 2) {
    $c = $s[0]
    if (($c -eq '"' -or $c -eq $Q) -and $s[$s.Length - 1] -eq $c) { $s = $s.Substring(1, $s.Length - 2) }
  }
  return $s.Trim()
}
# El comentario de fin de línea NO es parte del valor. El esquema declara sus campos opcionales
# justamente así —`status: pending  # pending | in-progress | done | blocked`—, y sin esto ese
# manifest da un status fuera de enum y un `orchestration_tasks:` comentado desaparece entero: la
# guarda pasaría en verde sin haber leído una sola tarea. Un `#` abre comentario solo si arranca la
# línea o viene tras un espacio, que es la regla de YAML. En un valor entrecomillado el comentario
# empieza recién tras la comilla de cierre: cortar antes dejaba `owner: "" # sin dueño` como un
# owner con texto, y el owner vacío que el esquema prohíbe pasaba en verde.
function Sincom($s) {
  $s = "$s".Trim()
  if ($s.Length -gt 0 -and ($s[0] -eq '"' -or $s[0] -eq $Q)) {
    $cierre = $s.IndexOf($s[0], 1)
    if ($cierre -ge 0) { return $s.Substring(0, $cierre + 1) }
    return $s
  }
  $m = [regex]::Match($s, '[ \t]#')
  if ($m.Success) { $s = $s.Substring(0, $m.Index) }
  return $s.Trim()
}
# Lista YAML en línea. `[]` es la lista vacía y no un elemento llamado "[]".
# La coma del `return` NO es adorno: `return @()` devuelve $null, y un `+=` sobre ese $null produce
# una CADENA en vez de una lista de dos elementos — un `covers_ac` en bloque terminaba siendo
# "AC-1AC-3" y ningún AC se reconocía. Con la coma vuelve el arreglo, vacío incluido.
function Lista($v) {
  $v = "$v".Trim()
  if ($v.StartsWith('[')) { $v = $v.Substring(1) }
  if ($v.EndsWith(']')) { $v = $v.Substring(0, $v.Length - 1) }
  $v = $v.Trim()
  if ($v -eq '') { return , @() }
  return , @($v -split ',' | ForEach-Object { Desnudo $_ } | Where-Object { $_ -ne '' })
}
# Registra el PRIMER hallazgo y descarta los demás. Cada fixture rojo lleva una sola mutación, así
# que dos diagnósticos en una corrida significan que dos comprobaciones se pisaron sobre el mismo
# defecto — y el arnés exige exactamente una línea GUARD:, así que emitirlos todos pone en rojo la
# fila de cada uno.
$G = ''; $CTX = ''
function Falla($m, $ctx) { if ($script:G -eq '') { $script:G = $m; $script:CTX = $ctx } }
function Ids($xs) { return ($xs -join ', ') }
# Un campo que la tarea no declara vale cadena vacía, y una lista que no declara vale lista vacía:
# la diferencia entre ausente y vacío se decide con `has`, no con el tipo de lo que devuelven.
function Esc($t, $c) { if ($t.has[$c]) { return "$($t.raw[$c])" } else { return '' } }
function Lst($t, $c) { if ($t.lst.ContainsKey($c)) { return , @($t.lst[$c]) } else { return , @() } }

# ── master-spec: la etiqueta de cada AC ───────────────────────────────────────
# La etiqueta se lee del criterio, no de la tabla de Reparto: la tabla es una vista humana derivada
# y el propio documento dice que ante una discrepancia manda el manifest.
# Diccionarios ORDINALES y comparadores `-c*`: los arreglos de awk se indexan por bytes y
# su `==` distingue mayúsculas. Una hashtable `@{}` y los operadores por defecto de .NET no,
# así que `g1` pasaría por la tarea `G1`, `Servicio-A` por el repo `servicio-a` y `Gate` por
# el `gate` del enum — y en la otra dirección, `g1` y `G1` contarían como el mismo id.
$tag = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
$intac = @()
foreach ($ln in (Get-Content -LiteralPath $master_spec)) {
  if ($ln -match '^-[ \t]*\*\*(AC-[0-9]+)[ \t]*\[([a-z-]+)\]') {
    $tag[$Matches[1]] = $Matches[2]
    if ($Matches[2] -ceq 'integration') { $intac += $Matches[1] }
  }
}

# ── manifest ──────────────────────────────────────────────────────────────────
# La columna manda: un campo de la tarea está a la altura de su `id:`, y todo lo que cuelgue más a
# la derecha pertenece al último campo abierto. Sin eso, una clave del mapa de participación es
# indistinguible de un campo de la tarea.
$repos_ = @(); $tareas = @()
$porid = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
$sec = ''; $t = $null; $indcampo = 0; $campo = ''; $enmapa = $false
foreach ($ln in (Get-Content -LiteralPath $manifest)) {
  # Una línea entera de comentario no abre ni cierra nada: si reseteara la sección, un comentario en
  # columna 0 partiría el manifest en dos y la mitad de abajo dejaría de leerse.
  if ($ln -match '^[ \t]*#') { continue }
  if ($ln -match '^[^ \t]') {
    $sec = ''
    if ($ln -match '^repos:[ \t]*(#.*)?$') { $sec = 'repos' }
    elseif ($ln -match '^orchestration_tasks:[ \t]*(#.*)?$') { $sec = 'tasks' }
    continue
  }
  if ($ln.Trim() -eq '') { continue }
  $ind = ($ln -replace '^([ \t]*).*$', '$1').Length + 1
  if ($sec -eq 'repos') {
    if ($ln -match '^[ \t]*-[ \t]*path:[ \t]*(.*)$') {
      $repos_ += , @{ path = (Desnudo (Sincom $Matches[1])); covers = @() }; $rcampo = 'path'
    } elseif ($repos_.Count -eq 0) {
      continue
    } elseif ($ln -match '^[ \t]*covers_ac:[ \t]*(.*)$') {
      $rcampo = 'covers_ac'; $repos_[$repos_.Count - 1].covers = Lista (Sincom $Matches[1])
    } elseif ($rcampo -eq 'covers_ac' -and $ln -match '^[ \t]*-[ \t](.*)$') {
      # Una lista en bloque es YAML igual de válido que una en línea, y acá no es cosmético: si el
      # `covers_ac` del repo se leyera vacío, el AC [integration] declarado del lado equivocado
      # dejaría de verse y la guarda daría verde sobre el defecto que existe para cazar.
      $repos_[$repos_.Count - 1].covers += (Desnudo (Sincom $Matches[1]))
    } elseif ($ln -match '^[ \t]*[A-Za-z_][A-Za-z0-9_]*:') {
      $rcampo = 'otro'
    }
    continue
  }
  if ($sec -ne 'tasks') { continue }
  if ($ln -match '^[ \t]*-[ \t]*id:[ \t]*(.*)$') {
    $t = @{ id = (Desnudo (Sincom $Matches[1])); has = @{}; raw = @{}; lst = @{}; pmodo = 'none'; pk = @(); pv = @() }
    $tareas += , $t
    if ($porid.ContainsKey($t.id)) { $porid[$t.id] = $porid[$t.id] + 1 } else { $porid[$t.id] = 1 }
    $indcampo = $ln.IndexOf('id:') + 1; $campo = ''; $enmapa = $false
    continue
  }
  if ($null -eq $t) { continue }
  if ($ind -gt $indcampo) {
    if ($enmapa) {
      if ($ln -match '^[ \t]*-[ \t](.*)$') {                          # repo de la clave abierta
        if ($t.pk.Count -gt 0) { $t.pv[$t.pv.Count - 1] += (Desnudo (Sincom $Matches[1])) }
      } elseif ($ln -match '^[ \t]*([^ \t:]+):[ \t]*(.*)$') {          # una clave del mapa
        $t.pk += (Desnudo $Matches[1]); $t.pv += , (Lista (Sincom $Matches[2]))
      }
    } elseif ($campo -ne '' -and $ln -match '^[ \t]*-[ \t](.*)$') {    # ítem de una lista en bloque
      $t.lst[$campo] = (Lst $t $campo) + (Desnudo (Sincom $Matches[1]))
    }
    continue
  }
  if ($ind -ne $indcampo) { continue }
  if ($ln -notmatch '^[ \t]*([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$') { continue }
  $campo = $Matches[1]; $v = Sincom $Matches[2]
  $t.has[$campo] = $true; $t.raw[$campo] = (Desnudo $v); $enmapa = $false
  if ($campo -eq 'participating_repos') {
    if ($v -eq '') { $t.pmodo = 'map'; $enmapa = $true }
    elseif ($v -match '^\{[ \t]*\}$') { $t.pmodo = 'empty' }
    else { $t.pmodo = 'map' }
    continue
  }
  if ($campo -eq 'depends_on' -or $campo -eq 'covers_ac' -or $campo -eq 'blocks_repos') {
    $t.lst[$campo] = Lista $v
  }
}

# ── identidad ─────────────────────────────────────────────────────────────────
foreach ($t in $tareas) {
  if ($porid[$t.id] -gt 1) { Falla 'id-duplicado' "el id $($t.id) abre $($porid[$t.id]) entradas de orchestration_tasks" }
}

# ── enums y campos obligatorios ───────────────────────────────────────────────
foreach ($t in $tareas) {
  $p = Esc $t 'phase'
  if ($p -cne 'gate' -and $p -cne 'closeout') { Falla 'phase-fuera-de-enum' "la tarea $($t.id) declara phase=[$p], fuera de {gate, closeout}" }
}
foreach ($t in $tareas) {
  $st = Esc $t 'status'
  if ($st -cne 'pending' -and $st -cne 'in-progress' -and $st -cne 'done' -and $st -cne 'blocked') {
    Falla 'status-fuera-de-enum' "la tarea $($t.id) declara status=[$st], fuera de {pending, in-progress, done, blocked}"
  }
}
foreach ($t in $tareas) { if (-not $t.has['owner']) { Falla 'owner-ausente' "la tarea $($t.id) no declara owner" } }
foreach ($t in $tareas) { if ($t.has['owner'] -and (Esc $t 'owner') -eq '') { Falla 'owner-vacio' "la tarea $($t.id) declara owner vacío" } }
foreach ($t in $tareas) { if (-not $t.has['done_when']) { Falla 'done_when-ausente' "la tarea $($t.id) no declara done_when" } }
foreach ($t in $tareas) { if ($t.has['done_when'] -and (Esc $t 'done_when') -eq '') { Falla 'done_when-vacio' "la tarea $($t.id) declara done_when vacío" } }

# ── grafo: ejecutabilidad antes que forma ─────────────────────────────────────
foreach ($t in $tareas) {
  if ($t.has['blocks_repos'] -and (Esc $t 'phase') -cne 'gate') {
    Falla 'blocks_repos-en-closeout' "la tarea $($t.id) es phase=$(Esc $t 'phase') y declara blocks_repos: [$(Ids (Lst $t 'blocks_repos'))]"
  }
}
foreach ($t in $tareas) {
  foreach ($d in (Lst $t 'depends_on')) {
    if (-not $porid.ContainsKey($d)) { Falla 'depends_on-inexistente' "la tarea $($t.id) depende de $d, que ninguna orchestration_task declara" }
  }
}
$espath = [Collections.Generic.Dictionary[string, bool]]::new([StringComparer]::Ordinal)
foreach ($r in $repos_) { $espath[$r.path] = $true }
foreach ($t in $tareas) {
  foreach ($b in (Lst $t 'blocks_repos')) {
    if (-not $espath.ContainsKey($b)) { Falla 'blocks_repos-inexistente' "la tarea $($t.id) bloquea $b, que no es un path de repos" }
  }
}
# Un gate corre antes del fan-out y un closeout después: el grafo es acíclico y aun así inejecutable.
foreach ($t in $tareas) {
  if ((Esc $t 'phase') -cne 'gate') { continue }
  foreach ($d in (Lst $t 'depends_on')) {
    foreach ($u in $tareas) {
      if ($u.id -ceq $d -and (Esc $u 'phase') -ceq 'closeout') { Falla 'gate-depende-de-closeout' "el gate $($t.id) depende de $($u.id), que es phase=closeout" }
    }
  }
}
# Ciclo por eliminación sucesiva: lo que nunca queda sin dependencias vivas está en un ciclo. Las
# referencias muertas no cuentan como arista — si no, una ref inexistente se leería como ciclo.
$vivos = @(); foreach ($t in $tareas) { $vivos += $true }
$cambio = $true
while ($cambio) {
  $cambio = $false
  for ($i = 0; $i -lt $tareas.Count; $i++) {
    if (-not $vivos[$i]) { continue }
    $atado = $false
    foreach ($d in (Lst $tareas[$i] 'depends_on')) {
      if ($d -ceq $tareas[$i].id) { $atado = $true; continue }
      for ($j = 0; $j -lt $tareas.Count; $j++) { if ($vivos[$j] -and $tareas[$j].id -ceq $d) { $atado = $true } }
    }
    if (-not $atado) { $vivos[$i] = $false; $cambio = $true }
  }
}
$ciclo = @()
for ($i = 0; $i -lt $tareas.Count; $i++) { if ($vivos[$i]) { $ciclo += $tareas[$i].id } }
if ($ciclo.Count -gt 0) { Falla 'ciclo-en-depends_on' "estas tareas no llegan a ejecutarse nunca: $(Ids $ciclo)" }

# ── ubicación de cada AC, en los dos sentidos ─────────────────────────────────
foreach ($r in $repos_) {
  foreach ($ac in $r.covers) {
    if ($tag[$ac] -ceq 'integration') { Falla 'integration-en-covers_ac-de-repo' "el repo $($r.path) declara $ac, que la master-spec etiqueta [integration]" }
  }
}
foreach ($t in $tareas) {
  foreach ($ac in (Lst $t 'covers_ac')) {
    if ($tag[$ac] -ceq 'repo-local') { Falla 'repo-local-en-covers_ac-de-tarea' "la tarea $($t.id) declara $ac, que la master-spec etiqueta [repo-local]" }
  }
}

# ── cardinalidad AC [integration] ↔ tarea de cierre ───────────────────────────
$huerf = @(); $condetalle = $false
foreach ($ac in $intac) {
  $cub = @()
  foreach ($t in $tareas) { if ((Lst $t 'covers_ac') -ccontains $ac) { $cub += $t.id } }
  if ($cub.Count -eq 0) { $huerf += $ac }
  if ($cub.Count -gt 1) { Falla 'ac-cubierto-por-dos-tareas' "$ac lo cubren $($cub.Count) tareas de cierre: $(Ids $cub)" }
}
if ($huerf.Count -gt 0 -and $G -eq '') {
  Falla 'ac-integration-huerfano' "ninguna orchestration_task cubre $(Ids $huerf)"
  $condetalle = $true
}

# ── participación: el mapa AC → repos ─────────────────────────────────────────
foreach ($t in $tareas) {
  if ((Lst $t 'covers_ac').Count -eq 0) { continue }
  if ($t.pmodo -eq 'none') {
    Falla 'participacion-ausente-con-covers_ac' "la tarea $($t.id) cubre [$(Ids (Lst $t 'covers_ac'))] y no declara participating_repos"
  } elseif ($t.pmodo -eq 'empty' -or $t.pk.Count -eq 0) {
    Falla 'participacion-vacia-con-covers_ac' "la tarea $($t.id) cubre [$(Ids (Lst $t 'covers_ac'))] con participating_repos vacío"
  }
}
foreach ($t in $tareas) {
  for ($j = 0; $j -lt $t.pk.Count; $j++) {
    for ($k = $j + 1; $k -lt $t.pk.Count; $k++) {
      if ($t.pk[$j] -ceq $t.pk[$k]) { Falla 'participacion-clave-duplicada' "la tarea $($t.id) repite la clave $($t.pk[$j]) en participating_repos" }
    }
  }
}
# Las dos direcciones de la misma cláusula: las claves son EXACTAMENTE el conjunto de covers_ac.
# Una clave de más cuelga la participación de una tarea que no es su dueña; una de menos deja la
# relación AC → repos indefinida, y ahí ninguna otra guarda la reclama.
foreach ($t in $tareas) {
  foreach ($k in $t.pk) {
    if (-not ((Lst $t 'covers_ac') -ccontains $k)) {
      Falla 'participacion-clave-ajena' "la tarea $($t.id) declara la clave $k, que no está en su covers_ac [$(Ids (Lst $t 'covers_ac'))]"
    }
  }
}
foreach ($t in $tareas) {
  if ($t.pmodo -ne 'map') { continue }
  foreach ($ac in (Lst $t 'covers_ac')) {
    if (-not ($t.pk -ccontains $ac)) { Falla 'participacion-ac-sin-clave' "la tarea $($t.id) cubre $ac y no le declara clave en participating_repos" }
  }
}
foreach ($t in $tareas) {
  foreach ($k in $t.pk) {
    if ($tag[$k] -cne 'integration') { Falla 'participacion-ac-no-integration' "la clave $k de la tarea $($t.id) no es un AC [integration] de la master-spec" }
  }
}
foreach ($t in $tareas) {
  for ($j = 0; $j -lt $t.pk.Count; $j++) {
    foreach ($p in @($t.pv[$j])) {
      if (-not $espath.ContainsKey($p)) { Falla 'participacion-repo-inexistente' "la clave $($t.pk[$j]) de la tarea $($t.id) nombra $p, que no es un path de repos" }
    }
  }
}

if ($G -eq '') { exit 0 }
# El marcador va SOLO en su línea: el arnés lo compara entero, así que el dato medido vive abajo.
# `[Console]::Error.WriteLine` y no `Write-Error`: los eventos van por stderr —es donde los lee
# el arnés de paridad—, pero el renderizado de un ErrorRecord antepone su propio prefijo y la
# línea deja de empezar por GUARD:. Escribir crudo en el canal da las dos cosas.
[Console]::Error.WriteLine("GUARD:model $G")
[Console]::Error.WriteLine("  $CTX")
[Console]::Error.WriteLine("  manifest: $manifest")
if ($condetalle) { foreach ($ac in $huerf) { [Console]::Error.WriteLine("DETALLE:$ac") } }
exit 1
# @fin:orchestration-model-ps
```

`@bloque:orchestration-contract` valida la otra mitad del reparto: el **enlace tarea ↔ fila**. Lee el
`manifest.yml` y el contrato de integración, y no vuelve a comprobar nada de la **forma** del
contrato —la cabecera de seis columnas, la consecutividad de las versiones y la cadena de
integridad ya las valida `cross-implement/contrato-verificacion.md`, que es su dueño—. Lo que mira
es lo que solo se ve cruzando los dos artefactos: que cada tarea tenga su fila y solo una, que
ninguna fila cierre algo que nadie pidió, que `v1` haya nacido completo y que ninguna versión
posterior toque el conjunto de IDs.

Las tres clases de cierre tienen marcador propio por lo que AC-8 existe para impedir. Materializar
en la Fase 1 **solo las filas de los gates** deja el contrato sin dónde probar los cierres, y como
el esquema canónico declara **invariante el conjunto de IDs entre versiones**, agregarlas después es
imposible: no es una demora, es un contrato que ya no se puede completar. La clase `gate` no lleva
marcador propio porque su ausencia no es ese defecto: la caza la cardinalidad, como cualquier otra
tarea sin fila.

```bash
# @bloque:orchestration-contract
# Predicado: el contrato de integración cierra contra las tareas del manifest: cada tarea posee
# exactamente una fila de v1 y ninguna fila queda huérfana, v1 aloja las tres clases de cierre
# —gate, closeout y auxiliar—, el baseline de toda fila está resuelto, y ninguna versión posterior
# agrega ni quita IDs.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica.
# Entradas: $manifest (el manifest.yml) y $contrato (el integracion.md de la orquestación)
for f in "$manifest" "$contrato"; do
  [ -f "$f" ] || { printf 'ARNES:no existe %s\n' "$f" >&2; exit 99; }
done
awk -v cf="$contrato" '
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
# Las mismas dos razones que en @bloque:orchestration-model, donde están explicadas: un escalar YAML
# puede venir entrecomillado —`done_when: ""` es vacío y no dos caracteres— y el comentario de fin de
# línea no es parte del valor, que es como el esquema declara sus campos opcionales.
function desnudo(s,   c) {
  s = trim(s)
  if (length(s) >= 2) {
    c = substr(s, 1, 1)
    if ((c == "\"" || c == Q) && substr(s, length(s), 1) == c) s = substr(s, 2, length(s) - 2)
  }
  return trim(s)
}
function sincom(s,   c, i, n) {
  s = trim(s); c = substr(s, 1, 1)
  if (c == "\"" || c == Q) {
    n = length(s)
    for (i = 2; i <= n; i++) if (substr(s, i, 1) == c) return substr(s, 1, i)
    return s
  }
  if (match(s, /[ \t]#/)) s = substr(s, 1, RSTART - 1)
  return trim(s)
}
# Cuántos elementos tiene una lista YAML en línea. `[]` es la lista vacía y no un elemento llamado
# "[]": de esa diferencia depende reconocer a una tarea auxiliar.
function nlista(v,   n, i, x, tmp) {
  v = trim(v); sub(/^\[/, "", v); sub(/\]$/, "", v); v = trim(v)
  if (v == "") return 0
  n = split(v, tmp, ","); x = 0
  for (i = 1; i <= n; i++) if (desnudo(tmp[i]) != "") x++
  return x
}
# Registra el PRIMER hallazgo y descarta los demás. Cada fixture rojo lleva una sola mutación, así
# que dos diagnósticos en una corrida significan que dos comprobaciones se pisaron sobre el mismo
# defecto — y el arnés exige exactamente una línea GUARD:, así que emitirlos todos pone en rojo la
# fila de cada uno.
function falla(m, ctx) { if (G == "") { G = m; CTX = ctx } }
# El enlace fila → tarea lo declara el `Requisito`, cuya gramática es `<id-tarea> — <what> [AC-n]`.
# El guión se compara por bytes y NO dentro de una clase de caracteres: `—` ocupa tres bytes y un
# awk que cuente bytes matchearía solo el primero, dejando huérfana a una fila bien escrita.
# El id se compara como prefijo y con el separador pegado: `index()` a secas daba por dueña de
# `X12 — …` a la tarea `X1`.
function duenia(req, id,   resto) {
  if (index(req, id) != 1) return 0
  resto = substr(req, length(id) + 1)
  if (resto !~ /^[ \t]/) return 0
  sub(/^[ \t]+/, "", resto)
  return (index(resto, DASH " ") == 1 || index(resto, "- ") == 1)
}
function filasde(t,   s, k) {
  s = ""
  for (k = 1; k <= fn[iv1]; k++) if (own[k, t]) s = s (s == "" ? "" : ", ") fid[iv1, k]
  return s
}
function lista_ids(a, n,   s, i) {
  s = ""
  for (i = 1; i <= n; i++) s = s (i > 1 ? ", " : "") a[i]
  return s
}

BEGIN { Q = sprintf("%c", 39); DASH = "—" }

# ── manifest: id, phase, done_when y si covers_ac está vacía ──────────────────
# La columna manda, igual que en @bloque:orchestration-model: un campo de la tarea está a la altura
# de su `id:`, y lo que cuelgue más a la derecha pertenece al último campo abierto. Sin eso, una
# clave del mapa de participación sería indistinguible de un campo de la tarea.
FNR == NR {
  if ($0 ~ /^[ \t]*#/) next
  if ($0 ~ /^[^ \t]/) {
    sec = ($0 ~ /^orchestration_tasks:[ \t]*(#.*)?$/) ? "tasks" : ""
    next
  }
  if (sec != "tasks") next
  ind = match($0, /[^ \t]/); if (ind == 0) next
  if (match($0, /^[ \t]*-[ \t]*id:[ \t]*/)) {
    nt++; indcampo = index($0, "id:"); campo = ""
    tid[nt] = desnudo(sincom(substr($0, RSTART + RLENGTH)))
    next
  }
  if (!nt) next
  # Una lista en bloque es YAML igual de válido que una en línea: un `covers_ac` escrito así se
  # leería vacío, y una tarea que cubre AC pasaría por auxiliar.
  if (ind > indcampo) {
    if (campo == "covers_ac" && $0 ~ /^[ \t]*-[ \t]/) ncov[nt]++
    next
  }
  if (ind != indcampo) next
  if (!match($0, /^[ \t]*[A-Za-z_][A-Za-z0-9_]*:/)) next
  campo = substr($0, RSTART, RLENGTH); sub(/:$/, "", campo); campo = trim(campo)
  v = sincom(substr($0, RSTART + RLENGTH))
  if (campo == "phase") tph[nt] = desnudo(v)
  else if (campo == "done_when") tdw[nt] = desnudo(v)
  else if (campo == "covers_ac") ncov[nt] = nlista(v)
  next
}

# ── contrato: una tabla por versión ───────────────────────────────────────────
# `### Baseline de vN` no abre una versión: el encabezado tiene que terminar en el número.
{
  if (match($0, /^#+[ \t]*v[0-9]+[ \t]*$/)) {
    s = $0; sub(/^#+[ \t]*v/, "", s)
    nv++; vnum[nv] = trim(s) + 0; ver = nv
    next
  }
  if (!ver) next
  if ($0 !~ /^[ \t]*\|/) next
  if ($0 ~ /^[ \t]*\|[ \t]*ID[ \t]*\|/) next
  if ($0 ~ /^[ \t]*\|[-: \t|]+\|[ \t]*$/) next
  # El baseline se lee desde el final y no por número de columna: la fila termina en `|`, así que la
  # última columna es la penúltima celda. Que las columnas sean seis y estén en su orden lo valida el
  # contrato canónico, no este bloque.
  n = split($0, c, "[|]")
  if (n < 4) next
  k = ++fn[ver]
  fid[ver, k] = trim(c[2]); freq[ver, k] = trim(c[3]); fbase[ver, k] = trim(c[n - 1])
  next
}

END {
  # La versión inicial se busca por su NÚMERO: es la que AC-8 exige completa, y leerla por posición
  # la confundiría con la primera que aparezca escrita.
  iv1 = 0
  for (i = 1; i <= nv; i++) if (vnum[i] == 1) iv1 = i

  # ── enlace tarea ↔ fila ─────────────────────────────────────────────────────
  # Las dos mitades del enlace suman: el `Requisito` nombra la tarea y el `done_when` nombra la fila.
  # Con una sola, dos filas que cierran la misma tarea pasan por una fila huérfana; que las dos
  # coincidan entre sí lo exige AC-9, y lo valida @bloque:orchestration-state.
  for (k = 1; k <= fn[iv1]; k++)
    for (t = 1; t <= nt; t++)
      if (duenia(freq[iv1, k], tid[t]) || (tdw[t] != "" && fid[iv1, k] == tdw[t])) {
        own[k, t] = 1; nfila[t]++; ndue[k]++
      }

  # ── las clases de cierre que v1 tiene que alojar ────────────────────────────
  # Una auxiliar es un cierre SIN AC propio, así que es también una closeout. Medir la clase auxiliar
  # como "covers_ac vacía" a secas la daría por presente con la fila de un gate que no cubre ningún
  # AC, y el contrato que nace sin el cierre de la auxiliar pasaría en verde.
  nsc = 0; nsa = 0
  for (t = 1; t <= nt; t++) {
    if (tph[t] != "closeout") continue
    hayclo = 1; if (nfila[t] > 0) conclo = 1; else sinclo[++nsc] = tid[t]
    if (ncov[t] != 0) continue
    hayaux = 1; if (nfila[t] > 0) conaux = 1; else sinaux[++nsa] = tid[t]
  }
  if (hayclo && !conclo)
    falla("fila-closeout-ausente", "v1 no aloja el cierre de ninguna tarea phase=closeout; sin fila: " lista_ids(sinclo, nsc))
  if (hayaux && !conaux)
    falla("fila-auxiliar-ausente", "v1 no aloja el cierre de ninguna tarea auxiliar; sin fila: " lista_ids(sinaux, nsa))

  # ── cardinalidad: exactamente una fila por tarea, ninguna fila huérfana ─────
  for (t = 1; t <= nt; t++)
    if (nfila[t] == 0)
      falla("tarea-sin-fila", "la tarea " tid[t] " no tiene fila en v1 (done_when: " (tdw[t] == "" ? "—" : tdw[t]) ")")
  for (t = 1; t <= nt; t++)
    if (nfila[t] > 1)
      falla("tarea-con-dos-filas", "la tarea " tid[t] " tiene " nfila[t] " filas en v1: " filasde(t))
  for (k = 1; k <= fn[iv1]; k++)
    if (ndue[k] == 0)
      falla("fila-sin-tarea", "la fila " fid[iv1, k] " de v1 no cierra ninguna orchestration_task")

  # ── baseline resuelto en toda fila y en toda versión ────────────────────────
  # Los cuatro valores del enum canónico cuentan como resueltos, NOT_APPLICABLE y BLOCKED incluidos:
  # lo que impide congelar es no haberlo decidido, no haber decidido que no se mide. Que BLOCKED
  # además no despache es una regla del despacho, y la valida @bloque:orchestration-state.
  for (i = 1; i <= nv; i++)
    for (k = 1; k <= fn[i]; k++) {
      b = fbase[i, k]
      if (b != "RED" && b != "GREEN_ALREADY" && b != "NOT_APPLICABLE" && b != "BLOCKED")
        falla("baseline-sin-resolver", "la fila " fid[i, k] " de v" vnum[i] " declara baseline [" b "], fuera de {RED, GREEN_ALREADY, NOT_APPLICABLE, BLOCKED}")
    }

  # ── el conjunto de IDs es invariante entre versiones ────────────────────────
  # Son DOS defectos y no uno: agregar estrena una exigencia que nadie congeló, y quitar retira una
  # que ya se había congelado. Se compara contra la versión inmediatamente anterior; que estén
  # numeradas sin saltos lo valida el contrato canónico.
  for (i = 2; i <= nv; i++) {
    for (k = 1; k <= fn[i]; k++) {
      hay = 0
      for (j = 1; j <= fn[i - 1]; j++) if (fid[i - 1, j] == fid[i, k]) hay = 1
      if (!hay) falla("id-agregado-entre-versiones", "v" vnum[i] " estrena la fila " fid[i, k] ", que v" vnum[i - 1] " no declara")
    }
    for (j = 1; j <= fn[i - 1]; j++) {
      hay = 0
      for (k = 1; k <= fn[i]; k++) if (fid[i, k] == fid[i - 1, j]) hay = 1
      if (!hay) falla("id-quitado-entre-versiones", "v" vnum[i] " no lleva la fila " fid[i - 1, j] ", que v" vnum[i - 1] " declara")
    }
  }

  if (G == "") exit 0
  # El marcador va SOLO en su línea: el arnés lo compara entero, así que el dato medido vive abajo.
  print "GUARD:contract " G
  print "  " CTX
  print "  contrato: " cf
  exit 1
}
' "$manifest" "$contrato" >&2
exit $?
# @fin:orchestration-contract
```

```powershell
# @bloque:orchestration-contract-ps
# Predicado: el contrato de integración cierra contra las tareas del manifest: cada tarea posee
# exactamente una fila de v1 y ninguna fila queda huérfana, v1 aloja las tres clases de cierre
# —gate, closeout y auxiliar—, el baseline de toda fila está resuelto, y ninguna versión posterior
# agrega ni quita IDs.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica.
# Entradas: $manifest (el manifest.yml) y $contrato (el integracion.md de la orquestación)
foreach ($f in @($manifest, $contrato)) {
  if (-not (Test-Path -LiteralPath $f)) { [Console]::Error.WriteLine("ARNES:no existe $f"); exit 99 }
}
$Q = [char]39
$DASH = [char]0x2014   # el em dash por punto de código: no depende del encoding con que se lea este bloque
# Las mismas dos razones que en @bloque:orchestration-model, donde están explicadas: un escalar YAML
# puede venir entrecomillado —`done_when: ""` es vacío y no dos caracteres— y el comentario de fin de
# línea no es parte del valor, que es como el esquema declara sus campos opcionales.
function Desnudo($s) {
  $s = "$s".Trim()
  if ($s.Length -ge 2) {
    $c = $s[0]
    if (($c -eq '"' -or $c -eq $Q) -and $s[$s.Length - 1] -eq $c) { $s = $s.Substring(1, $s.Length - 2) }
  }
  return $s.Trim()
}
function Sincom($s) {
  $s = "$s".Trim()
  if ($s.Length -gt 0 -and ($s[0] -eq '"' -or $s[0] -eq $Q)) {
    $cierre = $s.IndexOf($s[0], 1)
    if ($cierre -ge 0) { return $s.Substring(0, $cierre + 1) }
    return $s
  }
  $m = [regex]::Match($s, '[ \t]#')
  if ($m.Success) { $s = $s.Substring(0, $m.Index) }
  return $s.Trim()
}
# Cuántos elementos tiene una lista YAML en línea. `[]` es la lista vacía y no un elemento llamado
# "[]": de esa diferencia depende reconocer a una tarea auxiliar.
function NLista($v) {
  $v = "$v".Trim()
  if ($v.StartsWith('[')) { $v = $v.Substring(1) }
  if ($v.EndsWith(']')) { $v = $v.Substring(0, $v.Length - 1) }
  $v = $v.Trim()
  if ($v -eq '') { return 0 }
  return @($v -split ',' | ForEach-Object { Desnudo $_ } | Where-Object { $_ -ne '' }).Count
}
# Registra el PRIMER hallazgo y descarta los demás. Cada fixture rojo lleva una sola mutación, así
# que dos diagnósticos en una corrida significan que dos comprobaciones se pisaron sobre el mismo
# defecto — y el arnés exige exactamente una línea GUARD:, así que emitirlos todos pone en rojo la
# fila de cada uno.
$G = ''; $CTX = ''
function Falla($m, $ctx) { if ($script:G -eq '') { $script:G = $m; $script:CTX = $ctx } }
# El enlace fila → tarea lo declara el `Requisito`, cuya gramática es `<id-tarea> — <what> [AC-n]`.
# El id se compara como prefijo y con el separador pegado: un `StartsWith` a secas daba por dueña de
# `X12 — …` a la tarea `X1`.
function Duenia($req, $id) {
  if (-not "$req".StartsWith($id)) { return $false }
  $resto = "$req".Substring($id.Length)
  if ($resto -notmatch '^[ \t]') { return $false }
  $resto = $resto -replace '^[ \t]+', ''
  return ($resto.StartsWith("$DASH ") -or $resto.StartsWith('- '))
}
function Ids($xs) { return ($xs -join ', ') }

# ── manifest: id, phase, done_when y si covers_ac está vacía ──────────────────
# La columna manda, igual que en @bloque:orchestration-model: un campo de la tarea está a la altura
# de su `id:`, y lo que cuelgue más a la derecha pertenece al último campo abierto. Sin eso, una
# clave del mapa de participación sería indistinguible de un campo de la tarea.
$tareas = @()
$sec = ''; $t = $null; $indcampo = 0; $campo = ''
foreach ($ln in (Get-Content -LiteralPath $manifest)) {
  if ($ln -match '^[ \t]*#') { continue }
  if ($ln -match '^[^ \t]') {
    $sec = ''
    if ($ln -match '^orchestration_tasks:[ \t]*(#.*)?$') { $sec = 'tasks' }
    continue
  }
  if ($sec -ne 'tasks') { continue }
  if ($ln.Trim() -eq '') { continue }
  $ind = ($ln -replace '^([ \t]*).*$', '$1').Length + 1
  if ($ln -match '^[ \t]*-[ \t]*id:[ \t]*(.*)$') {
    $t = @{ id = (Desnudo (Sincom $Matches[1])); phase = ''; dw = ''; ncov = 0; nfila = 0; filas = @() }
    $tareas += , $t
    $indcampo = $ln.IndexOf('id:') + 1; $campo = ''
    continue
  }
  if ($null -eq $t) { continue }
  # Una lista en bloque es YAML igual de válido que una en línea: un `covers_ac` escrito así se
  # leería vacío, y una tarea que cubre AC pasaría por auxiliar.
  if ($ind -gt $indcampo) {
    if ($campo -eq 'covers_ac' -and $ln -match '^[ \t]*-[ \t]') { $t.ncov = $t.ncov + 1 }
    continue
  }
  if ($ind -ne $indcampo) { continue }
  if ($ln -notmatch '^[ \t]*([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$') { continue }
  $campo = $Matches[1]; $v = Sincom $Matches[2]
  if ($campo -eq 'phase') { $t.phase = (Desnudo $v) }
  elseif ($campo -eq 'done_when') { $t.dw = (Desnudo $v) }
  elseif ($campo -eq 'covers_ac') { $t.ncov = NLista $v }
}

# ── contrato: una tabla por versión ───────────────────────────────────────────
# `### Baseline de vN` no abre una versión: el encabezado tiene que terminar en el número.
$vers = @(); $cur = $null
foreach ($ln in (Get-Content -LiteralPath $contrato)) {
  if ($ln -match '^#+[ \t]*v([0-9]+)[ \t]*$') {
    $cur = @{ num = [int]$Matches[1]; filas = @() }; $vers += , $cur; continue
  }
  if ($null -eq $cur) { continue }
  if ($ln -notmatch '^[ \t]*\|') { continue }
  if ($ln -match '^[ \t]*\|[ \t]*ID[ \t]*\|') { continue }
  if ($ln -match '^[ \t]*\|[-: \t|]+\|[ \t]*$') { continue }
  # El baseline se lee desde el final y no por número de columna: la fila termina en `|`, así que la
  # última columna es la penúltima celda. Que las columnas sean seis y estén en su orden lo valida el
  # contrato canónico, no este bloque.
  $c = $ln -split '\|'
  if ($c.Count -lt 4) { continue }
  $cur.filas += , @{ id = $c[1].Trim(); req = $c[2].Trim(); base = $c[$c.Count - 2].Trim() }
}

# La versión inicial se busca por su NÚMERO: es la que AC-8 exige completa, y leerla por posición la
# confundiría con la primera que aparezca escrita.
$f1 = @()
foreach ($v in $vers) { if ($v.num -eq 1) { $f1 = @($v.filas); break } }

# ── enlace tarea ↔ fila ───────────────────────────────────────────────────────
# Las dos mitades del enlace suman: el `Requisito` nombra la tarea y el `done_when` nombra la fila.
# Con una sola, dos filas que cierran la misma tarea pasan por una fila huérfana; que las dos
# coincidan entre sí lo exige AC-9, y lo valida @bloque:orchestration-state.
$ndue = @(0) * $f1.Count
for ($k = 0; $k -lt $f1.Count; $k++) {
  foreach ($t in $tareas) {
    if ((Duenia $f1[$k].req $t.id) -or ($t.dw -ne '' -and $f1[$k].id -eq $t.dw)) {
      $t.nfila = $t.nfila + 1; $t.filas += $f1[$k].id; $ndue[$k] = $ndue[$k] + 1
    }
  }
}

# ── las clases de cierre que v1 tiene que alojar ──────────────────────────────
# Una auxiliar es un cierre SIN AC propio, así que es también una closeout. Medir la clase auxiliar
# como "covers_ac vacía" a secas la daría por presente con la fila de un gate que no cubre ningún
# AC, y el contrato que nace sin el cierre de la auxiliar pasaría en verde.
$hayclo = $false; $conclo = $false; $sinclo = @()
$hayaux = $false; $conaux = $false; $sinaux = @()
foreach ($t in $tareas) {
  if ($t.phase -ne 'closeout') { continue }
  $hayclo = $true; if ($t.nfila -gt 0) { $conclo = $true } else { $sinclo += $t.id }
  if ($t.ncov -ne 0) { continue }
  $hayaux = $true; if ($t.nfila -gt 0) { $conaux = $true } else { $sinaux += $t.id }
}
if ($hayclo -and -not $conclo) {
  Falla 'fila-closeout-ausente' "v1 no aloja el cierre de ninguna tarea phase=closeout; sin fila: $(Ids $sinclo)"
}
if ($hayaux -and -not $conaux) {
  Falla 'fila-auxiliar-ausente' "v1 no aloja el cierre de ninguna tarea auxiliar; sin fila: $(Ids $sinaux)"
}

# ── cardinalidad: exactamente una fila por tarea, ninguna fila huérfana ───────
foreach ($t in $tareas) {
  if ($t.nfila -eq 0) {
    $dw = $(if ($t.dw -eq '') { $DASH } else { $t.dw })
    Falla 'tarea-sin-fila' "la tarea $($t.id) no tiene fila en v1 (done_when: $dw)"
  }
}
foreach ($t in $tareas) {
  if ($t.nfila -gt 1) { Falla 'tarea-con-dos-filas' "la tarea $($t.id) tiene $($t.nfila) filas en v1: $(Ids $t.filas)" }
}
for ($k = 0; $k -lt $f1.Count; $k++) {
  if ($ndue[$k] -eq 0) { Falla 'fila-sin-tarea' "la fila $($f1[$k].id) de v1 no cierra ninguna orchestration_task" }
}

# ── baseline resuelto en toda fila y en toda versión ──────────────────────────
# Los cuatro valores del enum canónico cuentan como resueltos, NOT_APPLICABLE y BLOCKED incluidos:
# lo que impide congelar es no haberlo decidido, no haber decidido que no se mide. Que BLOCKED
# además no despache es una regla del despacho, y la valida @bloque:orchestration-state.
foreach ($v in $vers) {
  foreach ($fila in $v.filas) {
    # `-cnotin` y no `-notin`: el par POSIX resuelve el enum con un `case`, que distingue
    # mayúsculas. Con el operador por defecto, un baseline `red` pasaría por el `RED` del enum.
    if ($fila.base -cnotin @('RED', 'GREEN_ALREADY', 'NOT_APPLICABLE', 'BLOCKED')) {
      Falla 'baseline-sin-resolver' "la fila $($fila.id) de v$($v.num) declara baseline [$($fila.base)], fuera de {RED, GREEN_ALREADY, NOT_APPLICABLE, BLOCKED}"
    }
  }
}

# ── el conjunto de IDs es invariante entre versiones ──────────────────────────
# Son DOS defectos y no uno: agregar estrena una exigencia que nadie congeló, y quitar retira una
# que ya se había congelado. Se compara contra la versión inmediatamente anterior; que estén
# numeradas sin saltos lo valida el contrato canónico.
for ($i = 1; $i -lt $vers.Count; $i++) {
  $prev = @($vers[$i - 1].filas | ForEach-Object { $_.id })
  $act = @($vers[$i].filas | ForEach-Object { $_.id })
  foreach ($id in $act) {
    if (-not ($prev -ccontains $id)) {
      Falla 'id-agregado-entre-versiones' "v$($vers[$i].num) estrena la fila $id, que v$($vers[$i - 1].num) no declara"
    }
  }
  foreach ($id in $prev) {
    if (-not ($act -ccontains $id)) {
      Falla 'id-quitado-entre-versiones' "v$($vers[$i].num) no lleva la fila $id, que v$($vers[$i - 1].num) declara"
    }
  }
}

if ($G -eq '') { exit 0 }
# El marcador va SOLO en su línea: el arnés lo compara entero, así que el dato medido vive abajo.
# `[Console]::Error.WriteLine` y no `Write-Error`: los eventos van por stderr —es donde los lee
# el arnés de paridad—, pero el renderizado de un ErrorRecord antepone su propio prefijo y la
# línea deja de empezar por GUARD:. Escribir crudo en el canal da las dos cosas.
[Console]::Error.WriteLine("GUARD:contract $G")
[Console]::Error.WriteLine("  $CTX")
[Console]::Error.WriteLine("  contrato: $contrato")
exit 1
# @fin:orchestration-contract-ps
```

`@bloque:orchestration-state` es la única de las tres que lee la **bitácora**, y por eso la única que
juzga **acciones** en vez de estados. El caso que lo resume: el estado final de dos repos puede ser
idéntico —uno esperó a que se cerrara su gate, el otro se despachó igual y volvió— y lo único que los
distingue es qué eventos quedaron registrados y en qué orden. De ahí que varios de sus rojos tengan
un control verde gemelo que difiere solo en el `resultado` del evento: un despacho `consumado` con el
gate abierto falla, y el mismo intento `rechazado` pasa limpio.

Lee cinco artefactos —el `manifest.yml`, la `master-spec.md`, el contrato de integración, la bitácora
y el `plan.md` de cada repo— y emite **un solo diagnóstico por corrida**: el primero del orden en que
están escritas sus comprobaciones, que va de la integridad del registro (si hay bitácora, y si sus
eventos están completos) al reparto y sus gates, de ahí a la correspondencia entre cada resultado y
su transición, y al final al cierre de cada tarea y a la frescura de su evidencia. Ese orden no es
cosmético: hay comprobaciones correctas que ven el mismo defecto —un despacho consumado con el gate
abierto es también una promoción indebida, y una evidencia que cambió de fila es también una fila sin
evidencia—, y emitir las dos convierte un defecto en dos hallazgos sin decir cuál hay que arreglar.

Sin hallazgos emite el **estado agregado** como `ESTADO:<valor>`, con la tabla de precedencia de la
Fase 3 recorrida de lo menos grave a lo más grave. Sale al final y solo en verde a propósito: sobre
un modelo inválido no hay nada que agregar, y un `ESTADO:done` al lado de un `GUARD:` sería un
mensaje que contradice su propio veredicto. Y `owner: UNASSIGNED` es lo único que **no** bloquea:
sale como `REPORTE:` con exit 0 mientras la tarea no intente cerrar, porque declarar trabajo todavía
sin asignar es justo para lo que el centinela existe.

```bash
# @bloque:orchestration-state
# Predicado: el estado de la orquestación cierra contra su bitácora: ninguna tarea pasa a `done` sin
# dueño real, con un `depends_on` abierto o con evidencia que no sea fresca y de su propia fila;
# ningún repo se despacha con su gate abierto ni con el baseline de su fila local en `BLOCKED`, ni se
# queda sin promover con el gate ya cerrado; cada evento lleva sus seis campos, un `resultado` del
# enum y un `id` único y comparable, y solo un resultado consumado materializa su transición; y la
# precedencia produce un único estado agregado que nunca oculta el más grave.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica.
# Entradas: $manifest, $master_spec, $contrato, $bitacora y $repos (un plan.md por repo)
for f in "$manifest" "$master_spec" "$contrato"; do
  [ -f "$f" ] || { printf 'ARNES:no existe el artefacto %s\n' "$f" >&2; exit 99; }
done
for f in $repos; do
  [ -f "$f" ] || { printf 'ARNES:no existe el plan %s\n' "$f" >&2; exit 99; }
done
# Una bitácora que no existe NO es un error del arnés sino el hallazgo `bitacora-ausente`: AC-20 pide
# el mismo veredicto que una transición inválida, nunca un verde por omisión. Se sustituye por
# /dev/null para que awk lea el resto igual y el estado agregado salga de todos modos.
bit="$bitacora"; [ -f "$bit" ] || bit=/dev/null
awk -v MS="$master_spec" -v MF="$manifest" -v CF="$contrato" -v BF="$bit" '
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
function desnudo(s,   c) {
  s = trim(s)
  if (length(s) >= 2) {
    c = substr(s, 1, 1)
    if ((c == "\"" || c == Q) && substr(s, length(s), 1) == c) s = substr(s, 2, length(s) - 2)
  }
  return trim(s)
}
function sincom(s,   c, i, n) {
  s = trim(s); c = substr(s, 1, 1)
  if (c == "\"" || c == Q) {
    n = length(s)
    for (i = 2; i <= n; i++) if (substr(s, i, 1) == c) return substr(s, 1, i)
    return s
  }
  if (match(s, /[ \t]#/)) s = substr(s, 1, RSTART - 1)
  return trim(s)
}
function lista(v, arr,   n, i, x, tmp) {
  delete arr
  v = trim(v); sub(/^\[/, "", v); sub(/\]$/, "", v); v = trim(v)
  if (v == "") return 0
  n = split(v, tmp, ","); x = 0
  for (i = 1; i <= n; i++) if (desnudo(tmp[i]) != "") arr[++x] = desnudo(tmp[i])
  return x
}
function falla(m, ctx) { if (G == "") { G = m; CTX = ctx } }
function duenia(req, id,   resto) {
  if (index(req, id) != 1) return 0
  resto = substr(req, length(id) + 1)
  if (resto !~ /^[ \t]/) return 0
  sub(/^[ \t]+/, "", resto)
  return (index(resto, DASH " ") == 1 || index(resto, "- ") == 1)
}
function promovido(st) { return (st != "planned") }
function despachado(st) { return (st != "planned" && st != "tasks-ready" && st != "blocked") }
function elegible(st) { return (st != "planned" && st != "blocked" && st != "failed") }
function verde(st) { return (st == "verified" || st == "committed" || st == "pushed" || st == "pr-open" || st == "done") }

BEGIN { Q = sprintf("%c", 39); DASH = "—" }

# ── master-spec: el ancla versionada declarada de cada recurso no ligado a código ─────
FILENAME == MS {
  if ($0 ~ /^#+[ \t]/) { enanclas = ($0 ~ /^#+[ \t]*Anclas versionadas[ \t]*$/); next }
  if (!enanclas) next
  if (match($0, /`[^`]*`/)) {
    s = substr($0, RSTART + 1, RLENGTH - 2)
    if (match(s, /^[^:]+:/)) ancla[trim(substr(s, 1, RLENGTH - 1))] = trim(substr(s, RLENGTH + 1))
  }
  next
}

# ── manifest: repos, tareas y outcome ────────────────────────────────────────────────
FILENAME == MF {
  if ($0 ~ /^[ \t]*#/) next
  if ($0 ~ /^[^ \t]/) {
    sec = ""
    if ($0 ~ /^repos:[ \t]*(#.*)?$/) sec = "repos"
    else if ($0 ~ /^orchestration_tasks:[ \t]*(#.*)?$/) sec = "tasks"
    else if (match($0, /^outcome:[ \t]*/)) outcome = desnudo(sincom(substr($0, RSTART + RLENGTH)))
    next
  }
  if (sec == "repos") {
    if (match($0, /^[ \t]*-[ \t]*path:[ \t]*/)) {
      rpath[++nrep] = desnudo(sincom(substr($0, RSTART + RLENGTH))); esrepo[rpath[nrep]] = nrep; next
    }
    if (!nrep) next
    if (match($0, /^[ \t]*status:[ \t]*/)) rst[nrep] = desnudo(sincom(substr($0, RSTART + RLENGTH)))
    next
  }
  if (sec != "tasks") next
  ind = match($0, /[^ \t]/); if (ind == 0) next
  if (match($0, /^[ \t]*-[ \t]*id:[ \t]*/)) {
    nt++; indcampo = index($0, "id:"); campo = ""; enmapa = 0
    tid[nt] = desnudo(sincom(substr($0, RSTART + RLENGTH))); porid[tid[nt]] = nt
    next
  }
  if (!nt) next
  # La columna manda, igual que en @bloque:orchestration-model: lo que cuelga más a la derecha
  # pertenece al último campo abierto, y sin eso una clave del mapa de participación sería
  # indistinguible de un campo de la tarea.
  if (ind > indcampo) {
    if (enmapa) {
      if ($0 ~ /^[ \t]*-[ \t]/) {
        match($0, /^[ \t]*-[ \t]*/); part[nt, ++npart[nt]] = desnudo(sincom(substr($0, RSTART + RLENGTH)))
      } else if (match($0, /^[ \t]*[^ \t:]+:[ \t]*/)) {
        k = lista(sincom(substr($0, RSTART + RLENGTH)), tmpa)
        for (i = 1; i <= k; i++) part[nt, ++npart[nt]] = tmpa[i]
      }
    } else if (campo != "" && $0 ~ /^[ \t]*-[ \t]/) {
      match($0, /^[ \t]*-[ \t]*/); lv[nt, campo, ++ln[nt, campo]] = desnudo(sincom(substr($0, RSTART + RLENGTH)))
    }
    next
  }
  if (ind != indcampo) next
  if (!match($0, /^[ \t]*[A-Za-z_][A-Za-z0-9_]*:/)) next
  campo = substr($0, RSTART, RLENGTH); sub(/:$/, "", campo); campo = trim(campo)
  v = sincom(substr($0, RSTART + RLENGTH)); enmapa = 0
  if (campo == "phase") tph[nt] = desnudo(v)
  else if (campo == "owner") town[nt] = desnudo(v)
  else if (campo == "status") tst[nt] = desnudo(v)
  else if (campo == "done_when") tdw[nt] = desnudo(v)
  else if (campo == "participating_repos") { if (v == "") enmapa = 1 }
  else if (campo == "depends_on" || campo == "blocks_repos") {
    ln[nt, campo] = lista(v, tmpa)
    for (i = 1; i <= ln[nt, campo]; i++) lv[nt, campo, i] = tmpa[i]
  }
  next
}

# ── contrato: una tabla por versión ──────────────────────────────────────────────────
FILENAME == CF {
  if (match($0, /^#+[ \t]*v[0-9]+[ \t]*$/)) {
    s = $0; sub(/^#+[ \t]*v/, "", s); nv++; vnum[nv] = trim(s) + 0; ver = nv; next
  }
  if (!ver) next
  if ($0 !~ /^[ \t]*\|/) next
  if ($0 ~ /^[ \t]*\|[ \t]*ID[ \t]*\|/) next
  if ($0 ~ /^[ \t]*\|[-: \t|]+\|[ \t]*$/) next
  n = split($0, c, "[|]")
  if (n < 4) next
  k = ++fn[ver]
  fid[ver, k] = trim(c[2]); freq[ver, k] = trim(c[3]); fesp[ver, k] = trim(c[n - 2])
  next
}

# ── bitácora: un evento por línea, con sus campos entre backticks ────────────────────
FILENAME == BF {
  nbl++
  if ($0 !~ /^[ \t]*-[ \t]*`/) next
  ne++; s = $0
  while (match(s, /`[^`]*`/)) {
    f = substr(s, RSTART + 1, RLENGTH - 2); s = substr(s, RSTART + RLENGTH)
    if (f !~ /^[A-Za-z_]+:/) continue
    k = f; sub(/:.*$/, "", k)
    val = f; sub(/^[A-Za-z_]+:[ \t]*/, "", val)
    evhas[ne, k] = 1; ev[ne, k] = trim(val)
  }
  next
}

# ── plan.md por repo: estado del header, SHA y baseline de su contrato local ─────────
{
  if (FNR == 1) { curr = ""; fm = 0 }
  if ($0 ~ /^---[ \t]*$/) { fm++; next }
  if (fm == 1) {
    if (match($0, /^repo:[ \t]*/)) { curr = trim(substr($0, RSTART + RLENGTH)); planfile[curr] = FILENAME }
    else if (match($0, /^status:[ \t]*/)) planst[curr] = trim(substr($0, RSTART + RLENGTH))
    else if (match($0, /^head_sha:[ \t]*/)) plansha[curr] = trim(substr($0, RSTART + RLENGTH))
    next
  }
  if (curr == "" || $0 !~ /^[ \t]*\|/) next
  n = split($0, c, "[|]")
  if (n >= 4 && trim(c[n - 1]) == "BLOCKED") planblocked[curr] = 1
}

END {
  # ── índices derivados ──────────────────────────────────────────────────────────────
  vig = 0
  for (i = 1; i <= nv; i++) if (vig == 0 || vnum[i] > vnum[vig]) vig = i
  for (t = 1; t <= nt; t++) {
    fila[t] = ""
    for (k = 1; k <= fn[vig]; k++) if (duenia(freq[vig, k], tid[t])) { fila[t] = fid[vig, k]; esp[t] = fesp[vig, k] }
  }
  for (t = 1; t <= nt; t++) {
    if (tph[t] != "gate") continue
    for (i = 1; i <= ln[t, "blocks_repos"]; i++) {
      p = lv[t, "blocks_repos", i]; retiene[p]++
      if (tst[t] != "done") abierto[p]++
    }
  }
  for (e = 1; e <= ne; e++) {
    pa = ev[e, "paso"]; ob = ev[e, "objeto"]; re = ev[e, "resultado"]
    if (pa == "promover-repo" && re == "consumado") { promok[ob] = 1; hayreparto = 1 }
    else if (pa == "promover-repo") hayreparto = 1
    else if (pa == "despachar-repo" && re == "consumado") despok[ob] = 1
    else if (pa == "cerrar-tarea" && re == "consumado") cierreok[ob] = 1
    else if (pa == "ejecutar-evidencia" && re == "consumado") {
      porfila[ev[e, "fila"]]++
      if (evfila[ev[e, "fila"]] == 0) evfila[ev[e, "fila"]] = e
      if (evobj[ob] == 0) evobj[ob] = e
    }
  }

  # ── la bitácora existe ─────────────────────────────────────────────────────────────
  # Un archivo sin una sola línea es una bitácora ausente; uno con encabezado y cero eventos es la
  # bitácora legítima de una orquestación que todavía no intentó ninguna transición.
  if (nbl == 0) falla("bitacora-ausente", "no hay bitácora que leer en " BF)

  # ── el evento: seis campos obligatorios, resultado del enum, id único y comparable ─
  ncampos = split("id paso actor objeto resultado timestamp", campos, " ")
  for (i = 1; i <= ncampos; i++)
    for (e = 1; e <= ne; e++)
      if (!evhas[e, campos[i]])
        falla("evento-sin-" campos[i], "el evento " e "º de la bitácora no declara " campos[i])
  for (e = 1; e <= ne; e++)
    if (evhas[e, "resultado"] && ev[e, "resultado"] != "consumado" && ev[e, "resultado"] != "rechazado")
      falla("resultado-fuera-de-enum", "el evento " ev[e, "id"] " declara resultado=[" ev[e, "resultado"] "], fuera de {consumado, rechazado}")
  for (e = 1; e <= ne; e++) if (evhas[e, "id"]) cuantos[ev[e, "id"]]++
  for (e = 1; e <= ne; e++)
    if (evhas[e, "id"] && cuantos[ev[e, "id"]] > 1)
      falla("evento-id-duplicado", "el id " ev[e, "id"] " abre " cuantos[ev[e, "id"]] " eventos de la bitácora")
  # El id ordena porque es un entero: uno que no admite comparación deja el orden indeterminable, y
  # el timestamp no lo suple porque admite empates.
  for (e = 1; e <= ne; e++)
    if (evhas[e, "id"] && ev[e, "id"] !~ /^[0-9]+$/)
      falla("orden-no-determinable", "el evento con id [" ev[e, "id"] "] no lleva un entero comparable")

  # ── archive con tareas de orquestación sin cerrar ──────────────────────────────────
  if (outcome == "archived") {
    for (t = 1; t <= nt; t++) if (tst[t] != "done") pend[++npend] = tid[t]
    if (npend > 0) {
      lst = ""
      for (i = 1; i <= npend; i++) lst = lst (i > 1 ? ", " : "") pend[i]
      falla("archive-con-tareas-pendientes", "quedan " npend " orchestration_tasks fuera de done: " lst)
      condetalle = 1
    }
  }

  # ── despacho y promoción contra los gates ──────────────────────────────────────────
  # Un despacho CONSUMADO con el gate abierto gana sobre la promoción indebida que lo acompaña:
  # son el mismo defecto visto dos veces, y emitir los dos no dice cuál hay que arreglar.
  for (r = 1; r <= nrep; r++)
    if (abierto[rpath[r]] > 0 && despok[rpath[r]])
      falla("despacho-exitoso-con-gate-abierto", "el repo " rpath[r] " se despachó con " abierto[rpath[r]] " gate(s) fuera de done")
  for (r = 1; r <= nrep; r++)
    if (abierto[rpath[r]] > 0 && elegible(rst[r]))
      falla("repo-bloqueado-promovido", "el repo " rpath[r] " está en " rst[r] " con " abierto[rpath[r]] " gate(s) fuera de done")
  # `planned` solo es defecto si el reparto se aprobó, y esa señal es la existencia de un evento
  # promover-repo: sin él, todo en planned es el estado correcto de una orquestación sin repartir.
  for (r = 1; r <= nrep; r++)
    if (hayreparto && rst[r] == "planned" && retiene[rpath[r]] == 0)
      falla("repo-libre-sin-promover", "el repo " rpath[r] " sigue en planned y ninguna tarea gate lo retiene")
  for (r = 1; r <= nrep; r++)
    if (hayreparto && rst[r] == "planned" && retiene[rpath[r]] > 0 && abierto[rpath[r]] == 0)
      falla("gate-cerrado-sin-promover", "el repo " rpath[r] " sigue en planned con sus " retiene[rpath[r]] " gate(s) en done")
  for (r = 1; r <= nrep; r++)
    if (rst[r] == "tasks-ready" && retiene[rpath[r]] > 0 && abierto[rpath[r]] == 0 && !despok[rpath[r]])
      falla("gate-cerrado-sin-despachar", "el repo " rpath[r] " se promovió al cerrar su gate y nunca se despachó")
  # AC-8: con el baseline de su fila local sin medir no se despacha. Va ANTES de la correspondencia
  # resultado ↔ transición porque nombra la causa: el despacho no debió ocurrir, y que además su
  # evento diga otra cosa es consecuencia y no diagnóstico.
  for (r = 1; r <= nrep; r++)
    if (planblocked[rpath[r]] && despachado(rst[r]))
      falla("despacho-con-baseline-blocked", "el repo " rpath[r] " está en " rst[r] " con una fila de baseline BLOCKED en su contrato local")
  for (r = 1; r <= nrep; r++)
    if (planfile[rpath[r]] != "" && planst[rpath[r]] != rst[r])
      falla("manifest-y-plan-divergen", "el repo " rpath[r] " vale " rst[r] " en el manifest y " planst[rpath[r]] " en su plan.md")

  # ── la liberación del lock exige una decisión previa ───────────────────────────────
  for (e = 1; e <= ne; e++) {
    if (ev[e, "paso"] != "liberar-lock" || ev[e, "resultado"] != "consumado") continue
    hay = 0
    for (j = 1; j <= e; j++) if (evhas[j, "decision"]) hay = 1
    if (!hay) falla("liberacion-de-lock-sin-decision", "el evento " ev[e, "id"] " liberó el lock de " ev[e, "objeto"] " sin una decisión registrada antes")
  }

  # ── resultado ↔ transición, en sus tres formas ─────────────────────────────────────
  # Solo los pasos cuyo efecto es un estado del manifest: liberar-lock y ejecutar-evidencia no
  # materializan ninguno, así que exigirles un cambio de estado sería inventarles un observable.
  for (e = 1; e <= ne; e++) {
    pa = ev[e, "paso"]; ob = ev[e, "objeto"]; re = ev[e, "resultado"]
    if (pa == "cerrar-tarea") mat = (ob in porid) ? (tst[porid[ob]] == "done") : 0
    else if (pa == "despachar-repo") mat = (ob in esrepo) ? despachado(rst[esrepo[ob]]) : 0
    else if (pa == "promover-repo") mat = (ob in esrepo) ? promovido(rst[esrepo[ob]]) : 0
    else continue
    if (re == "consumado" && !mat)
      falla("exito-sin-transicion", "el evento " ev[e, "id"] " consumó " pa " sobre " ob " y su estado no cambió")
    if (re == "rechazado" && mat)
      falla("rechazo-con-transicion", "el evento " ev[e, "id"] " rechazó " pa " sobre " ob " y su estado cambió igual")
  }
  for (t = 1; t <= nt; t++)
    if (tst[t] == "done" && !cierreok[tid[t]])
      falla("transicion-sin-evento", "la tarea " tid[t] " está en done y ningún evento cerrar-tarea la consumó")
  for (r = 1; r <= nrep; r++) {
    if (despachado(rst[r]) && !despok[rpath[r]])
      falla("transicion-sin-evento", "el repo " rpath[r] " está en " rst[r] " y ningún evento despachar-repo lo consumó")
    if (promovido(rst[r]) && !promok[rpath[r]])
      falla("transicion-sin-evento", "el repo " rpath[r] " está en " rst[r] " y ningún evento promover-repo lo consumó")
  }

  # ── el gate del paso a done (AC-7 y AC-9) ──────────────────────────────────────────
  for (t = 1; t <= nt; t++) {
    if (town[t] != "UNASSIGNED") continue
    if (tst[t] == "done") falla("cierre-con-owner-unassigned", "la tarea " tid[t] " (phase=" tph[t] ") cerró con owner UNASSIGNED")
    else { rep = 1; repl[++nreps] = tid[t] }
  }
  for (t = 1; t <= nt; t++) {
    if (tst[t] != "done") continue
    for (i = 1; i <= ln[t, "depends_on"]; i++) {
      d = lv[t, "depends_on", i]
      if (!(d in porid) || tst[porid[d]] != "done")
        falla("depends_on-insatisfecho", "la tarea " tid[t] " cerró con " d " fuera de done")
    }
  }
  # Ni la evidencia ni el dueño se comparten: dos tareas que declaren la misma fila —o el mismo
  # dueño de ejecución— no son dos cierres sino uno contado dos veces.
  for (e = 1; e <= ne; e++)
    if (ev[e, "paso"] == "ejecutar-evidencia" && ev[e, "resultado"] == "consumado" && porfila[ev[e, "fila"]] > 1)
      falla("evidencia-duplicada", "la fila " ev[e, "fila"] " la ejecutan " porfila[ev[e, "fila"]] " eventos de tareas distintas")
  # UNASSIGNED es el centinela de un dueño pendiente, no un dueño: dos tareas sin asignar no son dos
  # tareas con el mismo dueño, y AC-7 ya las bloquea por su lado.
  for (t = 1; t <= nt; t++) {
    if (town[t] == "" || town[t] == "UNASSIGNED") continue
    for (u = t + 1; u <= nt; u++)
      if (town[u] == town[t])
        falla("dueno-duplicado", "las tareas " tid[t] " y " tid[u] " declaran el mismo owner " town[t])
  }

  # ── la frescura de la evidencia (AC-20) ────────────────────────────────────────────
  for (t = 1; t <= nt; t++) {
    if (tst[t] != "done" || fila[t] == "") continue
    e = evfila[fila[t]]
    if (e > 0 && ev[e, "objeto"] != tid[t])
      falla("evidencia-de-otra-tarea", "la fila " fila[t] " de " tid[t] " la ejecutó un evento con objeto " ev[e, "objeto"])
    else if (e == 0 && evobj[tid[t]] > 0)
      falla("evidencia-de-otra-fila", "la tarea " tid[t] " cierra con " fila[t] " y su evidencia ejecutó " ev[evobj[tid[t]], "fila"])
    else if (e == 0)
      falla("evidencia-obsoleta", "la tarea " tid[t] " cerró sin ningún evento ejecutar-evidencia de su fila " fila[t])
  }
  for (t = 1; t <= nt; t++) {
    if (tst[t] != "done" || fila[t] == "") continue
    e = evfila[fila[t]]
    if (e == 0 || ev[e, "objeto"] != tid[t]) continue
    if (ev[e, "contrato"] != "v" vnum[vig])
      falla("evidencia-de-version-anterior", "la fila " fila[t] " se midió contra el contrato " ev[e, "contrato"] " y la versión vigente es v" vnum[vig])
    # El anclaje es uno u otro según de qué esté hecha la evidencia, y participating_repos es quien
    # lo decide: con repos participantes se mide un SHA por CADA uno, y sin ninguno el ancla
    # versionada declarada hace las veces y se revalida con la misma vara.
    if (npart[t] > 0) {
      nsha = split(ev[e, "sha"], pares, ",")
      delete medido
      for (i = 1; i <= nsha; i++) {
        par = trim(pares[i]); nom = par; sub(/=.*$/, "", nom); val = par; sub(/^[^=]*=/, "", val)
        if (nom != "") medido[nom] = val
      }
      for (i = 1; i <= npart[t]; i++) {
        p = part[t, i]
        if (!(p in medido)) falla("repo-relevante-sin-sha", "la tarea " tid[t] " participa " p " y su evidencia no lo mide")
        else if (medido[p] != plansha[p]) falla("repo-cambiado-tras-medir", "la tarea " tid[t] " midió " p " en " medido[p] " y su plan.md declara " plansha[p])
      }
    } else if (!evhas[e, "ancla"]) {
      falla("ancla-versionada-ausente", "la tarea " tid[t] " no participa ningún repo y su evidencia no declara ancla versionada")
    } else {
      nom = ev[e, "ancla"]; sub(/=.*$/, "", nom); val = ev[e, "ancla"]; sub(/^[^=]*=/, "", val)
      if (!(nom in ancla) || ancla[nom] != val)
        falla("ancla-versionada-obsoleta", "la tarea " tid[t] " midió " nom " en " val " y la vigente es " (nom in ancla ? ancla[nom] : "ninguna declarada"))
    }
    if (ev[e, "observado"] != esp[t])
      falla("esperado-no-satisfecho", "la fila " fila[t] " esperaba [" esp[t] "] y observó [" ev[e, "observado"] "]")
  }
  for (t = 1; t <= nt; t++)
    if (tst[t] == "done" && fila[t] != "" && tdw[t] != fila[t])
      falla("done_when-no-referencia-su-fila", "la tarea " tid[t] " cierra en la fila " fila[t] " y su done_when dice " (tdw[t] == "" ? "—" : tdw[t]))

  if (rep) {
    lst = ""
    for (i = 1; i <= nreps; i++) lst = lst (i > 1 ? ", " : "") repl[i]
    print "REPORTE:owner-unassigned"
    print "  sin dueño asignado y sin cerrar: " lst
  }
  if (G != "") {
    # El marcador va SOLO en su línea: el arnés lo compara entero, así que el dato medido vive abajo.
    # Y va por stderr explícito, no por una redirección de la invocación: este bloque es el único
    # que emite las DOS cosas —el hallazgo y el estado agregado—, y tienen canales distintos. El
    # hallazgo es un evento; `REPORTE:` y `ESTADO:` son el dato que el bloque produce y salen por
    # stdout. Con el `>&2` afuera no hay forma de separarlos: ahí la stdout de awk YA es stderr.
    print "GUARD:state " G          > "/dev/stderr"
    print "  " CTX                  > "/dev/stderr"
    print "  manifest: " MF         > "/dev/stderr"
    if (condetalle) for (i = 1; i <= npend; i++) print "DETALLE:" pend[i] > "/dev/stderr"
    exit 1
  }

  # ── el estado agregado, por precedencia declarada ──────────────────────────────────
  # Sale SOLO cuando no hubo hallazgo: sobre un modelo inválido no hay nada que agregar, y un
  # `ESTADO:done` al lado de un `GUARD:` es un mensaje que contradice su propio veredicto.
  # Se asigna de lo menos grave a lo más grave y gana la última: es la tabla de precedencia de la
  # Fase 3 leída al revés, y por eso ningún estado puede ocultar a uno de rango menor.
  est = "done"
  for (t = 1; t <= nt; t++) if (tst[t] != "done") est = "no-verificado:integracion-pendiente"
  for (r = 1; r <= nrep; r++) if (!verde(rst[r])) est = "en-curso"
  for (t = 1; t <= nt; t++) if (tph[t] == "gate" && tst[t] == "blocked") est = "no-verificado:gate-blocked"
  for (r = 1; r <= nrep; r++) if (rst[r] == "blocked") est = "no-verificado:repo-blocked"
  for (r = 1; r <= nrep; r++) if (rst[r] == "failed") est = "no-verificado:repo-failed"
  print "ESTADO:" est
  exit 0
}
' "$master_spec" "$manifest" "$contrato" "$bit" $repos
exit $?
# @fin:orchestration-state
```

```powershell
# @bloque:orchestration-state-ps
# Predicado: el estado de la orquestación cierra contra su bitácora: ninguna tarea pasa a `done` sin
# dueño real, con un `depends_on` abierto o con evidencia que no sea fresca y de su propia fila;
# ningún repo se despacha con su gate abierto ni con el baseline de su fila local en `BLOCKED`, ni se
# queda sin promover con el gate ya cerrado; cada evento lleva sus seis campos, un `resultado` del
# enum y un `id` único y comparable, y solo un resultado consumado materializa su transición; y la
# precedencia produce un único estado agregado que nunca oculta el más grave.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que es el de la fábrica.
# Entradas: $manifest, $master_spec, $contrato, $bitacora y $repos (un plan.md por repo)
foreach ($f in @($manifest, $master_spec, $contrato)) {
  if (-not (Test-Path -LiteralPath $f)) { [Console]::Error.WriteLine("ARNES:no existe el artefacto $f"); exit 99 }
}
$planes = @($repos -split '\s+' | Where-Object { $_ })
foreach ($f in $planes) {
  if (-not (Test-Path -LiteralPath $f)) { [Console]::Error.WriteLine("ARNES:no existe el plan $f"); exit 99 }
}
$Q = [char]39
function Desnudo($s) {
  $s = "$s".Trim()
  if ($s.Length -ge 2) {
    $c = $s[0]
    if (($c -eq '"' -or $c -eq $Q) -and $s[$s.Length - 1] -eq $c) { $s = $s.Substring(1, $s.Length - 2) }
  }
  return $s.Trim()
}
function Sincom($s) {
  $s = "$s".Trim()
  if ($s.Length -gt 0 -and ($s[0] -eq '"' -or $s[0] -eq $Q)) {
    $cierre = $s.IndexOf($s[0], 1)
    if ($cierre -ge 0) { return $s.Substring(0, $cierre + 1) }
    return $s
  }
  $m = [regex]::Match($s, '[ \t]#')
  if ($m.Success) { $s = $s.Substring(0, $m.Index) }
  return $s.Trim()
}
# La coma del `return` NO es adorno: `return @()` devuelve $null y el `+=` siguiente produciría una
# cadena en vez de una lista. Con la coma vuelve el arreglo, vacío incluido.
function Lista($v) {
  $v = "$v".Trim()
  if ($v.StartsWith('[')) { $v = $v.Substring(1) }
  if ($v.EndsWith(']')) { $v = $v.Substring(0, $v.Length - 1) }
  $v = $v.Trim()
  if ($v -eq '') { return , @() }
  return , @($v -split ',' | ForEach-Object { Desnudo $_ } | Where-Object { $_ -ne '' })
}
$G = ''; $CTX = ''
function Falla($m, $ctx) { if ($script:G -eq '') { $script:G = $m; $script:CTX = $ctx } }
# El enlace fila → tarea lo declara el `Requisito`, cuya gramática es `<id-tarea> — <what> [AC-n]`.
# El id se compara como prefijo y con el separador pegado: buscarlo a secas daba por dueña de
# `X12 — …` a la tarea `X1`.
function Duenia($req, $id) {
  if ($req.IndexOf($id) -ne 0) { return $false }
  $resto = $req.Substring($id.Length)
  if ($resto -notmatch '^[ \t]') { return $false }
  $resto = $resto -replace '^[ \t]+', ''
  return ($resto.IndexOf('— ') -eq 0 -or $resto.IndexOf('- ') -eq 0)
}
function Promovido($st) { return ($st -cne 'planned') }
function Despachado($st) { return ($st -cne 'planned' -and $st -cne 'tasks-ready' -and $st -cne 'blocked') }
function Elegible($st) { return ($st -cne 'planned' -and $st -cne 'blocked' -and $st -cne 'failed') }
function Verde($st) { return ($st -ceq 'verified' -or $st -ceq 'committed' -or $st -ceq 'pushed' -or $st -ceq 'pr-open' -or $st -ceq 'done') }

# ── master-spec: el ancla versionada declarada de cada recurso no ligado a código ─────
# Diccionarios ORDINALES y comparadores `-c*` en todo el bloque: los arreglos de awk se
# indexan por bytes y su `==` distingue mayúsculas. Con una hashtable `@{}` y los operadores
# por defecto de .NET, `SERVICIO-A` sería el repo `servicio-a`, `Consumado` pasaría por el
# `consumado` del enum y `v-c1` por la fila `V-C1` — y en la otra dirección, dos owners que
# solo difieren en caja contarían como el mismo dueño.
$ancla = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
$enanclas = $false
foreach ($ln in (Get-Content -LiteralPath $master_spec)) {
  if ($ln -match '^#+[ \t]') { $enanclas = ($ln -match '^#+[ \t]*Anclas versionadas[ \t]*$'); continue }
  if (-not $enanclas) { continue }
  if ($ln -match '`([^`]*)`') {
    $s = $Matches[1]
    if ($s -match '^([^:]+):(.*)$') { $ancla[$Matches[1].Trim()] = $Matches[2].Trim() }
  }
}

# ── manifest: repos, tareas y outcome ────────────────────────────────────────────────
$rpath = @(); $rst = @()
$esrepo = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
$tareas = @()
$porid = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
$outcome = ''
$sec = ''; $t = $null; $indcampo = 0; $campo = ''; $enmapa = $false
foreach ($ln in (Get-Content -LiteralPath $manifest)) {
  if ($ln -match '^[ \t]*#') { continue }
  if ($ln -match '^[^ \t]') {
    $sec = ''
    if ($ln -match '^repos:[ \t]*(#.*)?$') { $sec = 'repos' }
    elseif ($ln -match '^orchestration_tasks:[ \t]*(#.*)?$') { $sec = 'tasks' }
    elseif ($ln -match '^outcome:[ \t]*(.*)$') { $outcome = Desnudo (Sincom $Matches[1]) }
    continue
  }
  if ($ln.Trim() -eq '') { continue }
  $ind = ($ln -replace '^([ \t]*).*$', '$1').Length + 1
  if ($sec -ceq 'repos') {
    if ($ln -match '^[ \t]*-[ \t]*path:[ \t]*(.*)$') {
      $rpath += (Desnudo (Sincom $Matches[1])); $rst += ''; $esrepo[$rpath[$rpath.Count - 1]] = $rpath.Count
    } elseif ($rpath.Count -gt 0 -and $ln -match '^[ \t]*status:[ \t]*(.*)$') {
      $rst[$rst.Count - 1] = (Desnudo (Sincom $Matches[1]))
    }
    continue
  }
  if ($sec -cne 'tasks') { continue }
  if ($ln -match '^[ \t]*-[ \t]*id:[ \t]*(.*)$') {
    $t = @{ id = (Desnudo (Sincom $Matches[1])); phase = ''; owner = ''; st = ''; dw = ''; deps = @(); blocks = @(); part = @() }
    $tareas += , $t; $porid[$t.id] = $tareas.Count
    $indcampo = $ln.IndexOf('id:') + 1; $campo = ''; $enmapa = $false
    continue
  }
  if ($null -eq $t) { continue }
  # La columna manda, igual que en @bloque:orchestration-model: lo que cuelga más a la derecha
  # pertenece al último campo abierto, y sin eso una clave del mapa de participación sería
  # indistinguible de un campo de la tarea.
  if ($ind -gt $indcampo) {
    if ($enmapa) {
      if ($ln -match '^[ \t]*-[ \t](.*)$') { $t.part += (Desnudo (Sincom $Matches[1])) }
      elseif ($ln -match '^[ \t]*[^ \t:]+:[ \t]*(.*)$') { $t.part += (Lista (Sincom $Matches[1])) }
    } elseif ($campo -ne '' -and $ln -match '^[ \t]*-[ \t](.*)$') {
      if ($campo -ceq 'depends_on') { $t.deps += (Desnudo (Sincom $Matches[1])) }
      elseif ($campo -ceq 'blocks_repos') { $t.blocks += (Desnudo (Sincom $Matches[1])) }
    }
    continue
  }
  if ($ind -ne $indcampo) { continue }
  if ($ln -notmatch '^[ \t]*([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$') { continue }
  $campo = $Matches[1]; $v = Sincom $Matches[2]; $enmapa = $false
  if ($campo -ceq 'phase') { $t.phase = Desnudo $v }
  elseif ($campo -ceq 'owner') { $t.owner = Desnudo $v }
  elseif ($campo -ceq 'status') { $t.st = Desnudo $v }
  elseif ($campo -ceq 'done_when') { $t.dw = Desnudo $v }
  elseif ($campo -ceq 'participating_repos') { if ($v -eq '') { $enmapa = $true } }
  elseif ($campo -ceq 'depends_on') { $t.deps = Lista $v }
  elseif ($campo -ceq 'blocks_repos') { $t.blocks = Lista $v }
}

# ── contrato: una tabla por versión ──────────────────────────────────────────────────
$vnum = @(); $filas = @(); $ver = 0
foreach ($ln in (Get-Content -LiteralPath $contrato)) {
  if ($ln -match '^#+[ \t]*v([0-9]+)[ \t]*$') { $vnum += [int]$Matches[1]; $filas += , @(); $ver = $vnum.Count; continue }
  if ($ver -eq 0) { continue }
  if ($ln -notmatch '^[ \t]*\|') { continue }
  if ($ln -match '^[ \t]*\|[ \t]*ID[ \t]*\|') { continue }
  if ($ln -match '^[ \t]*\|[-: \t|]+\|[ \t]*$') { continue }
  $c = $ln -split '\|'
  if ($c.Count -lt 4) { continue }
  # El Esperado se lee desde el final y no por número de columna: la fila termina en `|`, así que la
  # última celda es la penúltima. Que las columnas sean seis lo valida el contrato canónico.
  $filas[$ver - 1] += , @{ id = $c[1].Trim(); req = $c[2].Trim(); esp = $c[$c.Count - 3].Trim() }
}

# ── bitácora: un evento por línea, con sus campos entre backticks ────────────────────
$nbl = 0; $eventos = @()
if (Test-Path -LiteralPath $bitacora) {
  foreach ($ln in (Get-Content -LiteralPath $bitacora)) {
    $nbl++
    if ($ln -notmatch '^[ \t]*-[ \t]*`') { continue }
    $e = @{}
    foreach ($m in [regex]::Matches($ln, '`[^`]*`')) {
      $f = $m.Value.Substring(1, $m.Value.Length - 2)
      if ($f -match '^([A-Za-z_]+):[ \t]*(.*)$') { $e[$Matches[1]] = $Matches[2].Trim() }
    }
    $eventos += , $e
  }
}

# ── plan.md por repo: estado del header, SHA y baseline de su contrato local ─────────
$planst = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
$plansha = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
$planblocked = [Collections.Generic.Dictionary[string, bool]]::new([StringComparer]::Ordinal)
$planfile = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
foreach ($pf in $planes) {
  $curr = ''; $fm = 0
  foreach ($ln in (Get-Content -LiteralPath $pf)) {
    if ($ln -match '^---[ \t]*$') { $fm++; continue }
    if ($fm -eq 1) {
      if ($ln -match '^repo:[ \t]*(.*)$') { $curr = $Matches[1].Trim(); $planfile[$curr] = $pf }
      elseif ($ln -match '^status:[ \t]*(.*)$') { $planst[$curr] = $Matches[1].Trim() }
      elseif ($ln -match '^head_sha:[ \t]*(.*)$') { $plansha[$curr] = $Matches[1].Trim() }
      continue
    }
    if ($curr -eq '' -or $ln -notmatch '^[ \t]*\|') { continue }
    $c = $ln -split '\|'
    if ($c.Count -ge 4 -and $c[$c.Count - 2].Trim() -ceq 'BLOCKED') { $planblocked[$curr] = $true }
  }
}

# ── índices derivados ────────────────────────────────────────────────────────────────
$vig = -1
for ($i = 0; $i -lt $vnum.Count; $i++) { if ($vig -lt 0 -or $vnum[$i] -gt $vnum[$vig]) { $vig = $i } }
foreach ($t in $tareas) {
  $t.fila = ''; $t.esp = ''
  if ($vig -ge 0) {
    foreach ($f in $filas[$vig]) { if (Duenia $f.req $t.id) { $t.fila = $f.id; $t.esp = $f.esp } }
  }
}
$retiene = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
$abierto = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
foreach ($p in $rpath) { $retiene[$p] = 0; $abierto[$p] = 0 }
foreach ($t in $tareas) {
  if ($t.phase -cne 'gate') { continue }
  foreach ($p in $t.blocks) {
    if (-not $retiene.ContainsKey($p)) { $retiene[$p] = 0; $abierto[$p] = 0 }
    $retiene[$p]++
    if ($t.st -cne 'done') { $abierto[$p]++ }
  }
}
$promok = [Collections.Generic.Dictionary[string, bool]]::new([StringComparer]::Ordinal)
$despok = [Collections.Generic.Dictionary[string, bool]]::new([StringComparer]::Ordinal)
$cierreok = [Collections.Generic.Dictionary[string, bool]]::new([StringComparer]::Ordinal)
$porfila = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
$evfila = [Collections.Generic.Dictionary[string, object]]::new([StringComparer]::Ordinal)
$evobj = [Collections.Generic.Dictionary[string, object]]::new([StringComparer]::Ordinal)
$hayreparto = $false
foreach ($e in $eventos) {
  $pa = "$($e['paso'])"; $ob = "$($e['objeto'])"; $re = "$($e['resultado'])"
  if ($pa -ceq 'promover-repo') { $hayreparto = $true; if ($re -ceq 'consumado') { $promok[$ob] = $true } }
  elseif ($pa -ceq 'despachar-repo') { if ($re -ceq 'consumado') { $despok[$ob] = $true } }
  elseif ($pa -ceq 'cerrar-tarea') { if ($re -ceq 'consumado') { $cierreok[$ob] = $true } }
  elseif ($pa -ceq 'ejecutar-evidencia' -and $re -ceq 'consumado') {
    $fi = "$($e['fila'])"
    if ($porfila.ContainsKey($fi)) { $porfila[$fi]++ } else { $porfila[$fi] = 1 }
    if (-not $evfila.ContainsKey($fi)) { $evfila[$fi] = $e }
    if (-not $evobj.ContainsKey($ob)) { $evobj[$ob] = $e }
  }
}

# ── la bitácora existe ───────────────────────────────────────────────────────────────
# Un archivo sin una sola línea es una bitácora ausente; uno con encabezado y cero eventos es la
# bitácora legítima de una orquestación que todavía no intentó ninguna transición.
if ($nbl -eq 0) { Falla 'bitacora-ausente' "no hay bitácora que leer en $bitacora" }

# ── el evento: seis campos obligatorios, resultado del enum, id único y comparable ───
foreach ($c in @('id', 'paso', 'actor', 'objeto', 'resultado', 'timestamp')) {
  for ($i = 0; $i -lt $eventos.Count; $i++) {
    if (-not $eventos[$i].ContainsKey($c)) { Falla "evento-sin-$c" "el evento $($i + 1)º de la bitácora no declara $c" }
  }
}
foreach ($e in $eventos) {
  if ($e.ContainsKey('resultado') -and $e['resultado'] -cne 'consumado' -and $e['resultado'] -cne 'rechazado') {
    Falla 'resultado-fuera-de-enum' "el evento $($e['id']) declara resultado=[$($e['resultado'])], fuera de {consumado, rechazado}"
  }
}
$cuantos = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
foreach ($e in $eventos) { if ($e.ContainsKey('id')) { if ($cuantos.ContainsKey($e['id'])) { $cuantos[$e['id']]++ } else { $cuantos[$e['id']] = 1 } } }
foreach ($e in $eventos) {
  if ($e.ContainsKey('id') -and $cuantos[$e['id']] -gt 1) {
    Falla 'evento-id-duplicado' "el id $($e['id']) abre $($cuantos[$e['id']]) eventos de la bitácora"
  }
}
# El id ordena porque es un entero: uno que no admite comparación deja el orden indeterminable, y
# el timestamp no lo suple porque admite empates.
foreach ($e in $eventos) {
  if ($e.ContainsKey('id') -and $e['id'] -notmatch '^[0-9]+$') {
    Falla 'orden-no-determinable' "el evento con id [$($e['id'])] no lleva un entero comparable"
  }
}

# ── archive con tareas de orquestación sin cerrar ────────────────────────────────────
$pend = @(); $condetalle = $false
if ($outcome -ceq 'archived') {
  foreach ($t in $tareas) { if ($t.st -cne 'done') { $pend += $t.id } }
  if ($pend.Count -gt 0) {
    Falla 'archive-con-tareas-pendientes' "quedan $($pend.Count) orchestration_tasks fuera de done: $($pend -join ', ')"
    $condetalle = $true
  }
}

# ── despacho y promoción contra los gates ────────────────────────────────────────────
# Un despacho CONSUMADO con el gate abierto gana sobre la promoción indebida que lo acompaña:
# son el mismo defecto visto dos veces, y emitir los dos no dice cuál hay que arreglar.
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ($abierto[$rpath[$r]] -gt 0 -and $despok.ContainsKey($rpath[$r])) {
    Falla 'despacho-exitoso-con-gate-abierto' "el repo $($rpath[$r]) se despachó con $($abierto[$rpath[$r]]) gate(s) fuera de done"
  }
}
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ($abierto[$rpath[$r]] -gt 0 -and (Elegible $rst[$r])) {
    Falla 'repo-bloqueado-promovido' "el repo $($rpath[$r]) está en $($rst[$r]) con $($abierto[$rpath[$r]]) gate(s) fuera de done"
  }
}
# `planned` solo es defecto si el reparto se aprobó, y esa señal es la existencia de un evento
# promover-repo: sin él, todo en planned es el estado correcto de una orquestación sin repartir.
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ($hayreparto -and $rst[$r] -ceq 'planned' -and $retiene[$rpath[$r]] -eq 0) {
    Falla 'repo-libre-sin-promover' "el repo $($rpath[$r]) sigue en planned y ninguna tarea gate lo retiene"
  }
}
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ($hayreparto -and $rst[$r] -ceq 'planned' -and $retiene[$rpath[$r]] -gt 0 -and $abierto[$rpath[$r]] -eq 0) {
    Falla 'gate-cerrado-sin-promover' "el repo $($rpath[$r]) sigue en planned con sus $($retiene[$rpath[$r]]) gate(s) en done"
  }
}
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ($rst[$r] -ceq 'tasks-ready' -and $retiene[$rpath[$r]] -gt 0 -and $abierto[$rpath[$r]] -eq 0 -and -not $despok.ContainsKey($rpath[$r])) {
    Falla 'gate-cerrado-sin-despachar' "el repo $($rpath[$r]) se promovió al cerrar su gate y nunca se despachó"
  }
}
# AC-8: con el baseline de su fila local sin medir no se despacha. Va ANTES de la correspondencia
# resultado ↔ transición porque nombra la causa: el despacho no debió ocurrir, y que además su
# evento diga otra cosa es consecuencia y no diagnóstico.
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ($planblocked.ContainsKey($rpath[$r]) -and (Despachado $rst[$r])) {
    Falla 'despacho-con-baseline-blocked' "el repo $($rpath[$r]) está en $($rst[$r]) con una fila de baseline BLOCKED en su contrato local"
  }
}
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ($planfile.ContainsKey($rpath[$r]) -and $planst[$rpath[$r]] -cne $rst[$r]) {
    Falla 'manifest-y-plan-divergen' "el repo $($rpath[$r]) vale $($rst[$r]) en el manifest y $($planst[$rpath[$r]]) en su plan.md"
  }
}

# ── la liberación del lock exige una decisión previa ─────────────────────────────────
for ($i = 0; $i -lt $eventos.Count; $i++) {
  if ($eventos[$i]['paso'] -cne 'liberar-lock' -or $eventos[$i]['resultado'] -cne 'consumado') { continue }
  $hay = $false
  for ($j = 0; $j -le $i; $j++) { if ($eventos[$j].ContainsKey('decision')) { $hay = $true } }
  if (-not $hay) {
    Falla 'liberacion-de-lock-sin-decision' "el evento $($eventos[$i]['id']) liberó el lock de $($eventos[$i]['objeto']) sin una decisión registrada antes"
  }
}

# ── resultado ↔ transición, en sus tres formas ───────────────────────────────────────
# Solo los pasos cuyo efecto es un estado del manifest: liberar-lock y ejecutar-evidencia no
# materializan ninguno, así que exigirles un cambio de estado sería inventarles un observable.
foreach ($e in $eventos) {
  $pa = "$($e['paso'])"; $ob = "$($e['objeto'])"; $re = "$($e['resultado'])"
  if ($pa -ceq 'cerrar-tarea') { $mat = $porid.ContainsKey($ob) -and $tareas[$porid[$ob] - 1].st -ceq 'done' }
  elseif ($pa -ceq 'despachar-repo') { $mat = $esrepo.ContainsKey($ob) -and (Despachado $rst[$esrepo[$ob] - 1]) }
  elseif ($pa -ceq 'promover-repo') { $mat = $esrepo.ContainsKey($ob) -and (Promovido $rst[$esrepo[$ob] - 1]) }
  else { continue }
  if ($re -ceq 'consumado' -and -not $mat) { Falla 'exito-sin-transicion' "el evento $($e['id']) consumó $pa sobre $ob y su estado no cambió" }
  if ($re -ceq 'rechazado' -and $mat) { Falla 'rechazo-con-transicion' "el evento $($e['id']) rechazó $pa sobre $ob y su estado cambió igual" }
}
foreach ($t in $tareas) {
  if ($t.st -ceq 'done' -and -not $cierreok.ContainsKey($t.id)) {
    Falla 'transicion-sin-evento' "la tarea $($t.id) está en done y ningún evento cerrar-tarea la consumó"
  }
}
for ($r = 0; $r -lt $rpath.Count; $r++) {
  if ((Despachado $rst[$r]) -and -not $despok.ContainsKey($rpath[$r])) {
    Falla 'transicion-sin-evento' "el repo $($rpath[$r]) está en $($rst[$r]) y ningún evento despachar-repo lo consumó"
  }
  if ((Promovido $rst[$r]) -and -not $promok.ContainsKey($rpath[$r])) {
    Falla 'transicion-sin-evento' "el repo $($rpath[$r]) está en $($rst[$r]) y ningún evento promover-repo lo consumó"
  }
}

# ── el gate del paso a done (AC-7 y AC-9) ────────────────────────────────────────────
$repl = @()
foreach ($t in $tareas) {
  if ($t.owner -cne 'UNASSIGNED') { continue }
  if ($t.st -ceq 'done') { Falla 'cierre-con-owner-unassigned' "la tarea $($t.id) (phase=$($t.phase)) cerró con owner UNASSIGNED" }
  else { $repl += $t.id }
}
foreach ($t in $tareas) {
  if ($t.st -cne 'done') { continue }
  foreach ($d in $t.deps) {
    if (-not $porid.ContainsKey($d) -or $tareas[$porid[$d] - 1].st -cne 'done') {
      Falla 'depends_on-insatisfecho' "la tarea $($t.id) cerró con $d fuera de done"
    }
  }
}
# Ni la evidencia ni el dueño se comparten: dos tareas que declaren la misma fila —o el mismo
# dueño de ejecución— no son dos cierres sino uno contado dos veces.
foreach ($e in $eventos) {
  if ($e['paso'] -ceq 'ejecutar-evidencia' -and $e['resultado'] -ceq 'consumado' -and $porfila["$($e['fila'])"] -gt 1) {
    Falla 'evidencia-duplicada' "la fila $($e['fila']) la ejecutan $($porfila["$($e['fila'])"]) eventos de tareas distintas"
  }
}
# UNASSIGNED es el centinela de un dueño pendiente, no un dueño: dos tareas sin asignar no son dos
# tareas con el mismo dueño, y AC-7 ya las bloquea por su lado.
for ($i = 0; $i -lt $tareas.Count; $i++) {
  if ($tareas[$i].owner -eq '' -or $tareas[$i].owner -ceq 'UNASSIGNED') { continue }
  for ($j = $i + 1; $j -lt $tareas.Count; $j++) {
    if ($tareas[$j].owner -ceq $tareas[$i].owner) {
      Falla 'dueno-duplicado' "las tareas $($tareas[$i].id) y $($tareas[$j].id) declaran el mismo owner $($tareas[$i].owner)"
    }
  }
}

# ── la frescura de la evidencia (AC-20) ──────────────────────────────────────────────
foreach ($t in $tareas) {
  if ($t.st -cne 'done' -or $t.fila -eq '') { continue }
  $e = $null; if ($evfila.ContainsKey($t.fila)) { $e = $evfila[$t.fila] }
  if ($null -ne $e -and $e['objeto'] -cne $t.id) {
    Falla 'evidencia-de-otra-tarea' "la fila $($t.fila) de $($t.id) la ejecutó un evento con objeto $($e['objeto'])"
  } elseif ($null -eq $e -and $evobj.ContainsKey($t.id)) {
    Falla 'evidencia-de-otra-fila' "la tarea $($t.id) cierra con $($t.fila) y su evidencia ejecutó $($evobj[$t.id]['fila'])"
  } elseif ($null -eq $e) {
    Falla 'evidencia-obsoleta' "la tarea $($t.id) cerró sin ningún evento ejecutar-evidencia de su fila $($t.fila)"
  }
}
foreach ($t in $tareas) {
  if ($t.st -cne 'done' -or $t.fila -eq '') { continue }
  if (-not $evfila.ContainsKey($t.fila)) { continue }
  $e = $evfila[$t.fila]
  if ($e['objeto'] -cne $t.id) { continue }
  if ($e['contrato'] -cne "v$($vnum[$vig])") {
    Falla 'evidencia-de-version-anterior' "la fila $($t.fila) se midió contra el contrato $($e['contrato']) y la versión vigente es v$($vnum[$vig])"
  }
  # El anclaje es uno u otro según de qué esté hecha la evidencia, y participating_repos es quien
  # lo decide: con repos participantes se mide un SHA por CADA uno, y sin ninguno el ancla
  # versionada declarada hace las veces y se revalida con la misma vara.
  if ($t.part.Count -gt 0) {
    $medido = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
    foreach ($par in ("$($e['sha'])" -split ',')) {
      $par = $par.Trim()
      if ($par -match '^([^=]*)=(.*)$') { if ($Matches[1] -ne '') { $medido[$Matches[1]] = $Matches[2] } }
    }
    foreach ($p in $t.part) {
      if (-not $medido.ContainsKey($p)) { Falla 'repo-relevante-sin-sha' "la tarea $($t.id) participa $p y su evidencia no lo mide" }
      elseif ($medido[$p] -cne $plansha[$p]) { Falla 'repo-cambiado-tras-medir' "la tarea $($t.id) midió $p en $($medido[$p]) y su plan.md declara $($plansha[$p])" }
    }
  } elseif (-not $e.ContainsKey('ancla')) {
    Falla 'ancla-versionada-ausente' "la tarea $($t.id) no participa ningún repo y su evidencia no declara ancla versionada"
  } else {
    $nom = "$($e['ancla'])"; $val = ''
    if ($nom -match '^([^=]*)=(.*)$') { $nom = $Matches[1]; $val = $Matches[2] }
    if (-not $ancla.ContainsKey($nom) -or $ancla[$nom] -cne $val) {
      $vigente = 'ninguna declarada'; if ($ancla.ContainsKey($nom)) { $vigente = $ancla[$nom] }
      Falla 'ancla-versionada-obsoleta' "la tarea $($t.id) midió $nom en $val y la vigente es $vigente"
    }
  }
  if ($e['observado'] -cne $t.esp) {
    Falla 'esperado-no-satisfecho' "la fila $($t.fila) esperaba [$($t.esp)] y observó [$($e['observado'])]"
  }
}
foreach ($t in $tareas) {
  if ($t.st -ceq 'done' -and $t.fila -ne '' -and $t.dw -cne $t.fila) {
    $dicho = $t.dw; if ($dicho -eq '') { $dicho = '—' }
    Falla 'done_when-no-referencia-su-fila' "la tarea $($t.id) cierra en la fila $($t.fila) y su done_when dice $dicho"
  }
}

if ($repl.Count -gt 0) {
  Write-Output 'REPORTE:owner-unassigned'
  Write-Output "  sin dueño asignado y sin cerrar: $($repl -join ', ')"
}
if ($G -ne '') {
  # El marcador va SOLO en su línea: el arnés lo compara entero, así que el dato medido vive abajo.
  # `[Console]::Error.WriteLine` y no `Write-Error`: los eventos van por stderr —es donde los lee
  # el arnés de paridad—, pero el renderizado de un ErrorRecord antepone su propio prefijo y la
  # línea deja de empezar por GUARD:. Escribir crudo en el canal da las dos cosas.
  [Console]::Error.WriteLine("GUARD:state $G")
  [Console]::Error.WriteLine("  $CTX")
  [Console]::Error.WriteLine("  manifest: $manifest")
  if ($condetalle) { foreach ($p in $pend) { [Console]::Error.WriteLine("DETALLE:$p") } }
  exit 1
}

# ── el estado agregado, por precedencia declarada ────────────────────────────────────
# Sale SOLO cuando no hubo hallazgo: sobre un modelo inválido no hay nada que agregar, y un
# `ESTADO:done` al lado de un `GUARD:` es un mensaje que contradice su propio veredicto.
# Se asigna de lo menos grave a lo más grave y gana la última: es la tabla de precedencia de la
# Fase 3 leída al revés, y por eso ningún estado puede ocultar a uno de rango menor.
$est = 'done'
foreach ($t in $tareas) { if ($t.st -cne 'done') { $est = 'no-verificado:integracion-pendiente' } }
foreach ($s in $rst) { if (-not (Verde $s)) { $est = 'en-curso' } }
foreach ($t in $tareas) { if ($t.phase -ceq 'gate' -and $t.st -ceq 'blocked') { $est = 'no-verificado:gate-blocked' } }
foreach ($s in $rst) { if ($s -ceq 'blocked') { $est = 'no-verificado:repo-blocked' } }
foreach ($s in $rst) { if ($s -ceq 'failed') { $est = 'no-verificado:repo-failed' } }
Write-Output "ESTADO:$est"
exit 0
# @fin:orchestration-state-ps
```

```bash
# @bloque:integracion-ownership
# Predicado: ninguna fila de un AC [integration] vive completa en el contrato de un repo, y cada
# repo referencia en solo-lectura EXACTAMENTE los AC en los que participating_repos lo declara
# participante —ni uno de menos ni uno de más, y ninguno cuando no participa en ninguno—, con la
# evidencia N/A: orchestration-owned y apuntando a la fila autoritativa V-<id-tarea>.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que mira la forma de cada
# fila antes que el conjunto del repo, porque son dos defectos distintos sobre la misma referencia.
# Entradas: $manifest (el manifest.yml) y $repos (uno o más plan.md por repo, separados por espacios)
[ -f "$manifest" ] || { printf 'ARNES:no existe el manifest %s\n' "$manifest" >&2; exit 99; }
for f in $repos; do
  [ -f "$f" ] || { printf 'ARNES:no existe el plan %s\n' "$f" >&2; exit 99; }
done
# El manifest es entrada y no un lujo: sin `participating_repos` no hay forma de saber quién
# participa, y exigirle a TODO plan.md una referencia deja en rojo al repo que no participa y a la
# orquestación sin AC [integration] entera — el caso retrocompatible, que es correcto por diseño.
awk -v MF="$manifest" '
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
function desnudo(s,   c) {
  s = trim(s)
  if (length(s) >= 2) {
    c = substr(s, 1, 1)
    if ((c == "\"" || c == Q) && substr(s, length(s), 1) == c) s = substr(s, 2, length(s) - 2)
  }
  return trim(s)
}
function sincom(s,   c, i, n) {
  s = trim(s); c = substr(s, 1, 1)
  if (c == "\"" || c == Q) {
    n = length(s)
    for (i = 2; i <= n; i++) if (substr(s, i, 1) == c) return substr(s, 1, i)
    return s
  }
  if (match(s, /[ \t]#/)) s = substr(s, 1, RSTART - 1)
  return trim(s)
}
function lista(v, arr,   n, i, x, tmp) {
  delete arr
  v = trim(v); sub(/^\[/, "", v); sub(/\]$/, "", v); v = trim(v)
  if (v == "") return 0
  n = split(v, tmp, ","); x = 0
  for (i = 1; i <= n; i++) if (desnudo(tmp[i]) != "") arr[++x] = desnudo(tmp[i])
  return x
}
function falla(m, ctx, arch) { if (G == "") { G = m; CTX = ctx; ARCH = arch } }
# La fila que nombra la observación `ver V-<id-tarea> de integracion.md`. Vacía cuando no nombra
# ninguna, que es lo mismo que nombrar la equivocada: la referencia no lleva a la fila autoritativa.
function refdela(s) { if (match(s, /V-[A-Za-z0-9_.-]+/)) return substr(s, RSTART, RLENGTH); return "" }
function junta(a, n,   i, s) { s = ""; for (i = 1; i <= n; i++) s = s (i > 1 ? ", " : "") a[i]; return s }

BEGIN { Q = sprintf("%c", 39); OWNED = "N/A: orchestration-owned"; VIEJO = "N/A: Fase 3" }

# ── manifest: covers_ac y el mapa de participación de cada tarea ─────────────────────
# La columna manda, igual que en `orchestration-model`: un campo de la tarea está a la altura de su
# `id:`, y lo que cuelgue más a la derecha pertenece al último campo abierto. Sin eso una clave del
# mapa de participación es indistinguible de un campo de la tarea.
FILENAME == MF {
  if ($0 ~ /^[ \t]*#/) next
  if ($0 ~ /^[^ \t]/) { sec = ($0 ~ /^orchestration_tasks:[ \t]*(#.*)?$/) ? "tasks" : ""; next }
  if (sec != "tasks") next
  ind = match($0, /[^ \t]/); if (ind == 0) next
  if (match($0, /^[ \t]*-[ \t]*id:[ \t]*/)) {
    nt++; indcampo = index($0, "id:"); campo = ""; enmapa = 0
    tid[nt] = desnudo(sincom(substr($0, RSTART + RLENGTH)))
    next
  }
  if (!nt) next
  if (ind > indcampo) {
    if (enmapa) {
      if ($0 ~ /^[ \t]*-[ \t]/) {                                  # repo de la clave abierta
        match($0, /^[ \t]*-[ \t]*/)
        if (pn[nt] > 0) { j = pn[nt]; pv[nt, j, ++pvn[nt, j]] = desnudo(sincom(substr($0, RSTART + RLENGTH))) }
      } else if (match($0, /^[ \t]*[^ \t:]+:[ \t]*/)) {            # una clave del mapa
        k = substr($0, RSTART, RLENGTH); sub(/:[ \t]*$/, "", k)
        pk[nt, ++pn[nt]] = desnudo(k)
        pvn[nt, pn[nt]] = lista(sincom(substr($0, RSTART + RLENGTH)), tmpa)
        for (i = 1; i <= pvn[nt, pn[nt]]; i++) pv[nt, pn[nt], i] = tmpa[i]
      }
    } else if (campo == "covers_ac" && $0 ~ /^[ \t]*-[ \t]/) {     # covers_ac en bloque
      match($0, /^[ \t]*-[ \t]*/)
      cov[nt, ++cn[nt]] = desnudo(sincom(substr($0, RSTART + RLENGTH)))
    }
    next
  }
  if (ind != indcampo) next
  if (!match($0, /^[ \t]*[A-Za-z_][A-Za-z0-9_]*:/)) next
  campo = substr($0, RSTART, RLENGTH); sub(/:$/, "", campo); campo = trim(campo)
  v = sincom(substr($0, RSTART + RLENGTH)); enmapa = 0
  if (campo == "participating_repos") { if (v == "") enmapa = 1; next }
  if (campo == "covers_ac") {
    cn[nt] = lista(v, tmpa)
    for (i = 1; i <= cn[nt]; i++) cov[nt, i] = tmpa[i]
  }
  next
}

# ── plan.md por repo: sus filas de AC [integration] ──────────────────────────────────
# Se leen las FILAS, no las menciones: el AC aparece igual en la lista de criterios del plan, así
# que buscar en el archivo entero daría verde con la fila borrada.
{
  if (FNR == 1) { np++; arch[np] = FILENAME; fm = 0 }
  if ($0 ~ /^---[ \t]*$/) { fm++; next }
  if (fm == 1) {
    if (match($0, /^repo:[ \t]*/)) rep[np] = trim(substr($0, RSTART + RLENGTH))
    next
  }
  if ($0 !~ /^[ \t]*\|/) next
  if ($0 ~ /^[ \t]*\|[ \t]*ID[ \t]*\|/) next
  if ($0 ~ /^[ \t]*\|[-: \t|]+\|[ \t]*$/) next
  if (index($0, "[integration]") == 0) next
  # Una fila de seis columnas parte en ocho campos: el vacío de cada extremo cuenta. Con menos no
  # tiene el esquema canónico, y esa forma la valida `contrato-verificacion.md`, que es su dueño.
  n = split($0, c, "[|]")
  if (n < 8) next
  if (!match(c[3], /AC-[0-9]+/)) next
  k = ++fn[np]
  fac[np, k] = substr(c[3], RSTART, RLENGTH)
  fev[np, k] = trim(c[4]); fobs[np, k] = trim(c[5]); fbl[np, k] = trim(c[7])
}

END {
  # ── índices derivados del manifest ─────────────────────────────────────────────────
  # La fila autoritativa de un AC es la de la tarea que lo cubre; que sea UNA sola lo garantiza
  # `orchestration-model`, así que acá alcanza con la primera.
  for (t = 1; t <= nt; t++)
    for (i = 1; i <= cn[t]; i++)
      if (!(cov[t, i] in autoritativa)) autoritativa[cov[t, i]] = "V-" tid[t]
  for (t = 1; t <= nt; t++)
    for (j = 1; j <= pn[t]; j++)
      for (i = 1; i <= pvn[t, j]; i++)
        if (!((pv[t, j, i], pk[t, j]) in participa)) {
          participa[pv[t, j, i], pk[t, j]] = 1
          espl[pv[t, j, i], ++espn[pv[t, j, i]]] = pk[t, j]
        }

  # ── la forma de cada referencia ────────────────────────────────────────────────────
  # Va primero que el conjunto: una fila con evidencia local SÍ referencia su AC, mal escrita, y
  # tratarla como ausente reportaría el defecto equivocado.
  for (p = 1; p <= np; p++) {
    if (rep[p] == "") { print "ARNES:el plan " arch[p] " no declara repo: en su frontmatter"; exit 99 }
    for (k = 1; k <= fn[p]; k++) {
      ac = fac[p, k]
      if (!((p, ac) in vista)) { vista[p, ac] = 1; presl[p, ++presn[p]] = ac }
      if (index(fev[p, k], VIEJO) || index(fbl[p, k], VIEJO))
        falla("referencia-obsoleta-fase-3", "el repo " rep[p] " referencia " ac " con el literal viejo, que anuncia una fase y no un dueño", arch[p])
      else if (index(fev[p, k], "NOT_APPLICABLE") || index(fbl[p, k], "NOT_APPLICABLE"))
        falla("fila-integration-not-applicable", "el repo " rep[p] " marca NOT_APPLICABLE la fila de " ac ", que borraría una obligación global", arch[p])
      else if (fev[p, k] != OWNED || fbl[p, k] != OWNED)
        falla("fila-integration-con-evidencia-local", "el repo " rep[p] " cierra " ac " de su lado: evidencia [" fev[p, k] "] y baseline [" fbl[p, k] "]", arch[p])
      else {
        rf = refdela(fobs[p, k])
        if (autoritativa[ac] != "" && rf != autoritativa[ac])
          falla("referencia-a-fila-equivocada", "el repo " rep[p] " referencia " ac " apuntando a [" rf "], y su fila autoritativa es " autoritativa[ac], arch[p])
      }
    }
  }

  # ── el conjunto exacto por repo, en las dos direcciones ────────────────────────────
  # Cero referencias es correcto cuando el conjunto esperado es vacío: el repo que no participa y
  # la orquestación sin AC [integration] pasan por la misma puerta.
  for (p = 1; p <= np; p++) {
    nf = 0
    for (i = 1; i <= espn[rep[p]]; i++) if (!((p, espl[rep[p], i]) in vista)) falt[++nf] = espl[rep[p], i]
    if (nf > 0)
      falla("referencia-esperada-ausente", "el repo " rep[p] " participa en " junta(falt, nf) " y no lo referencia", arch[p])
  }
  for (p = 1; p <= np; p++) {
    ns = 0
    for (k = 1; k <= presn[p]; k++) if (!((rep[p], presl[p, k]) in participa)) sob[++ns] = presl[p, k]
    if (ns > 0)
      falla("referencia-en-repo-no-participante", "el repo " rep[p] " referencia " junta(sob, ns) ", y participating_repos no lo declara participante", arch[p])
  }

  if (G == "") exit 0
  # El marcador va SOLO en su línea: el arnés lo compara entero, así que el repo y los AC van abajo.
  print "GUARD:integracion " G
  print "  " CTX
  print "  plan: " ARCH
  exit 1
}
' "$manifest" $repos >&2
exit $?
# @fin:integracion-ownership
```

```powershell
# @bloque:integracion-ownership-ps
# Predicado: ninguna fila de un AC [integration] vive completa en el contrato de un repo, y cada
# repo referencia en solo-lectura EXACTAMENTE los AC en los que participating_repos lo declara
# participante —ni uno de menos ni uno de más, y ninguno cuando no participa en ninguno—, con la
# evidencia N/A: orchestration-owned y apuntando a la fila autoritativa V-<id-tarea>.
# Un solo diagnóstico por corrida: gana el primero del orden de abajo, que mira la forma de cada
# fila antes que el conjunto del repo, porque son dos defectos distintos sobre la misma referencia.
# Entradas: $manifest (el manifest.yml) y $repos (uno o más plan.md por repo, separados por espacios)
if (-not (Test-Path -LiteralPath $manifest)) { [Console]::Error.WriteLine("ARNES:no existe el manifest $manifest"); exit 99 }
$planes = @($repos -split '\s+' | Where-Object { $_ })
foreach ($f in $planes) {
  if (-not (Test-Path -LiteralPath $f)) { [Console]::Error.WriteLine("ARNES:no existe el plan $f"); exit 99 }
}
$Q = [char]39
$OWNED = 'N/A: orchestration-owned'
$VIEJO = 'N/A: Fase 3'
function Desnudo($s) {
  $s = "$s".Trim()
  if ($s.Length -ge 2) {
    $c = $s[0]
    if (($c -eq '"' -or $c -eq $Q) -and $s[$s.Length - 1] -eq $c) { $s = $s.Substring(1, $s.Length - 2) }
  }
  return $s.Trim()
}
function Sincom($s) {
  $s = "$s".Trim()
  if ($s.Length -gt 0 -and ($s[0] -eq '"' -or $s[0] -eq $Q)) {
    $cierre = $s.IndexOf($s[0], 1)
    if ($cierre -ge 0) { return $s.Substring(0, $cierre + 1) }
    return $s
  }
  $m = [regex]::Match($s, '[ \t]#')
  if ($m.Success) { $s = $s.Substring(0, $m.Index) }
  return $s.Trim()
}
# La coma del `return` NO es adorno: `return @()` devuelve $null y el `+=` siguiente produciría una
# cadena en vez de una lista. Con la coma vuelve el arreglo, vacío incluido.
function Lista($v) {
  $v = "$v".Trim()
  if ($v.StartsWith('[')) { $v = $v.Substring(1) }
  if ($v.EndsWith(']')) { $v = $v.Substring(0, $v.Length - 1) }
  $v = $v.Trim()
  if ($v -eq '') { return , @() }
  return , @($v -split ',' | ForEach-Object { Desnudo $_ } | Where-Object { $_ -ne '' })
}
$G = ''; $CTX = ''; $ARCH = ''
function Falla($m, $ctx, $arch) {
  if ($script:G -eq '') { $script:G = $m; $script:CTX = $ctx; $script:ARCH = $arch }
}
# La fila que nombra la observación `ver V-<id-tarea> de integracion.md`. Vacía cuando no nombra
# ninguna, que es lo mismo que nombrar la equivocada: la referencia no lleva a la fila autoritativa.
function RefDeLa($s) {
  $m = [regex]::Match("$s", 'V-[A-Za-z0-9_.-]+')
  if ($m.Success) { return $m.Value }
  return ''
}

# ── manifest: covers_ac y el mapa de participación de cada tarea ─────────────────────
# La columna manda, igual que en `orchestration-model`: un campo de la tarea está a la altura de su
# `id:`, y lo que cuelgue más a la derecha pertenece al último campo abierto. Sin eso una clave del
# mapa de participación es indistinguible de un campo de la tarea.
$tareas = @(); $t = $null; $sec = ''; $indcampo = 0; $campo = ''; $enmapa = $false
foreach ($ln in (Get-Content -LiteralPath $manifest)) {
  if ($ln -match '^[ \t]*#') { continue }
  if ($ln -match '^[^ \t]') {
    $sec = ''
    if ($ln -match '^orchestration_tasks:[ \t]*(#.*)?$') { $sec = 'tasks' }
    continue
  }
  if ($sec -ne 'tasks' -or $ln.Trim() -eq '') { continue }
  $ind = ($ln -replace '^([ \t]*).*$', '$1').Length + 1
  if ($ln -match '^[ \t]*-[ \t]*id:[ \t]*(.*)$') {
    $t = @{ id = (Desnudo (Sincom $Matches[1])); cov = @(); pk = @(); pv = @() }
    $tareas += , $t
    $indcampo = $ln.IndexOf('id:') + 1; $campo = ''; $enmapa = $false
    continue
  }
  if ($null -eq $t) { continue }
  if ($ind -gt $indcampo) {
    if ($enmapa) {
      if ($ln -match '^[ \t]*-[ \t](.*)$') {                          # repo de la clave abierta
        if ($t.pk.Count -gt 0) { $t.pv[$t.pv.Count - 1] += (Desnudo (Sincom $Matches[1])) }
      } elseif ($ln -match '^[ \t]*([^ \t:]+):[ \t]*(.*)$') {          # una clave del mapa
        $t.pk += (Desnudo $Matches[1]); $t.pv += , (Lista (Sincom $Matches[2]))
      }
    } elseif ($campo -eq 'covers_ac' -and $ln -match '^[ \t]*-[ \t](.*)$') {   # covers_ac en bloque
      $t.cov += (Desnudo (Sincom $Matches[1]))
    }
    continue
  }
  if ($ind -ne $indcampo) { continue }
  if ($ln -notmatch '^[ \t]*([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$') { continue }
  $campo = $Matches[1]; $v = Sincom $Matches[2]; $enmapa = $false
  if ($campo -eq 'participating_repos') { if ($v -eq '') { $enmapa = $true }; continue }
  if ($campo -eq 'covers_ac') { $t.cov = Lista $v }
}

# ── plan.md por repo: sus filas de AC [integration] ──────────────────────────────────
# Se leen las FILAS, no las menciones: el AC aparece igual en la lista de criterios del plan, así
# que buscar en el archivo entero daría verde con la fila borrada.
$planinfo = @()
foreach ($pf in $planes) {
  $info = @{ arch = $pf; repo = ''; filas = @(); vistas = @() }
  $fm = 0
  foreach ($ln in (Get-Content -LiteralPath $pf)) {
    if ($ln -match '^---[ \t]*$') { $fm++; continue }
    if ($fm -eq 1) {
      if ($ln -match '^repo:[ \t]*(.*)$') { $info.repo = $Matches[1].Trim() }
      continue
    }
    if ($ln -notmatch '^[ \t]*\|') { continue }
    if ($ln -match '^[ \t]*\|[ \t]*ID[ \t]*\|') { continue }
    if ($ln -match '^[ \t]*\|[-: \t|]+\|[ \t]*$') { continue }
    if ($ln -notmatch '\[integration\]') { continue }
    # Una fila de seis columnas parte en ocho campos: el vacío de cada extremo cuenta. Con menos no
    # tiene el esquema canónico, y esa forma la valida `contrato-verificacion.md`, que es su dueño.
    $c = $ln -split '\|'
    if ($c.Count -lt 8) { continue }
    $m = [regex]::Match($c[2], 'AC-[0-9]+')
    if (-not $m.Success) { continue }
    $info.filas += , @{ ac = $m.Value; ev = $c[3].Trim(); obs = $c[4].Trim(); bl = $c[6].Trim() }
  }
  $planinfo += , $info
}

# ── índices derivados del manifest ───────────────────────────────────────────────────
# La fila autoritativa de un AC es la de la tarea que lo cubre; que sea UNA sola lo garantiza
# `orchestration-model`, así que acá alcanza con la primera.
# Diccionarios ORDINALES y no `@{}`: una hashtable de PowerShell compara sus claves sin
# distinguir mayúsculas, así que fundiría `API` con `api` y daría por participante a un repo
# que el manifest nombra de otra forma. Los arreglos de awk se indexan por bytes.
$autoritativa = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
foreach ($t in $tareas) {
  foreach ($ac in $t.cov) { if (-not $autoritativa.ContainsKey($ac)) { $autoritativa[$ac] = "V-$($t.id)" } }
}
$participa = [Collections.Generic.Dictionary[string, bool]]::new([StringComparer]::Ordinal)
$esperado  = [Collections.Generic.Dictionary[string, object]]::new([StringComparer]::Ordinal)
foreach ($t in $tareas) {
  for ($j = 0; $j -lt $t.pk.Count; $j++) {
    foreach ($r in @($t.pv[$j])) {
      $clave = "$r|$($t.pk[$j])"
      if (-not $participa.ContainsKey($clave)) {
        $participa[$clave] = $true
        if (-not $esperado.ContainsKey($r)) { $esperado[$r] = @() }
        $esperado[$r] += $t.pk[$j]
      }
    }
  }
}

# ── la forma de cada referencia ──────────────────────────────────────────────────────
# Va primero que el conjunto: una fila con evidencia local SÍ referencia su AC, mal escrita, y
# tratarla como ausente reportaría el defecto equivocado.
foreach ($p in $planinfo) {
  if ($p.repo -eq '') { [Console]::Error.WriteLine("ARNES:el plan $($p.arch) no declara repo: en su frontmatter"); exit 99 }
  foreach ($f in $p.filas) {
    if (-not ($p.vistas -ccontains $f.ac)) { $p.vistas += $f.ac }
    if ($f.ev.Contains($VIEJO) -or $f.bl.Contains($VIEJO)) {
      Falla 'referencia-obsoleta-fase-3' "el repo $($p.repo) referencia $($f.ac) con el literal viejo, que anuncia una fase y no un dueño" $p.arch
    } elseif ($f.ev.Contains('NOT_APPLICABLE') -or $f.bl.Contains('NOT_APPLICABLE')) {
      Falla 'fila-integration-not-applicable' "el repo $($p.repo) marca NOT_APPLICABLE la fila de $($f.ac), que borraría una obligación global" $p.arch
    } elseif ($f.ev -cne $OWNED -or $f.bl -cne $OWNED) {
      Falla 'fila-integration-con-evidencia-local' "el repo $($p.repo) cierra $($f.ac) de su lado: evidencia [$($f.ev)] y baseline [$($f.bl)]" $p.arch
    } else {
      $rf = RefDeLa $f.obs
      if ($autoritativa.ContainsKey($f.ac) -and $rf -cne $autoritativa[$f.ac]) {
        Falla 'referencia-a-fila-equivocada' "el repo $($p.repo) referencia $($f.ac) apuntando a [$rf], y su fila autoritativa es $($autoritativa[$f.ac])" $p.arch
      }
    }
  }
}

# ── el conjunto exacto por repo, en las dos direcciones ──────────────────────────────
# Cero referencias es correcto cuando el conjunto esperado es vacío: el repo que no participa y la
# orquestación sin AC [integration] pasan por la misma puerta.
foreach ($p in $planinfo) {
  $falta = @()
  if ($esperado.ContainsKey($p.repo)) {
    foreach ($ac in $esperado[$p.repo]) { if (-not ($p.vistas -ccontains $ac)) { $falta += $ac } }
  }
  if ($falta.Count -gt 0) {
    Falla 'referencia-esperada-ausente' "el repo $($p.repo) participa en $($falta -join ', ') y no lo referencia" $p.arch
  }
}
foreach ($p in $planinfo) {
  $sobra = @()
  foreach ($ac in $p.vistas) { if (-not $participa.ContainsKey("$($p.repo)|$ac")) { $sobra += $ac } }
  if ($sobra.Count -gt 0) {
    Falla 'referencia-en-repo-no-participante' "el repo $($p.repo) referencia $($sobra -join ', '), y participating_repos no lo declara participante" $p.arch
  }
}

if ($G -eq '') { exit 0 }
# El marcador va SOLO en su línea: el arnés lo compara entero, así que el repo y los AC van abajo.
# `[Console]::Error.WriteLine` y no `Write-Error`: los eventos van por stderr —es donde los lee
# el arnés de paridad—, pero el renderizado de un ErrorRecord antepone su propio prefijo y la
# línea deja de empezar por GUARD:. Escribir crudo en el canal da las dos cosas.
[Console]::Error.WriteLine("GUARD:integracion $G")
[Console]::Error.WriteLine("  $CTX")
[Console]::Error.WriteLine("  plan: $ARCH")
exit 1
# @fin:integracion-ownership-ps
```

```bash
# @bloque:gate-fase-3
# Predicado: la Fase 3 revalida la versión vigente del contrato antes de ejecutar evidencia y nunca
# agrega ni quita IDs —la invariancia del conjunto entre versiones la hace cumplir el bloque
# `orchestration-contract`; acá se comprueba que el documento lo declare así y no como un
# congelado de la Fase 3—, y la agregación no puede dar verde con filas ausentes o BLOCKED.
# Entradas: $skill_orq (el SKILL.md de sdd-orchestrator)
[ -f "$skill_orq" ] || { printf 'ARNES:no existe %s\n' "$skill_orq" >&2; exit 99; }
rc=0
grep -q 'Gate de apertura del contrato de integración' "$skill_orq" || {
  echo "GUARD:gate-fase-3 sin-gate-de-apertura" >&2
  echo "  la Fase 3 no declara el gate previo a ejecutar evidencia" >&2; rc=1; }
# Un solo marcador para las dos mitades. El documento tiene que declarar la revalidación Y no
# conservar el congelado anclado a esta fase: emitirlas por separado daría DOS líneas GUARD: ante un
# documento migrado a medias —el que dice las dos cosas—, y el arnés compara una línea entera.
if ! grep -q 'revalida la versión vigente' "$skill_orq" \
   || grep -q 'Congelarlo \*\*antes\*\*' "$skill_orq"; then
  echo "GUARD:gate-fase-3 no-revalida-version-vigente" >&2
  echo "  la Fase 3 no declara que revalida la versión vigente del contrato antes de ejecutar evidencia" >&2
  rc=1
fi
grep -q 'no verificado' "$skill_orq" || {
  echo "GUARD:gate-fase-3 sin-veredicto-no-verificado" >&2
  echo "  la agregación no declara que una fila ausente impide el verde" >&2; rc=1; }
exit $rc
# @fin:gate-fase-3
```

```powershell
# @bloque:gate-fase-3-ps
# Predicado: la Fase 3 revalida la versión vigente del contrato antes de ejecutar evidencia y nunca
# agrega ni quita IDs —la invariancia del conjunto entre versiones la hace cumplir el bloque
# `orchestration-contract`; acá se comprueba que el documento lo declare así y no como un
# congelado de la Fase 3—, y la agregación no puede dar verde con filas ausentes o BLOCKED.
# Entradas: $skill_orq (el SKILL.md de sdd-orchestrator)
if (-not (Test-Path -LiteralPath $skill_orq)) { [Console]::Error.WriteLine("ARNES:no existe $skill_orq"); exit 99 }
$rc = 0
$doc = (Get-Content -LiteralPath $skill_orq) -join "`n"
# `[Console]::Error.WriteLine` y no `Write-Error`: los eventos van por stderr —es donde los lee
# el arnés de paridad—, pero el renderizado de un ErrorRecord antepone su propio prefijo y la
# línea deja de empezar por GUARD:. Escribir crudo en el canal da las dos cosas.
# Los operadores van en su variante case-sensitive: el par POSIX busca con `grep -q`, que distingue
# mayúsculas. Con el operador por defecto de .NET, un `no Verificado` en la skill daría por cumplida
# la cláusula, y un `Congelarlo **antes**` que sobrevivió en otra caja dejaría de detectarse.
if ($doc -cnotmatch 'Gate de apertura del contrato de integración') {
  [Console]::Error.WriteLine('GUARD:gate-fase-3 sin-gate-de-apertura')
  [Console]::Error.WriteLine('  la Fase 3 no declara el gate previo a ejecutar evidencia')
  $rc = 1
}
# Un solo marcador para las dos mitades. El documento tiene que declarar la revalidación Y no
# conservar el congelado anclado a esta fase: emitirlas por separado daría DOS líneas GUARD: ante un
# documento migrado a medias —el que dice las dos cosas—, y el arnés compara una línea entera.
if (($doc -cnotmatch 'revalida la versión vigente') -or ($doc -cmatch 'Congelarlo \*\*antes\*\*')) {
  [Console]::Error.WriteLine('GUARD:gate-fase-3 no-revalida-version-vigente')
  [Console]::Error.WriteLine('  la Fase 3 no declara que revalida la versión vigente del contrato antes de ejecutar evidencia')
  $rc = 1
}
if ($doc -cnotmatch 'no verificado') {
  [Console]::Error.WriteLine('GUARD:gate-fase-3 sin-veredicto-no-verificado')
  [Console]::Error.WriteLine('  la agregación no declara que una fila ausente impide el verde')
  $rc = 1
}
exit $rc
# @fin:gate-fase-3-ps
```
