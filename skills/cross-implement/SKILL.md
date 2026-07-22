---
name: cross-implement
description: >-
  Implementación cruzada cross-model: el conductor delega un work order
  CONGELADO a un modelo de otra familia (Codex si conduce Claude; Claude si
  conduce Codex) con escritura acotada; luego revisa el diff completo como PR
  ajeno, corre las pruebas, itera fixes en la misma sesión (loop acotado) y
  commitea solo tras gate humano. También la invoca sdd-flow con implement_mode
  "cross". Triggers directos: "/cross-implement <ruta>", "que Codex implemente
  este plan", "implementa esto con Codex y revisas tú", "que Claude implemente
  esto". NO sirve para diseñar: el work order debe existir y estar aprobado;
  tampoco para cambios triviales (~<20 líneas), revisar código existente (code
  review) ni artefactos de diseño (cross-review). No invocarla espontáneamente:
  solo por pedido explícito o desde sdd-flow.
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
   pasos, límites y prueba. El implementador arranca con CERO contexto de la sesión: todo lo que
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
5. **Fix loop acotado, misma sesión.** Problemas encontrados → reanudar la MISMA sesión del
   implementador (conserva su contexto; siempre con el override de sandbox explícito — el modo de
   la sesión original no es garantía al reanudar) con la lista concreta de qué corregir. Máximo
   `max_fix_rounds` (default 2); al agotarse, **takeover**: el conductor termina los fixes
   directamente y lo registra. Nunca ping-pong indefinido.
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
9. **Contrato de verificación congelado o nada (normal/complex).** Sin verification contract
   resuelto no hay dispatch; antes de consumir rondas se hace triage manual, y el mismo contrato
   rige el takeover. Envolver la corrida con el manifest es telemetría, no gate. Detalle en
   `reference.md` → "Verification contract (normal/complex)", "Triage de ownership" e
   "Instrumentación con manifest".

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
| "El diff trae un cambio extra razonable, lo dejo pasar" | Todo hunk fuera del work order se reporta como drift: se pide su reversión en el fix round, o se declara explícitamente (en SDD: `## Extras`). Nada entra sin rastro. |
| "El árbol está casi limpio, lanzo igual" | Clean-tree gate (regla 2): código sin commitear = diff imposible de aislar. Commitear/stashear antes. |
| "El baseline ya estaba verde, cuenta igual" | `GREEN_ALREADY` exige adjudicación previa; como `already_satisfied` solo prueba no-regresión. Nunca demuestra el cambio por sí solo. |
| "Seguro es defecto del implementador" | Antes del segundo `IMPLEMENTATION_DEFECT` consecutivo del mismo check, registrar una razón falsable de por qué el contrato no está defectuoso. |
| "Arreglo el contrato y sigo" | Toda corrección crea una versión nueva, preserva la anterior y recalcula el baseline contra la revisión pre-dispatch. |

## Contrato de invocación

Quien la invoca (el usuario en modo directo, o `sdd-flow` en modo embebido) provee:

- **`work_order`** — ruta(s) al contrato congelado: `.plans/<id>/` (spec+plan+tasks SDD), un
  `PLAN.md`, o equivalente. En modo directo sin archivo, el conductor **destila** el contrato de
  la conversación y lo escribe a `cross-implement/work-order.md` ANTES de lanzar (queda auditable
  y respeta la regla 1).
- **`working_dir`** — raíz del repo donde se implementa (límite de escritura del implementador).
- **`proof_cmd`** — comando exacto que prueba el resultado (tests acotados, build, script). Si
  falta y no se puede derivar del work order, **una sola pregunta** al usuario antes de lanzar.
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
2. **Gates previos**: work order existe y se lee como contrato (regla 1); clean-tree (regla 2);
   `proof_cmd` resuelto; en normal/complex, verification contract validado, con baseline
   registrado, adjudicado y congelado (regla 9). Cualquiera falla → no se lanza.
3. **Resolver el transporte** (`cli` u `orca-session` — ver `reference.md` → "Transporte: rama
   `orca-session` (escritura acotada, sesión propia)"). **Armar el prompt-contrato** (`reference.md`
   → "Prompt del implementador": GOAL / SPEC / KEY PATHS / CONSTRAINTS / NON-GOALS / PROOF /
   OUTPUT), escrito a archivo con la tool Write, y **lanzar** por la vía de la familia
   (`reference.md` → "Vías de invocación", o la rama `orca-session` si el resolver la eligió),
   capturando la referencia de sesión para el fix loop.
4. **Revisión del conductor** (reglas 4 y 9): diff completo como PR ajeno; archivos declarados vs
   `git status`; drift fuera del work order; evidencia fresca del contrato fila por fila corrida
   por el conductor. Si el work order es SDD, atribuir hunks a tasks y marcar `- [x]` las
   cubiertas. Checklist en `reference.md` → "Revisión del conductor".
5. **Fix loop** (reglas 5 y 9): clasificar cada falla con el triage de ownership antes de gastar
   otra ronda; solo `IMPLEMENTATION_DEFECT` reanuda la misma sesión con un delta. Re-revisar
   (paso 4) tras cada ronda. Al agotar `max_fix_rounds` → **takeover** bajo el mismo contrato; un
   `DESIGN_GAP` suspende y vuelve a plan/spec. Detalle en `reference.md` → "Triage de ownership"
   y "Fix loop".
6. **Cierre**: registrar todo en el log (`reference.md` → "Log de implementación") y devolver el
   resultado a la llamadora — o, en modo directo, presentar diff + prueba + rondas y ofrecer el
   commit (que ejecuta el conductor tras confirmación, con la disciplina de commit del flujo que
   corresponda).

**Modo embebido (sdd-flow, `implement_mode: cross`):** esta skill cubre solo el paso 2 del "Paso
común" de `implement` (aplicar los cambios). Todo lo demás sigue siendo del conductor en sdd-flow:
tests+build completos, `verify` de AC con gate function, revisión manual, staging selectivo,
commit y push con sus STOPs. El tope de `sdd-flow` ("3 fixes de la misma falla = problema de
diseño → volver a plan/specify") manda por encima de `max_fix_rounds`.

## Salida

A la llamadora (o presentada al usuario en modo directo):

- **Estado:** `IMPLEMENTED` (diff revisado + contrato en verde) | `PARTIAL` (takeover: qué quedó
  hecho por el implementador y qué terminó el conductor) | `DESIGN_GAP (suspendida)` (volver a
  plan/spec; en modo embebido, aplica la regla de diseño de sdd-flow) | `UNAVAILABLE`.
- **Resumen del diff** (archivos, qué cambió) + evidencia terminal del contrato corrida por el
  conductor (incluido `proof_cmd` cuando corresponda).
- **Rondas usadas** y desviaciones del work order reportadas por el implementador.
- **Ruta del log** (`implement-log.md`).

## Router de intención

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
   marca la capacidad como ausente para el resto de la tanda.
4. Reporte no parseable → el diff sigue siendo la verdad: revisarlo igual (regla 4); solo se
   pierde la narrativa del implementador.

## Referencias internas

- `reference.md` — "Descubrir el implementador", "Vías de invocación" (Codex/Claude, POSIX +
  PowerShell, con matriz de verificación), el transporte alternativo "Transporte: rama
  `orca-session` (escritura acotada, sesión propia)" (sesión write propia + vigilancia manual +
  cosecha raw→promote del reporte, código ya escrito en el worktree), "Prompt del implementador",
  "Verification contract (normal/complex)", "Revisión del conductor", "Triage de ownership",
  "Fix loop", "Instrumentación con manifest", "Latencia, deadlines y banner", "Archivos de
  trabajo (scratch)", "Log de implementación".
- `README.md` — qué es, cuándo usarla, requisitos e instalación.

## Atribución

El patrón "el otro modelo construye desde una spec congelada, el autor revisa el diff y exige
prueba" está inspirado en la skill `codex-build` de chaseai (a su vez adaptada del patrón
`codex-first` de Peter Steinberger). Acá se toma la **idea** con mecánica propia: bidireccional
por familias, sandbox acotado en vez de bypass (`--yolo`), y contratos de invocación verificados
end-to-end (ver `reference.md` → "Matriz de verificación").
