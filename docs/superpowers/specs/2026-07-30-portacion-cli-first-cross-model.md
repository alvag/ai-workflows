# Portación CLI-first: qué rescatar de dos ramas experimentales

Fecha: 2026-07-30
Actualizado: 2026-07-31 — pasos 1 y 2 de la secuencia implementados; estado por punto al día
Estado: catálogo aprobado y **en ejecución**. Hechos: pasos 1 (`dd2f3b7`) y 2 (`97cc694`).
Siguiente: paso 3 (puntos 2, 3, 11 y 12)
Skills afectadas: `co-explore`, `cross-implement`, `cross-review`, `sdd-flow` (config)
Ramas analizadas: rama de runtime `ffcc851`, `feat/cross-model-real-sessions` (`2979d6d`)
Rama destino: `feat/cross-model` (24fc46b, idéntica a `main`)

## Objetivo

Registrar qué ideas de las dos ramas de transporte valen la pena portar al ecosistema
**CLI-first** que ya funciona, y cuáles conviene dejar donde están. El eje de la decisión es el
objetivo original de las skills — **performance, usabilidad y productividad** — y no la
capacidad de abrir sesiones interactivas visibles de la otra familia.

Ninguna de las ideas de este catálogo depende del runtime descartado ni de Orca. Todas corren sobre el
transporte que las skills ya usan hoy: `codex exec -s read-only` y `claude -p`.

## Contexto: dónde quedó cada rama

| Rama | Markdown agregado | Archivos `.mjs` | Suites de test | Skill nueva |
|---|---|---|---|---|
| `feat/cross-model` (base) | — | 0 | 0 | — |
| `feat/cross-model-real-sessions` | +13.826 líneas | 19 | 9 | `cross-model-orca` |
| rama de runtime (`ffcc851`) | +79.074 líneas | 244 | 124 | `cross-model-runtime` |

La línea base son 7.233 líneas de Markdown sin un solo archivo ejecutable, coherente con la
premisa del repo declarada en `CLAUDE.md`: *"No es una app: no hay build ni runtime"*.

### Hallazgos verificados sobre la rama de runtime `ffcc851`

Estos hechos motivan no continuar por ese camino. Se verificaron leyendo código y artefactos,
sin correr las suites ni probar el transporte interactivo en vivo.

1. **Codex quedó sin transporte CLI.**
   `skills/cross-model-runtime/assets/adapters/codex-cli.mjs` es un stub: `preflight()` devuelve
   siempre `available: false` con razón `codex-headless-approval-unsupported` y `dispatch()`
   lanza. Codex solo funciona vía transporte interactivo; el CLI quedó Claude-only.
   La decisión está registrada en el adoption log local de esa rama
   ("T17 cut Codex headless", 2026-07-30), tras cinco intentos de promoción con rollback.
2. **El motivo es más estrecho que la consecuencia.**
   `codex exec` 0.145.0 no expone `-a/--ask-for-approval` (verificado en `codex exec --help`),
   así que la política efectiva es `never` y la spec de esa rama la prohíbe. La prohibición tiene
   sentido para el rol *write*; para un worker **read-only** con `-s read-only`, `never` es el
   comportamiento deseado: el sandbox contiene y la escalada se deniega sola.
3. **El cap de prompt excluye los casos reales grandes.**
   El transporte interactivo acepta 65.536 bytes de prompt operacional. Los dos consumers medidos —`cross-review.max`
   (112.160 B) y `counter-plan.max` (78.081 B)— resuelven CLI antes de crear topología y, sumado
   al punto 1, terminan `partial` / `degraded` / `single-worker`.
4. **Costo de la opción, aunque no se use.**
   `co-explore/reference.md` pasa de 620 a 962 líneas y su `SKILL.md` de 395 a 540: resolución de
   transporte, capability, degradación y journal se leen en cada corrida, se elija CLI o no.
5. **El adoption log registra fricción sostenida:** 66 outcomes, 32 `pass`, 26 `failed`,
   1 `degraded`.
6. **No hay ventaja económica.** La justificación más fuerte del transporte nativo era que sus
   workers usan el perfil de suscripción mientras el CLI headless podría facturar por API.
   Confirmado por Max el 2026-07-31: **el CLI headless usa la suscripción**, no la API. La única
   condición que podía dar vuelta este análisis por economía en vez de por arquitectura queda
   descartada.

**Conclusión:** mergear esa rama tal cual deja el caso base peor que la línea base actual, y no
compra ahorro que compense el costo de mantenerla.

### Estado de `feat/cross-model-real-sessions`

El transporte `orca-session` tiene el mismo problema de fondo (complejidad de transporte que no
mejora el resultado), pero la rama contiene dos aportes **transport-agnostic** de alto valor —
verification contract y triage de ownership— y un documento de análisis de primer nivel:
`docs/research/fusion-harness/README.md` (717 líneas, sometido a debate cross-model).

Ese research ya llega a esta misma conclusión en su §15: bajo *Keep* está "transporte portable
con fallback"; bajo *Adapt*, el contract, el triage, los prompts externos y la escalera de rigor.
Ninguna de las dos listas menciona el transporte de sesión real. Su §12, Fase 3, fija además el
freno correcto: *"no expandir si los datos no muestran señal o el manifest resulta intrusivo"*.
Ese freno nunca se ejecutó.

---

## Catálogo de ideas portables

Ordenadas por valor sobre costo. Cada una es independiente de las demás.

### 1. Coordinador puro + índice compacto y lectura selectiva

> **HECHO** — commit `97cc694` (2026-07-31). Implementado con una diferencia respecto de lo
> anotado abajo: la lectura selectiva se apoya en un **split a dos archivos** (`index-*` /
> `detail-*`), no en extraer rangos del informe completo — leer el índice pasa a ser leer un
> archivo chico. Se sumaron además el envelope de retorno, la escalera de cuatro ramas, la
> excepción de familia acotada y la decisión de retoma. Artefactos del flujo en
> `.plans/punto-1-coordinador-puro/`.

- **Origen:** catálogo de arquitectura recuperado del worktree de esa rama.
- **Qué era:** el conductor exploraba él mismo *y además* despachaba un worker, por lo que pagaba
  el contexto completo de la exploración. La idea es que el conductor **no explore**: despacha dos
  workers frescos y actúa como árbitro. Cada worker entrega **dos capas**:
  - un **índice compacto** que enumera *todos* los hallazgos, cada uno con ID estable, severidad
    o impacto, confianza y punteros a evidencia;
  - un **informe detallado** con el desarrollo completo.

  El conductor consume siempre el envelope y el índice completo, y abre el detalle **solo** ante
  uno de estos disparadores: divergencia entre workers, alto riesgo, baja confianza o una decisión
  que arbitrar.
- **Por qué:** es el mayor ahorro de contexto del conductor y el salto de performance más grande
  de todo el catálogo. El índice **no reemplaza** al informe: es una capa de navegación.
- **Cómo se ve en CLI:** dos invocaciones en paralelo (`codex exec` + `claude -p`) y una regla de
  lectura en el `SKILL.md`. Sin runtime.
- **Guardrail a conservar:** paridad mecánica entre índice y detalle — la cantidad y los IDs deben
  coincidir, y eso debe poder validarse. Es el único chequeo automático que justifica su costo.
- **Costo:** medio, todo en Markdown.
- **Qué NO traer:** cohort v1, quorum 2/1, journal durable, reducer monotónico, transition claims.

### 2. Verification contract congelado antes del dispatch

- **Origen:** `feat/cross-model-real-sessions`, §P0.2 del research; implementación en
  `skills/cross-model-orca/assets/verification-contract.mjs` (299 líneas) y
  `run-verification-contract.mjs` (42); documentación en `skills/cross-implement/reference.md`
  (+475 líneas en esa rama).
- **Qué es:** una tabla declarativa en el work order, derivada de spec/plan/tasks, **congelada
  antes** de despachar al implementador, que este no puede ablandar:

  | ID | Requisito | Evidencia | Comando/observación | Esperado | Baseline |
  |---|---|---|---|---|---|
  | V1 | AC-1 | test | `npm test -- --run foo.spec.ts` | pasa | RED |
  | V2 | AC-2 | build | `npm run build` | exit 0 | N/A |

  El baseline se ejecuta y se tipa: `RED`, `GREEN_ALREADY`, `NOT_APPLICABLE` o `BLOCKED`. Un verde
  previo nunca se acepta sin adjudicación. El contrato rige **también durante el takeover** del
  conductor.
- **Por qué:** el criterio de "hecho" existe antes de ver la implementación. Ataca directamente la
  productividad: menos rondas gastadas discutiendo qué contaba como terminado.
- **Costo:** bajo. El validador es reusable casi tal cual; solo hay que sacarlo de
  `cross-model-orca`, donde quedó acoplado sin motivo, y llevarlo a `cross-implement/assets/`.
- **Qué NO traer:** generación automática de un `gate.py`. El contrato declarativo es obligatorio;
  el gate ejecutable es opcional y, si existe, requiere revisión previa.

**Por qué el contrato va justo acá y no en todas partes.** `co-explore` es un **equipo**: dos voces
deliberan, se critican y se corrigen en vivo. `cross-implement` es una **delegación**: un handoff
congelado, sin nadie deliberando mientras se construye. Cuando no hay deliberación que corrija el
rumbo, el criterio de "hecho" tiene que ser externo y escrito antes. Ese es el argumento que
delimita dónde poner este rigor.

#### Reglas de congelamiento (de la implementación, no del diseño)

El piloto de la Fase 2 (`2979d6d`) afinó el diseño original con reglas que el research no tenía y
que son las que hacen que el mecanismo sea honesto en vez de decorativo:

1. **Cobertura bidireccional.** Cada requisito en alcance tiene al menos una fila y cada fila
   referencia un requisito real. Un requisito sin cobertura **o una fila huérfana** impide
   congelar. La misma regla ataca el hueco y el scope creep.
2. **IDs estables e invariantes.** Cada `ID` es un slug único, y **el conjunto de IDs no cambia
   entre versiones**. Cambiar la cobertura no es corregir una prueba: es `DESIGN_GAP`. Sin esta
   regla, `VERIFICATION_DEFECT` (punto 3) se convierte en una puerta trasera para hacer
   desaparecer cualquier check incómodo, y todo el mecanismo pierde sentido.
3. **Append-only.** El archivo contiene versiones completas (`## v1`, `## v2`, …); la mayor es la
   vigente y las anteriores nunca se editan. Una corrección agrega una versión entera, no parchea
   la vigente.
4. **Baseline ejecutado y auditable.** Cada fila registra el commit evaluado, timestamp ISO-8601 y
   el resultado observado. Sin ese registro no hay congelamiento.
5. **Adjudicación de verdes previos**, con tres salidas posibles y una prohibición:

   | Adjudicación | Efecto |
   |---|---|
   | `already_satisfied` | La fila queda como chequeo de no-regresión y deja de contar como evidencia del cambio. |
   | `weak_check` | Fortalecer la evidencia y repetir el baseline contra la misma revisión. **Nunca fabricar un rojo.** |
   | `invalid_assumption` | Corregir la fila antes de congelar: el supuesto original era inválido. |

   Solo `already_satisfied` sobrevive en una versión congelada; las otras dos son estados del
   proceso y su rastro queda en el log.
6. **Condición terminal explícita.** `IMPLEMENTED` exige `Expected` cumplido en toda fila
   aplicable, ninguna `BLOCKED` y justificación registrada por cada `NOT_APPLICABLE`. Cualquier
   otro estado va a triage, a suspensión por `DESIGN_GAP` o a cierre no exitoso.

### 3. Triage de ownership antes de gastar otra ronda

- **Origen:** `feat/cross-model-real-sessions`, §P0.3 del research; implementación afinada en
  `skills/cross-implement/reference.md` → "Triage de ownership" (`2979d6d`). Puro proceso, cero
  código.
- **Qué es:** ante una falla de evidencia, clasificar **cada check** antes de consumir otra ronda.
  La unidad del triage es el `checkId` — el mismo ID estable de la fila del contrato:

  | Clase | ¿Consume ronda? | Control de flujo |
  |---|---:|---|
  | `IMPLEMENTATION_DEFECT` | Sí | Agrupar los defectos del delta y reanudar la misma sesión. |
  | `VERIFICATION_DEFECT` | No | Versión nueva del contrato, re-baseline de la fila, congelar y repetir la evidencia. |
  | `ENVIRONMENT_FAILURE` | No | Reparar y repetir. Si no es reparable, fila `BLOCKED` y cierre no exitoso. |
  | `DESIGN_GAP` | No | Suspender de inmediato, también en takeover, y volver a plan/spec. En modo embebido, devolverlo al flujo llamador. |

- **Por qué:** un gate defectuoso deja de quemar rondas del implementador. Es la contraparte
  necesaria del punto 2: sin triage, el contrato convierte todo error de verificación en culpa
  del implementador.
- **Costo:** nulo en código.

#### Refinamientos que aparecieron al implementarlo

1. **La razón falsable tiene definición, no solo nombre.** Antes de clasificar la **segunda falla
   consecutiva del mismo check** como `IMPLEMENTATION_DEFECT`, hay que registrar *"una afirmación
   que una observación concreta pueda refutar"* — explícitamente no vale «seguro es el código».
   Sin la definición, la regla se cumple con cualquier frase.
2. **Varios checks comparten un fix round.** Una entrada de triage por check, pero los defectos
   del delta se agrupan en una sola ronda. Evita quemar `max_fix_rounds` de a un defecto.
3. **El delta del fix es concreto y no re-manda el work order:** *qué está mal · en qué archivo ·
   qué prueba debe pasar*, más la versión vigente del contrato solo si cambió. Ahorro de contexto
   directo en cada ronda.
4. **El re-baseline corre en un worktree temporal aislado** sobre el commit pre-dispatch
   registrado — nunca `checkout`, `reset` ni `stash` sobre el árbol activo, que contiene el diff
   del implementador y quedaría destruido. Si el worktree no se puede crear o limpiar con
   garantías, la fila queda `BLOCKED`. La rama trae los bloques POSIX y PowerShell resueltos:

   ```bash
   TMP_WORKTREE=$(mktemp -d)
   git worktree add --detach "$TMP_WORKTREE" <sha-pre-dispatch>
   ( cd "$TMP_WORKTREE" && <evidencia-de-la-fila> )
   git worktree remove --force "$TMP_WORKTREE"
   ```

5. **El delta identifica el cambio de contrato de forma explícita:** «rige v\<N\>; cambió la fila
   \<checkId\>». El implementador nunca descubre solo que el criterio se movió.
6. **Toda clasificación queda registrada** con check, clase, evidencia y `consumedRound: true|false`.
   Es lo que después permite responder si el gate o el implementador es el que falla seguido.

### 4. Worker con MCP y hooks apagados

> **HECHO** — commit `dd2f3b7`. Se implementó con más alcance del anotado: sumó el preflight
> fail-closed, la lectura validada del config del usuario y la persistencia del modelo entre rondas.

- **Origen:** `feat/cross-model-real-sessions`, `skills/cross-model-orca/assets/launch/profiles.md`
  y sección 3 de su `SKILL.md`.
- **Qué es:** el worker delegado no necesita MCP —todo su contexto viaja en el prompt— y no debe
  disparar automatización local. Se apagan ambos.
- **Por qué:** en esa rama midieron que los MCP dominan el boot de la TUI (~2x) y que en Windows
  llegaron a colgarlo en "MCP startup incomplete". Además cierra superficie: un worker read-only
  con los MCP del entorno puede alcanzar una tool MCP de **ejecución** y correr comandos fuera del
  working dir (hallazgo real de esa rama, no hipotético).
- **Cómo se ve en CLI:** dos flags por familia, no una matriz familia×rol×modo.
  - Codex: `--disable hooks`, más overrides `-c mcp_servers.<name>.enabled=false` enumerados del
    `config.toml` vigente al momento de lanzar (nunca una lista fija).
  - Claude: `--strict-mcp-config` con un `--mcp-config` vacío, `--disallowedTools "mcp__*"` y
    `disableAllHooks`.
- **Costo:** bajo. Performance inmediata y gratis.
- **Qué NO traer:** la matriz completa de lanzamiento por familia × rol × modo atendido/desatendido.

### 5. Degradación parcial declarada en vez de `UNAVAILABLE`

> **HECHO en forma reducida** — commit `dd2f3b7` (rama terminal de una sola voz). La versión
> completa dependía del punto 1 y llegó con él en `97cc694`: escalera de cuatro ramas.

- **Origen:** catálogo de arquitectura recuperado del worktree de esa rama.
- **Qué es:** hoy `co-explore` devuelve `UNAVAILABLE` si no hay revisor de la otra familia
  (regla 7, paso 1 de sus pasos de ejecución). La idea es continuar con un solo worker y
  **declarar explícitamente la diversidad reducida** en la salida.
- **Por qué:** la disponibilidad de una sola familia no debería bloquear el flujo. Dos familias
  distintas siguen siendo el caso preferido, no una precondición.
- **Matiz a preservar:** el ahorro de contexto viene de delegar en sesiones frescas; la diversidad
  de familias mejora la independencia de criterio pero no cambia ese ahorro. Son dos beneficios
  separados y conviene reportarlos por separado.
- **Costo:** trivial.

### 6. Perfiles de worker en `.specify/config.yml`

- **Origen:** catálogo de arquitectura recuperado del worktree de esa rama, sección
  "Decisión: perfiles nombrados de workers".
- **Qué es:** un perfil describe **cómo ejecutar** un worker (familia, modelo, esfuerzo), nunca
  qué tarea hacer. La skill conserva la autoridad sobre rol, prompt, permisos y límites de
  escritura; un perfil no puede elevar permisos.

  ```yaml
  cross_model:
    schema_version: 1
    profiles:
      claude-deep: { family: claude, model: sonnet, effort: high }
      codex-deep:  { family: codex,  model: default, effort: high }

  co_explore:
    workers:
      profiles: [claude-deep, codex-deep]
      target_success: 2
      min_success: 1
      family_diversity: prefer
  ```

- **Reglas que valen la pena:** precedencia override conversacional > `.specify/config.yml` >
  defaults de la skill; un modelo explícito no disponible vuelve ese perfil `UNAVAILABLE` y
  **nunca** se sustituye en silencio por otro; `model: default` sí delega la elección al proveedor;
  un adaptador no debe ignorar una opción de esfuerzo incompatible sin avisar.
- **Por qué:** control real sobre costo y latencia sin tocar las skills.
- **Costo:** bajo.

> **Cerrado el 2026-08-01 — revertido, no implementado.** El vocabulario se portó (el YAML de arriba
> llegó al esquema del config) y **el consumidor nunca**: ninguna línea de lanzamiento leía un perfil,
> así que escribir `model: sonnet` despachaba el modelo de siempre sin avisar — la sustitución
> silenciosa que las reglas de este mismo punto prohíben. Se quitaron `cross_model.profiles` y
> `co_explore.workers` enteros; las reglas sobre modelo y esfuerzo sobreviven en
> `co-explore/reference.md` → "Modelo y esfuerzo del worker", que es donde estaban vivas.
>
> Tres cosas que se aprendieron y valen más que la capacidad:
>
> 1. **El "costo: bajo" estaba mal medido.** Cablearlo eran 31 bloques de invocación en 4 archivos,
>    3 guardas nuevas y un `v2` del contrato. Lo barato era el YAML, no el consumidor.
> 2. **El ejemplo que lo motivaba ya era el comportamiento por defecto** (`co-explore` con `opus`,
>    `cross-implement` con `sonnet`): el trabajo compraba poder *cambiarlos*, no tenerlos.
> 3. **`target_success`, `min_success` y `family_diversity` tampoco tenían consumidor**, y además
>    describían mal la skill: con la topología dual del punto 1, la diversidad de familia dejó de ser
>    una preferencia configurable. Sobrevivieron porque nadie volvió a mirarlos.
>
> La spec completa (18 AC, 5+9 rondas de revisión) queda en `.plans/perfiles-por-skill/` por si algún
> día vuelve a hacer falta. Si vuelve, **entra con su consumidor o no entra.**

### 7. Prompts como assets versionados

- **Origen:** §P0.4 del research (`feat/cross-model-real-sessions`).
- **Qué es:** sacar los prompts de `reference.md` a `assets/prompts/*.md` con placeholders
  validados: `explore.md`, `counter-plan.md`, `investigate.md`, `debate-round-0.md`,
  `debate-cross.md`, `review.md`, `implement.md`, `fix.md`.
- **Por qué:** `SKILL.md` conserva políticas, `reference.md` conserva contratos y los assets pasan
  a ser la entrada exacta del worker. Además adelgaza los `reference.md`, que ya están gordos
  (`co-explore/reference.md`: 620 líneas; `bitbucket-code-review/reference.md`: 881).
- **Costo:** bajo-medio, mecánico.
- **Qué NO traer (por ahora):** hashes de prompt y golden tests. Se evalúan si aparece la necesidad.

### 8. Escalera de rigor documentada

- **Origen:** §P1.3 del research.
- **Qué es:** documentar cuándo escalar entre skills, para no usar el martillo caro:

  ```text
  respuesta local
    → co-explore: mapa, investigación o debate
    → cross-review: crítica de una decisión escrita
    → cross-implement: construcción desde contrato congelado
    → sdd-flow verify: evidencia final por AC
  ```

- **Costo:** ~20 líneas de documentación.
- **Decisión asociada:** **no** crear un modo `opinion` (A/B barato) hasta tener un caso de uso real
  donde `co-explore` resulte desproporcionado. Ambas familias convergieron en diferirlo.

### 9. Manifest mínimo de corrida (opcional, último)

> **HECHO** — canon en `cross-review/reference.md` → "Manifest de corrida", enganchado en las tres
> skills y en `cross_model.manifest` del config. Ocho campos, un archivo por corrida en
> `.cross-model/runs/`, y el recorte del catálogo respetado más uno: se fue también el `.partial`
> con rename atómico, que protegía una escritura incremental que acá no existe.
>
> **La decisión que define si sirve no estaba en el catálogo:** *cuándo* se escribe. Un manifest
> escrito al cerrar bien una corrida registra solo éxitos y responde "¿esto me está sirviendo?" con
> la única muestra incapaz de contestarlo. Quedó como regla —se escribe donde se resuelve el
> outcome, y **todos** los caminos de salida pasan por ahí— con una guarda bidireccional que la
> sostiene: todo estado terminal que una skill declara tiene que ser registrable, y todo término del
> manifest tiene que existir en la skill que lo produce.

- **Origen:** §P0.1 del research; implementación en
  `skills/cross-model-orca/assets/run-manifest.mjs`.
- **Qué es:** un `run.json` por invocación con lo mínimo para responder *"¿esto me está sirviendo?"*:
  workflow, modo, familia, transporte efectivo, duración, outcome y degradación.
- **Por qué:** sin datos, cualquier decisión posterior sobre expandir o recortar es intuición.
- **Costo:** bajo **solo si se recorta**. La versión de esa rama incluye `attempts[]` con owner
  único, `.partial` con rename atómico, `finish` que rechaza attempts abiertos y una matriz
  normativa de procedencia por ruta a nivel de schema. Nada de eso hace falta sin fallback entre
  dos transportes.
- **Qué NO traer:** `attempts[]`, schemas versionados, `usage.source`, parent/child runs.

### 10. Llevar el triage a `systematic-debugging`

> **HECHO, reubicado** — commit `dd2f3b7`. `systematic-debugging` es del plugin superpowers y no
> pertenece a este repo, así que la regla vive en `co-explore investigate` como el criterio de éxito
> tratado como una hipótesis más.

- **Origen:** `docs/research/fusion-harness/claude/README.md`, oportunidad 2.
- **Qué es:** esa skill ya sostiene el principio "una hipótesis de causa raíz, no prueba y error".
  Lo que le falta es la vuelta de tuerca: **una de las hipótesis válidas es que tu criterio de
  éxito esté equivocado**. Un bug que resiste tres intentos puede ser un test mal escrito, no un
  código mal escrito.
- **Por qué:** ataca una clase real de bucles improductivos, en la skill de uso más frecuente de
  todo el ecosistema. Hoy el tope es binario —tres fallos de la misma falla y se vuelve a diseño—
  sin el paso intermedio de entender por qué está atascado.
- **Costo:** una línea de contrato más un párrafo de guía. La mejor relación valor/costo del
  catálogo.

### 11. Declarar los checks en `plan`/`tasks`, no en `verify`

- **Origen:** ambos insumos del research lo señalaron por separado
  (`claude/README.md` oportunidad 1, puente con sdd-flow; `codex/README.md` §1).
- **Qué es:** el `verify` de `sdd-flow` ya exige evidencia fresca por AC y tiene **revert-to-confirm**,
  que es *más* riguroso que el gate de fusion-harness porque prueba que el test tiene dientes. Lo
  que le falta no es rigor sino **momento**: la evidencia se selecciona después de implementar.
  La mejora es declarar en `plan`/`tasks` la tabla `AC → prueba → resultado esperado → baseline`
  —aunque todas las filas arranquen en rojo— y dejar `verify` como pura ejecución.
- **Por qué:** cierra el único gap de rigor real del flujo, y es el mismo contrato que consume
  `cross-implement` (punto 2), así que no se escribe dos veces.
- **Costo:** medio. Toca `sdd-flow/SKILL.md` y su `reference.md`.

### 12. Verificar lo declarado contra el estado real del árbol

- **Origen:** `skills/cross-implement/reference.md` → "Revisión del conductor" (`2979d6d`).
- **Qué es:** contrastar la sección `FILES` del reporte del implementador contra
  `git status --porcelain`. Un archivo tocado y no declarado, o declarado y no tocado, es sospecha
  y va al fix round. Complementa la detección de drift por hunks.
- **Regla hermana:** **un reporte no parseable no invalida la revisión** — el diff sigue siendo la
  verdad; se pierde la narrativa, no el control. Vale como principio general de degradación.
- **Costo:** una línea de checklist.

### 13. Nota de límite en las síntesis

> **HECHO** — commit `dd2f3b7`. Slot obligatorio en las seis superficies de salida.

- **Origen:** `docs/research/fusion-harness/claude/README.md` §6, "blind-spot honesty".
- **Qué es:** cerrar las síntesis de `co-explore` y las conclusiones de `cross-review` con una
  nota honesta: *una segunda familia sube cobertura, no garantiza correctitud; un punto ciego
  compartido entre ambas familias queda sin detectar*.
- **Por qué:** contrapeso al exceso de confianza en "ya lo revisó la otra familia". Verificado que
  hoy no existe en `main`: `co-explore` menciona los puntos ciegos como argumento **a favor** del
  método, nunca como advertencia sobre su techo.
- **Costo:** una línea por skill.

### 14. Handoff destilado, nunca transcript crudo

- **Origen:** `docs/research/fusion-harness/claude/README.md`, apéndice A.
- **Qué es:** documentar como principio explícito que al secundario se le pasa un **contrato
  destilado**, nunca el transcript literal del conductor.
- **Por qué:** no es solo elegancia de diseño. Fusion-harness documenta un caso real donde
  reproducir un transcript construido bajo un modelo dentro de otro activó clasificadores de
  usage policy y **bloqueó todas las requests** —incluso triviales— mientras la misma consulta en
  sesión fresca pasaba. El prompt por archivo del enfoque CLI ya *es* un handoff destilado: el
  diseño barato resulta ser también el seguro. Conviene escribir el porqué para que nadie lo
  "optimice" pasando contexto ambiente al delegado.
- **Costo:** un párrafo en el `reference.md` de cada skill que despacha.

### 15. Descarte auditable en la síntesis

- **Origen:** `docs/research/fusion-harness/claude/README.md`, oportunidad 3(c).
- **Qué es:** `co-explore` en `main` ya produce la tabla de convergencias/divergencias, el duelo de
  enfoques con su porqué auditable y el checkpoint de divergencias no resueltas. Lo único que
  falta de esa familia de ideas es registrar **qué hallazgos o hipótesis se descartaron y por qué**,
  que hoy queda implícito.
- **Por qué:** registrar por qué se eligió un enfoque no es lo mismo que registrar qué se tiró.
  Lo segundo es lo que permite revisar la síntesis meses después sin reconstruirla de cero.
- **Costo:** una fila más en la plantilla de `synthesis.md`.

---

## Descartado explícitamente

Del research original (§15, lista *Reject*) más lo que agrega este análisis:

- Migración a Pi o a un harness monolítico.
- Transporte interactivo (`skills/cross-model-runtime/`) y transporte `orca-session`
  (`skills/cross-model-orca/`) como tales.
- Capability manifests con verificación por bytes y SHA-256, `worker-capabilities.json`,
  integridad de entrypoints.
- Cohort v1 con quorum 2/1, journal durable, reducers monotónicos, transition claims, recovery
  multi-ronda, los 12 schemas JSON.
- Matriz de lanzamiento familia × rol × modo (se conserva solo la idea del punto 4).
- Escritores concurrentes, ejecución ciega de código generado, memoria global por rol, modelos
  hardcodeados, un tercer agente "fuser" obligatorio, PASS sin baseline significativo.

## Invariantes que no se tocan

Vienen de la lista *Keep* del research y siguen vigentes:

- Skills separadas por intención; `co-explore` explora, `cross-review` revisa diseño,
  `cross-implement` escribe código, `systematic-debugging` arregla bugs.
- El conductor conserva la autoridad: sintetiza, arbitra, revisa el diff y corre las pruebas.
- La familia opuesta por construcción, con degradación honesta cuando falta.
- Clean tree, un solo escritor por working tree, diff completo y pruebas frescas.
- Transporte portable con fallback; el CLI es el status quo y la base estable.
- Español neutro y portabilidad POSIX/PowerShell en cualquier comando nuevo.

## Secuencia propuesta

Todo sobre `feat/cross-model`, sin runtime nuevo. Cada paso es entregable por sí solo.

0. ~~**Archivar las ramas de origen** con un tag, sin borrarlas.~~ — **descartado**. Las ramas y sus
   worktrees quedan tal como están, por si en algún momento se retoman. El tag existía para poder
   borrarlas sin perder la referencia; si no se borran, no compra nada.
1. ~~**Puntos 4, 5, 10 y 13**~~ — **HECHO**, commit `dd2f3b7`.
2. ~~**Punto 1** (coordinador puro + índice/detalle)~~ — **HECHO**, commit `97cc694`.
3. ~~**Puntos 2, 3, 11 y 12**~~ — **HECHO**, commits `82b619d`, `a7ae11b` y `411636d`. Incluyó
   además los tres pendientes detectados al ejecutar el paso 2 (índice paginado,
   `clarification-needed` y separación de reparación de formato vs retry semántico), que se
   sumaron al alcance por decisión del usuario.
4. ~~**Puntos 6, 7, 8, 14 y 15**~~ — **HECHO**. Perfiles de worker en `cross_model.profiles` +
   `co_explore.workers`, seis prompts movidos a `assets/prompts/`, escalera de rigor canónica en
   `co-explore/reference.md`, handoff destilado en las tres skills que despachan, y `## Descartados`
   obligatoria en la síntesis.

   **Corrección al punto 7:** el catálogo nombraba **ocho** assets y solo **seis** existen como
   bloque literal. `investigate` y `fix` están definidos **por delta** —el primero sobre `explore`,
   el segundo como contenido mínimo por ronda—, así que moverlos habría sido *escribir* prompts que
   hoy no existen: un cambio de contenido disfrazado de mudanza de archivo. Quedan como delta, con
   la razón anotada donde alguien los buscaría.
5. ~~**Punto 9** (manifest mínimo)~~ — **HECHO**. Canon del manifest en `cross-review/reference.md`
   (la sede de la mecánica compartida, donde ya vivía la portabilidad de shells), enganchado en el
   punto donde cada skill resuelve su outcome, más `cross_model.manifest` en el config y una sección
   "Qué escribe en tu repo" en los tres README. De yapa se repararon las dos citas cruzadas
   abreviadas vivas, para que la guarda nueva de punteros entre skills naciera con **alcance total
   y sin lista de exentos** — una guarda con exentos envejece hacia adentro, porque cada excepción
   nueva se justifica con la anterior.

Estimación gruesa original: los pasos 1–4 en menos de 1.800 líneas de Markdown. **Medido:** el
paso 1 costó 923 líneas, el paso 2, 1.328 (neto +677), y el paso 3, **2.457** (neto +2.393,
repartido en `cross-implement` +1.350, `co-explore` +715, `sdd-orchestrator` +169 y `sdd-flow`
+161). La estimación original ya se pasó **tres veces** con el paso 4 todavía sin empezar: cada
paso rinde más de lo previsto y cuesta cerca del doble del anterior.

**Lo que la estimación no contaba, y es la mayor parte del trabajo:** el paso 3 sumó un arnés que
vive en `.plans/` y no se publica. Las líneas de Markdown publicado miden el entregable, no el
esfuerzo — y sin ese arnés cinco guardas habrían quedado en verde sin poder detectar el defecto que
decían detectar.

**Cierre del catálogo.** El paso 5 costó **+338 / −3** en 10 archivos, el más barato de los cinco y
el único que se acercó a su estimación. El arnés terminó en **100 archivos, 14 guardas, 20 fixtures
y 92 mutaciones declaradas**, con la corrida completa en **147 verificaciones**. La suma de los
cinco pasos triplica largamente las 1.800 líneas estimadas, y la razón es la misma en cada paso:
escribir la regla es la parte barata; construir la evidencia de que la regla puede detectar su
violación cuesta más que la regla.

~~**Pendiente de portar, detectado al ejecutar el paso 2**~~ — **HECHO en el paso 3**: índice
paginado sin pérdida, `clarification-needed` con paquete de contexto versionado, y las tres
identidades de reintento (`transportAttempt` / `formatRepair` / `semanticAttempt`) separadas.

## Riesgo de pérdida de insumos

`.plans/` es untracked por diseño. Dos documentos citados acá viven **solo** en el worktree de la
rama de runtime `ffcc851` (`/Users/max/Personal/repos/ai-workflows`) y no están en ninguna rama:

- El catálogo local de ideas —**rescatado** antes de limpiar el worktree— vuelve a quedar solo en
  esa copia de trabajo tras retirar su publicación versionada.
- El adoption log local (1.229 líneas) —la evidencia de los
  hallazgos verificados. **Sigue en riesgo**, y el riesgo no cambió al descartar el archivado: no
  depende de que la rama exista, sino de que el archivo es untracked. Un `git clean -xdf` o borrar
  el worktree se lo lleva, y la rama seguiría ahí sin él. Lo que sí bajó es la probabilidad: nadie
  va a limpiar un worktree que se decidió dejar en pie.

## Método y límites de la verificación

Se verificó leyendo código y artefactos: el stub del adapter Codex, los flags de `codex exec`
(`--help` de `codex-cli 0.145.0`), los conteos de archivos y líneas por rama, y los outcomes del
adoption log. **No** se corrió ninguna de las suites de las ramas analizadas ni se probó el transporte interactivo u
Orca en vivo. El hallazgo 6 (identidad de facturación del CLI headless) no se midió: lo aportó
Max desde su propio entorno. Las cifras de tests que aparecen en el adoption log (runtime 260/260, co-explore
224/224, cross-review 117/117) son las que ese documento reporta, no ejecuciones propias.

## Fuentes

- `docs/research/fusion-harness/README.md` (en `feat/cross-model-real-sessions`) — informe
  consolidado, debate cross-model y las listas Keep/Adapt/Reject.
- `docs/research/fusion-harness/claude/README.md` — insumo independiente; origen de los puntos 10,
  13, 14 y 15, y del encuadre equipo vs. delegación.
- `docs/research/fusion-harness/codex/README.md` — insumo independiente; converge con el anterior
  en el punto 11.
- `skills/cross-implement/reference.md` en `2979d6d` — implementación del contract y el triage;
  origen de todas las reglas de congelamiento y los refinamientos del triage.
- `docs/research/cross-model-real-sessions/README.md` (misma rama).
- El catálogo de arquitectura y el adoption log del worktree de `ffcc851`, consultados el
  2026-07-31.
- `skills/cross-model-runtime/` y `skills/cross-model-orca/` en sus respectivas ramas.
