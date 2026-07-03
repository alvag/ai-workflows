---
name: sdd-co-explore
description: >-
  Exploración paralela cross-model para flujos SDD: un modelo de otra familia
  que el autor (Codex cuando conduce Claude; Claude cuando conduce Codex)
  explora el código en background y devuelve un informe estructurado de
  hallazgos, ANTES de escribir la spec (modo explore) o como contra-enfoque
  antes del plan/reparto (modo counter-plan). La invocan sdd-flow y
  sdd-orchestrator cuando cross_review.co_explore está activo; también se puede
  invocar directo: "/sdd-co-explore <ticket|descripción>" o "que Codex explore
  esto en paralelo". NO revisa artefactos escritos (eso es sdd-cross-review):
  produce hallazgos e hipótesis propios para que compitan con los del conductor.
  No invocarla espontáneamente: solo ante un pedido explícito del usuario o
  invocada por sdd-flow/sdd-orchestrator.
---

# sdd-co-explore — dos mapas independientes antes de la spec y el plan

Helper que, antes de que el conductor escriba `spec.md` o `plan.md`, despacha a un modelo de
otra familia (Codex cuando conduce Claude; Claude cuando conduce Codex) a explorar el mismo
código en background, read-only, y a devolver un informe estructurado propio: mapa de
archivos, hipótesis, puntos de reúso, riesgos, incógnitas y enfoque sugerido. Mientras el
revisor explora, el conductor hace su propia exploración de siempre — no hay espera
secuencial, ambos avanzan en paralelo.

El valor no es que el revisor "ayude" al conductor: es que produce un mapa **independiente**,
sin ver nada de lo que el conductor ya pensó, para que las diferencias entre los dos mapas
salgan a la luz antes de que las decisiones queden tomadas. Dos exploraciones convergen
fácil (son hechos + hipótesis); dos specs no (son decisiones ya tomadas) — por eso el punto
de encuentro es temprano, en los hallazgos, no al final.

El informe alimenta la **síntesis del conductor** (que compara los dos mapas, hace competir
los enfoques en méritos y decide con rationale auditable) y, más adelante, la **crítica
informada** de `sdd-cross-review`, que recibe ese informe como contexto persistente en el
gate. Esta skill **no revisa artefactos escritos** — eso lo hace `sdd-cross-review`:
`sdd-co-explore` produce hallazgos e hipótesis propios que compiten con los del conductor, no
una crítica de lo que el conductor ya escribió.

```
paquete de contexto ──► [sdd-co-explore: revisor explora en background, read-only]
                              │                        (el conductor explora en paralelo
                              ▼                         por su cuenta — no espera)
                    findings-<familia>.md ──► síntesis del conductor ──► spec/plan
                    (+ session.json opcional)   (convergencias/divergencias,
                                                 competencia de enfoques)
```

## Reglas no negociables

1. **Read-only.** El explorador nunca escribe en el repo: se invoca en modo read-only, sin
   permisos de escritura. Su salida se captura por redirección del conductor —stdout hacia
   `co-explore/scratch/`—, nunca porque el explorador tenga permiso para tocar archivos (ver
   `reference.md` → "Archivos de trabajo (scratch)").
2. **Independencia (anti-anclaje).** El explorador arranca únicamente con el paquete de
   contexto: nunca recibe hallazgos, hipótesis ni borradores del conductor. Es simétrico — la
   skill llamadora tampoco lee `findings-<familia>.md` del revisor hasta haber cerrado su
   propia exploración y escrito su propio informe. El valor está en dos mapas sin contaminar,
   no en uno que copia al otro.
3. **Nunca se bloquea por dudas.** El explorador corre no-interactivo: no puede preguntar a
   mitad de camino ni esperar una respuesta. Toda duda se registra y se sigue explorando — una
   pregunta abierta que no pudo resolver va a `## Incógnitas`; una decisión que tomó para
   poder seguir avanzando va a `## Supuestos`, con el porqué.
4. **Informe estructurado o nada.** La salida tiene que respetar el "Formato del informe"
   (`reference.md`). Si la respuesta del revisor no parsea contra ese formato, se degrada: se
   conserva como texto libre si aporta contexto, o se descarta si es ruido — y en cualquier
   caso se registra la degradación.
5. **Loop acotado, deadline duro.** Una sola pasada por modo — sin rondas, a diferencia de
   `sdd-cross-review`. Al vencer `deadline` se mata el proceso del explorador y se devuelve
   `UNAVAILABLE` con lo que haya alcanzado a producir. Nunca se espera de forma indefinida.
6. **Opcional y degradable.** Es una capacidad, no un requisito. Sin revisor de otra familia
   disponible, con un fallo en runtime, o con `mode: off`, el resultado es `UNAVAILABLE` en una
   línea y la llamadora sigue con la exploración del conductor solamente.
7. **Revisor de OTRA familia, por capacidad.** Misma regla 7 de `sdd-cross-review`: familia =
   modelo de respaldo, no el CLI/harness; se identifica sondeando el entorno, con higiene de
   entorno si el revisor es Claude con la sesión redirigida. El algoritmo canónico vive en
   `sdd-cross-review/reference.md` → "Descubrir el revisor"; acá solo el puntero + un fallback
   mínimo (ver `reference.md` → "Descubrir el revisor (puntero + fallback)").

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos que aparecen *en el
momento*. Ley fundamental:

> **DOS MAPAS INDEPENDIENTES O NINGUNO.** El valor está en la divergencia, no en una
> coincidencia forzada. Contaminar el paquete de contexto o leer el informe antes de tiempo
> mata la señal (regla 2).

Si reconoces alguno de estos pensamientos, detente y vuelve a la regla que estás por saltear.

| Racionalización | Realidad |
|---|---|
| "Le paso al explorador mi hipótesis para que no pierda tiempo" | Rompe la independencia (regla 2): el valor está en dos mapas sin contaminar. Solo viaja el paquete de contexto. |
| "Miro su informe mientras exploro, total ya terminó" | El conductor no lee `findings-*` hasta cerrar y escribir su propio informe. |
| "El explorador no contestó, espero un poco más" | Deadline duro (regla 5): matar el proceso, `UNAVAILABLE`, seguir con lo propio. |
| "Su enfoque se ve bien, lo adopto y listo" | Los enfoques compiten en la síntesis: evaluar en méritos y registrar el porqué en `synthesis.md`; enfoques viables pero distintos = divergencia al checkpoint. |
| "Su duda la respondo yo mentalmente y sigo" | Las Incógnitas que cambiarían el diseño van a `clarify`; las respuestas quedan en `## Clarifications` de la spec. |

## Contrato de invocación (lo que pasa la skill llamadora)

Al invocarla, `sdd-flow`/`sdd-orchestrator` (o el usuario en modo directo) proveen:

- **`mode`** — `explore` (pre-spec) | `counter-plan` (pre-plan/pre-reparto).
- **`context_package`** — digest del ticket + prompt del usuario + AC preliminares si existen +
  **evidencia observada de reproducción** si la hubo (consola/red/pasos, capturada por la
  llamadora ANTES de despachar: el explorador es headless y no puede abrir URLs; ver el `<task>`
  del prompt). La evidencia viaja como hechos observados, nunca como hipótesis de la llamadora.
  En `counter-plan`: ruta de la `spec.md` (o `master-spec.md`) aprobada + ruta del propio
  `findings-<familia>.md` de la fase `explore`, con resume oportunista del thread si
  `session.json` lo permite, o sesión fresca con esos archivos si no.
- **`working_dir`** — uno, o una lista de repos cuando llama el orquestador (exploración
  cross-repo).
- **`complexity`** — `trivial | normal | complex`; modula profundidad/esfuerzo.
- **`execution`** — `auto | sync | background`. Para `explore` el valor útil es `background`:
  el conductor explora mientras tanto. En `counter-plan` o si el conductor no puede lanzar
  background, se espera con tope (`sync`).
- **`deadline`** — opcional; defaults 600s (`explore`) / 300s (`counter-plan`), ver
  `reference.md` → "Latencia y deadlines".

### Pasos de ejecución

1. **Resolver el revisor** (regla 7). Sin revisor de otra familia disponible → `UNAVAILABLE`.
2. **Armar el prompt** desde `reference.md` → "Prompt de exploración" (una variante por modo),
   con el paquete de contexto inline.
3. **Lanzar en background, read-only**, con el stdout redirigido a
   `co-explore/scratch/explorer.out`; guardar el PID y, si el runtime lo expone, la referencia
   de sesión en `co-explore/session.json`.
4. En `explore`, **devolver el control de inmediato** ("explorando en background") — la
   llamadora hace su propia exploración y vuelve a consultar en el punto de encuentro. En
   `counter-plan` o con `execution: sync`, esperar con tope.
5. **Punto de encuentro:** si el explorador terminó, normalizar la salida al "Formato del
   informe" y escribirla en `co-explore/findings-<familia>.md` (`explore`) o
   `co-explore/counter-plan-<familia>.md` (`counter-plan`) — ver `reference.md` → "Archivos de
   trabajo (scratch)". Si venció el `deadline`, matar el proceso y devolver `UNAVAILABLE`.

**Modo directo** (el usuario invoca `/sdd-co-explore <ticket|descripción>`): inferir
`mode: explore`, armar el `context_package` desde el prompt (+ tracker si hay clave y MCP
disponible), correr los pasos de arriba y **presentar** el informe al usuario.

## Salida

**Salida a la llamadora:** estado `READY` | `UNAVAILABLE` · ruta del informe
(`findings-<familia>.md` en `explore`, `counter-plan-<familia>.md` en `counter-plan`; si hay) ·
resumen de 3-5 líneas (hallazgos top + enfoque sugerido) · ruta de `session.json` si existe.

## La síntesis (guía para la skill llamadora)

La síntesis la ejecuta **el conductor**, no esta skill — pero como `sdd-flow` y
`sdd-orchestrator` la necesitan por igual, la guía vive acá una sola vez para que ninguna de
las dos la duplique:

1. Escribir el propio `findings-<familia>.md` del conductor **antes** de leer el del revisor
   (regla 2 — independencia hasta el final).
2. Comparar los dos informes sección por sección.
3. Producir `synthesis.md` (plantilla en `reference.md` → "Plantilla de `synthesis.md`") con:
   - una tabla de **convergencias / divergencias**;
   - el **duelo de enfoques**: evaluar los dos "Enfoque sugerido" en méritos (reúso, riesgo,
     simplicidad, encaje con el repo), elegir uno o hibridar, y registrar el **porqué** —
     auditable, no implícito;
   - las **Incógnitas fusionadas** de ambos mapas: las que cambiarían el diseño alimentan
     `clarify` (obligatorio en complejos).
4. Las **divergencias no resueltas** se presentan en un checkpoint informativo de la llamadora
   antes de escribir la spec/plan (no es un gate SDD, y solo ocurre si hay divergencias sin
   resolver; si los mapas convergen, se sigue directo sin stop extra).

## Configuración

Clave bajo `cross_review` en `.specify/config.yml` (sdd-flow) o en el `manifest.yml` de la
orquestación (sdd-orchestrator):

```yaml
cross_review:
  co_explore:
    mode: auto        # auto (por complejidad: complejo on, normal opt-in, trivial nunca) | "on" | "off"
    deadline: 600     # segundos (explore; counter-plan usa 300 salvo override)
```

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default por complejidad**. Default por complejidad: `complex` on, `normal` opt-in
(off salvo pedido), `trivial` nunca. `deadline` por defecto: 600s en `explore` (una
exploración tarda más que una crítica), 300s en `counter-plan`, ver `reference.md` → "Latencia
y deadlines".

`co_explore` es **ortogonal** a `cross_review.mode`: esta clave gobierna la exploración
paralela y el contra-enfoque; `cross_review.mode` gobierna las críticas en los gates. Quien
lee ambas y orquesta es la skill llamadora (`sdd-flow`/`sdd-orchestrator`), nunca esta skill.

## Degradación

Nunca bloquea el flujo SDD. Cuatro vías de falla, todas con el mismo final:

1. Skill no instalada → la llamadora la omite y sigue con la exploración del
   conductor.
2. Sin revisor de otra familia disponible → `UNAVAILABLE`; la llamadora sigue con la
   exploración del conductor.
3. Deadline vencido → se mata el proceso y se registra; la llamadora sigue con la exploración
   del conductor.
4. Informe no parseable → se degrada (texto libre como contexto, o descarte si es ruido) y se
   registra; la llamadora sigue con la exploración del conductor.

## Router de intención

| El usuario dice (ej.) | Acción |
|---|---|
| "/sdd-co-explore `<ticket|descripción>`" | modo directo: `mode: explore`, corre y presenta el informe |
| "que Codex explore esto en paralelo" | modo directo, mismo flujo que arriba |
| "con co-exploración" | override `on` para la corrida — lo registra la llamadora |
| "sin co-exploración" | override `off` para la corrida — lo registra la llamadora |
| (invocada por `sdd-flow`/`sdd-orchestrator` post-`gather-context` o pre-`plan`/reparto) | modo embebido: explorar y devolver informe + resumen, sin STOP propio |

## Referencias internas

- `reference.md` — "Prompt de exploración" (por modo), "Formato del informe", "Plantilla de
  `synthesis.md`", "Descubrir el revisor (puntero + fallback)", "Latencia y deadlines",
  "Archivos de trabajo (scratch)".
- `README.md` — qué es, cuándo usarla, requisitos e instalación.
