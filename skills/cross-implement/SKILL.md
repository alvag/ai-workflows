---
name: cross-implement
description: >-
  Implementación cruzada cross-model: el conductor (autor del plan) delega un
  work order CONGELADO a la otra familia (Codex cuando conduce Claude; Claude
  cuando conduce Codex), que escribe código con escritura acotada al working
  dir; el conductor revisa el diff completo como un PR ajeno, corre la prueba él
  mismo, itera fixes en la misma sesión del implementador (loop acotado) y es
  quien commitea tras el gate humano. Sirve para cualquier flujo donde uno
  planifica y el otro implementa; también la
  invoca sdd-flow cuando implement_mode es "cross". Invocación directa:
  "/cross-implement <ruta-del-work-order>", "que Codex implemente este plan",
  "implementa esto con Codex y revisas tú". NO es para diseñar (el work order
  debe existir y estar aprobado), NO para cambios triviales (~<20 líneas), NO
  para revisar código existente (eso es code review) ni artefactos de diseño
  (eso es cross-review). No invocarla espontáneamente: solo ante un pedido
  explícito del usuario o invocada por sdd-flow.
---

# cross-implement — uno planifica, el otro implementa, el primero revisa

Helper que **cruza los roles entre familias de modelos**: el conductor (el agente que escribió
o posee el work order) no implementa — despacha la implementación completa a un modelo de la
otra familia, con escritura acotada, y se queda con los dos roles que más valor tienen cruzados:
**revisor del diff** (un revisor que no escribió el código, de otra familia, es genuinamente
externo) y **verificador de la prueba** (la corre él mismo; el reporte del implementador es
advisory). El humano entra en dos puntos: el kickoff y el sign-off del diff.

El valor es el mismo que funda a `co-explore` y `cross-review`: romper la correlación de
errores. Hoy, cuando un modelo implementa su propio plan, autor y revisor del código son el
mismo modelo con los mismos puntos ciegos. Acá implementador y revisor son de familias distintas
**por construcción**.

```
work order congelado ──► [implementador de otra familia: escribe, corre la prueba, reporta]
   (spec/plan/tasks              │ escritura acotada al working dir, nunca commitea
    aprobados, o contrato        ▼
    destilado)          diff + reporte ──► conductor: lee el diff completo como PR ajeno,
                                            corre la prueba él mismo, itera fixes (loop
                                            acotado, misma sesión) ──► gate humano ──► commit
                                                                                    (del conductor)
```

## Reglas no negociables

1. **Work order congelado o nada (spec gate).** No se delega sin un contrato completo y aprobado:
   spec/plan/tasks SDD, un plan que sobrevivió una revisión, o un contrato destilado con objetivo,
   pasos, límites y prueba — **y su tabla de verificación congelada** (`contrato-verificacion.md` →
   "El gate previo al dispatch"): un work order sin tabla, o con una tabla sin congelar, no se delega. El implementador arranca con CERO contexto de la sesión: todo lo que
   necesita viaja en el prompt. Si escribir el work order obliga a tomar decisiones de diseño,
   eso es diseño y se queda con el conductor — delegar diseño es cómo falla este patrón.
2. **Clean-tree gate.** Antes de lanzar, `git status` limpio de código sin commitear (los locales
   `.plans/`/`.specify/` no cuentan). Innegociable: el implementador escribe con libertad dentro
   del working dir, y un árbol sucio impide aislar o revertir su diff.
3. **Escritura acotada, nunca commit.** El implementador escribe SOLO dentro del `working_dir`
   (sandbox `workspace-write` en Codex; permisos path-scoped en Claude — ver `reference.md` →
   "Vías de invocación"; **nunca** modos de bypass total). No commitea, no pushea, no toca
   `.plans/`/`.specify/` ni los archivos de trabajo de esta skill.
4. **El reporte es advisory.** El conductor valida siempre por su cuenta: lee el **diff completo**
   como un PR de un contribuidor externo, contrasta los archivos declarados contra `git status`,
   y corre `proof_cmd` **él mismo** — la salida pegada por el implementador no cuenta como prueba.
5. **Fix loop acotado, y solo para lo que se arregla implementando.** Cada falla se clasifica
   primero (`ownership.md` → "Las cuatro clases"); **solo `IMPLEMENTATION_DEFECT` reanuda la sesión**
   del implementador (con el override de sandbox explícito — el modo original no es garantía al
   reanudar) y consume ronda. Las otras tres tienen presupuesto propio y no abren fix round. Máximo
   `max_fix_rounds` (default 2); al agotarse, **takeover**: el conductor termina y lo registra, sin
   poder ablandar las filas que él escribió. Nunca ping-pong indefinido.
6. **El commit es del conductor, tras gate humano.** Presentar diff + prueba + rondas y esperar
   confirmación. El implementador jamás commitea; el conductor tampoco auto-commitea.
7. **Opcional y degradable.** Sin implementador de la otra familia disponible, o ante un fallo en
   runtime o deadline vencido → `UNAVAILABLE` en una línea y el conductor implementa inline (su
   rol de siempre). Nunca bloquea al flujo llamador.
8. **Implementador de OTRA familia, por capacidad.** Misma regla 7 de `cross-review`: dos
   familias (Claude y GPT/Codex), el autor es la del agente que conduce, el implementador es
   siempre el de la otra. Algoritmo canónico en `cross-review/reference.md` → "Descubrir el
   revisor"; acá la tabla invertida (con escritura) vive en `reference.md` → "Descubrir el
   implementador".

## Red flags — detente y reconsidera

Ley fundamental:

> **EL DIFF ES LA VERDAD, NO EL REPORTE.** Nada se acepta, se marca ni se commitea sin que el
> conductor haya leído el diff completo y corrido la prueba él mismo (regla 4).

| Racionalización | Realidad |
|---|---|
| "El reporte dice que la prueba pasó, avanzo" | La salida pegada no es evidencia. Correr `proof_cmd` fresco, leer salida + exit code (regla 4). |
| "Es un cambio chico, igual lo delego" | ~<20 líneas: el overhead de delegar supera al cambio. Implementar inline. |
| "El work order tiene un hueco, que el implementador decida" | Un hueco de diseño se resuelve ANTES de delegar (con el usuario o el flujo llamador), no en el prompt (regla 1). |
| "Le doy acceso total así no falla por permisos" | Bypass de sandbox/permisos = regla 3 rota. Si el work order necesita escribir fuera del working dir, está mal recortado. |
| "Una ronda más de fix y seguro sale" | `max_fix_rounds` es el tope. Al agotarse: takeover del conductor, registrado (regla 5). |
| "Falló la verificación, lo mando a corregir" | Antes hay que clasificar de quién es la falla (regla 5). Mandarle un `VERIFICATION_DEFECT` o un `ENVIRONMENT_FAILURE` le pide arreglar algo que no está en su código, y lo más probable es que fuerce el síntoma hasta que pase. |
| "La fila no se deja cumplir, la ajusto y sigo" | Cambiar `Requisito` o `Esperado` no es reparar una prueba: es `DESIGN_GAP` y vuelve al diseño (`contrato-verificacion.md` → "Qué es invariante entre versiones"). En takeover también. |
| "El diff trae un cambio extra razonable, lo dejo pasar" | Todo hunk fuera del work order se reporta como drift: se pide su reversión en el fix round, o se declara explícitamente (en SDD: `## Extras`). Nada entra sin rastro. |
| "El árbol está casi limpio, lanzo igual" | Clean-tree gate (regla 2): código sin commitear = diff imposible de aislar. Commitear/stashear antes. |

## Contrato de invocación

Quien la invoca (el usuario en modo directo, o `sdd-flow` en modo embebido) provee:

- **`work_order`** — ruta(s) al contrato congelado: `.plans/<id>/` (spec+plan+tasks SDD), un
  `PLAN.md`, o equivalente. En modo directo sin archivo, el conductor **destila** el contrato de
  la conversación y lo escribe a `cross-implement/work-order.md` ANTES de lanzar (queda auditable
  y respeta la regla 1).
- **`working_dir`** — raíz del repo donde se implementa (límite de escritura del implementador).
- **`proof_cmd`** — comprobación **agregada y opcional** que el conductor corre para ver el
  conjunto de un vistazo (la suite completa, el build). No sustituye ninguna fila del contrato ni
  alcanza para dar un requisito por cumplido. El gate acepta contrato **sin** `proof_cmd`; nunca
  `proof_cmd` sin contrato (`contrato-verificacion.md` → "`proof_cmd` frente al contrato").
- **`max_fix_rounds`** — default 2.
- **`execution`** — `auto | sync | background`. `auto`: sync con timeout largo si el conductor
  puede fijarlo (Claude Code: Bash hasta 600000ms) y el work order es chico; background con
  deadline y banner para work orders grandes o conductores de exec corto (Codex ~120s). Ver
  `reference.md` → "Latencia, deadlines y banner".
- **`deadline`** — segundos; tope duro del wait en background (default 1800). En sync no aplica
  (lo acota el timeout de exec del conductor).

> **Fuente de estos parámetros.** En modo **directo** son defaults de la skill / override
> conversacional. En modo **embebido** por `sdd-flow` (`implement_mode: cross`), `execution`,
> `max_fix_rounds` y `deadline` se resuelven del bloque **`cross_implement`** del
> `.specify/config.yml` (con estos mismos defaults como fallback); el resto (`work_order`,
> `working_dir`, `proof_cmd`) los arma sdd-flow por corrida. La **familia** del implementador la
> fija el conductor (no es configurable).

### Pasos de ejecución

1. **Resolver el implementador** (regla 8) + prechequeos (versión del CLI, no pinear modelo, eco
   del modelo activo — ver `reference.md` → "Descubrir el implementador"). Sin implementador →
   `UNAVAILABLE`.
2. **Gates previos**: work order existe y se lee como contrato (regla 1); **contrato de
   verificación congelado** — versión vigente, cobertura bidireccional, campos obligatorios y
   baseline resuelto en toda fila, ninguna en `BLOCKED` (`contrato-verificacion.md` → "El gate
   previo al dispatch"); clean-tree (regla 2). En modo directo el conductor deriva la tabla y
   ejecuta el baseline, el usuario la aprueba en el kickoff y recién ahí se congela
   (`contrato-verificacion.md` → "Contrato en work orders sin flujo SDD"). Cualquiera falla → no se
   lanza.
3. **Armar el prompt-contrato** (`reference.md` → "Prompt del implementador": GOAL / SPEC / KEY
   PATHS / CONSTRAINTS / NON-GOALS / PROOF / OUTPUT), escrito a archivo con la tool Write, y
   **lanzar** por la vía de la familia (`reference.md` → "Vías de invocación"), capturando la
   referencia de sesión para el fix loop.
4. **Revisión del conductor** (regla 4): diff completo como PR ajeno; archivos declarados vs
   `git status`; drift fuera del work order; `proof_cmd` fresco corrido por el conductor. Si el
   work order es SDD, atribuir hunks a tasks y marcar `- [x]` las cubiertas. Checklist en
   `reference.md` → "Revisión del conductor".
5. **Fix loop** (regla 5): con problemas concretos, reanudar la misma sesión con el delta (qué
   está mal, en qué archivo, qué prueba debe pasar). Re-revisar (paso 4) tras cada ronda. Al
   agotar `max_fix_rounds` → **takeover** del conductor, registrado en el log.
6. **Cierre**: registrar todo en el log (`reference.md` → "Log de implementación") y devolver el
   resultado a la llamadora — o, en modo directo, presentar diff + prueba + rondas y ofrecer el
   commit (que ejecuta el conductor tras confirmación, con la disciplina de commit del flujo que
   corresponda).

**Modo embebido (sdd-flow, `implement_mode: cross`):** esta skill cubre solo el paso 2 del "Paso
común" de `implement` (aplicar los cambios). Todo lo demás sigue siendo del conductor en sdd-flow:
tests+build completos, `verify` de AC con gate function, revisión manual, staging selectivo,
commit y push con sus STOPs. El contrato de verificación llega ya escrito en el `## Verification`
del `plan.md`. El tope de `sdd-flow` ("3 fixes de la misma falla = problema de diseño → volver a
plan/specify") manda por encima de `max_fix_rounds`; las clases que no consumen ronda tampoco
cuentan para él (`ownership.md` → "Precedencia entre los tres topes de corte").

## Salida

A la llamadora (o presentada al usuario en modo directo):

- **Estado:** `IMPLEMENTED` (diff revisado + prueba en verde) | `PARTIAL` (takeover: qué quedó
  hecho por el implementador y qué terminó el conductor) | `UNAVAILABLE`. El `UNAVAILABLE` va con su
  **causa** del enum compartido —`confirmed_wall` · `launch_flake` · `runtime_failure` ·
  `deadline_exceeded`—: son causas, no estados nuevos (`cross-review/reference.md` → "Latencia y
  timeout (Claude revisor)").
- **Resumen del diff** (archivos, qué cambió) + salida de `proof_cmd` corrida por el conductor.
- **Rondas usadas** y desviaciones del work order reportadas por el implementador.
- **Ruta del log** (`implement-log.md`).

Al resolver el estado se escribe además el **manifest de corrida**, en los tres casos: un
`UNAVAILABLE` por pared confirmada es el dato que dice que la capacidad no existe en este entorno, y
un `PARTIAL` es el que dice cuánto termina haciendo el conductor. Registrar solo los `IMPLEMENTED`
dejaría una serie que responde "siempre funciona" porque solo se anotó cuando funcionó. Esquema y
vocabulario en `cross-review/reference.md` → "Manifest de corrida". Su `degradation` admite además
`transport_fallback`, causa de la **corrida** y no del estado: se registra incluso con un
`IMPLEMENTED`.

## Configuración

Claves bajo `cross_implement` en el `.specify/config.yml` del repo. Solo aplican con
`implement_mode: cross`; en los otros modos se ignoran. Todas opcionales:

```yaml
cross_implement:
  execution: auto        # auto (por tamaño del work order) | sync | background — cómo espera al implementador
  max_fix_rounds: 2      # tope del fix loop antes del takeover del conductor (el tope de sdd-flow "3 fixes de la misma falla → volver a plan/specify" manda por encima)
  deadline: 1800         # segundos; tope duro del wait en background
  # sin `implementer:` — la familia la fija el conductor, no es configurable
```

A diferencia de `cross_review` y `co_explore`, estas claves **no** viajan en el `manifest.yml`
de una orquestación: ahí solo va `implement_mode`, que elige el modo pero no lo parametriza. En
modo embebido bajo `sdd-orchestrator`, cada `sdd-flow` delegado resuelve estos tres valores del
`.specify/config.yml` de **su propio repo**, no del manifest compartido.

Esta skill es **dueña** de estas tres claves: su enum y su descripción se definen acá. El
ejemplo copiable del archivo completo vive en `sdd-flow/config-ejemplo.md`, que es una **vista**
ensamblada de este bloque y sus hermanos; ante discrepancia manda este bloque.

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default de la skill**.

## Router de intención

> **¿Es este el peldaño que hace falta?** La escalera de rigor —respuesta local → `co-explore` →
> `cross-review` → `cross-implement` → `verify`— dice cuál es la opción **más barata que
> alcanza**, que casi nunca es la más completa: `co-explore/reference.md` → "Escalera de rigor".

| El usuario dice (ej.) | Acción |
|---|---|
| "/cross-implement `.plans/X/`", "/cross-implement `PLAN.md`" | modo directo con ese work order |
| "que Codex implemente este plan", "implementa esto con Codex y revisas tú" | modo directo; si no hay archivo, destilar el work order primero (contrato de invocación) |
| "que Claude implemente esto" (conduciendo Codex) | modo directo, vía inversa |
| (invocada por `sdd-flow` con `implement_mode: cross`) | modo embebido: pasos 1-6, devolver salida sin STOP propio (los STOPs son de sdd-flow) |
| "cambio de 3 líneas, delégalo igual" | advertir el overhead (red flag) y, si insiste, proceder — el pedido explícito manda |

## Degradación

Nunca bloquea. Cuatro vías de falla, mismo final — el conductor implementa inline:

1. Skill no instalada → la llamadora la omite.
2. **Fallo de arranque.** Dos casos, según el preflight de capacidad del CLI:
   - **Pared confirmada** — el binario no está, auth rechazada o versión incompatible: reintentar es
     chocar contra la misma pared → `UNAVAILABLE`. Es **terminal para la corrida**; si la llamadora
     despacha en tanda (p. ej. `sdd-orchestrator` sobre varios repos), la capacidad queda no
     disponible para toda la tanda (no se re-diagnostica por ítem).
   - **Flake transitorio** — el binario existe pero el lanzamiento falló por arranque frío, timeout
     de spawn o una race: 2-3 reintentos con backoff corto, no un loop abierto; solo si ninguno
     levanta → `UNAVAILABLE`.
3. **Fallo en runtime / tarea** (deadline vencido, error de ejecución tras arrancar bien) → matar el
   proceso, conservar el diff parcial **solo si** el conductor lo revisa y decide qué mantener (por
   default, revertirlo), registrar y `UNAVAILABLE`. A diferencia del punto 2, es **por-intento**: no
   marca la capacidad como ausente para el resto de la tanda. Lleva dos **causas** distintas:
   `deadline_exceeded` si venció el tope sin `STATUS: done` —arrancó bien y el corte lo puso el
   conductor, así que `runtime_failure` sugeriría una falla de infraestructura que no ocurrió— y
   `runtime_failure` si falló ejecutando.
4. Reporte no parseable → el diff sigue siendo la verdad: revisarlo igual (regla 4); solo se
   pierde la narrativa del implementador. Vale **porque acá el artefacto es el diff**; donde el
   artefacto *es* el informe no aplica (`reference.md` → "Cuándo un reporte ilegible no invalida la
   revisión").

**`transport_fallback` no es una quinta vía de falla: es una causa, y la implementación sí ocurre.**
Se registra cuando la intención se resolvió a la vía de panes y el transporte efectivo fue el CLI
—**por resultado**, sin importar si cayó en el preflight de capacidad o en el lanzamiento—, para que
esa corrida no quede indistinguible de una CLI intencional. `transport` guarda la vía que
efectivamente corrió y la causa raíz concreta va al log de la skill. **Excepción:** con el intento en
resultado incierto **no hay fallback** hasta resolver el recovery — con escritura acotada al working
dir, dos implementadores vivos sobre el mismo árbol es el peor caso. Las cinco reglas, en
`reference.md` → "Vías de invocación" y `cross-review/reference.md` → "Latencia y timeout (Claude
revisor)".

## Referencias internas

- `reference.md` — "Descubrir el implementador", "Vías de invocación" (Codex/Claude, POSIX +
  PowerShell, con matriz de verificación), "Prompt del implementador", "Revisión del conductor",
  "Fix loop", "Latencia, deadlines y banner", "Archivos de trabajo (scratch)", "Log de
  implementación", "Cuándo un reporte ilegible no invalida la revisión".
- `contrato-verificacion.md` — el esquema del contrato, las reglas de congelamiento, la adjudicación
  del baseline, el gate previo al dispatch y el flujo en work orders sin SDD. Se lee **al armar y
  aprobar el contrato**, antes de delegar.
- `ownership.md` — las cuatro clases de falla, sus presupuestos, el re-baseline en worktree aislado,
  el takeover y la precedencia de topes. Se lee **cuando una ronda falla**.
- `transporte-herdr.md` — el adaptador del transporte por panes: activación, permisos, entradas y
  salidas, independencia, deadline, continuidad entre rondas, validación y cleanup. Se lee **solo
  cuando la activación del flujo resolvió a esa vía**; con el transporte CLI vigente no se carga.
- `README.md` — qué es, cuándo usarla, requisitos e instalación.

## Atribución

El patrón "el otro modelo construye desde una spec congelada, el autor revisa el diff y exige
prueba" está inspirado en la skill `codex-build` de chaseai (a su vez adaptada del patrón
`codex-first` de Peter Steinberger). Acá se toma la **idea** con mecánica propia: bidireccional
por familias, sandbox acotado en vez de bypass (`--yolo`), y contratos de invocación verificados
end-to-end (ver `reference.md` → "Matriz de verificación").
