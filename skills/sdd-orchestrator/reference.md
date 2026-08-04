# sdd-orchestrator — Referencia

Detalle operativo de la skill `sdd-orchestrator`. El `SKILL.md` apunta acá cuando necesita esquemas, plantillas, la matriz de detección o los algoritmos del lock y la cascada.

## Tabla de contenidos

- [Matriz de detección de repos](#matriz-de-detección-de-repos)
- [Esquema de `manifest.yml`](#esquema-de-manifestyml)
- [Transporte de las corridas delegadas](#transporte-de-las-corridas-delegadas)
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
implement_mode: ""             # opcional; modo de implementación que heredan los sdd-flow delegados: inline | subagent | cross (vacío → cada sdd-flow resuelve el suyo: config del repo > default). `cross` exige la capacidad (skill cross-implement + CLI de la otra familia) en el contexto del agente delegado
# outcome: aborted             # solo si la orquestación terminó abortada (sub-paso `abort`)
cross_review:                  # opcional; segunda opinión cross-model EN LOS GATES (ver skill cross-review)
  mode: auto                   # auto | "on" | "off"  (entre comillas: sin ellas YAML los parsea como booleanos)
  execution: auto              # auto (por capacidad del conductor) | sync | background
  artifacts: [master-spec, reparto]
  max_rounds: 3
co_explore: {mode: auto, deadline: 600}  # co-exploración cross-repo ANTES del reparto; ORTOGONAL a cross_review (bloque hermano, no anidado); default on en orquestación; ver SKILL.md → Co-exploración cross-model
cross_model: {schema_version: 1, transport: cli}  # opcional; intención de transporte que heredan los sdd-flow delegados para SUS corridas delegadas: cli (default) | herdr — nunca para el fan-out por repos. `schema_version` es obligatorio si el bloque existe; ver "Transporte de las corridas delegadas"
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
```

El `branch` de cada repo se computa al hacer el reparto resolviendo el prefijo con precedencia **`branch_prefix` local del repo (`<repo>/.specify/config.yml`) > `branch_prefix` de la orquestación (este `manifest.yml`) > prefijo semántico**. Por eso dos repos de la misma orquestación pueden tener prefijos distintos (uno con config local, otro no).

### Valores de `status`

Reusa el ciclo de `sdd-flow` por-repo, más dos estados **propios del orquestador**:

```
planned → tasks-ready → implementing → verified → committed → pushed → (pr-open) → done
                                   ↘ failed        (propio del orquestador)
                                   ↘ blocked       (propio del orquestador: dependía de un failed)
```

- `planned … done` — idénticos a `sdd-flow` (el `plan.md` del repo es la fuente fina). Incluye el
  opcional `pr-open` (el usuario abrió el PR del repo vía `sdd-flow`): cuenta como **terminal verde**
  para el lock, la elegibilidad del DAG y el `archive`.
- `failed` — el agente del repo no logró dejarlo verde (tests/build rojos o AC no cumplido). No se commitea.
- `blocked` — el repo no arrancó porque un `depends_on` quedó `failed`.

`failed`/`blocked` viven solo en el `manifest.yml`; `sdd-flow` no los conoce.

**Este esquema mezcla estado de corrida (`id`, `created_at`, `master_spec`, `repos`) con
configuración.** Las claves de configuración son propias de esta skill (`branch_prefix`,
`execution_mode`, `implement_mode`) salvo `cross_review.*`, `co_explore.*` y `cross_model.*`, cuyo
enum lo define su dueño: `cross_review.*` en `cross-review/SKILL.md` → "Configuración";
`co_explore.*` en `co-explore/SKILL.md` → "Configuración"; `cross_model.*` en
`sdd-flow/reference.md` → "Esquema de `.specify/config.yml`". Solo esas 11 claves, listas para
copiar y con la misma vista que `config-ejemplo.md` de `sdd-flow`, están en `manifest-ejemplo.md`.

## Transporte de las corridas delegadas

`cross_model.transport` del `manifest.yml` es la **intención** de transporte de la orquestación: dónde se alojan las corridas delegadas (`co-explore`, `cross-review`, `cross-implement`) que corren **dentro de cada repo**. El predicado de **capacidad** y la durabilidad del override son los de `sdd-flow` (`sdd-flow/reference.md` → "Transporte de las corridas delegadas"), heredados por puntero y no re-especificados acá; la mecánica y la sintaxis del multiplexor tampoco se copian: la autoridad es su skill externa.

**La precedencia es un orden total de cinco niveles**, no dos criterios que el lector tenga que combinar. Se recorre de arriba hacia abajo y gana el **primer nivel presente**:

| # | Nivel | Sede |
|---|---|---|
| 1 | override conversacional **específico del repo** | la sesión de la orquestación ("en `<repo>` por CLI") |
| 2 | override conversacional **global** | la sesión de la orquestación ("todo en panes") |
| 3 | **config del repo** | `<repo>/.specify/config.yml` → `cross_model.transport` (el proyecto manda sobre la orquestación, igual que con `branch_prefix`) |
| 4 | **config de la orquestación** | este `manifest.yml` → `cross_model.transport` |
| 5 | **default** | `cli` |

Los cinco niveles fijan los dos ejes de una sola vez —**fuente** (override sobre config) y **nivel** (repo sobre global)—, así que ninguna combinación queda sin resolver. El valor resuelto **se persiste** en el nivel del orquestador (nivel 4, lo único que sobrevive a una sesión nueva) y **llega a cada** `sdd-flow` delegado por el prompt del fan-out (línea `Override de esta corrida: transport: <valor>`), que lo trata como el override conversacional de **su** corrida.

**El fan-out por repos del orquestador está excluido, y no es un olvido.** El despacho de los agentes por repo **no se convierte a panes** en ninguna combinación de la tabla: sigue con el mecanismo de subagentes vigente. Las tres condiciones que lo habilitarían están **declaradas no probadas** —multi-repo, presupuesto de layout del multiplexor y escrituras paralelas de varios agentes— y un transporte no probado ahí arriesga la coordinación entera, no una corrida. El orquestador propaga la **intención**; su propio transporte no se toca.

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
un dueño único: el orquestador. Su evidencia se ejecuta y se agrega en la **Fase 3**.

Es la forma contractual de la regla no negociable que ya rige —ningún AC `[integration]` se da por
cumplido en un repo—: si su fila viviera en el contrato del repo, el `verify` local la ejecutaría y
la cerraría, que es exactamente lo prohibido. Y si viviera en **dos** repos, cada uno la cerraría con
media evidencia.

El contrato del repo la **referencia en modo solo-lectura**, con su ID global y una evidencia que no
es un estado del enum:

```markdown
| ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |
|---|---|---|---|---|---|
| V3 | AC-7 [integration] — el checkout confirma contra el servicio de pagos | N/A: Fase 3 | — | se verifica en el contrato de integración | N/A: Fase 3 |
```

`N/A: Fase 3` es deliberadamente **ninguno de los dos atajos** que parecen naturales:

- **no es `NOT_APPLICABLE`**, que significa "medir un baseline es semánticamente inaplicable" y
  borraría una obligación global: el AC sí se verifica, en otro lado;
- **no es una fila pendiente ni `BLOCKED`**, que bloquearía el gate del repo por algo que no le toca
  resolver y dejaría el flujo local trabado para siempre.

La referencia es obligatoria y no opcional: sin ella, el contrato del repo tendría un AC en alcance
sin fila y la cobertura bidireccional no cerraría. Eliminarla para "simplificar" rompe el gate.

### Gate de la Fase 3 y agregación

El contrato de integración pasa por un gate **equivalente** al que `cross-implement` aplica antes de
delegar (`cross-implement/contrato-verificacion.md` → "El gate previo al dispatch"): versión vigente
identificada, cobertura bidireccional contra los AC `[integration]`, campos obligatorios presentes y
baseline resuelto en toda fila, ninguna en `BLOCKED`. Se congela **antes** de ejecutar la primera
evidencia.

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
Override de esta corrida: transport: <valor resuelto para ESTE repo> (rige tus corridas delegadas).
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

## Bloques de validación de la integración

Predicados sobre el reparto y el contrato de integración. Cada bloque declara su **predicado**, y esa
línea es idéntica en las dos variantes de shell.

```bash
# @bloque:integracion-ownership
# Predicado: ninguna fila de un AC [integration] vive completa en el contrato de un repo; cada repo
# que participa la referencia en solo-lectura con evidencia N/A: Fase 3, nunca NOT_APPLICABLE.
# Entradas: $repos (uno o más plan.md por repo, separados por espacios)
rc=0
for f in $repos; do
  [ -f "$f" ] || { printf 'ARNES:no existe %s\n' "$f" >&2; exit 99; }
  grep -E '^\|' "$f" | grep -vE '^\|[[:space:]]*(ID[[:space:]]*\||[-: |]+\|)' \
    | grep -F '[integration]' | while IFS= read -r fila; do
        ev=$(printf '%s' "$fila" | awk -F'|' '{gsub(/^ +| +$/,"",$4); print $4}')
        bl=$(printf '%s' "$fila" | awk -F'|' '{gsub(/^ +| +$/,"",$7); print $7}')
        case "$ev@$bl" in
          'N/A: Fase 3@N/A: Fase 3') ;;
          *NOT_APPLICABLE*) printf 'GUARD:integracion-no-local %s: fila [integration] marcada NOT_APPLICABLE (borraria una obligacion global)\n' "$f" >&2 ;;
          *) printf 'GUARD:integracion-no-local %s: fila [integration] con evidencia local "%s"/"%s"\n' "$f" "$ev" "$bl" >&2 ;;
        esac
      done > "$f.err" 2>&1
  [ -s "$f.err" ] && { cat "$f.err" >&2; rc=1; }
  rm -f "$f.err"
done
# Control en el otro sentido: un repo que participa y NO la referencia deja su cobertura abierta.
# Se busca la FILA, no la mencion: el AC aparece igual en la lista de criterios del plan, asi que
# buscar en el archivo entero daria verde con la fila borrada.
for f in $repos; do
  grep -qE '^\|.*\[integration\]' "$f" || {
    printf 'GUARD:integracion-no-local %s: no referencia ninguna fila [integration]\n' "$f" >&2; rc=1; }
done
exit $rc
# @fin:integracion-ownership
```

```powershell
# @bloque:integracion-ownership-ps
# Predicado: ninguna fila de un AC [integration] vive completa en el contrato de un repo; cada repo
# que participa la referencia en solo-lectura con evidencia N/A: Fase 3, nunca NOT_APPLICABLE.
# Entradas: $repos (uno o más plan.md por repo, separados por espacios)
$rc = 0
# Los operadores van en su variante case-sensitive: el par POSIX filtra con `grep -E`/`grep -F` y
# decide con `case`, que distinguen mayúsculas. Con los operadores por defecto de .NET, `[INTEGRATION]`
# contaría como una fila de integración, `n/a: fase 3` como la evidencia exigida y `not_applicable`
# como la marca prohibida.
foreach ($f in ($repos -split '\s+' | Where-Object { $_ })) {
  # Mismo corte que el par POSIX: un plan que no existe es un error de invocación, no un plan que
  # incumple. Sin esto, `Get-Content` lanzaba y el bloque seguía con `$filas` vacío, reportando
  # "no referencia ninguna fila [integration]" sobre un archivo que nadie escribió nunca.
  if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { Write-Error "ARNES:no existe $f"; exit 99 }
  $filas = Get-Content -LiteralPath $f | Where-Object { $_ -cmatch '^\|' -and $_ -cnotmatch '^\|\s*(ID\s*\||[-: |]+\|)' -and $_ -cmatch '\[integration\]' }
  foreach ($fila in $filas) {
    $c = $fila -split '\|'; $ev = $c[3].Trim(); $bl = $c[6].Trim()
    if ($ev -ceq 'N/A: Fase 3' -and $bl -ceq 'N/A: Fase 3') { continue }
    if ($ev -cmatch 'NOT_APPLICABLE' -or $bl -cmatch 'NOT_APPLICABLE') {
      Write-Error "GUARD:integracion-no-local ${f}: fila [integration] marcada NOT_APPLICABLE (borraria una obligacion global)"
    } else {
      Write-Error "GUARD:integracion-no-local ${f}: fila [integration] con evidencia local `"$ev`"/`"$bl`""
    }
    $rc = 1
  }
  # Se busca la FILA, no la mencion: el AC aparece igual en la lista de criterios del plan.
  if ($filas.Count -eq 0) {
    Write-Error "GUARD:integracion-no-local ${f}: no referencia ninguna fila [integration]"; $rc = 1
  }
}
exit $rc
# @fin:integracion-ownership-ps
```

```bash
# @bloque:gate-fase-3
# Predicado: la Fase 3 congela el contrato de integración antes de ejecutar evidencia, y la
# agregación no puede dar verde con filas ausentes o BLOCKED.
# Entradas: $skill_orq (el SKILL.md de sdd-orchestrator)
rc=0
grep -q 'Gate de apertura del contrato de integración' "$skill_orq" || {
  echo "GUARD:gate-fase-3 la Fase 3 no tiene gate de apertura" >&2; rc=1; }
grep -q 'Congelarlo \*\*antes\*\*' "$skill_orq" || {
  echo "GUARD:gate-fase-3 el gate no exige congelar antes de ejecutar" >&2; rc=1; }
grep -q 'no verificado' "$skill_orq" || {
  echo "GUARD:gate-fase-3 la agregacion no declara que una fila ausente impide el verde" >&2; rc=1; }
exit $rc
# @fin:gate-fase-3
```

```powershell
# @bloque:gate-fase-3-ps
# Predicado: la Fase 3 congela el contrato de integración antes de ejecutar evidencia, y la
# agregación no puede dar verde con filas ausentes o BLOCKED.
# Entradas: $skill_orq (el SKILL.md de sdd-orchestrator)
$rc = 0
$doc = (Get-Content -LiteralPath $skill_orq) -join "`n"
# `-cnotmatch` y no `-notmatch`: el par POSIX busca con `grep -q`, que distingue mayúsculas. Con el
# operador por defecto de .NET, un `no Verificado` en la skill daría por cumplida la cláusula.
if ($doc -cnotmatch 'Gate de apertura del contrato de integración') { Write-Error 'GUARD:gate-fase-3 la Fase 3 no tiene gate de apertura'; $rc = 1 }
if ($doc -cnotmatch 'Congelarlo \*\*antes\*\*') { Write-Error 'GUARD:gate-fase-3 el gate no exige congelar antes de ejecutar'; $rc = 1 }
if ($doc -cnotmatch 'no verificado') { Write-Error 'GUARD:gate-fase-3 la agregacion no declara que una fila ausente impide el verde'; $rc = 1 }
exit $rc
# @fin:gate-fase-3-ps
```
