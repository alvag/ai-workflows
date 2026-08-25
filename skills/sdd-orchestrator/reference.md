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

## Resolución del intérprete de Python

Antes de ejecutar un script Python de la skill, resolver Python 3.9 o superior mediante una prueba
ejecutable. La presencia del nombre en `PATH` no alcanza: cada candidato debe correr código con
`-c`. El wrapper resultante conserva `py -3` como dos argumentos.

<!-- resolvedor-python:inicio -->
```sh
resolve_skill_python() {
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
      >/dev/null 2>&1; then
    python_skill() { python3 "$@"; }
    PYTHON_SKILL='python3'
    return 0
  fi
  if py -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' \
      >/dev/null 2>&1; then
    python_skill() { py -3 "$@"; }
    PYTHON_SKILL='py -3'
    return 0
  fi
  printf '%s\n' \
    'ERROR: no executable Python 3.9+; python3 -c and py -3 -c failed or reported an older version' \
    >&2
  return 1
}
resolve_skill_python || exit 1
# Run scripts as: python_skill <script> [arguments...]
```

```powershell
$script:PythonSkill = $null
$PythonCandidates = @(
  @{ Display = 'python3'; File = 'python3'; Prefix = @() },
  @{ Display = 'py -3'; File = 'py'; Prefix = @('-3') }
)
foreach ($Candidate in $PythonCandidates) {
  try {
    $Prefix = @($Candidate.Prefix)
    & $Candidate.File @Prefix -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' *> $null
    if ($LASTEXITCODE -eq 0) {
      $script:PythonSkill = $Candidate
      break
    }
  } catch {
    continue
  }
}
if ($null -eq $script:PythonSkill) {
  throw 'ERROR: no executable Python 3.9+; python3 -c and py -3 -c failed or reported an older version'
}
function Invoke-SkillPython {
  $Prefix = @($script:PythonSkill.Prefix)
  & $script:PythonSkill.File @Prefix @args
}
# Run scripts as: Invoke-SkillPython <script> [arguments...]
```
<!-- resolvedor-python:fin -->


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

## Validación de la integración

Los consumidores ejecutan los módulos Python canónicos sobre el reparto y el contrato de
integración.

Los escenarios contra los que corren esos predicados los materializa una **fábrica única**:
`python_skill <repo>/tests/fabricas/orquestacion.py <escenario>`. Deja sus artefactos en el directorio
actual y escribe `env.sh` y `env.ps1`; un solo cuerpo decide qué es cada escenario y todas las
guardas consumen exactamente el mismo material.


`python_skill <skill_dir>/scripts/orchestration-model.py <manifest> <master-spec>` valida el reparto
contra la master-spec: es la guarda que caza el AC
`[integration]` sin dueño. Lee dos artefactos —el `manifest.yml` y la `master-spec.md`— y emite **un
solo diagnóstico por corrida**: el primero del orden en que están escritas sus comprobaciones, que
va de la identidad de la tarea a los enums, de ahí al grafo, después a la ubicación de cada AC y al
final al mapa de participación. Ese orden no es cosmético. Dos comprobaciones correctas pueden ver
el mismo defecto —un AC `[repo-local]` en el `covers_ac` de una tarea es, a la vez, una clave de
participación que no es `[integration]`— y emitir las dos convierte un defecto en dos hallazgos, sin
decir cuál de los dos es el que hay que arreglar.



`python_skill <skill_dir>/scripts/orchestration-contract.py <manifest> <contrato>` valida la otra
mitad del reparto: el **enlace tarea ↔ fila**. Lee el
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



`python_skill <skill_dir>/scripts/orchestration-state.py <manifest> <master-spec> <contrato>
<bitácora> <planes-repo>` es la única de las tres que lee la **bitácora**, y por eso la única que
juzga **acciones** en vez de estados. El caso que lo resume: el estado final de dos repos puede ser
idéntico —uno esperó a que se cerrara su gate, el otro se despachó igual y volvió— y lo único que los
distingue es qué eventos quedaron registrados y en qué orden. De ahí que varios de sus rojos tengan
un control verde equivalente que difiere solo en el `resultado` del evento: un despacho `consumado`
con el gate abierto falla, y el mismo intento `rechazado` pasa limpio.

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
