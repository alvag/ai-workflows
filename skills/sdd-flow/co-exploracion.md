# Co-exploración cross-model — detalle operativo

Detalle de la sección `## Co-exploración cross-model (opcional)` de `SKILL.md`, que conserva los
predicados que deciden si hay que abrir este archivo. No se lee de entrada: se llega desde uno de
sus tres punteros, y cada uno depende de su propio gobierno.

## Los dos momentos
- **Momento 1 — `explore` (pre-spec).** Tras confirmar el contexto y la clasificación en
  `gather-context`: (1) armar el **paquete de contexto** (digest del ticket + prompt del usuario +
  complejidad + paths resueltos de `domain_context`), que viaja **idéntico a los dos workers**.
  Suma además los **hechos crudos** del bloque declarativo de la búsqueda de antecedentes:
  los **términos buscados**, el **estado de cada fuente** con la razón de cada una no comprobada, y las
  **coincidencias crudas** con su ref, su ruta y su SHA. Viajan **también cuando el resultado es
  vacío**: sin los términos y los estados por fuente, "no se encontró nada" y "no se buscó en esa
  fuente" dejan de distinguirse para quien recibe el paquete. Lo que **no** viaja es ninguna
  clasificación ya resuelta —cobertura total o parcial, delta pendiente, impacto en el alcance—: el
  paquete tiene prohibido llevar conclusiones del conductor, y una ya tomada contamina justamente la
  independencia que la co-exploración compra. Si el prompt/ticket trae **URLs de reproducción** ("abre esta URL para ver el
  error") y hay tool de navegador, el conductor **reproduce antes de despachar** y suma al
  paquete un digest **observacional** de la evidencia (salida de consola, requests fallidos,
  pasos observados) — hechos, **sin hipótesis propias**, que contaminarían la independencia del
  explorador (que es headless: no puede navegar). Sin tool de navegador, degradación de la regla
  6: pedir capturas/pasos al usuario, o seguir sin reproducción avisando; (2) invocar
  `co-explore` (Skill tool) con `mode: explore`, `execution: background`; (3) **el conductor no
  explora**: espera el envelope y arbitra desde los índices, abriendo detalle solo por disparador
  (ver `co-explore` → "Lectura selectiva"). Solo si el envelope resuelve a una **rama degradada**
  el conductor produce su propio mapa, con el mismo contrato de índice y detalle; (4) **punto de
  encuentro:** leer el envelope — `outcome`, `branch`, `diversity`, `workers[]`, `contributors[]`—
  y declarar la rama alcanzada en una línea; (5) **síntesis**, siguiendo la guía de
  `co-explore` → "La síntesis (guía para la skill llamadora)" (no se duplica acá): compara **por
  ID**, admite `∅` en divergencias unilaterales, registra qué detalles se abrieron, y fusiona las
  incógnitas (las que cambiarían el diseño alimentan `clarify`); (6) **checkpoint informativo
  condicional** (no es un gate SDD): solo si quedaron
  divergencias sin resolver o enfoques viables materialmente distintos, presentarlos y dejar
  decidir al usuario antes de escribir la spec — si los mapas convergen, se sigue directo a
  `specify` sin stop extra.
- **Momento 2 — `counter-plan` (pre-plan).** Con la spec aprobada (y ya posicionados en la rama
  feature), antes de escribir `plan.md`: invocar `co-explore` con `mode: counter-plan`
  (contexto: **núcleo común** con la spec aprobada + paths resueltos de `domain_context`, más un
  **anexo privado** por worker con su propio índice y detalle de la fase `explore` — nunca el de la
  otra familia, nunca por ruta); contrastar los dos contra-enfoques en una adenda del cierre (mismo criterio de la síntesis: méritos, no adopción automática) y escribir
  `plan.md` con esa síntesis a la vista.
- **Los artefactos no citan la co-exploración.** `spec.md` y `plan.md` se escriben con la
  síntesis a la vista pero redactados de forma autónoma: sin referencias a la co-exploración,
  a los informes del revisor, a `co-explore/` ni al vocabulario conductor/revisor (ver
  `co-explore` → "La síntesis", paso 5). La trazabilidad queda en `.plans/<id>/co-explore/`.
  El checkpoint informativo conversacional no está alcanzado por esta regla, y tampoco lo están las
  **tres excepciones** que declara la lista cerrada de esa misma regla de `co-explore` —nota de
  límite, advertencia de una sola voz y **aviso de corridas delegadas en vuelo**—, que valen igual
  cuando `co-explore` corre standalone.
- **Efecto en `analyze`.** Con co-exploración **nominal** (rama 1), este paso **no explora**: el
  contra-enfoque de `counter-plan` ya cubrió el terreno, y `analyze` queda acotado a comprobar
  **vigencia sobre el HEAD** real de la rama (archivos movidos, código cambiado) y a las
  **verificaciones puntuales** de punteros que habilite un disparador. Solo las **ramas degradadas**
  recuperan el `analyze` completo, porque ahí el mapa del conductor sí es el insumo.
- **Crítica informada.** En los gates de `specify` y `plan`, si la revisión cross-model está
  activa, pasar a `cross-review` los paths resueltos de `domain_context` y, de la co-exploración,
  **los índices y la síntesis** — nunca los `detail-*` completos, que reintroducirían el costo que
  la lectura selectiva elimina. Qué sesión reanuda el revisor **no queda a criterio**: lo fija la
  matriz de `cross-review/reference.md` → "Matriz de resume desde co-exploración", que nunca
  resuelve a la familia del autor ni a un worker `INVALID`.

## Debate en decisiones
- **En `clarify`:** cuando una pregunta es una decisión abierta real (no algo que el código
  responde) y `co_explore.debate.mode` es `on`/`auto`, ofrecer: *"esta decisión (X vs Y) es
  contestable — ¿la someto a debate cross-model antes de que decidas?"*. Si aceptas → invocar
  `co-explore` con `mode: debate` (la pregunta + las opciones + `spec.md` como contexto) → presentar
  la síntesis → decides → registrar la respuesta en `## Clarifications`. Si no → clarify normal.
- **En `plan`:** cuando hay un trade-off contestable (los que ya se nombran en "Decisiones y
  trade-offs" del plan) y el modo lo habilita, ofrecer someter *ese* trade-off a debate (con
  `plan.md` como contexto) antes del gate del plan; la decisión resultante se refleja en el plan.
- **Lo que aterriza en el artefacto va limpio.** La respuesta de `clarify` en `spec.md` y el
  trade-off resuelto en `plan.md` se escriben **sin** mencionar el debate, las familias ni el
  método (fluyen a Jira/PR). La atribución por familia vive solo en `co-explore/debate.md`, local
  (ver `co-explore` → "Publicado vs local").

## Tercera pasada adversarial
**Qué hacer con cada terminal del retorno.** Acá **no existe** el gate de artefacto donde
`cross-review` espera que su salida se presente —todavía no hay spec ni plan escritos—, así que los
tres se consumen explícitamente:

| Terminal | Qué hace `sdd-flow` |
|---|---|
| `APPROVED` | continúa, y escribe el artefacto **desde la síntesis revisada** |
| `UNAVAILABLE` | avisa en una línea y continúa con la síntesis tal como estaba |
| `REVISE` | presenta las **cinco opciones** del checkpoint según el orden normado del retorno, conserva el `run_id` para reanudar la misma corrida, y **no escribe la spec ni el plan** hasta que se resuelva |

**Qué se hace con lo que la crítica encuentre.** Cada hallazgo se arbitra por el **ledger** de
`cross-review` —aplicado, rechazado con motivo, o escalado—, y **un hallazgo adoptado corrige la
síntesis**: aceptarlo sin que cambie ningún insumo posterior es un estado inválido. La corrección se
publica de forma **atómica** y vuelve a validar el **predicado de cierre** de `co-explore` **antes**
de escribir la spec o el plan; una edición puede romper la cabecera, los IDs o una sección
obligatoria, y entonces el flujo consumiría un cierre que `co-explore` rechazaría al retomar.

**La crítica también se verifica.** Los hallazgos son insumo, no órdenes, y acá hay un dato medido:
en la corrida que originó este paso, **uno de los ocho** hallazgos era falso — y era justamente el que
acusaba de roto al comando de verificación del conductor. Se refutó con un control positivo de una
línea. Aceptar una crítica sin verificarla es el mismo error que ignorarla.

**La sesión que criticó no se reutiliza.** Para juzgar si la síntesis representó bien los informes, el
crítico los recibe completos, así que esa sesión queda **contaminada** con material que la revisión
posterior de la spec o del plan no debe ver. Esa revisión sale con **worker fresco**, y recibe los
**índices** y la **síntesis corregida** como contexto.

**Cómo se sabría que el paso paga.** Sobre las pasadas **aceptadas y completadas** —no las declinadas
ni las degradadas—, en una ventana de al menos **seis**, se registra cuántas cambiaron una
recomendación. Se revisa la consigna **salvo que `cambios / pasadas > 1/3`**: la evidencia pedía
cambiar una recomendación en *más* de una de cada tres, así que exactamente un tercio no paga. El
registro vive en una sección `### Métrica de tercera pasada` del `review-log.md`, **separada del
ledger** —cuyo esquema es cerrado y no se amplía en silencio—, con los campos `eligible`,
`recommendation_changed` y `run_id`, y la escribe `sdd-flow` **después** del terminal. El cálculo es
manual y no lleva guarda.

