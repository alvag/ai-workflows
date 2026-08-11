# Roadmap — subagentes y perfiles de ejecución para las siete skills

**Estado:** propuesta de secuencia; no autoriza implementación

**Fecha:** 2026-08-06

**Entradas:** `propuesta.md`, `co-explore/synthesis-explore.md`, documentación oficial de
[subagentes Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents) y
[subagentes Claude Code](https://code.claude.com/docs/es/sub-agents)

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

### Fase 0 — Spec, contrato y baseline

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
