---
name: cross-review
description: >-
  Usar cuando el usuario pida una "segunda opinión", una "revisión independiente
  o adversarial", un "cross-review", una "mirada externa", o "que otro modelo o
  Codex revise/critique/desafíe" un artefacto de Spec-Driven Development (spec,
  plan, tasks, master-spec, reparto) antes de implementar o de un gate. También
  la invocan sdd-flow y sdd-orchestrator en sus gates (modo embebido). También
  cubre el caso "tengo una idea/plan claro pero ningún artefacto": modo draft —
  redacta un plan ligero desde la conversación + el código y lo somete al mismo
  loop ("stress-test de esta idea", "arma un plan y que Codex lo critique"). NO
  es code review: no usarla sobre diffs, PRs ni código fuente — solo documentos
  de diseño. No invocarla espontáneamente: solo ante un pedido explícito del
  usuario o invocada por una skill SDD. Invocación directa:
  "/cross-review <ruta-del-artefacto>", o sin ruta para el modo draft.
---

# cross-review — segunda opinión cross-model para artefactos SDD

Helper que toma un artefacto SDD y le pide una **crítica adversarial a un worker seleccionado**
<!-- corpus-invariante:inicio:cross-review.SKILL.md.be17f0869bbc -->
—por default, de la familia opuesta al autor— antes de que
<!-- corpus-invariante:fin:cross-review.SKILL.md.be17f0869bbc -->
un humano lo apruebe. El valor es romper la correlación de errores: el mismo modelo que escribe
<!-- corpus-invariante:inicio:cross-review.SKILL.md.ecc42237f1e7 -->
la spec/plan/tasks es, hoy, el único que los revisa antes del gate. Un revisor de otra familia
<!-- corpus-invariante:fin:cross-review.SKILL.md.ecc42237f1e7 -->
caza huecos que ese modelo no ve — un AC faltante, un enfoque frágil, un riesgo no considerado,
un contrato inconsistente.

**No reemplaza el gate humano: lo alimenta.** La revisión corre *antes* del STOP de aprobación
y su crítica se presenta *junto* al artefacto, para que la persona decida con esa entrada ya
incorporada. Y **nunca bloquea el flujo**: si no hay revisor disponible o algo falla, se degrada
limpio al gate humano de siempre.

```
artefacto escrito ──► [cross-review] ──► artefacto (quizá revisado) + resumen de crítica ──► GATE humano
                         loop acotado, read-only,                          (lo presenta la skill
                         Claude árbitro, log auditable                      llamadora; STOP normal)
```

## Reglas no negociables

1. **Read-only por contrato.** El prompt le prohíbe escribir y modificar, y la única salida permitida
   del revisor es su veredicto en el scratch de la corrida. El **aislamiento por permisos** también
   está garantizado: por CLI se lo invoca sin permiso de escritura y el veredicto lo captura el
   conductor. Quien edita el artefacto —si hay algo que aplicar— es Claude, no el revisor.
2. **Loop acotado — el tope existe siempre, y quien lo extiende es el humano.** `max_rounds`
   (default 3) es el presupuesto de **una tanda**, no de la corrida entera: al agotarse **no se
   cierra**, se abre un checkpoint donde el humano elige entre cuatro opciones, y si concede, la
   corrida sigue con otra tanda finita. Lo que esta regla garantiza es que **el loop nunca corre sin
   tope**; no existe un modo que corra hasta `APPROVED` sin límite, ni siquiera el automático, que
   captura el suyo al elegirse. **Donde no hay forma de presentar un gate humano no se pregunta:** se
   agota, se cierra en `REVISE` con las disputas abiertas y se escala. Esa excepción se funda en la
   **capacidad de presentar un gate**, nunca en `execution` ni en el transporte.
3. **Claude/el usuario son el árbitro final — sin sycophancy, en las dos direcciones.** Los findings
   del revisor son *insumo*, no órdenes. Antes de aplicar cualquiera, evaluarlo con la disciplina de
   `superpowers:receiving-code-review`: verificar técnicamente, rebatir lo incorrecto o
   inaplicable, y **registrar el porqué** de cada decisión — un rechazo sin motivo es un estado
   inválido. Aceptar a ciegas es tan dañino como ignorar a ciegas. **Y vale igual del otro lado:**
   una defensa admisible del revisor obliga a **re-arbitrar**, no a aceptar; nadie se vuelve árbitro
   por defender bien.
4. **Foco, no estilo.** La revisión apunta a correctitud del enfoque, AC faltantes o
   contradictorios, riesgos, testeabilidad de los AC y gaps de contrato (en multi-repo). **No**
   a wording, formato ni preferencias cosméticas — eso es "review theater" y mete ruido.
5. **Auditable.** Cada corrida deja un `review-log.md` junto al artefacto: rondas, findings,
   veredictos, y qué decidió Claude con su rationale. La revisión tiene que poder reconstruirse. Los
   archivos de trabajo del revisor (prompts, veredictos crudos, deltas, session, stderr) van a un
   subdirectorio `cross-review/` junto al artefacto, no sueltos en la raíz del flujo (ver
   `reference.md` → "Archivos de trabajo (scratch)").
6. **Opcional y degradable.** Es una **capacidad**, no un requisito. Si falta el revisor o falla,
   avisar en una línea y devolver el control al gate humano. El flujo SDD sigue intacto (ver
   "Degradación").
7. <!-- corpus-invariante:inicio:cross-review.SKILL.md.34fb3b023a63 -->
7. **Descubrir por capacidad, no por nombre; familia opuesta como default y recomendación.** El
7. <!-- corpus-invariante:fin:cross-review.SKILL.md.34fb3b023a63 -->
   revisor se busca por capacidad, no por un nombre de tool fijo. Con ambas familias seleccionadas,
   se elige la opuesta al autor para romper la correlación de errores. Si la allowlist obliga a la
   propia, la revisión **corre** con un worker fresco de esa familia: conductor Claude → worker
   Claude; conductor Codex → worker Codex. Detalle y precedencia en `reference.md` → "Descubrir el
   revisor".

   > **Contrapeso same-family:** la salida debe decir: `Se recomienda revisión humana adicional: el
   > <!-- corpus-invariante:inicio:cross-review.SKILL.md.07028569a2d1 -->
   > worker ya no es de otra familia que el autor, por lo que no rompe la correlación de errores.`
   > <!-- corpus-invariante:fin:cross-review.SKILL.md.07028569a2d1 -->

## Corridas delegadas en vuelo

Todo revisor que esta skill despacha nace con su **sobre** en `.cross-model/active/<skill>/`, escrito
**antes** del despacho, y mientras el sobre siga activo cada turno del conductor cierra informando su
estado. El punto de despacho propio es uno:

- el **revisor por ronda** del loop de revisión — la ronda 1 y cada ronda siguiente que reanuda el
  mismo thread, por cualquiera de las vías A/B/C

Campos del sobre, transiciones, sonda por turno, cosecha y condiciones del retiro:
`corridas-en-vuelo.md`, hermano de este archivo. Es la regla normativa; acá solo se enumera dónde
aplica.

## Red flags — detente y reconsidera

Las reglas de arriba dicen *qué* hacer; esta sección frena los atajos al procesar la crítica. Ley fundamental:

> **LOS FINDINGS SON INSUMO, NO ÓRDENES — VERIFICAR ANTES DE APLICAR.** Aceptar a ciegas es tan dañino como ignorar a ciegas (regla 3).

Si reconoces alguno de estos pensamientos, detente y aplica la disciplina de `superpowers:receiving-code-review`.

| Racionalización | Realidad |
|---|---|
| "El revisor lo marcó, lo aplico" | Antes de aplicar: verificar técnicamente, rebatir lo incorrecto/inaplicable y **registrar el porqué** (regla 3). |
| "Tiene razón, le agradezco y edito" | Sin sycophancy. La respuesta correcta es reformular el requisito o directamente corregir — no validación performativa. |
| "Le respondo el delta y de paso pulo el wording que sugirió" | Foco, no estilo (regla 4): wording/formato es review theater. La revisión apunta a correctitud, AC, riesgos y contratos. |
| "No hay revisor disponible, espero / reintento en loop" | Degradación: avisar en una línea y ceder al gate humano. Loop acotado a `max_rounds`, con tope duro → `UNAVAILABLE` (reglas 2, 6). |

## Contrato de invocación (lo que pasa la skill llamadora)

Al invocarla, `sdd-flow`/`sdd-orchestrator` (o el usuario) proveen:

- **`artifact_type`** — `spec | plan | tasks | master-spec | reparto`. Define el foco de la
  revisión (ver `reference.md` → "Foco por tipo de artefacto").
- **`artifact_path`** — ruta del artefacto a revisar (p. ej. `.plans/ABC-123/plan.md`).
- **`context_paths`** — artefactos relacionados para grounding (p. ej. al revisar `tasks`, pasar
  también `spec` y `plan`; al revisar `reparto`, la `master-spec`). Opcional pero recomendado. Si
  el flujo corrió **co-exploración** (`co-explore`), la llamadora pasa acá los **índices** y la
  **síntesis** —nunca los `detail-*` completos, que reintroducirían el costo que la lectura
  selectiva elimina—. Qué sesión se reanuda lo fija la matriz normativa de `reference.md` →
  "Matriz de resume desde co-exploración": nunca resuelve a la familia del autor ni a un worker
  `INVALID`.
- **`working_dir`** — directorio desde donde el revisor puede leer el código en read-only.
- **`family_inventory`** — selección declarada y resuelta por la raíz, con `families`, `source`,
  `selection` y `root`. La skill **hereda la elección**; si falta, esta invocación es la raíz y la
  resuelve antes de despachar.
- **`complexity`** — `trivial | normal | complex` (de `sdd-flow`); modula profundidad/esfuerzo.
- **`execution`** — `auto | sync | background` (de la config `cross_review`); cómo se espera al
  revisor. `auto` (default) elige por la capacidad de timeout del conductor; `sync` fuerza llamada
  bloqueante; `background` fuerza poll acotado. En todos hay tope duro → `UNAVAILABLE` (ver
  `reference.md` → "Latencia y timeout (Claude revisor)").
- **`ac_context`** — los `AC-n` y contratos en juego, para que la crítica los referencie.
  Opcional: si la llamadora no lo pasa, derivarlos de `context_paths` (la spec/master-spec ya
  los contiene).

**Modo de uso:**
- *Embebido* (lo llama otra skill SDD): no hace STOP propio. Devuelve el artefacto (quizá
  revisado) + un resumen de la crítica para que la llamadora lo presente en su gate.
- *Directo* (lo llama el usuario con `/cross-review <ruta>`): infiere `artifact_type` por el
  nombre/encabezado del archivo, corre el loop y **presenta** el resultado al usuario.
- *Draft* (directo **sin ruta**, con una idea/plan claro en la conversación): el conductor
  redacta primero un plan ligero y lo somete al mismo loop — ver "Modo draft" abajo.

## Modo draft (directo, sin artefacto)

Para cuando hay una idea clara pero ningún artefacto que revisar — el punto de entrada portable,
fuera de todo flujo SDD (inspirado en `codex-review` de chaseai):

1. **Una sola pregunta si falta el objetivo.** Si la conversación no deja claro qué se quiere
   construir, preguntarlo (una vez). Si escribir el plan obliga a resolver ambigüedades de diseño
   más profundas, este modo no alcanza: ofrecer `sdd-flow` (con su `clarify`) en vez de un draft
   con huecos. Y si lo que falta no es decisión sino **terreno** (no está claro qué existe en el
   repo, dónde tocar, qué riesgos hay), el paso previo natural es `co-explore` — **mapa antes que
   veredicto**: un draft escrito sin conocer el terreno le da al revisor un blanco flojo y quema
   rondas en problemas que una exploración habría evitado (ver la fila de desambiguación del
   router).
2. **Planificar de verdad.** Leer el código relevante del repo (no planear en el aire) y escribir
   el plan a `.cross-review/<slug>/plan.md` — dir local untracked, mismo criterio que el modo
   directo de `co-explore` — con la estructura: `## Objetivo`, `## Enfoque` (pasos concretos),
   `## Decisiones y trade-offs` (las apuestas contestables, nombradas — los blancos del revisor),
   `## Riesgos y preguntas abiertas`, `## Fuera de alcance`.
3. **Correr el loop normal** con `artifact_type: plan`, `artifact_path` ese archivo,
   `working_dir` el repo y `complexity` estimada (anunciarla). El `review-log.md` y el scratch
   `cross-review/` quedan junto al plan draft.
4. **Presentar** el plan convergido (o el deadlock con sus disputas, regla 2) y **ofrecer el
   handoff**: implementarlo el conductor, o —si la skill `cross-implement` y el CLI de la otra
   familia están disponibles— delegar la implementación cruzada con este plan como `work_order`
   (el conductor revisa el diff). El código se escribe solo tras ese sign-off del usuario.

El draft **no es** un `plan.md` de sdd-flow (sin header YAML, sin ciclo de status, sin rama): si
el usuario quiere el ciclo completo con gates y verify, el camino es `sdd-flow` — este modo es el
stress-test portable de una idea, no un flujo de desarrollo.

## Paso 0 — descubrir el revisor

Antes de nada, resolver si hay un segundo modelo disponible (algoritmo y opciones en
`reference.md` → "Descubrir el revisor"):

Si el contrato trae `family_inventory`, heredarlo: no releer config, no ejecutar el preflight de la
familia ausente y no volver a anunciar su ausencia. Los preflights reales de una familia presente
siguen aplicando y sus fallos se informan como hasta ahora.

1. **Identificar la familia del autor.** Es la del agente que conduce la skill, sin importar la
   superficie donde corre (CLI, app de escritorio, IDE, web): un agente **Claude** → autor
   Claude; un agente **Codex** → autor GPT/Codex.
2. <!-- corpus-invariante:inicio:cross-review.SKILL.md.248755b760dd -->
2. **Elegir dentro de `cross_model.families`.** Con `auto`, preferir la familia opuesta (regla 7):
2. <!-- corpus-invariante:fin:cross-review.SKILL.md.248755b760dd -->
   - Autor **Claude** → revisor **Codex**: el subagente `codex:codex-rescue` si existe en el
     entorno; si no, el CLI `codex exec` en read-only.
   - Autor **GPT/Codex** → revisor **Claude**: el CLI `claude -p` restringido a tools de lectura.
   Si la allowlist contiene solo la familia del autor, lanzar un worker fresco de esa familia y
   emitir el contrapeso de revisión humana, en las dos direcciones.
3. Si `cross_review.reviewer` fuerza una vía (`claude` | `codex`), solo puede elegir dentro de
   `families`. Fuera de ella → error, sin despacho: `reviewer: <X> está fuera de
   cross_model.families: [<Y>]`. Dentro de ella se respeta; si coincide con el autor, emitir el
   contrapeso same-family. La matriz canónica vive en `reference.md`.
4. Si **no hay CLI** para el revisor seleccionado → no romper: devolver veredicto
   `UNAVAILABLE` con el aviso estándar y ceder al gate humano (ver "Degradación").
5. Si hay revisor → seguir con el loop.

> **Portabilidad.** Los comandos para descubrir e invocar al revisor tienen variante **POSIX**
> (macOS/Linux/Git Bash) y **PowerShell** (Windows). Elegir según el shell del entorno — detalle y
> bloques listos para ejecutar en `reference.md` → "Portabilidad entre shells (POSIX / PowerShell)".

## El loop de revisión

1. **Ronda 1.** Armar el prompt de revisión (plantilla XML en `reference.md` → "Prompt de
   revisión": `<task>`, `<artifact>`, `<context>`, `<grounding_rules>`,
   `<structured_output_contract>`, `<dig_deeper_nudge>`), incluyendo el **contenido** del
   artefacto inline (grounding) y el foco según `artifact_type`. Invocar al revisor en
   **read-only**. Guardar referencia del thread para poder reanudarlo en rondas siguientes.
2. **Validar la conformidad** de la respuesta contra el formato estructurado (`reference.md` →
   "Formato de salida"): lista de `findings` `[severidad, confianza, qué, por qué, cambio sugerido,
   AC/sección]` + un veredicto `APPROVED | REVISE`, con su marca final. Una salida no conforme no se
   arbitra (ver "Degradación").
3. **Asignar identidad y deduplicar por tema.** El ID lo asigna el conductor, no el revisor, y dos
   emisiones del mismo tema se unifican **antes** de cualquier arbitraje (`ciclo-de-vida.md` →
   "Identidad").
4. **Arbitrar, en dos pasadas y en este orden:** primero las **respuestas a rechazos** —aceptaciones
   y defensas, evaluando su admisibilidad—, después los **findings nuevos**. Para cada uno, **decidir
   como árbitro** (regla 3, vía `receiving-code-review`): aplicar / rechazar / escalar. Ordenar el
   triage por severidad×confianza (atacar primero lo grave y probable), pero **verificar cada finding
   igual** — la confianza no saltea la regla 3. Aplicar los aceptados editando el artefacto (Claude
   edita, no el revisor). **Todo rechazo lleva motivo: un rechazo sin motivo es un estado inválido,
   no un default.** Registrar cada evento en el **ledger** del `review-log.md`.
5. **Registrar el cierre de la ronda.** Ante **toda** salida conforme —incluida la que no trae
   findings nuevos ni respuestas— apendizar al ledger una entrada `control-corrida` con
   `ronda-completada-valida` si esta ronda recibió el artefacto actualizado, o `ronda-completada` si
   no. **Registra una ronda ya ejecutada: no despacha ninguna ni obliga a correr una adicional.**
6. **Derivar el veredicto del ledger** —no del bloque del revisor— y recién entonces **evaluar el
   corte**: `APPROVED` cierra el loop y va a "Salida"; `REVISE` sigue. La tabla del predicado, con
   sus cuatro ramas, está en `reference.md` → "Veredicto derivado".
7. **Siguiente ronda** reanudando el mismo thread, con el asset `review-round-n.md`: el delta se
   **proyecta desde el ledger**, el revisor debe pronunciarse por cada rechazo —aceptarlo o
   defenderlo con argumento nuevo— y, **si hay aplicaciones pendientes de revisión, el artefacto
   actualizado viaja completo en el prompt**. Repetir desde el paso 2.
8. **Corte por tanda.** `max_rounds` es el presupuesto de **una tanda**, no de la corrida: al
   agotarse se abre el **checkpoint** donde el humano elige entre cuatro opciones, y la numeración
   de rondas acumula si concede. Ver `ciclo-de-vida.md` y `reference.md` → "Tandas y salida de
   rondas".

> **Por qué el corte va después de arbitrar, y no antes.** El veredicto se deriva del ledger una vez
> arbitrado todo, así que evaluarlo antes leería un estado que todavía no existe: una defensa sin
> evaluar quedaría sin arbitrar para siempre, y una edición recién aplicada contaría como convergida
> sin que nadie la haya visto. El registro del cierre va en el medio a propósito — después del
> arbitraje, para que la ronda no libere lo que ella misma aplicó; antes del corte, para que una
> ronda limpia quede registrada aunque el veredicto cierre el loop enseguida.

## Salida

Devolver a la skill llamadora (o presentar, en modo directo):

- **Veredicto final:** `APPROVED` | `REVISE (rondas agotadas, N disputas abiertas, M aplicaciones
  pendientes de revisión)` | `UNAVAILABLE`.
  El `UNAVAILABLE` va con su **causa** —`confirmed_wall` · `launch_flake` · `runtime_failure` ·
  `deadline_exceeded` · `host_sandbox_wall`—: son causas del enum compartido, no veredictos nuevos (`reference.md` →
  "Latencia y timeout (Claude revisor)"). **El conteo `M` va en el texto del veredicto, no solo en el
  log:** un `REVISE (rondas agotadas, 0 disputas abiertas)` se lee como cierre limpio, y puede estar
  ocultando tres ediciones que nadie revisó.
- **`aplicaciones_pendientes` e `ids_pendientes`, también cuando el veredicto es `UNAVAILABLE`.** Una
  degradación **no abre checkpoint**, así que no lleva `tandas_concedibles` y la señal se perdería
  entera por esa ruta: si una ronda aplicó findings y la siguiente murió por timeout, error o salida
  ilegible, el gate humano se libera igual y el artefacto se aprueba sin que nadie sepa que hay
  ediciones sin mirar. Los dos campos viajan con los **mismos nombres** que abajo, en el retorno de
  la degradación. El enum de causas **no cambia**: esto agrega datos al retorno, no una causa nueva.
- **Resumen de la crítica:** qué marcó el revisor, qué aplicó Claude y qué rechazó (con el porqué).
- **Diff del artefacto** si hubo cambios.
- **Ruta del `review-log.md`.**
- **`tandas_concedibles`** — presente en **todo `REVISE` que abra el checkpoint**, por cualquiera de
  sus dos causas: `disponibles` (bool) · `rondas_consumidas` (entero, de la corrida) ·
  `tamano_tanda` (entero, el `max_rounds` vigente) · `causa_corte` (`tanda_agotada` |
  `solo_disputas`) · **`aplicaciones_pendientes`** (entero no negativo) · **`ids_pendientes`** (lista
  de IDs) · `run_id`, con el que la llamadora reanuda **la misma** corrida.
  `disponibles` es **falso** solo cuando la causa es `solo_disputas` —ninguna ronda las resuelve—, y
  **no oculta ni deshabilita ninguna opción**: las cuatro se ofrecen siempre; lo que hace es advertir
  que conceder no puede converger.

  **`aplicaciones_pendientes` e `ids_pendientes` son obligatorios aunque valgan `0` y lista vacía.**
  Un campo que desaparece cuando no hay nada que reportar es indistinguible de un productor que no lo
  implementó, y quien presenta el checkpoint no puede distinguir "no hay pendientes" de "no me lo
  dijeron". Se derivan contando los IDs cuya transición **más reciente** a `aplicado` sigue sin una
  ronda posterior válida (`ciclo-de-vida.md` → "Aplicación pendiente de revisión").

  **`causa_corte` no gana un valor nuevo por esto.** El checkpoint se abre porque se agotó la tanda:
  la aplicación pendiente describe el **estado** del ledger, no la **causa** del corte. Un valor
  nuevo mezclaría las dos cosas y obligaría a cada consumidor a desambiguarlas.
- **Nota de límite** (obligatoria, una vez por corrida):

  > <!-- corpus-invariante:inicio:cross-review.SKILL.md.2d888ab3fdcf -->

  > Un revisor independiente de otra familia aporta una crítica adicional; sigue siendo **una

  > <!-- corpus-invariante:fin:cross-review.SKILL.md.2d888ab3fdcf -->
  > sola** revisión. No prueba correctitud y no reemplaza el gate humano.

  Va **una vez, al cierre de la corrida** — no en el formato de salida del revisor ni repetida por
  ronda. Es distinta de "no reemplaza el gate humano" a secas: eso dice quién decide, esto dice
  cuánta cobertura compró la decisión. La asimetría importa: acá hay **un** revisor frente a un
  autor, no dos voces simétricas como en `co-explore`.

La llamadora presenta este resumen **junto al artefacto** en su gate humano (mismo STOP, sin gate
extra). El humano aprueba con la segunda opinión ya a la vista, y ahí mismo elige entre las **cuatro
opciones** del checkpoint si la corrida lo abrió. En modo **directo** y **draft** no hay llamadora:
las presenta `cross-review`, que ya presenta su propio resultado.

> **Con `aplicaciones_pendientes` mayor que cero, el conteo y sus IDs se declaran ANTES de ofrecer
> las opciones.** Vale para **todo** presentador del checkpoint —hoy `sdd-flow`, `sdd-orchestrator`,
> `sdd-pr-feedback`, y esta misma skill en directo y draft—, y también cuando lo que se devuelve es
> un `UNAVAILABLE` que libera el gate sin abrir checkpoint. La obligación es de **quien presenta**,
> no de una lista: cualquier skill que ofrezca las cuatro opciones queda alcanzada, y enumerarlas es
> una ayuda de lectura, no la condición. Quien elige "continuar así" está
> aprobando el artefacto: si no sabe que hay ediciones que ningún revisor miró, decide sin el único
> dato que este loop existe para darle, y el hueco reaparece en la interfaz después de haberse
> cerrado en el predicado.

Además, al resolver el veredicto se escribe el **manifest de corrida** — los tres veredictos, no
solo `APPROVED`: una serie que registra las revisiones que convergieron y omite las que agotaron
rondas o nunca encontraron revisor no puede decir si esta capacidad rinde. Esquema y vocabulario en
`reference.md` → "Manifest de corrida".

## Degradación (nunca bloquea el flujo SDD)

Tres modos de falla, todos terminan en el gate humano de siempre con un aviso de una línea
("revisión cross-model no disponible — sigo con el gate humano"):

1. **El revisor no arranca.** Según el preflight de capacidad del CLI seleccionado:
   - **Pared confirmada** (binario ausente, auth rechazada, versión incompatible): reintentar no
     sirve → Paso 0 devuelve `UNAVAILABLE`, **terminal para la corrida** (no se reintenta en rondas
     posteriores del loop ni en despachos siguientes de la misma tanda).
   - **Flake transitorio** (el binario existe pero el lanzamiento flaqueó por arranque frío o
     timeout de spawn): 2-3 reintentos con backoff corto, no un loop abierto; solo ahí `UNAVAILABLE`.
   (Distinto del punto 2, el fallo en runtime **tras** arrancar bien, que es por-intento.)
2. **El revisor falla en runtime** (error, timeout de exec, `poll_deadline` vencido sin `VERDICT:`,
   o respuesta no parseable) → registrar el fallo en `review-log.md`, cortar el loop (y matar el
   proceso en background si lo hubo) y devolver `UNAVAILABLE` con lo que haya. **Nunca quedar
   esperando indefinida** — todos los caminos tienen tope duro (ver `reference.md` → "Latencia y timeout (Claude revisor)").
   Son dos **causas**, no dos veredictos: `runtime_failure` para el error de ejecución o la respuesta
   ilegible, y `deadline_exceeded` cuando venció el tope de pared sin `VERDICT:`. El revisor arrancó
   bien y el corte lo puso el conductor, así que registrarlo como `runtime_failure` sugiere una falla
   de infraestructura que no ocurrió — y esconde que la palanca es el presupuesto.
3. **Config la desactiva** (`cross_review.mode: off`, o complejidad por debajo del umbral) → ni
   se intenta; la llamadora va directo al gate.

> La cuarta forma de degradación —**que esta skill ni siquiera esté instalada**— la maneja la
> skill llamadora: `sdd-flow`/`sdd-orchestrator` chequean si `cross-review` está disponible
> y, si no, omiten la revisión. Por eso la dependencia es **blanda**: las skills SDD funcionan
> igual sin este helper.

## Configuración

Claves bajo `cross_review` en `.specify/config.yml` (sdd-flow) o en el `manifest.yml` de la
orquestación (sdd-orchestrator). Todas opcionales:

```yaml
cross_review:
  mode: auto            # auto (por complejidad) | "on" | "off"  (entre comillas: sin ellas YAML los parsea como booleanos)
  execution: auto       # auto (por capacidad del conductor) | sync | background
  artifacts: [spec, plan, tasks]   # qué tipos revisar (sdd-orchestrator: [master-spec, reparto])
  max_rounds: 3         # rondas POR TANDA, no de la corrida entera; al agotarse se abre el checkpoint
  reviewer: auto        # auto (familia opuesta si está en la allowlist) | claude | codex
```

Precedencia (igual que el resto de overrides SDD): **override conversacional de la corrida >
config > default por complejidad**. Default por complejidad en `sdd-flow`: `trivial` off,
`normal` opt-in (off salvo pedido), `complex` on. En `sdd-orchestrator`, `auto` = **on** para
`master-spec`/`reparto`, que se revisan como `complex`. `execution: auto` (default) corre **sync** cuando
el conductor puede fijar un timeout largo (Claude Code: `Bash` hasta 600000ms) y **background+poll
acotado** cuando su exec es corto (Codex ~120s); en todos los modos hay tope duro → `UNAVAILABLE`,
nunca espera indefinida (ver `reference.md` → "Latencia y timeout (Claude revisor)").

## Router de intención

> **¿Es este el peldaño que hace falta?** La escalera de rigor —respuesta local → `co-explore` →
> `cross-review` → `cross-implement` → `verify`— dice cuál es la opción **más barata que
> alcanza**, que casi nunca es la más completa: `co-explore/reference.md` → "Escalera de rigor".

| El usuario dice (ej.) | Acción |
|---|---|
| "/cross-review `.plans/X/plan.md`", "revisa este plan con otra opinión" | revisar el artefacto nombrado (modo directo) |
| "pídele a Codex que critique la spec", "segunda opinión del plan" | revisar el artefacto (modo directo) |
| "/cross-review" sin ruta, "stress-test de esta idea", "arma un plan y que Codex lo critique" | **modo draft**: redactar el plan ligero + loop + ofrecer handoff (ver "Modo draft") |
| "segunda opinión sobre esta idea" (ambiguo, sin artefacto) | desambiguar con **¿mapa o veredicto?** — ya hay un enfoque elegido y quiere que lo ataquen → modo draft (veredicto); todavía no hay enfoque y falta entender el terreno (qué existe, dónde tocar, riesgos) → `co-explore` (mapa), no esta skill |
| (invocada por `sdd-flow`/`sdd-orchestrator` en un gate) | modo embebido: revisar y devolver resumen |
| "sin cross-review", "salta la segunda opinión" | desactivar para la corrida (`mode: off`) |

## Referencias internas

- `reference.md` — cómo descubrir e invocar el revisor (subagente codex / `codex exec`
  read-only / resume entre rondas), **portabilidad entre shells (POSIX / PowerShell)**, plantilla
  del prompt, formato de salida, plantilla del `review-log.md`, y el foco de revisión por tipo de
  artefacto.
- `ciclo-de-vida.md` — identidad del finding, estados y transiciones, ledger y su esquema,
  presupuestos, **aplicación pendiente de revisión**, vara de admisión de la defensa, cierre y
  adopción de logs legacy. Se carga ante la **primera salida conforme que traiga al menos un finding,
  cualquiera sea el veredicto** — no al primer rechazo (la ingesta ya está gobernada por ese
  contrato) y no al primer `REVISE` (un `APPROVED` con findings `low` también lo necesita). Una
  corrida `APPROVED` **sin** findings no lo carga: apendiza igual su fila de cierre de ronda, pero
  para eso alcanza con el paso 5 del loop, que nombra la clase, el campo y sus dos valores.
- `README.md` — qué es, cuándo usarla, requisitos e instalación.

## Atribución

El patrón de "revisión adversarial de otro modelo antes de implementar" está inspirado en la
skill `grill-me-codex` de chaseai (su "Acto 2") y, más atrás, en `grill-me` de Matt Pocock
(MIT); el **modo draft** ("redactar el plan primero y someterlo al loop") viene de su variante
standalone `codex-review`. Acá se toma la **idea**, no el código: la implementación, el contrato
con el runtime de Codex y la integración con el ciclo SDD son propios.
