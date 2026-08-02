# Herdr como transporte de workers cross-model — informe del ejercicio

**Fecha:** 2026-08-01 · **Rama:** `exp/herdr-panes-transport` · **Estado:** ejercicio cerrado

> **⚠ Superado por `2026-08-02-herdr-transporte-sintesis.md`.** Este documento registra un solo
> ejercicio, conducido por Claude. Al día siguiente se contrastó con un ejercicio equivalente
> conducido por Codex y el resultado consensuado —validado en dos rondas de debate cruzado— vive en
> el otro archivo, que **manda sobre este** donde difieran.
>
> Cuatro afirmaciones de acá quedaron corregidas por esa validación:
>
> 1. El perfil de permisos **read-only** figura como practicable; es **diseño sin validar**. Un
>    worker con `--sandbox read-only` no puede escribir su propio informe, y ningún ejercicio probó
>    el punto intermedio.
> 2. El conteo de artefactos (§8) no es reproducible: son 23 en `planned-desambiguacion/`, o 28
>    sumando el tramo inicial.
> 3. "La cosecha por archivo es la única vía" exagera: es la única **uniforme y robusta probada en
>    ambas familias**; Codex expone `--no-alt-screen`, que no se ejercitó.
> 4. Los IDs de pane **no** desaparecen: se conservan como estado efímero de la corrida para el
>    wait desacoplado y el ownership del cleanup. Lo que no se persiste son los session IDs del
>    proveedor.
>
> Se conserva porque su narrativa —cómo se descubrió cada hallazgo, en qué orden y a costa de qué
> error— no está en el documento de síntesis.

> **Los cambios a las skills se revierten.** El objetivo era medir el transporte, no modificar
> `sdd-flow`. El cambio implementado (`plan-approved` + `status_version`) fue el vehículo del
> ejercicio y queda descartado; los artefactos del flujo sobreviven en
> `.plans/planned-desambiguacion/` como evidencia, untracked.

---

## 1. La pregunta

Una rama anterior (`feat/herdr-cli-cross-model`) intentó integrar Herdr al ecosistema SDD
construyendo andamiaje: scripts, adapters, runtime, recovery. Terminó en ~160 archivos de
implementación y se abandonó por peso propio.

La hipótesis contraria, que este ejercicio pone a prueba:

> Si la sesión ya invocó la skill `herdr`, el transporte de workers cross-model **no necesita
> andamiaje**. Basta con que las skills digan: "cuando estemos dentro de Herdr, en vez de
> `codex exec` / `claude -p`, lanzá el worker en un pane". El resto lo aporta el CLI, que ya sabe
> crear panes, arrancar agentes, mandarles texto y esperar su estado.

**Veredicto: la hipótesis se sostiene.** El transporte completo son seis comandos y ninguna línea
de plomería. Los detalles y las excepciones, abajo.

---

## 2. Qué se corrió

Un flujo SDD completo de punta a punta, con el transporte de Herdr en cada fase que despacha
workers.

**Objetivo inicial (descartado a mitad de camino).** Una skill `sdd-status` que reportara los
flujos SDD abiertos. La co-exploración demostró en su primera corrida que **ya existe**
(`/sdd-flow status` y `doctor`), y de paso refutó una premisa falsa del brief. El objetivo se
reemplazó por uno que salió de los propios hallazgos.

**Objetivo real.** Desambiguar `status: planned`, que en un flujo *complejo* colapsa tres
situaciones distintas (plan sin aprobar / plan aprobado sin tasks / tasks sin aprobar). La propia
skill lo admitía sin resolverlo: `SKILL.md:551` era la única fila de la tabla de retomado con dos
destinos y sin regla para elegir.

### Fases ejecutadas

| Fase | Transporte | Resultado |
|---|---|---|
| `gather-context` + clasificación | conductor | complejo (3 gates, cross-review on) |
| `co-explore` modo `explore` | **2 panes**, uno por familia | 2 mapas independientes; refutaron el objetivo |
| `specify` | conductor | `spec.md`, 8 AC |
| `cross-review` de la spec | **1 pane**, 3 rondas | `APPROVED` |
| `clarify` | conductor (en paralelo al revisor) | 3 preguntas resueltas contra el código |
| `create-branch` · `analyze` | conductor | seguir en la rama; co-exploración nominal |
| `co-explore` modo `counter-plan` | **2 panes**, uno por familia | 2 enfoques; conductor arbitró |
| `plan` | conductor | `plan.md`, tabla de 15 filas, contrato de 16 |
| `cross-review` del plan | **1 pane**, 2 rondas | `REVISE`, 2 disputas escaladas |
| `tasks` | conductor | 9 tasks, self-review |
| `implement` modo `cross` | **1 pane**, escritura | 8/9 tasks, 16/16 predicados, 1 fix |

**Ocho agentes** en total, en siete panes: `explorer-codex`, `explorer-claude`, `reviewer-codex`,
`planner-codex`, `planner-claude`, `reviewer-plan`, `implementer` (más uno creado y descartado).

---

## 3. El patrón que funcionó

Seis comandos. No hizo falta nada más.

```bash
# 1. Crear el pane (nunca encadenado con el paso 2 — ver H11)
herdr pane split --current --direction right --cwd "$PWD" --no-focus
#    → leer .result.pane.pane_id de la respuesta JSON

# 2. Arrancar el agente, con los flags nativos después de --
herdr agent start explorer-codex  --kind codex  --pane wW:p3 --timeout 60000 \
  -- --ask-for-approval never --sandbox workspace-write
herdr agent start explorer-claude --kind claude --pane wW:p4 --timeout 60000 \
  -- --permission-mode auto

# 3. Pasar la tarea como una RUTA, no como un prompt
herdr agent prompt explorer-codex \
  'Tu tarea completa está en .plans/<id>/prompts/explore-codex.md. Leelo y ejecutalo.'

# 4. Esperar (separado del prompt, para no serializar)
herdr agent wait explorer-codex --timeout 900000

# 5. Cosechar del filesystem, no de la terminal
cat .plans/<id>/reports/explore-codex.md

# 6. Limpiar
herdr pane close wW:p3
```

**Geometría.** Pane de 189×62 partido a la derecha, y ese partido abajo: dos workers de 94×31,
ambos visibles mientras trabajan. Split a la derecha si el pane es ancho, abajo si es angosto o
alto; nunca dos splits seguidos en la misma dirección.

---

## 4. Hallazgos sobre el transporte

### H1 — El informe por archivo no es una optimización, es la única vía

Los agentes TUI corren en la pantalla alternativa del terminal, y las filas que salen de ahí **no
entran al scrollback**. Subir `--lines` no recupera nada. Un informe de 24 KB como el que produjo
el worker Claude es irrecuperable desde el pane.

Consecuencia: *"decile al worker dónde escribir"* es un **requisito del transporte**, no un
consejo de prolijidad. La terminal sirve para el acuse de recibo; el contenido viaja por el
filesystem.

Y acá está el punto que más importa para el diseño: **es exactamente lo que `co-explore` y
`cross-review` ya hacen** con sus rutas de informe. El contrato de artefactos de las skills ya
estaba listo para Herdr.

### H2 — Pasar la tarea por ruta elimina el problema de quoting, y con él la asimetría de shells

El `CLAUDE.md` del repo advierte: *"el markdown con backticks rompe el quoting del shell"*, y de
ahí sale toda la mecánica de `< prompt.txt` en POSIX contra `Get-Content -Raw | codex exec ... -`
en PowerShell.

Con Herdr, por la línea de comando viaja **una sola oración de texto plano** con la ruta. El
prompt real, con todo su markdown, vive en un archivo del repo. **No hay quoting que romper si no
hay markdown en la línea de comando**, y la bifurcación POSIX/PowerShell desaparece del problema.

### H3 — Dos `agent prompt --wait` en paralelo se serializan (y eso rompe `co-explore`)

Los dos primeros prompts se mandaron en un solo bloque de llamadas concurrentes. Se ejecutaron en
serie: Codex terminó 21:03, Claude arrancó ahí y terminó 21:11.

El costo de reloj es lo de menos. El problema es de diseño: **`co-explore` exige que los dos
workers exploren a la vez y sin verse**. Serializados, el segundo corre en un mundo donde el
primero ya escribió su informe en el repo que el segundo está explorando.

**El patrón correcto separa el disparo de la espera:**

```bash
herdr agent prompt planner-codex  '<ruta>'   # sin --wait: retorna en el acto
herdr agent prompt planner-claude '<ruta>'   # ambos en el MISMO comando bash
herdr agent wait planner-codex  --timeout 900000
herdr agent wait planner-claude --timeout 900000
```

`agent prompt` sin `--wait` igual valida que el agente cambie de estado dentro de 5s, así que no
se pierde la detección de un worker que nunca arrancó.

**Medido:** con el patrón corregido los dos prompts salieron en el **mismo segundo** (21:41:49) y
los dos workers terminaron juntos (21:49:44). Ocho minutos contra dieciséis.

### H4 — El conductor no queda bloqueado, y eso cambia el flujo

Con `codex exec` el conductor **espera**: la llamada es bloqueante. Con Herdr, `agent prompt` sin
`--wait` retorna en el acto y el worker sigue en su pane.

Durante el `cross-review` de la spec se aprovechó esa ventana para ejecutar el paso 1 de
`clarify` —*"el código responde primero"*— con grep local. Cuando el revisor terminó, el conductor
ya tenía tres preguntas resueltas.

No es una optimización de reloj: **dos pasos que el flujo declara secuenciales pueden solaparse**
cuando el worker corre en otra terminal. Es el argumento más concreto a favor de instruir a las
skills sobre Herdr — no hacen lo mismo más rápido, pueden hacer algo que antes no podían.

### H5 — El resume entre rondas es gratis, y ahí el andamiaje se cae solo

`cross-review` corre un loop de hasta 3 rondas, y las rondas 2+ deben **reanudar el mismo thread
del revisor** mandando solo el delta (`cross-review/SKILL.md:186`). Lo mismo exige el fix loop de
`cross-implement`.

Por CLI eso obliga a capturar el `SESSION_ID`, persistirlo, y reinvocar con
`codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write"`, con su recuperación para
cuando el ID se perdió. **Buena parte del runtime de la rama abandonada existía para eso.**

En Herdr no hay nada que capturar: el agente sigue vivo en su pane con su contexto. La ronda 2 es
el mismo comando que la ronda 1, con otro texto. Se usó cinco veces en este ejercicio (3 rondas de
spec, 2 de plan) más el fix loop del implementador.

### H6 — Los nombres de agente son mejor handle que los IDs de pane

`herdr agent start <nombre>` bautiza al agente, y `prompt`/`wait`/`read`/`get` lo aceptan como
target. El conductor nunca vuelve a tocar un ID de pane después de crearlo.

Para una skill esto importa: **el nombre puede derivarse del rol** (`explorer-codex`,
`reviewer-plan`, `implementer`) en vez de trackear IDs opacos en un estado persistido. Buena parte
del andamiaje viejo existía para llevar esa contabilidad.

### H7 — El clasificador del conductor limita los flags del worker

`codex --dangerously-bypass-approvals-and-sandbox` fue **bloqueado por el clasificador de
auto-mode de la sesión conductora**, no por Herdr. El equivalente que sí pasa y cumple el mismo
objetivo de cero interrupciones:

| Familia | Flag que funciona |
|---|---|
| Codex | `--ask-for-approval never --sandbox workspace-write` |
| Claude | `--permission-mode auto` |

Ambos son además los correctos por otras razones: `workspace-write` es el patrón que el repo ya
documenta para `cross-implement`, y `--permission-mode auto` es menos bruto que
`--dangerously-skip-permissions`, que fue lo primero que se probó.

### H8 — Encadenar `pane split` y `agent start` falla

`herdr pane split ... && herdr agent start ...` en un mismo comando devuelve error: el pane existe
pero su shell todavía no llegó al prompt interactivo, y `agent start` exige un pane disponible. El
mismo `agent start` funciona al reintentarlo un segundo después.

**Son dos pasos, no uno.** Crear el pane, leer su ID de la respuesta, arrancar el agente aparte.

### H9 — El worker que escribe código respeta el límite

La fase de implementación fue la primera en que un worker **escribió en el repo**. Se lanzó con
`--sandbox workspace-write` y un `CONSTRAINTS` explícito que nombraba los cuatro archivos
permitidos y prohibía el resto.

`git status` mostró exactamente los tres archivos versionados del work order. No tocó la bitácora
del conductor, ni otros flujos de `.plans/`, ni otras skills, ni commiteó.

El límite se sostuvo por **las dos cosas juntas**, y ninguna sola habría alcanzado: el sandbox
permite todo el working dir, y el contrato sin sandbox es una promesa.

### H10 — El work order congelado se comportó bien ante un cambio del mundo

Mientras corría la implementación, los flujos viejos de `.plans/` se movieron a
`.plans/archived/`. La task T9 apuntaba a uno de ellos. El implementador **reportó el artefacto
ausente y dejó la task sin hacer**, en vez de buscarlo en otro lado o inventar un sustituto.

Es el comportamiento correcto ante un contrato congelado, y conviene registrarlo porque el impulso
natural sería premiar lo contrario. Una task que se auto-repara sobre una ruta que nadie autorizó
es peor que una que falla ruidosamente.

---

## 5. Hallazgos sobre la calidad del resultado

El transporte trivial no degradó nada. Al contrario.

### El cross-review encontró 18 hallazgos en 5 rondas, con 0 rechazos del conductor

| Artefacto | Rondas | Hallazgos | Veredicto |
|---|---|---|---|
| `spec.md` | 3 | 8 | `APPROVED` |
| `plan.md` | 2 | 10 | `REVISE`, 2 disputas escaladas |

**El valor escaló con las rondas en vez de agotarse.** La ronda 2 de la spec aportó dos hallazgos
*nuevos* sobre material que la ronda 1 no había visto, porque el delta lo creó. Lo mismo con el
plan.

### La ronda 2 del plan fue la más productiva de todas

El revisor dejó de *leer* los bloques normativos de `cross-implement/contrato-verificacion.md` y
pasó a **ejecutarlos** sobre el plan. Ninguna de las cuatro validaciones pasaba:

- el esquema rechazaba las celdas con pipes,
- el enum rechazaba `**GREEN_ALREADY**` por la negrita,
- la cobertura detectaba siete requisitos inventados (`AC-5.1`…`AC-5.7`) con `AC-5` huérfano,
- la cadena recalculaba un hash distinto del declarado.

Ninguno de esos cuatro se ve leyendo el documento con atención. **El valor no vino de un modelo más
listo: vino de que había un validador ejecutable y alguien lo corrió.**

### La topología dual de `co-explore` rindió

Los dos exploradores convergieron en lo esencial y divergieron en lo que importaba:

| | Aporte propio |
|---|---|
| Codex | Multi-repo tiene otra autoridad (`.sdd/<id>/manifest.yml`) · un artefacto canónico **vacío** es peor que uno ausente · **propuso `status_version`**, que el conductor descartó y la revisión terminó recuperando |
| Claude | 9 flujos declaran la **misma** rama · `committed` no es auditable: dos flujos inventaron el campo del SHA con nombres distintos · verificar AC-5 con una fila por punto en vez de un grep global, porque el grep solo alcanza 3 de los 7 puntos |

---

## 6. Lo que el transporte NO arregla

El hallazgo incómodo, y el más importante de registrar: **los errores serios del ejercicio fueron
todos del conductor**, y ninguno tiene que ver con Herdr.

1. Declaré los **quince baselines del contrato en `RED` sin ejecutarlos**. Dos ya pasaban
   (`GREEN_ALREADY`), uno seguiría rojo después del cambio, y el hash era un placeholder.
2. Escribí un predicado (`V14`) que **ya coincidía** con una línea ajena del repo,
   `SKILL.md:615`. Una guarda que nace verde no puede detectar nada.
3. **Arbitré mal el `counter-plan`**: descarté el `status_version` de Codex con un argumento —"la
   combinación es imposible"— que la revisión refutó con un contraejemplo concreto. La propuesta
   descartada volvió dos rondas después.
4. Inventé un hash en vez de calcularlo.
5. Congelé la tabla con un `(D1)` —referencia a una disputa del `review-log`— dentro de lo que
   iba a copiarse a una skill, violando la regla del repo de no dejar identificadores del flujo
   SDD en los artefactos.

El patrón es uno solo: **afirmé cosas verificables sin verificarlas.** El transporte no protege de
eso; el revisor de la otra familia, sí.

Y el punto 5 tiene una consecuencia práctica para el modo `cross`: el implementador **no
introdujo** ese defecto, lo **transcribió fielmente**. Un work order congelado se copia con sus
errores incluidos. La fidelidad del implementador amplifica lo que el conductor escribió, sea
bueno o malo.

---

## 7. Qué instrucciones harían falta en las skills

Esto es lo que el ejercicio buscaba contestar. **No hace falta andamiaje: hacen falta unas pocas
instrucciones**, casi todas en `reference.md`.

### 7.1 Detección (una línea, en cada `reference.md` que despache workers)

```bash
test "${HERDR_ENV:-}" = 1
```

Si da verdadero y el binario `herdr` está en `PATH`, el transporte es panes. Si no, el de siempre
(`codex exec` / `claude -p`). Es la misma lógica de **degradación por capacidad** que el repo ya
usa para MCPs y CLIs: no es un modo nuevo, es una vía más en la tabla de "Vías de invocación".

### 7.2 Una sección "Vía Herdr" en el `reference.md` de las tres skills

`co-explore`, `cross-review` y `cross-implement` ya tienen su sección de invocación por CLI. Al
lado va la de panes, con:

- los seis comandos del §3,
- la tabla de flags de H7,
- **el patrón de disparo separado de la espera** (H3), que es el único no obvio,
- la advertencia de H8 (split y start son dos pasos).

### 7.3 Tres reglas que conviene que sean explícitas

1. **Prompt por ruta, siempre** (H1, H2). No es una opción: es lo que hace que el transporte
   funcione y lo que elimina el problema de quoting.
2. **Un pane por worker, y el conductor lo cierra al cosechar.** Los nombres se derivan del rol
   (H6); no hace falta persistir IDs.
3. **En rondas siguientes, mismo agente** (H5). Reemplaza toda la mecánica de `SESSION_ID`.

### 7.4 Lo que se puede eliminar del diseño, no agregar

Si el transporte es Herdr, dejan de hacer falta: la captura y persistencia del `SESSION_ID`, la
recuperación de sesión perdida, la bifurcación POSIX/PowerShell para pasar el prompt, y la
contabilidad de IDs de worker. **La integración es más chica que lo que reemplaza.**

### 7.5 Lo que Herdr no cubre y hay que seguir haciendo igual

- La **cosecha sigue siendo por archivo** — es un requisito, no una preferencia (H1).
- El **contrato de verificación y su ejecución** siguen siendo del conductor. Herdr no valida nada.
- Los **gates humanos** no cambian en absoluto.

---

## 8. Datos del ejercicio

**Artefactos, en `.plans/planned-desambiguacion/`** (untracked, como manda el repo):

```
spec.md                       8 AC, endurecida por 3 rondas
plan.md                       tabla de 15 filas, contrato de 16, hash real
tasks.md                      9 tasks, 3 coberturas bidireccionales
review-log.md                 las 5 rondas con rationale de cada decisión
co-explore/                   los 2 mapas de la exploración
counter-plan/                 los 2 contra-enfoques
prompts/                      8 prompts, uno por despacho
reports/                      informes de los workers
```

El ejercicio del transporte inicial quedó en `.plans/herdr-panes-sdd-status/`.

**Métricas:**

| | |
|---|---|
| Agentes lanzados | 8, en 7 panes |
| Rondas de revisión | 5 (3 spec + 2 plan) |
| Hallazgos de revisión | 18, con 0 rechazos del conductor |
| Premisas del conductor refutadas | 3 |
| Implementación | 8/9 tasks, 16/16 predicados, 1 ronda de fix |
| Líneas de andamiaje escritas | **0** |

---

## 9. Deuda declarada

- **Fidelidad al flujo.** La primera mitad del ejercicio replicó el patrón de `co-explore` pero no
  el esqueleto de `sdd-flow`; se corrigió desde el cambio de objetivo. `constitution` se omitió
  (no hay `.specify/constitution.md` en este repo) y la rama se creó al principio, no después de
  `specify`.
- **`tasks` no tuvo cross-review** (decisión del usuario, para llegar a `implement`).
- **`verify` no se corrió.** AC-4 quedó sin verificar porque T9 no se ejecutó.
- **Dos disputas del plan quedaron abiertas** y se resolvieron por decisión del conductor con la
  opción conservadora, no por acuerdo con el revisor: si `tasks` puede probar la aprobación en un
  artefacto sin versión (se decidió que no), y si el manifest multi-repo necesita `status_version`
  (se decidió que no).
- **Windows sin probar.** Todo el ejercicio corrió en macOS. La vía Herdr debería ser *más*
  portable que el CLI —no hay redirección de stdin—, pero no está verificado.
- **Un solo repo, un solo tab.** No se probó la topología multi-workspace ni el
  `sdd-orchestrator` multi-repo, donde el reparto podría querer un pane por repo.
