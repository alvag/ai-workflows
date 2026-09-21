# Co-exploración cross-model — detalle operativo

Detalle de la sección `## Co-exploración cross-model (opcional)` de `SKILL.md`, que conserva los
predicados que deciden si hay que abrir este archivo. No se lee de entrada: se llega desde uno de
sus punteros, y cada uno depende de su propio gobierno.

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

## Lo que aterriza en el artefacto va limpio

La respuesta de `clarify` en `spec.md` y el trade-off resuelto en `plan.md` se escriben **sin**
mencionar las familias ni el método: esos textos fluyen a Jira y al PR. La atribución por familia
vive solo en los artefactos locales de `co-explore` (ver `co-explore` → "Publicado vs local").
