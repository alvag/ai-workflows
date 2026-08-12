# Roadmap — subagentes y perfiles de ejecución para las siete skills

**Estado:** Fase 0 **completada y cerrada**; Fase 0.5 es la siguiente. Fases 1–7 pendientes. La secuencia no autoriza
implementación por sí sola: cada fase entra por su propio flujo con su gate.

**Fecha:** 2026-08-06 · **Última actualización:** 2026-08-12 — cierre de la Fase 0 y **absorción**
de `implement-subagent-costo-y-diversidad/propuesta.md`, que deja de ser un plan paralelo: este
roadmap es la sede sobre la que se trabaja.

**Entradas:** `propuesta.md`, `co-explore/synthesis-explore.md`, documentación oficial de
[subagentes Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents) y
[subagentes Claude Code](https://code.claude.com/docs/es/sub-agents)

## 0. Dónde está el programa hoy

| Fase | Estado | Dónde se ejecutó |
|---|---|---|
| **0 — Spec, contrato y baseline** | **COMPLETADA** (2026-08-12) | dos flujos: `matriz-y-contrato` e `instrumento-y-baseline` |
| **0.5 — El paquete de contexto de los subagentes** | pendiente · **la siguiente** | — |
| 1 — Catálogo, adaptadores, perfiles e instalación | pendiente | — |
| 2 — Roles read-only | pendiente | — |
| 3 — Writers y cobertura de los trece despachos | pendiente | — |
| 4 — Piloto de revisión de diff | pendiente | — |
| 5 — `cross-implement` granular | pendiente, condicionada | — |
| 6 — Pipeline N/N+1 | pendiente, condicionada | — |
| 7 — Invariante dinámica | pendiente, condicionada a los datos de la Fase 4 | — |

**La Fase 0.5 no estaba en el reparto original.** La agrega la propuesta de costo del modo
`subagent` (2026-08-11), posterior a este roadmap. Entra **numerada 0.5 y no como Fase 1** a
propósito: el inventario de defectos del documento de contrato referencia «Fase 1», «Fase 2» y
«Fase 3» **por nombre** en quince lugares, así que renumerar rompería esas referencias en silencio.

## Decisión recomendada

Implementar **por fases horizontales**, no skill por skill ni como big-bang.

El ecosistema tiene siete skills y trece puntos de despacho existentes
(`scripts/verificar-sobre-en-vuelo.py:109-123`). Cambiar al mismo tiempo los agentes nativos, los
modelos, el esfuerzo de razonamiento, la distribución, los fallbacks, la revisión de diffs y la
concurrencia impediría atribuir una regresión a una causa y dejaría un rollback ambiguo.

La infraestructura común sí debe entrar como una unidad: catálogo, adaptadores, instalación,
resolución de perfiles y guardas anti-drift. La adopción conductual se despliega después, primero en
roles read-only, luego en writers y, por último, en los experimentos de revisión y concurrencia.

Recomendación de compromiso:

- **Aprobar desde ahora las Fases 0–4** como alcance del programa.
- **Condicionar las Fases 5–7 a métricas** de las fases anteriores.
- No hacer obligatoria la disponibilidad simultánea de Claude y Codex en ninguna fase.

## 1. Qué significa «soportado por las siete skills»

No significa crear un agente por skill o por gate. Significa que cada punto de despacho:

1. declara el **rol conductual** que necesita;
2. resuelve un **perfil de ejecución** compatible;
3. separa familia, rol, modelo, esfuerzo y transporte;
4. conserva su contrato de entrada, salida, permisos, deadline, snapshot y fallback;
5. funciona cuando existe una sola familia, sin presentar esa ejecución como evidencia cross-family.

Los siete consumidores y sus trece puntos actuales son:

| Skill | Puntos de despacho actuales | Rol reusable |
|---|---:|---|
| `co-explore` | fan-out dual; debate | `explorer`, `investigator`, `design-reviewer[decision-debate]` |
| `cross-review` | revisor por ronda | `design-reviewer` variante `artifact-review` |
| `cross-implement` | implementador inicial; fix loop | `bounded-implementer[work-order]`; después `diff-reviewer` |
| `sdd-flow` | analyze; implementer por task; reviewer por task; revisión final | `explorer`, `bounded-implementer[task]`, `diff-reviewer` |
| `sdd-orchestrator` | fan-out por repo | `bounded-implementer[repo-runner]` sobre Vía B |
| `sdd-pr-feedback` | implement delegado | `bounded-implementer[work-order]` sobre Vía B |
| `bitbucket-code-review` | panel; validador adversarial | `diff-reviewer[review]` y `diff-reviewer[refute]` |

Los scopes y variantes son parte obligatoria del contrato de invocación; no comparten por accidente
schema de salida ni autoridad. `decision-debate` produce posturas, no `APPROVED | REVISE`;
`diff-reviewer[refute]` intenta invalidar un finding, no revisar el diff completo. Los wrappers de Vía
B no justifican por sí solos un agente cognitivo nuevo: si `repo-runner` demuestra permisos o
lifecycle incompatibles, se separa como rol versionado en vez de ocultar la diferencia en el prompt.

## 2. Separar rol de perfil de ejecución

En este roadmap, **rol** y **perfil** no son sinónimos:

| Eje | Pregunta | Ejemplos | Dueño |
|---|---|---|---|
| Rol | ¿Qué trabajo hace y con qué restricciones? | `explorer`, `bounded-implementer` | la skill |
| Perfil de ejecución | ¿Con qué modelo y esfuerzo razona? | Claude Sonnet + `high` | config + resolver |
| Voz | ¿Qué familia produce la salida? | Claude, GPT/Codex | política de la corrida |
| Transporte | ¿Cómo se ejecuta y observa? | subagente, `cli-exec`, `cli-resume` | runtime |

La skill debe fijar el rol: permitir que `config.yml` convierta un reviewer read-only en implementer
rompería el gate. `config.yml` sí puede elegir el **perfil de ejecución** del rol —modelo y esfuerzo—,
porque eso cambia coste, latencia y profundidad, no la autoridad ni los permisos.

### 2.1 Perfiles configurables en `.specify/config.yml`

La capacidad está respaldada por ambas plataformas:

- Codex admite `model` y `model_reasoning_effort` en el agente. Si el archivo del agente los fija,
  esos valores tienen precedencia; por eso los adaptadores conductuales deben omitirlos y el resolver
  debe aplicarlos al despachar.
- Claude Code admite `model` y `effort` en el frontmatter y en definiciones efímeras con `--agents`.
  La documentación no demuestra un override de `effort` por invocación equivalente al de Codex: una
  configuración variable necesita `--agents`, una variante generada o heredar la sesión. No se asume
  simetría.

Schema candidato para validar en Fase 0:

```yaml
subagents:
  schema_version: 1
  profiles:
    economy:
      codex:
        model: inherit
        reasoning: low
      claude:
        model: inherit
        reasoning: low
    balanced:
      codex:
        model: inherit
        reasoning: medium
      claude:
        model: sonnet
        reasoning: medium
    deep-review:
      codex:
        model: inherit
        reasoning: high
      claude:
        model: sonnet
        reasoning: high
  bindings:
    default: balanced
    roles:
      explorer: economy
      investigator: deep-review
      design-reviewer: deep-review
      bounded-implementer: balanced
      diff-reviewer: deep-review
```

Es un ejemplo, no un default congelado. La configuración base debería heredar el modelo cuando el
usuario no lo elija. Los nombres comerciales no deben quedar fijados en los prompts ni en las skills;
solo aparecen como override explícito del usuario.

`reasoning` es el nombre portable del schema. El resolver lo traduce a
`model_reasoning_effort` en Codex y a `effort` en Claude. `inherit` significa omitir el campo nativo,
no confiar en que ambas plataformas acepten el mismo literal.

Precedencia controlada por las skills:

1. override explícito del usuario para la corrida;
2. binding específico del punto de despacho, si el schema final decide admitirlo;
3. binding rol → perfil de `.specify/config.yml` o del `manifest.yml` del orquestador;
4. perfil default portable;
5. default de la sesión/plataforma.

Las políticas externas del proveedor conservan su propia precedencia. El receipt nunca debe afirmar
que el modelo solicitado fue el efectivo si la plataforma u organización pudo sustituirlo y no expone
el resultado.

Restricciones:

- El perfil nunca modifica tools, sandbox, worktree, permisos, contrato de salida ni autoridad.
- Un modelo explícito no soportado no se sustituye en silencio. Si se detecta antes del launch, es una
  `confirmed_wall`; si solo se descubre al ejecutar, se clasifica con la causa operacional vigente que
  corresponda. Si el modelo se mantiene pero el esfuerzo no existe, puede continuar y el receipt marca
  `profile_degraded`; no se inventa un nuevo pseudoestado del worker.
- Un receipt durable por intento registra configuración **solicitada y efectiva**. No se amplía por
  defecto el manifest mínimo compartido. Cuando la plataforma no expone el valor efectivo, el receipt
  dice `NO_VERIFICABLE`.
- Las skills standalone consumen esta sección si existe; si no existe, usan defaults portables. No
  deben exigir crear `.specify/config.yml` para una revisión o investigación aislada.
- El resolver usa el esfuerzo más bajo que satisface el rol y la complejidad. `high` no es el default
  universal: exploraciones mecánicas pueden usar `low`; revisiones ambiguas o high-stakes pueden
  escalar.

### 2.2 Identidad de familia sin ambigüedad

`cross_family` necesita un referente. Un reviewer puede compartir familia con el conductor y, al
mismo tiempo, ser de otra familia respecto del implementador cuyo diff revisa. Cada intento debe
registrar:

- `conductor_family`;
- `artifact_author_family`;
- `worker_family`;
- relación del worker con el conductor y con el autor del artefacto;
- rol, perfil solicitado/efectivo y transporte.

Así se evita llamar «cross» a una relación distinta de la que realmente se está midiendo.

## 3. Arquitectura de distribución

Fuente y adaptadores propuestos:

```text
agents/
├── registry.yml                 # roles, consumidores, permisos y outputs
├── roles/                       # instrucciones canónicas
│   ├── explorer.md
│   ├── investigator.md
│   ├── design-reviewer.md
│   ├── bounded-implementer.md
│   └── diff-reviewer.md
└── generated/                   # vistas generadas, no editables a mano
    ├── codex/*.toml
    ├── claude/*.md
    └── claude/agents.json
```

Un instalador central materializa las vistas:

- Codex: `~/.codex/agents/*.toml` o `.codex/agents/*.toml`.
- Claude: `~/.claude/agents/*.md`, `.claude/agents/*.md` o `--agents` para una corrida efímera.
- Desarrollo POSIX: symlink administrado por el instalador.
- Entornos sin symlink portable: copia con hash y manifest de ownership.

No se enlaza el mismo archivo a las dos plataformas: TOML Codex y Markdown/JSON Claude tienen schemas
y capacidades distintas. `install`, `upgrade`, `doctor`, `dry-run` y `uninstall` operan sobre el
bundle completo. Nunca sobrescriben ni borran agentes ajenos; una instalación mezclada o un archivo
local modificado detiene la operación.

Los adaptadores persistentes contienen conducta y permisos, no modelos ni esfuerzo. Eso evita que un
valor global anule el perfil elegido por proyecto. El resolver único consume `subagents`; las siete
skills no deben parsear YAML ni traducir perfiles por separado.

## 4. Roadmap por fases

### Fase 0 — Spec, contrato y baseline · **COMPLETADA (2026-08-12)**

> **Cómo se ejecutó.** Se partió en dos flujos el 2026-08-09 porque el reparto de 43 tasks y 67 filas
> era demasiado grande para uno solo: `matriz-y-contrato` (17 AC) e `instrumento-y-baseline` (9 AC),
> más cuatro AC nuevos que las mitades agregaron. Los 29 AC de la fase quedaron cubiertos, cero
> huérfanos, y los dos flujos están `done`.
>
> **Qué entregó, contra lo que prometía:** los seis entregables están; el baseline se generó con
> **seis números medidos y dos declarados sin observaciones** —las dos latencias, porque ningún
> intento satisfizo la regla `primer_intento_valido`—. El evaluador de promoción emitió
> **`no_promovible`** por `limpieza-completa`. Eso **no es un incumplimiento de la fase**: la fase
> entregaba el instrumento y la medición, y la medición dijo que el ecosistema todavía no promociona.
> Es el insumo con el que se condicionan las Fases 5–7.
>
> **Lo que la fase descubrió y no estaba previsto:** once defectos, **todos al ejecutar** y ninguno
> cazado por revisión ni por control de mutación —los mutantes construyen los bundles a mano, así que
> ejercen el validador y nunca el productor—. Están adjudicados en `scripts/ledger-candidatos-fase-0.json`
> junto a otros diez candidatos: veintiuno en total, cuatro incorporados al inventario de defectos de
> este documento con su fase de corrección. Congelar el pre-registro antes de ejercer el flujo de
> punta a punta costó **siete reaperturas del gate**.
>
> **Artefactos vivos que las fases siguientes consumen:** la matriz de los trece puntos y su
> verificador · los tres schemas · el instrumento y el runner · el acta congelada y su baseline · el
> registro de topología con su regla de descubrimiento · el manifiesto de las 56 guardas · el ledger.

**Objetivo:** congelar el modelo antes de cambiar conducta.

**Entregables**

- spec que corrige las imprecisiones de `propuesta.md`;
- matriz 13/13: despacho → rol → permisos → voz → transporte → fallback;
- schema del perfil de ejecución y su precedencia;
- contratos de entrada/salida de las cinco familias de rol, sus scopes y variantes;
- política `cross-family`, `same-family` y `single-voice` sin equivalencias falsas;
- baseline de latencia, degradación, salidas inválidas, findings y cleanup.

**Gate de salida**

- 13/13 puntos tienen dueño, fallback y autoridad final;
- la matriz estática cubre 13/13 puntos y las siete skills, sin consumidores ni perfiles huérfanos;
- ningún perfil de ejecución puede elevar permisos;
- lifecycle operacional, validez del reporte y outcome semántico quedan como ejes separados: no se
  fuerza un enum único sobre contratos que hoy devuelven resultados distintos;
- se fija antes del piloto la cohorte y los umbrales de promoción.

**Rollback:** no aplica; solo artefactos de diseño.

### Fase 0.5 — El paquete de contexto de los subagentes

**Objetivo:** que un implementer delegado reciba lo que su task cita, y no el corpus entero. No
introduce agentes nuevos, ni perfiles, ni adaptadores: **mejora el modo `subagent` que ya existe**, y
por eso puede correr antes que toda la infraestructura común.

**Por qué va acá y no después.** Las Fases 2 a 6 despachan cada vez más agentes. Si el paquete no se
recorta antes, cada fase multiplica un costo que ya está medido —y la Fase 6, que paraleliza, lo
multiplica por el ancho del paralelismo: *k* agentes ingiriendo el corpus completo chocan contra
límites de concurrencia por el peso que nadie recortó.

**Medido** con `scripts/medir-dossier-de-task.py` sobre **20 flujos archivados y 296 tasks reales**:

| | |
|---|---|
| Lo que el prompt manda leer hoy | 184.665 b en el flujo más grande |
| La task que hay que ejecutar | 2.089 b de promedio · **ratio ~88:1** |
| Ingesta por task de comportamiento | **~76k tokens**, sumando implementer y reviewer |
| Reducción con dossier | **~14x mediana**, rango 4,2x a 32,8x, **los 20 flujos mejoran** |

**Entregables**

- el prompt del implementer recibe un **dossier interpolado** —la task, los AC que cita, las filas
  del contrato que la prueban, el `Produce` de lo que consume y el enfoque del plan— en vez de rutas
  a leer;
- la regla de escape: si el dossier no alcanza, `STATUS: failed` **diciendo qué pieza faltó**, sin ir
  a buscarla al repo;
- el armado del lado conductor, con sus reglas de extracción;
- el diff de cada task se acota por el campo `Archivos` en vez de depender de que el reporte llegue;
- el arnés de medición, que ya existe y es el que fija el número de la fase.

**Gate de salida**

- toda pieza que una task cita **resuelve**, o la task no se despacha: un dossier incompleto se lee
  igual que uno completo;
- un id declarado dos veces **no se colapsa en silencio**;
- el extractor tiene **control positivo**: todos los AC declarados salen no vacíos —sin él, un patrón
  que no reconoce el formato produce dossiers minúsculos que se leen como un éxito—;
- cero tasks parseadas es un **error con nombre**, no un dossier chico;
- el conjunto de tasks que hoy terminan `[x]` sigue terminando `[x]`, y los `failed` nuevos **nombran
  su pieza faltante**: son el dato que dice qué recortar, no una regresión;
- cambio conductual fuera del modo `subagent`: **cero**.

**Lo que esta fase deja medible y hoy no lo es.** La skill declara que las tasks son autosuficientes
—«cada task debe poder ejecutarla un agente fresco que solo ve spec/plan/su task»— y el prompt no le
cree: lo manda a leer los tres artefactos igual. Con dossier, **una task mal escrita se manifiesta**
en vez de quedar tapada por el corpus completo. La autosuficiencia pasa de aspiración a propiedad
falsable, y eso es insumo de todas las fases que delegan.

**Rollback:** volver el prompt a las rutas. No hay estado migrado ni artefacto nuevo que revertir.

**Riesgo declarado.** Puede existir contexto que hoy salva al agente en silencio y que la task no
cita. Se arranca **generoso** —el enfoque completo del plan pesa ~2 KB— y se recorta con los `failed`
reportados como evidencia, nunca por intuición.

### Fase 1 — Catálogo, adaptadores, perfiles e instalación

**Objetivo:** instalar y resolver agentes sin cambiar todavía el routing vigente.

**Entregables**

- catálogo canónico y generador determinista;
- adaptadores Codex/Claude;
- parser y validador de `subagents.profiles` y `subagents.bindings`;
- schema y vista equivalentes en el `manifest.yml` del orquestador, con precedencia container/repo
  explícita;
- `install`, `upgrade`, `doctor`, `dry-run` y `uninstall`;
- manifest de archivos propios, destinos, hashes y versión;
- fixtures: solo Codex, solo Claude, ambas plataformas y ninguna.

**Gate de salida**

- dos generaciones producen bytes idénticos;
- instalación y desinstalación son idempotentes;
- campos desconocidos, perfiles huérfanos y bindings rotos fallan cerrado;
- `doctor` distingue plataforma ausente, perfil no soportado e instalación rota;
- una config con Claude Sonnet + `high` y otra con `inherit` + `low` resuelven distinto y quedan
  registradas;
- los siete consumidores resuelven perfiles contra fixtures de config y manifest, sin ejecutar aún
  el nuevo routing;
- una matriz intención/config/complejidad → dispatcher conserva el baseline de cada skill;
- cambio conductual de las siete skills = cero.

**Rollback:** desinstalar adaptadores; el routing anterior sigue intacto.

### Fase 2 — Roles read-only

**Objetivo:** validar especialización, perfiles y resolución por plataforma con el menor riesgo.

**Alcance**

- `co-explore`: `explorer` e `investigator`;
- `cross-review`: `design-reviewer` sin relajar su requisito nominal de otra familia;
- `bitbucket-code-review`: `diff-reviewer` para review y refutación;
- `sdd-flow`: analyze, reviewer por task y revisión final;
- `sdd-orchestrator` reutiliza resultados de revisión producidos antes del fan-out y mantiene
  `cross_review`/`co_explore` apagados dentro del worker;
- `sdd-pr-feedback` conserva los reviews en el conductor antes de delegar. Ninguno anida un reviewer
  dentro de otro subagente.

**Gate de salida**

- violaciones read-only: 0;
- procesos sin deadline o cleanup: 0;
- receipt registra rol, perfil solicitado/efectivo y modelo verificable; los artefactos de corrida
  conservan la familia;
- una plataforma ausente degrada sin bloquear ni presentarse como diversidad;
- la matriz intención/config/complejidad → dispatcher coincide con el routing actual, incluidos el
  panel conductor-only por default y la revisión final solo cuando hoy corresponde;
- el formato semántico de los informes no cambia respecto del baseline.

**Rollback:** volver al subagente genérico o CLI vigente; los adaptadores quedan instalados sin uso.

#### 2.a El reparto de ejes de revisión, y la corrección del encuadre de «degradación»

Absorbido de la propuesta de costo (pieza C y su corrección de arrastre). Hoy el reviewer por-task de
`sdd-flow` es un subagente fresco **de la misma familia que el conductor** que evalúa dos ejes de una
vez. Esa fila **está dominada**: paga un despacho serial para dar un revisor que comparte los puntos
ciegos del implementer y tiene *menos* contexto que el conductor.

Los dos ejes no tienen la misma red de contención, y por eso no van al mismo lugar:

| Eje | ¿Hay segunda red? | Destino |
|---|---|---|
| `SPEC` — ¿cumple los AC? | **sí**: `verify` lo recorre al final con evidencia fresca | **el conductor**: tiene el mapa y cuesta cero despachos |
| `QUALITY` — code smells, patrones del repo | **ninguna** | **la otra familia** si hay CLI; con una sola familia, subagente fresco **agrupado**, no uno por task |

**Degradar a una sola familia degrada el eje de diversidad, no el de calidad:** el revisor sigue
existiendo y el contrato `SPEC`/`QUALITY` no se toca. Lo único que se pierde es la ruptura de
correlación de errores, que sin segunda familia no es obtenible por ningún medio.

**Corrección de arrastre, y vale por sí sola.** Hoy la revisión por el conductor está catalogada como
**degradación**. Eso es herencia del modo `inline`, donde el conductor revisaría **su propio código**.
En `subagent` no escribió nada: es un revisor legítimamente independiente, con el mapa cargado y **la
única vista de la coherencia entre tasks** —los reviewers por-task tienen instrucción explícita de
ignorar los hunks ajenos—. Frente a un subagente fresco de la misma familia, el conductor **empata**
en puntos ciegos y **gana** en coherencia.

**Gate propio de 2.a**

- ningún `QUALITY` agrupado juzga hunks de tasks fuera de su grupo: el diff se acota por paths, igual
  que hoy;
- la familia efectiva del revisor de `QUALITY` **se declara** en los artefactos de la corrida; una
  aprobación same-family nunca se presenta como evidencia cross-family;
- el eje `SPEC` movido al conductor conserva `verify` como red: no se elimina ninguna comprobación,
  se elimina un despacho.

**Riesgos que carga esta fase**

- **Feedback tardío:** agrupar corre el hallazgo de calidad hacia el final y un patrón malo se replica
  en varias tasks antes de que alguien lo vea. Mitigación: grupos chicos que no crucen fronteras de AC.
- **`SPEC` al conductor hereda su sesgo de autor:** escribió spec, plan y tasks, y las lee como «lo
  que quise decir». Contrapeso: `verify` con evidencia fresca por AC. **Riesgo aceptado y declarado**,
  no disimulado.
- **Sube el costo de tokens, no lo baja:** agrega un CLI externo. El ahorro viene de la Fase 0.5, y
  por eso esta fase va después.

### Fase 3 — Writers y cobertura de los trece despachos

**Objetivo:** adoptar `bounded-implementer` con scope explícito, sin introducir concurrencia nueva.

**Alcance**

- implementer por task de `sdd-flow`;
- implementador y fix loop de `cross-implement`;
- fan-out por repo de `sdd-orchestrator`;
- fix delegado de `sdd-pr-feedback`;
- conservar la regla 8 actual y el loop secuencial por working tree.

**Gate de salida**

- los trece puntos resuelven rol y perfil o ejecutan su fallback documentado;
- escrituras fuera del `working_dir`: 0;
- commits o push hechos por workers: 0;
- el conductor repite la evidencia y conserva `verify` y los STOP;
- todo fix/follow-up reanuda la identidad de sesión y `run_id` exigidos; un fixture que abra una
  sesión nueva debe fallar;
- el fan-out del orquestador conserva el orden `bitácora → sobre → despacho`, con fallos inyectados
  entre transiciones: nunca existe worker sin sobre ni despacho consumado sin evento previo;
- los cambios de tests están autorizados por el work order, aparecen en el diff auditado y, para AC
  de comportamiento, conservan evidencia RED mediante baseline o revert-to-confirm;
- recovery probado ante salida inválida, timeout y proceso muerto.

**Rollback:** cada writer vuelve al dispatcher anterior sin migrar artefactos SDD.

### Fase 4 — Piloto de revisión de diff, sin overlap

**Objetivo:** medir la posición revisora sin cambiar todavía doctrina ni concurrencia.

**Flujo piloto**

1. `cross-implement` conserva el implementador de la otra familia.
2. Al terminar el writer se captura un snapshot inmutable con `base_sha`, `snapshot_sha`, hash del
   diff y hashes de spec/plan/tasks.
3. Un `diff-reviewer` fresco, de familia distinta a la del implementador cuando esté disponible,
   revisa SPEC y QUALITY.
4. Sus findings entran a un ledger adjudicable.
5. El conductor lee el diff y repite las pruebas.

El reviewer puede compartir familia con el conductor; los artefactos de corrida lo declaran. Sin la
familia opuesta al autor del diff se puede usar un reviewer same-family como contexto fresco, pero su
aprobación no cuenta como evidencia independiente y su corrida no entra a la cohorte cross-family.

**Gate de salida**

- `base_sha`, `snapshot_sha`, diff y artefactos SDD revisados coinciden con el receipt: 100 %;
- brechas de sandbox, carreras o cleanup: 0;
- cada finding se adjudica y clasifica como ambigüedad contractual, defecto de implementación,
  duplicado o falso positivo;
- se mide latencia, coste, findings únicos, duplicación y rework por perfil de ejecución;
- el piloto demuestra valor con los umbrales pre-registrados en Fase 0.

**Rollback:** desactivar el reviewer y volver exactamente al `cross-implement` actual.

### Fase 5 — `cross-implement` granular por task, aún secuencial

**Objetivo:** crear la frontera que necesitaría N/N+1 sin abrir overlap.

**Entregables**

- task ID, ownership y DAG explícitos;
- snapshot y ledger por task;
- join `implementación + review + prueba`;
- resume desde la última transición persistida;
- un kernel pequeño para dispatch/poll/snapshot solo si la prosa ya no puede verificar el lifecycle.

**Gate de salida**

- una task no se marca `[x]` antes del join completo;
- un solo writer activo;
- crash inyectado en cada transición se recupera sin duplicar trabajo;
- el modo secuencial conserva el diff final normalizado, estado de tasks, ledger, evidencia por AC y
  comandos/exit codes del flujo actual;
- un finding nunca se atribuye a otra task.

**Rollback:** volver a tratar todo el work order como una unidad.

### Fase 6 — Pipeline limitado N/N+1

**Objetivo:** revisar N mientras se implementa N+1 solo cuando sea demostrablemente seguro.

**Elegibilidad obligatoria**

- snapshot inmutable de N;
- N y N+1 independientes en el DAG;
- ownership y joins verificables;
- un único writer sobre el working tree;
- re-invocación durable del conductor;
- ledger semántico separado del sobre operacional.

Leer el working tree mientras N+1 lo modifica queda prohibido. Si falta cualquiera de las
precondiciones, el flujo sigue secuencial.

**Gate de salida**

- cero colisiones, snapshots contaminados o joins perdidos;
- recovery de proceso muerto probado;
- ninguna task se publica o commitea antes de cerrar su review;
- equivalencia con el modo secuencial sobre diff normalizado, estado de tasks, ledger, evidencia por
  AC y comandos/exit codes;
- reducción de wall time superior al umbral pre-registrado, sin aumentar rework ni defectos escapados.

**Rollback:** dejar de abrir overlaps, drenar reviewers activos y continuar desde el ledger en modo
secuencial.

#### 6.a Worktrees paralelos por implementer — condición de activación y diseño

Absorbido de la propuesta de costo (pieza B), que la **difiere** con una medición: sobre la corrida
real de 30 tasks, **25 (83 %) declaran `Consume`** y tres archivos son tocados por más de una task.
Con ese grafo el ancho real de paralelismo es mínimo y se pagaría toda la maquinaria para paralelizar
un puñado de tasks. **Se difiere, no se descarta:** ese 83 % refleja cómo *este* repo escribe tasks;
en proyectos con tasks independientes el rendimiento sería otro.

**Condición de activación**, verificable antes de construir nada: con la Fase 0.5 ya aplicada,
`(tasks sin Consume ni colisión de archivos) ≥ 3` en una corrida concreta **y** el tiempo sigue
siendo el problema dominante. **Sin la Fase 0.5 esto es contraproducente:** *k* agentes ingiriendo el
corpus completo a la vez chocan contra límites de concurrencia justamente por el peso que no se
recortó.

**Diseño esbozado, para cuando se active**

1. **El anidamiento no es el problema.** Los worktrees no son jerárquicos: uno linked puede crear
   otros y el nuevo se registra como hermano.
2. **Ubicar el registro con `git rev-parse --git-common-dir`**, nunca asumiendo `<toplevel>/.git`: en
   un worktree linked `.git` es un *archivo*.
3. **La misma rama no puede estar checked out en dos worktrees**: los hijos van `--detach` sobre el
   commit base, coherente con que los subagentes no commitean.
4. **Crearlos FUERA del árbol de trabajo.** Uno anidado aparece como directorio untracked y contamina
   `git status --porcelain`, que es la fuente de verdad con la que el conductor clasifica propios y
   ajenos: lo rompería en silencio.
5. **La cosecha es el problema real.** El subagente tiene prohibido commitear, así que sus cambios
   quedan sin commitear **en otro árbol** y hay que traerlos worktree por worktree. **El paralelismo
   no elimina la serialidad: la mueve** — los implementers corren simultáneos, cosecha y revisión
   siguen seriales.
6. **Recuperabilidad:** si el conductor muere a mitad de cosecha quedan N worktrees con trabajo sin
   traer. El `plan.md` tiene que registrar los worktrees en vuelo o se pierde en silencio.
7. **Impacto sobre el contrato replicado de corridas en vuelo.** Hoy declara `subagent → fuente:
   ninguna` porque un subagente no está obligado a escribir a un archivo. Un implementer con **árbol
   exclusivo** sí deja superficie observable y atribuible. Puede que la fila igual no cambie, pero
   **hay que revisarlo en serio**: si cambia, se dispara la cadena completa de sincronización de sus
   siete copias y su baseline.

### Fase 7 — Invariante dinámica y degradación same-family

**Objetivo:** decidir con datos si se habilita la rama inversa:

- implementador de otra familia + reviewer fresco; o
- implementador same-family + reviewer de otra familia.

Esta fase queda última porque el autor del work order no tiene hoy un predicado independiente para
juzgar su propia ambigüedad (`propuesta.md:203-210`).

Habilitar la segunda rama contradice la descripción y la regla 8 actuales de `cross-implement`; no
puede entrar como routing interno. Requiere una decisión explícita de versionado: nuevo modo o cambio
doctrinal, con migración coordinada de config, manifests, documentación y guardas.

**Gate de salida**

- la cohorte demuestra qué domina: ambigüedad contractual o defecto de implementación;
- la rama inversa mejora coste/latencia sin aumentar defectos escapados ni rework;
- `same-family` siempre se declara y su aprobación nunca se agrega como evidencia independiente;
- si la evidencia no alcanza, se conserva indefinidamente la regla 8 actual.

**Rollback:** mantener el reviewer opcional y la regla 8 vigente.

## 4.bis Procedencia — la propuesta de costo del modo `subagent`, absorbida

El 2026-08-11 se escribió `implement-subagent-costo-y-diversidad/propuesta.md`, posterior a este
roadmap y sin conocerlo: mide el modo `subagent` de `sdd-flow` tal como existe y propone cuatro
piezas. **Su contenido está absorbido en las fases de arriba y este roadmap es su sede**; aquella
queda como origen y no como plan paralelo.

| Pieza de la propuesta | Dónde vive ahora |
|---|---|
| **A — dossier de task** | **Fase 0.5**, íntegra: entregables, gate, riesgo y medición |
| **Corrección del encuadre de «degradación»** | **Fase 2**, junto al reparto de ejes de revisión |
| **C — revisión por eje** (`SPEC` al conductor, `QUALITY` a la otra familia) | **Fase 2** la instala · **Fase 4** la mide |
| **B — worktrees paralelos** | **Fase 6**, con su condición de activación y su diseño esbozado |
| **D1–D7** (decisiones abiertas) | **§4.ter**, fusionadas con las de la propuesta doctrinal |
| **R1–R7** (riesgos) | cada uno en la fase que lo carga |

**Lo que aportó y no estaba en el reparto original:** el costo del modo `subagent` **medido** en vez
de supuesto, y con él la razón por la que la Fase 0.5 va antes que todo lo demás.

## 4.ter Las decisiones abiertas, y dónde se cierra cada una

El cruce de este roadmap con las dos propuestas deja cinco decisiones acopladas. **Cuatro se cierran
dentro de una fase ya declarada**; solo una es doctrina que ninguna fase resuelve sola.

| # | Pregunta | Dónde se cierra | Estado |
|---|---|---|---|
| 1 | ¿Dónde vive el revisor cross-family de diffs? | **resuelta por la arquitectura de este roadmap** | ver abajo |
| 2 | ¿Qué fuerza tienen sus findings? | **ninguna fase la resuelve sola** | **abierta — decisión del usuario** |
| 3 | ¿Qué eje de config expresa la combinación? | **Fase 1**, en una sola pasada | resuelta por secuencia |
| 4 | ¿Se adopta la invariante dinámica? | **Fase 7**, con los datos de la Fase 4 | resuelta por secuencia |
| 5 | ¿Se decide por argumento o se mide? | **Fase 4** | **se mide** |

**Decisión 1 — no es una skill, es un rol.** La propuesta doctrinal lo pone dentro de
`cross-implement`; la de costo, inline en `sdd-flow`. Las dos tienen razón en que hoy ninguna skill
cubre ese casillero, y las dos se equivocan al buscarle una skill dueña: este roadmap ya lo modela
como **una de las cinco familias de rol** (`diff-reviewer`), que **consume la skill que lo necesite**
—la Fase 2 se lo da a `sdd-flow` y a `bitbucket-code-review`, la Fase 4 a `cross-implement`—. No hay
dos sedes porque la sede es el contrato del rol. **Lo que sí hay que agregar a la regla de fronteras
del `CLAUDE.md`** es una frase: revisar un diff con la otra familia es un **rol**, no una skill nueva.

**Decisión 2 — la única genuinamente abierta.** La propuesta doctrinal la nombra como *«¿qué obliga a
hacer con los findings del revisor ajeno?»* y advierte que sin respuesta esa mitad de la invariante es
decorativa, porque la regla 4 de `cross-implement` deja la decisión en el conductor. La de costo la
nombra como *«¿quién aplica el fix de un `QUALITY: fail` agrupado?»* y la marca como **el punto más
filoso: sin cerrarlo, la pieza C no se puede escribir**. Es la misma pregunta.

> **Propuesta de resolución, para aprobar o corregir.** Aplicar el patrón que la Fase 0 ya construyó
> y probó: **todo finding se adjudica** —incorporado o descartado— **con su razón escrita, y el gate
> no cierra con findings sin adjudicar**. No obliga al conductor a aceptar ningún finding; lo obliga
> a **pronunciarse** sobre cada uno. Es verificable con un predicado, que es lo que distingue esta
> regla de «tenerlos en cuenta», y reusa el mecanismo de ledger adjudicable que la Fase 4 ya declara.

### Las decisiones de la propuesta de costo, en la fase que las cierra

| # | Pregunta | Fase | Estado |
|---|---|---|---|
| D1 | ¿De dónde sale cada pieza del dossier, sin ambigüedad? | **0.5** | **cerrada por medición** — ver abajo |
| D2 | ¿El dossier es configurable o siempre-on? | **0.5** | **siempre-on**: evita tocar las vistas de config y sus conteos en prosa |
| D3 | ¿Se reabre escribir el reporte del subagente a disco? | **0.5** | **no se reabre**: acotar el diff por el campo `Archivos` resuelve el síntoma sin tocar el contrato de despacho de cuatro skills |
| D4 | ¿`QUALITY` agrupado cada N tasks o uno al cierre? | **2** | abierta · recomendación: **al cierre**, que es casi la revisión final extendida |
| D5 | ¿Quién aplica el fix de un `QUALITY: fail` agrupado? | **2** | **es la decisión 2 de arriba con otro nombre** |
| D6 | ¿Skill nueva o inline? | **2** | **cerrada por la decisión 1**: es un rol, no una skill |
| D7 | ¿Clave de config nueva o reuso? | **1** | **es la decisión 3 de arriba** |

**D1 quedó cerrada con evidencia, no con criterio.** El arnés `scripts/medir-dossier-de-task.py` se
puso rojo tres veces sobre los flujos reales, y cada rojo fijó una regla:

- **el id necesita un delimitador de declaración** (`:`, `**` o ` —`), o una línea de prosa en
  negrita entra como declaración;
- **los duplicados no se colapsan en silencio**: 13 de 16 AC estaban declarados dos veces —el vigente
  y su copia en el apéndice de fidelidad— y un diccionario por id se quedaba con el del apéndice; para
  un AC eso significó **355 bytes en vez de 4.409**, o sea entregar el criterio heredado en lugar del
  vigente;
- **control positivo antes de armar nada**: el patrón cubría 2 de las 5 formas reales de declarar un
  AC y devolvía **0 en 12 de 21 flujos**; sin control, esos 12 producían dossiers minúsculos que se
  leen como un éxito espectacular.

La conclusión que ninguna de las dos propuestas tenía: **la fragilidad no está en el formato del
`- **AC-n:**`; está en que el id no es único ni inequívoco dentro del archivo.**

**Decisiones 3, 4 y 5 no necesitan respuesta hoy** — necesitan que las fases se ejecuten en orden. La
3 se cierra en la Fase 1 porque es la fase que construye el schema de perfiles: partir `implement_mode`
y extender `final_diff_review.mode` son el mismo cambio de superficie y van juntos o el segundo
invalida la verificación del primero. La 4 y la 5 ya estaban contestadas por la secuencia: la Fase 4
mide qué domina —ambigüedad contractual o defecto de implementación— con los umbrales que la Fase 0
pre-registró, y la Fase 7 decide con esos datos o conserva la regla 8 indefinidamente.

## 5. Cambios atómicos y cambios separados

Conviene agrupar en una sola entrega:

- schema de perfiles + todas sus vistas replicadas;
- catálogo + generador + adaptadores + instalador;
- actualización del contrato compartido de corridas y sincronización de sus siete copias.

Conviene separar:

- readers y writers;
- Codex/Claude adapter wiring y cambio doctrinal;
- revisión estable y overlap;
- soporte básico de las siete skills y la invariante dinámica.

El cambio de schema debe pasar `scripts/verificar-vistas-config.py`. El contrato de corridas debe
actualizarse en su sede canónica, sincronizarse y conservar la biyección de los trece puntos. Los
bloques POSIX/PowerShell nuevos o modificados conservan su verificación de paridad.

## 6. Criterio de finalización del programa

El programa puede considerarse cerrado al terminar la Fase 4 si:

- las siete skills resuelven roles y perfiles en Codex y Claude cuando están disponibles;
- funcionan con una sola familia o sin agentes instalados;
- la instalación y actualización son transaccionales y diagnosticables;
- readers y writers están acotados por mecanismo;
- el reviewer de diff trabaja sobre bytes inmutables y aporta evidencia medible;
- ningún agente reemplaza `verify`, los STOP ni la decisión del conductor.

Las Fases 5–7 son optimizaciones y cambios doctrinales. No deben convertirse en condición para decir
que las siete skills soportan subagentes y perfiles configurables.

## 7. Lo que sigue, en orden

1. **Fase 0.5 — el paquete de contexto.** La más barata, la de mayor retorno, y no prejuzga ninguna
   decisión doctrinal. Sus tres decisiones (D1, D2, D3) ya están cerradas, así que entra a flujo SDD
   sin nada pendiente.
2. **Cerrar la decisión 2** (§4.ter). Es la única que ninguna fase resuelve sola, y bloquea el §2.a
   de la Fase 2.
3. **Fase 1 — catálogo, adaptadores, perfiles e instalación**, que cierra de paso la decisión 3.
   Antes de apoyarse en el sandbox por agente de Codex hay que **re-medirlo**: la medición vigente es
   de `codex-cli 0.146.1` y hoy corre `0.147.0`, y la propia propuesta condiciona su validez a la
   versión —«lo invariante es nuestra exigencia, acotar por mecanismo y no por promesa, no la
   mecánica que hoy la satisface»—.
4. **Fase 2 — roles read-only**, con su §2.a: el reparto de ejes de revisión y la corrección del
   encuadre de «degradación», que vale sola y puede adelantarse.
5. **Fase 3 — writers.**
6. **Fase 4 — el piloto que mide**, y con él las decisiones 4 y 5.
7. Las **Fases 5–7** solo si sus métricas lo justifican.

**Cada fase entra por su propio flujo SDD.** La Fase 0 mostró el costo de no hacerlo: 43 tasks en un
flujo único hubo que partirlas en dos, y la curva de findings de su revisión subía en vez de bajar.

> **Nota de mantenimiento de este archivo.** Existe replicado en dos sedes byte-idénticas: ésta, que
> es la canónica y a la que apuntan los punteros normativos del documento de contrato, y
> `.plans/doctrina-implementador/roadmap.md`, que es local. **Editar una sola es divergencia
> silenciosa.** El puntero `#1-que-significa-soportado-por-las-siete-skills` está congelado por el
> contrato: su heading y los literales de familia que viven adentro no se tocan sin correr
> `python3 scripts/verificar-matriz-despachos.py --roles docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md`.
