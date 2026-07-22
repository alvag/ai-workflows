# Fusion Harness y evolución del ecosistema cross-model

- **Estado:** informe consolidado, sometido a debate cross-model y a una segunda pasada de revisión (ver §11)
- **Fecha:** 2026-07-22
- **Fuentes internas:** análisis de [Codex](./codex/README.md) y [Claude](./claude/README.md)
- **Repositorio externo:** [`disler/fusion-harness`](https://github.com/disler/fusion-harness)
- **Snapshot analizado:** [`5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4`](https://github.com/disler/fusion-harness/tree/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4)
- **Presentación:** [Engineers... STOP Picking GPT-5.6 Sol OR Claude Fable 5… FUSE THEM](https://www.youtube.com/watch?v=AQl5Q-0l7FQ) (26:22)

## 1. Decisión ejecutiva

No conviene migrar a Pi ni convertir nuestras skills en un harness monolítico. La arquitectura
actual es más segura y portable: separa intención de transporte, conserva al conductor como
autoridad, limita la escritura a un solo actor y valida el diff real.

Sí conviene adoptar estas ideas de Fusion Harness:

1. **Verification contract antes de implementar**, trazable desde requisito hasta evidencia.
2. **Baseline previo**, con estados explícitos en vez de asumir que todo debe comenzar en rojo.
3. **Triage de ownership** cuando una prueba falla repetidamente.
4. **Manifiesto y telemetría uniforme** por corrida cross-model.
5. **Prompts ejecutables versionados** fuera del runtime y compartidos entre transportes.
6. **Escalera de rigor explícita**, incluida una comparación read-only barata cuando tenga valor.

La regla de diseño resultante es:

> Las skills deciden por qué y bajo qué política se usa otra familia; `cross-model-orca` ejecuta,
> observa y reporta; el conductor define la aceptación, arbitra fallos y conserva la autoridad.

## 2. Alcance y verificación

Se consolidaron dos investigaciones independientes sobre el mismo material:

- los 59 archivos versionados de Fusion Harness;
- `fusion-harness.ts` completo, de 2.506 líneas;
- sus 10 archivos Markdown de prompts;
- README, recetas, artefactos de demostración y gate de validación;
- los captions automáticos completos del video;
- `cross-model-orca`, `co-explore`, `cross-review`, `cross-implement` y su relación con
  `sdd-flow`/`sdd-orchestrator`;
- el runtime y la suite local de `cross-model-orca`.

### Evidencia fresca local

```text
tests 103
pass 103
fail 0
duration_ms 305.401292
```

### Límite

No se ejecutó Fusion Harness contra modelos reales: el entorno no dispone de `pi` ni `just`, y
la corrida consumiría APIs de pago. El repositorio tampoco contiene `package.json`,
`tsconfig.json` ni tests automatizados para validar offline la extensión. Sus afirmaciones se
evaluaron contra código, contratos y artefactos versionados.

## 3. Qué construye Fusion Harness

Fusion Harness es una extensión de Pi que asigna modelos a roles y ofrece tres comandos:

| Comando | Flujo | Equivalente local aproximado |
|---|---|---|
| `/opinion` | Dos respuestas paralelas, read-only y sin merge. | No existe un modo idéntico; `co-explore` es más profundo. |
| `/fusion` | Dos workers paralelos y un tercer agente que fusiona. | Mapas + síntesis del conductor en `co-explore`. |
| `/auto-validate` | Validator diseña gate, builder implementa y el loop corrige hasta PASS o halt. | `cross-implement` + `sdd-flow verify`, pero nuestra aceptación se completa después del build. |

```text
HOST Pi = BUILDER
│
├─ /opinion
│  ├─ ARCHITECT ─┐
│  └─ BUILDER ───┴─► comparación A/B
│
├─ /fusion
│  ├─ ARCHITECT ─┐
│  ├─ BUILDER ───┴─► FUSION fresco ─► resultado atribuido
│  └─ ambos workers pueden escribir en el mismo cwd
│
└─ /auto-validate
   ├─ VALIDATOR ─► gate.py ─► baseline
   ├─ BUILDER ───► cambios
   ├─ gate.py ───► PASS | FAIL
   └─ FAIL repetido ─► TRIAGE ─► fix o reparación única del gate
```

### Aislamiento, estado y observabilidad

Los hijos arrancan con `--no-skills --no-extensions --no-context-files`. El contrato vive en
prompts externos. Esto reduce variabilidad, pero no implica sesiones siempre frescas:

- ARCHITECT conserva una sesión por proyecto y modelo;
- BUILDER intenta bifurcar la sesión del host y, si no puede, usa una propia persistente;
- FUSION nace fresco;
- cambiar el modelo crea otra identidad de sesión.

Por agente registra rol, modelo, duración, tokens, costo, tool calls, contexto, respuesta y error.
Cada corrida produce prompts, respuestas, gates, rondas y `summary.json` bajo `/tmp`.

### Tesis central del video

El video presenta un micro-SDLC basado en roles, no en un supuesto modelo ganador:

- [00:00–01:17](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=0s): combinar modelos en vez de elegir uno.
- [01:53–04:38](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=113s): medir latencia, tokens y costo sobre trabajo real.
- [04:47–08:00](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=287s): escribir la validación antes del trabajo.
- [12:55–13:24](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=775s): encadenar opinion, fusion y auto-validate.
- [16:18–17:25](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=978s): distinguir equipo de delegación clásica.
- [20:21–24:36](https://www.youtube.com/watch?v=AQl5Q-0l7FQ&t=1221s): tratar el harness como nodo de un workflow mayor.

La última idea encaja con nuestro diseño: el transporte no debe convertirse en el SDLC.

## 4. Comparación con `ai-workflows`

| Dimensión | Fusion Harness | `ai-workflows` | Decisión |
|---|---|---|---|
| Unidad | Harness con tres comandos. | Skills por intención + transporte compartido. | Mantener separación local. |
| Autoridad | HOST construye; validator/fuser deciden el resultado. | Conductor sintetiza, arbitra y verifica. | Mantener autoridad humana. |
| Exploración | Dos agentes responden el mismo prompt. | Modos explore, counter-plan, investigate y debate. | Nuestra semántica es más rica. |
| Revisión | Fusión general o validator. | `cross-review` tipa findings, confianza y arbitraje. | Mantener revisión local. |
| Implementación | Builder escribe; `/fusion` admite dos escritores. | Work order congelado, clean tree y un escritor. | Mantener disciplina local. |
| Verificación | Gate ejecutable antes del build. | `proof_cmd` y gate por AC se verifican después. | Adoptar anticipación, no el mecanismo ciego. |
| Falla repetida | Triage y una reparación del gate. | Loop acotado, takeover o retorno a diseño. | Añadir clasificación antes del takeover. |
| Transporte | Subprocess Pi acoplado a su extensión. | CLI portable + Orca + fallback. | Profundizar el kernel local. |
| Seguridad | Tool list e instrucciones; sandbox de proyecto no demostrado. | Sandbox, MCP controlado, contención, nonce y recuperación. | No retroceder. |
| Estado | Sesiones persistentes por rol/modelo. | Estado según workflow y resume acotado. | Mantener política por flujo. |
| Observabilidad | UI viva, duración, tokens, costo y summary. | Estados y logs, sin manifest común. | Cerrar este gap. |
| Prompts | Archivos interpolados. | Plantillas principalmente dentro de `reference.md`. | Extraer assets ejecutables. |
| Pruebas | No hay tests versionados. | `cross-model-orca`: 103 tests verdes. | Evolucionar sobre el kernel actual. |

## 5. Convergencias entre los dos análisis

Los informes originales coinciden en lo esencial:

1. **No pivotar de arquitectura.** Las skills Markdown portables y human-in-the-loop son una
   ventaja, no deuda que deba reemplazarse.
2. **Gate-first es la idea principal.** El criterio de done debe existir antes de ver la
   implementación y el implementador no debe poder ablandarlo.
3. **El verificador también puede fallar.** El loop necesita distinguir defecto de código de
   defecto de aceptación.
4. **El conductor conserva autoridad.** No se debe importar la autonomía total de Fusion.
5. **Un escritor por working tree.** Una convención de nombres no sustituye aislamiento físico.
6. **Usar mecanismos nativos del proyecto.** No imponer Python/`uv` como formato universal.
7. **No fijar roles a marcas de modelos.** La familia opuesta es un invariante más estable.

## 6. Divergencias y resolución

### 6.1 Qué implementar primero

- El análisis de Claude prioriza gate-first, luego triage y finalmente un modo `opinion`.
- El análisis de Codex prioriza observabilidad sin cambio de conducta, luego gate-first y triage.

El debate resolvió la diferencia con una variante de *thin vertical slice*: definir contratos
mínimos, instrumentar únicamente el piloto de `cross-implement` y después introducir verification
contract + triage en el mismo flujo. No se despliega observabilidad a todas las skills ni se lanza
gate-first sin medición.

### 6.2 Qué significa “gate”

Claude propone un gate ejecutable previo en scratch. Codex propone empezar por un contrato
declarativo, compuesto principalmente por tests/comandos existentes, y revisar cualquier helper
generado antes de ejecutarlo.

La síntesis segura es separar dos conceptos:

- **verification contract:** definición inmutable de requisitos, evidencia, comando/observación,
  resultado esperado y baseline;
- **gate executable:** implementación opcional de parte del contrato cuando los mecanismos
  existentes no bastan.

El contrato es obligatorio. El script generado no lo es.

### 6.3 Si necesitamos un modo `opinion`

Claude identifica un hueco para consultas A/B baratas. Codex no lo considera prioritario: un modo
nuevo amplía API, routing, prompts y mantenimiento antes de medir demanda real.

La decisión debe basarse en telemetría y casos de uso. Primero se puede documentar una escalera de
rigor usando los modos existentes; solo se agrega `opinion` si hay consultas reales donde
`co-explore` resulte desproporcionado.

### 6.4 Grader separado o conductor

Fusion usa un validator distinto. En nuestro flujo el conductor ya es distinto del implementador,
define el work order, revisa el diff y ejecuta pruebas. Un tercer rol obligatorio añade costo sin
resolver una falta de autoridad.

Default propuesto: el conductor define y aprueba el contrato. Para trabajo complejo puede pedir una
revisión read-only del contrato, pero esa revisión no toma control del gate.

## 7. Hallazgo del demo: el gate termina RED

El ejemplo versionado no acabó verde. Su manifest declara 11 checks PASS y 4 FAIL porque
`clean_md()` elimina underscores y vuelve imposibles cuatro comprobaciones. Se confirma en
[`gate.py:60-61`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/live_final_generation/harness-artifacts/gate.py#L60-L61)
y en el
[`MANIFEST`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/live_final_generation/MANIFEST-claude-fable-5-gpt-5.6-sol.md#L22-L36).

Esto no invalida gate-first. Demuestra que el verificador es software y requiere:

- versión y hash;
- ownership de fallas;
- revisión o pruebas propias;
- relación verificable entre commit, prompts, gate, ejecución y resultado promocionado.

## 8. Mejoras propuestas

> Nota de numeración: las etiquetas `P*` conservan el catálogo de propuestas previo al debate;
> la autoridad temporal es la secuencia de fases de §12. En particular, P0.4 está diferida a la
> Fase 5 (ver §11, R0).

### P0.1 — Manifiesto y telemetría mínima

El **caller** debe generar un único `run.json` para la invocación completa. Es el único actor que
observa `desired → intento Orca → fallback CLI → effective`. La salida JSON actual del kernel se
ingiere como una entrada de `attempts[]`; no se crea un segundo manifest del transporte en v1.

```json
{
  "schemaVersion": 1,
  "runId": "uuid",
  "workflow": "cross-implement",
  "mode": "implement",
  "role": "builder",
  "family": "claude",
  "model": null,
  "transport": {
    "desired": "auto",
    "effective": "cli",
    "fallbackUsed": true
  },
  "attempts": [
    {
      "transport": "orca-session",
      "startedAt": "ISO-8601",
      "finishedAt": "ISO-8601",
      "code": 4,
      "recovered": true
    },
    {
      "transport": "cli",
      "startedAt": "ISO-8601",
      "finishedAt": "ISO-8601",
      "code": 0,
      "recovered": null
    }
  ],
  "timing": {
    "startedAt": "ISO-8601",
    "finishedAt": "ISO-8601",
    "durationMs": 123456
  },
  "outcome": {
    "status": "ready",
    "code": 0
  },
  "usage": {
    "inputTokens": null,
    "outputTokens": null,
    "costUsd": null,
    "source": "unavailable"
  },
  "artifacts": [
    { "kind": "prompt", "path": "prompt.md", "sha256": "..." },
    { "kind": "report", "path": "result.md", "sha256": "..." }
  ],
  "ext": {
    "cross-implement": {
      "fixRounds": 1,
      "verificationReruns": 0,
      "triage": []
    }
  }
}
```

Reglas:

- el core es genérico; los campos del workflow viven bajo `ext.<workflow>`;
- `attempts[]` tiene un solo owner: el caller;
- duración, outcome, transporte y cada intento son obligatorios;
- tokens/costo permanecen `null` si la fuente no los entrega;
- la procedencia de las métricas es normativa a nivel de schema, no repetida por corrida: la
  spec incluye una matriz de procedencia por ruta, condicionada por transporte cuando aplica
  (`attempts[].code` proviene del JSON del kernel en `orca-session` y del exit code del proceso
  en `cli`; se deduce de `attempts[].transport` sin campo adicional);
- solo `usage` lleva `source` por corrida porque su procedencia sí varía; `usage.source` aplica
  homogéneamente a tokens y costo — nunca se mezclan valores reportados con estimados; una
  métrica que adquiera procedencia variable recibe su propio `source` en una versión aditiva;
- no se guarda razonamiento interno;
- un helper crea `<runId>.partial.json` antes del primer intento y lo actualiza por transición;
- la finalización normal usa rename atómico; un `.partial` sin estado terminal significa
  `incomplete`, nunca success;
- `finish` rechaza el cierre si queda algún attempt abierto — no auto-cierra ni repara: cerrar
  un intento no exitoso (abort, `unterminated`) es una transición explícita previa vía
  `attempt-finish`;
- un attempt cuyo escritor pueda seguir activo (ni terminó ni fue recuperado de forma
  demostrable) permanece incompleto y el manifest no se vuelve terminal;
- `attempts[].code` es nullable cuando no hubo exit code observable;
- v1 cubre solo `cross-implement` normal/complex; otros callers y parent/child runs se difieren.

### P0.2 — Verification contract antes del dispatch

Para `cross-implement` y flujos SDD normal/complex:

```markdown
## Verification contract

| ID | Requirement | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| V1 | AC-1 | test | npm test -- --run foo.spec.ts | test X passes | RED |
| V2 | AC-2 | build | npm run build | exit 0 | N/A |
| V3 | AC-3 | manual | viewport 390x844 | CTA visible | pending |
```

Flujo:

1. El conductor deriva el contrato desde spec, plan, tasks o work order.
2. Cada requisito tiene evidencia; ninguna prueba exige trabajo fuera de alcance.
3. Se ejecuta baseline donde tenga sentido.
4. El resultado se clasifica como `RED`, `GREEN_ALREADY`, `NOT_APPLICABLE` o `BLOCKED`.
5. Un baseline verde se adjudica como `already_satisfied`, `weak_check` o `invalid_assumption`.
6. El contrato se congela antes del dispatch y el implementador no puede modificarlo.
7. El conductor repite la evidencia final y `sdd-flow verify` conserva autoridad.

No se genera `gate.py` por default. Se prefieren tests específicos, build/lint existentes y
observaciones declarativas. Cualquier helper ejecutable requiere revisión, sandbox sin red,
dependencias vacías, allowlist y timeout.

### P0.3 — Triage de ownership

Antes de gastar otra ronda ante la misma falla:

| Clase | Acción | Consume ronda del implementador |
|---|---|---|
| `IMPLEMENTATION_DEFECT` | Feedback concreto a la misma sesión. | Sí |
| `VERIFICATION_DEFECT` | Corregir y versionar el contrato; repetir prueba. | No |
| `ENVIRONMENT_FAILURE` | Reparar entorno o marcar blocked. | No |
| `DESIGN_GAP` | Volver a plan/spec; no seguir parchando. | No |

El conductor hace el triage sobre estado real. Puede pedir opinión read-only en casos ambiguos,
pero no delega la decisión. Antes de clasificar la segunda falla consecutiva del mismo check como
`IMPLEMENTATION_DEFECT`, debe registrar una razón falsable de por qué el contrato no está
defectuoso. La taxonomía inicial se calibra con el piloto; la reparación automática se difiere.

El takeover no rebaja la vara: cuando el conductor agota las rondas y termina la implementación
él mismo, el verification contract congelado sigue definiendo "hecho" también para él. Toda
corrección del contrato durante el takeover pasa por este mismo triage —`VERIFICATION_DEFECT`
solo si el error es del verificador— y queda versionada; nunca es una edición silenciosa. Un
`DESIGN_GAP` descubierto durante el takeover lo suspende y devuelve el trabajo a plan/spec.

### P0.4 — Prompts como assets versionados

```text
skills/cross-model-orca/assets/prompts/
├── explore.md
├── counter-plan.md
├── investigate.md
├── debate-round-0.md
├── debate-cross.md
├── review.md
├── implement.md
└── fix.md
```

El renderer debe validar placeholders, producir el mismo prompt para CLI y Orca, calcular un hash
y permitir golden tests. `SKILL.md` conserva políticas; `reference.md`, contratos; los assets,
la entrada exacta del secundario.

### P1.1 — Eventos de lifecycle y cancelación

```text
session_created
boot_wait
dispatched
working
harvesting
promoted
completed | aborted | failed
```

Cada evento incluye `runId`, timestamp, familia, rol y transporte. El caller decide cómo
renderizarlo. La cancelación debe reutilizar la recuperación existente y distinguir abort del
usuario de fallo del modelo.

### P1.2 — Artifact protocol común

```text
<workflow-run>/
├── run.json
├── prompt.md
├── source-context.json
├── raw-report.md
├── result.md
├── rounds/
│   └── 01.json
└── proofs/
    └── V1.txt
```

Los paths actuales pueden mantenerse por compatibilidad. El manifest los referencia.

### P1.3 — Escalera de rigor cross-model

La documentación debe explicar cuándo escalar:

```text
respuesta local
  → comparación A/B barata, si existe demanda
  → co-explore: mapa, investigación o debate
  → cross-review: crítica de una decisión escrita
  → cross-implement: construcción desde contrato congelado
  → sdd-flow verify: evidencia final por AC
```

No crear `opinion` hasta definir un caso de uso y medir que `co-explore` sea demasiado costoso.
Si se agrega, debe ser read-only, sin merge obligatorio y sin tercer agente.

### P1.4 — Honestidad de límites y atribución de fallos

Los outputs deben:

- distinguir rol, familia, modelo efectivo, transporte y error;
- declarar que una segunda familia aumenta cobertura, no garantiza correctitud;
- conservar divergencias relevantes en vez de borrarlas en una síntesis;
- evitar trasladar nombres de familias o mecánica interna a artefactos públicos.

### P2.1 — Evals sobre trabajo real

Casos mínimos:

- exploración acotada;
- plan con defectos sembrados;
- implementación desde work order congelado;
- timeout y recovery;
- reporte mayor a 1 MB;
- verification contract defectuoso;
- drift fuera de alcance;
- Windows/POSIX.

Métricas:

| Métrica | Pregunta |
|---|---|
| `wall_ms` | ¿Cuánto tarda el workflow completo? |
| `secondary_ms` | ¿Cuánto consume la otra familia? |
| `accepted_findings / findings` | ¿La segunda opinión aporta señal? |
| `fix_rounds` | ¿El work order era suficiente? |
| `verification_defects` | ¿Los gates producen falsos rojos/verdes? |
| `fallback_rate` | ¿Es estable el transporte preferido? |
| `recovery_failure_rate` | ¿Existe riesgo de doble escritor? |
| `drift_hunks` | ¿Se respeta el alcance? |
| `human_interventions` | ¿El workflow reduce o desplaza trabajo? |

### P2.2 — Identidad de sesión por familia/modelo

El informe de Claude resalta un failure mode documentado por Fusion: reproducir un transcript largo
creado bajo otro modelo puede activar clasificadores de usage policy. Nuestro diseño ya mitiga el
riesgo al pasar contratos destilados y crear sesiones propias.

Regla: nunca hacer que una familia continúe como propia la transcripción cruda de otra; cualquier
resume se limita a la misma familia, workflow y ventana controlada.

## 9. Qué no debemos copiar

1. **Dos escritores concurrentes en el mismo cwd.** La prevención por naming no sustituye
   worktrees disjuntos.
2. **Ejecución ciega de Python generado.** Un prompt de “sin efectos laterales” no es sandbox.
3. **Host como builder y loop autónomo por default.** El humano sigue siendo autoridad.
4. **Memoria persistente global por rol.** La sesión se decide por workflow.
5. **IDs de modelos hardcodeados.** Registrar modelo efectivo; configurar perfiles semánticos.
6. **Tercer fuser obligatorio.** La síntesis del conductor es más barata y responsable.
7. **Runtime monolítico.** Separar módulos pequeños, contratos y tests.
8. **Python/`uv` universal.** Usar el mecanismo nativo del repo.
9. **TUI propia como requisito.** Lifecycle estructurado permite múltiples superficies.

## 10. Arquitectura objetivo

```text
┌──────────────────────────────────────────────────────────────┐
│ Workflow policies                                           │
│ co-explore · cross-review · cross-implement · sdd-flow      │
│ Deciden cuándo, por qué, gates humanos y autoridad final.   │
└───────────────────────────┬──────────────────────────────────┘
                            │ typed invocation
┌───────────────────────────▼──────────────────────────────────┐
│ Cross-model runtime kernel                                  │
│ transport · profiles · dispatch · harvest · resume · cancel │
│ recover · lifecycle events · telemetry                      │
└───────────────────────────┬──────────────────────────────────┘
                            │ artifacts
┌───────────────────────────▼──────────────────────────────────┐
│ Run protocol                                                │
│ run.json · prompt · report · verification contract · proofs │
└───────────────────────────┬──────────────────────────────────┘
                            │ evidence
┌───────────────────────────▼──────────────────────────────────┐
│ Human/conductor gate                                        │
│ adjudica · revisa diff · corre pruebas · commit/push         │
└──────────────────────────────────────────────────────────────┘
```

## 11. Revisión y debate cross-model

El consolidado se sometió a `co-explore debate` con Claude mediante sesiones Orca read-only. Hubo
una ronda de posturas independientes y dos rondas de crítica cruzada.

### R0 — Convergencia sobre la estrategia

Codex y Claude eligieron la opción C: contratos mínimos, telemetría acotada y piloto gate-first en
`cross-implement`. Coincidieron en:

- verification contract declarativo obligatorio; gate ejecutable opcional;
- contract y triage dentro del mismo piloto;
- separar `fixRounds` de `verificationReruns`;
- diferir `opinion`, prompts, artifact protocol, perfiles, UX y `sdd-flow`;
- no tocar `co-explore` ni `cross-review` en el primer rollout.

### R1 — Hallazgo de ownership

La crítica detectó que `run-orca-session.mjs` no ejecuta el fallback CLI: devuelve code 2/3/4 y el
caller decide si lanza CLI. Por tanto, el kernel no puede conocer por sí solo la corrida completa.
Un manifest kernel-only haría imposible medir correctamente `fallbackUsed` y `fallback_rate`.

La primera resolución propuso dos niveles, transport-attempt y workflow-run. La segunda crítica
mostró que mantener artefactos separados obligaría a reconciliar owners justo en la costura del
fallback y aumentaría el riesgo de doble conteo.

### R2 — Resolución final

Se acepta la objeción de Claude y se colapsa v1 en **un manifest caller-owned con `attempts[]`**:

1. El kernel conserva su JSON actual; el caller lo ingiere como intento Orca.
2. El caller registra también el intento CLI alrededor del `exec`.
3. El manifest empieza como `.partial` antes del primer intento.
4. Cada transición actualiza el mismo artefacto; la finalización normal hace rename atómico.
5. Si el caller muere, el `.partial` queda explícitamente incompleto, nunca se interpreta como éxito.
6. Los campos propios de implementación viven en `ext.cross-implement`.

La implementación mínima no requiere envolver todavía todos los workflows ni modificar
`harvest-core`, contención, dedup FSM, recovery o exit codes. Un helper caller-side provee las
operaciones `start`, `attempt-start`, `attempt-finish` y `finish`.

### Guardrails acordados

- `schemaVersion: 1` es mínimo y evoluciona de forma aditiva.
- El field-set deriva de métricas comprometidas, no de datos fáciles de capturar.
- Fallback produce dos entradas ordenadas en un solo `attempts[]`.
- La segunda falla del mismo check fuerza justificación antes de culpar a la implementación.
- El piloto cubre solo `cross-implement` normal/complex.
- La integración multi-nivel y `runId` parent/child quedan fuera de v1.
- `opinion` solo se considera con demanda demostrada.

### Resultado del debate

La convergencia no produjo un “ganador”; produjo un diseño más estrecho que las dos propuestas
iniciales. El mejor camino es **C con manifest caller-owned**, contract + triage en un piloto único y
expansión únicamente después de medir. Se cerró antes de una tercera crítica cruzada porque la
síntesis aceptó los dos guardrails residuales —manifest único y finalización caller-side— y no quedó
un desacuerdo técnico sustantivo. La decisión de adoptarlo sigue siendo de Max.

### Segunda pasada de revisión (2026-07-22)

Una revisión posterior del consolidado, conducida por Claude contrastándolo con los dos insumos,
detectó cinco ajustes y los sometió a un nuevo debate con Codex (una ronda de posturas
independientes y una de crítica cruzada; convergencia temprana sin desacuerdo residual). Lo
incorporado:

1. el contrato congelado rige también durante el takeover; correcciones solo vía triage tipado y
   versionado, y un `DESIGN_GAP` descubierto en takeover lo suspende (P0.3, Fase 2, §14.11);
2. `finish` rechaza attempts abiertos; los cierres no exitosos son transiciones explícitas
   previas, y un escritor posiblemente activo mantiene el manifest no terminal (P0.1, Fase 1);
3. la numeración `P*` queda anotada como catálogo pre-debate, con §12 como autoridad temporal;
4. los criterios de §14 declaran fase exigible, son acumulativos y los multi-fase se dividieron;
5. la regla de procedencia pasó a ser normativa a nivel de schema (matriz por ruta, condicionada
   por transporte), con `source` por corrida solo en `usage`.

Cabo suelto menor, a resolver al implementar: si la política aditiva de `schemaVersion` necesita
una definición formal de compatibilidad (qué significa "v1.x" para lectores estrictos) o basta el
guardrail existente.

## 12. Secuencia recomendada de implementación

### Fase 0 — ADR y baseline del sistema actual

1. Congelar invariantes: conductor autoritativo, un escritor y compatibilidad CLI/Orca.
2. Definir `schemaVersion: 1` mínimo para `run.json` y verification contract.
3. Capturar el baseline de los 103 tests actuales.

### Fase 1 — Manifest vertical `cross-implement`

1. Añadir un helper caller-side para crear/actualizar/finalizar `run.json`.
2. Registrar en un solo `attempts[]` Orca y CLI, incluido fallback.
3. Usar `.partial` como evidencia honesta de crash/abort no finalizado.
4. Añadir tests golden de fallback, kill-mid-run, `finish` rechazado con attempts abiertos y
   cierre explícito de un intento no exitoso.
5. No cambiar el kernel, sus exit codes ni las otras skills.

**Exit criterion:** una unidad SDD/PR behavior-neutral; si requiere modificar harvest, contención,
dedup o recovery, se detiene y reevalúa el diseño.

### Fase 2 — Piloto contract + triage en `cross-implement`

1. Verification contract en el work order.
2. Baseline tipado antes del dispatch.
3. Evidencia final ejecutada por el conductor.
4. Triage manual obligatorio antes de consumir otra ronda repetida.
5. El contrato congelado rige también el takeover; correcciones solo vía triage versionado.
6. Piloto en tareas normales y complejas; no en todos los workflows.

### Fase 3 — Adjudicar el piloto

1. Comparar `fixRounds`, `verificationReruns`, defects y fallback.
2. Estabilizar o corregir la taxonomía de cuatro clases.
3. Decidir si se habilita una reparación versionada sin consumir ronda.
4. No expandir si los datos no muestran señal o el manifest resulta intrusivo.

### Fase 4 — Integración con `sdd-flow`

1. Derivar el contrato desde AC y Verification del plan.
2. Reusar el mismo contrato en implement y verify.
3. Mantener revert-to-confirm y gates humanos.

### Fase 5 — Expansión selectiva

1. Extraer prompts sin cambiar contenido.
2. Añadir artifact protocol y hashes.
3. Incorporar otros callers uno por uno.
4. Evaluar `opinion`, perfiles y UI solo con datos de uso.

## 13. Cambios previstos por archivo

| Archivo | Cambio potencial |
|---|---|
| `skills/cross-model-orca/assets/run-manifest.mjs` | Nuevo helper caller-side: partial, attempts y finalización atómica. |
| `skills/cross-model-orca/assets/prompts/` | Templates canónicos para CLI y Orca. |
| `skills/cross-model-orca/assets/test/` | Tests de manifest, fallback, partial/crash y métricas. |
| `skills/co-explore/SKILL.md` | Escalera de rigor, honestidad de límites y quizá `opinion`. |
| `skills/cross-review/SKILL.md` | Registrar rondas/findings/adjudicación en manifest. |
| `skills/cross-implement/SKILL.md` | Verification contract y triage de ownership. |
| `skills/cross-implement/reference.md` | Baseline tipado y reparación del contrato. |
| `skills/sdd-flow/SKILL.md` | Derivar y consumir el contrato sin perder autoridad. |
| `skills/sdd-flow/reference.md` | Plantilla de contrato y evidencia baseline/final. |

## 14. Criterios de aceptación de la evolución

Cada criterio es exigible desde la fase indicada y permanece exigible en las siguientes
(acumulativos). Los marcados Fase 0 son invariantes congelados en el ADR y rigen todo el
programa.

1. **[Fase 0]** Ningún modo agrega escritores concurrentes en un working tree.
2. **[Fase 0]** Los artefactos públicos no exponen mecánica interna ni familias de modelos.
3. **[Fase 1]** Toda corrida del piloto crea un manifest o un `.partial` inequívocamente
   incompleto; `finish` rechaza attempts abiertos.
4. **[Fase 1]** Duración, attempts, transporte efectivo, status y recovery son verificables.
5. **[Fase 1]** Tokens/costo ausentes permanecen `null`.
6. **[Fase 1]** La telemetría no contiene prompts sensibles ni razonamiento interno.
7. **[Fase 1]** La suite actual sigue verde y suma cobertura de fallback, manifest y
   partial/crash.
8. **[Fase 2]** `cross-implement` normal/complex no despacha sin contrato resuelto.
9. **[Fase 2]** Baseline usa estados tipados; verde previo nunca se acepta sin adjudicación.
10. **[Fase 2]** Un defecto del contrato no consume ronda del implementador.
11. **[Fase 2]** El contrato congelado rige también el takeover; sus correcciones son triage
    versionado, nunca edición silenciosa.
12. **[Fase 2]** El conductor vuelve a ejecutar pruebas y leer el diff completo.
13. **[Fase 2]** La suite suma cobertura del verification contract.
14. **[Fase 5]** CLI y Orca renderizan el mismo prompt a partir del mismo template/version.

## 15. Keep, adapt, reject

### Keep

- skills separadas por intención;
- `sdd-flow` y conductor como autoridades;
- familia opuesta por construcción;
- clean tree, un escritor, diff y pruebas frescas;
- sesiones frescas o acotadas al workflow;
- transporte portable con fallback;
- sandbox, contención, nonce, dedup y recovery.

### Adapt

- verification contract pre-build;
- baseline tipado;
- triage de ownership y reparación versionada;
- manifest, lifecycle y benchmarking relativo;
- prompts externos y hasheados;
- escalera de rigor y honestidad de blind spots;
- identidad de sesión compatible con familia/modelo.

### Reject

- migración a Pi;
- harness monolítico;
- escritores concurrentes;
- ejecución ciega de código generado;
- memoria global por rol;
- modelos hardcodeados;
- fuser obligatorio;
- PASS sin baseline significativo.

## 16. Fuentes

- [Informe original de Codex](./codex/README.md)
- [Informe original de Claude](./claude/README.md)
- [Fusion Harness README](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/README.md)
- [Runtime `fusion-harness.ts`](https://github.com/disler/fusion-harness/blob/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/extensions/fusion-harness/fusion-harness.ts)
- [Prompts](https://github.com/disler/fusion-harness/tree/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/extensions/fusion-harness)
- [Artefactos del demo](https://github.com/disler/fusion-harness/tree/5852f2ed4f5f064a368d83d2dabad84fe6bfa0b4/live_final_generation)
- [Video](https://www.youtube.com/watch?v=AQl5Q-0l7FQ)
- `skills/cross-model-orca/`
- `skills/co-explore/`
- `skills/cross-review/`
- `skills/cross-implement/`
- `skills/sdd-flow/`
- `docs/research/cross-model-real-sessions/`
