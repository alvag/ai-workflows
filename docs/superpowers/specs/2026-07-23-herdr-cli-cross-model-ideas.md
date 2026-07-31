# Ideas: arquitectura cross-model con Herdr y CLI (rescatado)

**Fecha original:** 2026-07-23 · **Rescatado:** 2026-07-31
**Estado:** **descartado como arquitectura.** Vivía untracked en `.plans/` del worktree de
`feat/herdr-cli-cross-model` y se rescata acá antes de archivar esa rama, porque el catálogo
CLI-first lo cita como fuente y porque su registro de decisiones tiene valor más allá del
transporte que las motivó.

> **Qué se portó, y a dónde.** El **punto 1** del catálogo —coordinador puro, índice compacto con ID
> estable/severidad/confianza/punteros, lectura selectiva por disparadores y paridad mecánica
> índice↔detalle— salió de acá y está implementado en el commit `97cc694`. Las **etiquetas de
> diversidad efectiva** y la **degradación parcial declarada** también, en `dd2f3b7` y `97cc694`.
>
> **Qué queda pendiente de portar**, detectado al releer este documento: el **índice paginado sin
> pérdida** (el presupuesto limita el tamaño de cada entrada y página, **nunca** la cantidad de
> hallazgos), **`clarification-needed`** como resultado de worker —con la respuesta creando una
> **versión inmutable nueva** del paquete de contexto en vez de mutar el que el worker ya recibió—,
> y la separación entre **fallback de transporte**, **reparación de formato** y **retry semántico**,
> con una sola ronda de reparación en la misma sesión viva cuando el trabajo terminó pero el reporte
> no cumple el contrato.
>
> **Qué NO se porta, y por qué.** Todo lo que presupone un runtime con estado durable: lease del
> coordinador con heartbeat y takeover, ciclo de vida de runs con `generation`, política de
> worktrees y su sincronización con manifiesto, y la ubicación instalable del runtime. Es
> exactamente lo que el catálogo lista en "qué no traer", y no compra nada en un repo de Markdown
> sin build ni tests.
>
> Ver `docs/superpowers/specs/2026-07-30-portacion-cli-first-cross-model.md`.

---


> Documento local y evolutivo. Registra ideas aceptadas, abiertas y descartadas antes de formalizar la spec.

## Objetivo provisional

Desacoplar las políticas de los flujos cross-model de la forma concreta de ejecutar agentes,
permitiendo que el conductor coordine workers frescos sin ejecutar él mismo toda la tarea
delegada, pero conservando la autoridad sobre la síntesis, la verificación y las decisiones.

## Estado actual verificado

- El flujo CLI funciona y debe conservarse como base estable y fallback.
- `co-explore` usa hoy el modelo conductor + un worker de la otra familia; ambos exploran y el
  conductor sintetiza.
- `co-explore`, `cross-review` y `cross-implement` contienen sus propias reglas de invocación de
  `claude -p` y `codex exec`; no existe un runtime común.
- La selección de la otra familia es hoy una regla dura en las tres skills; si esa familia no
  está disponible, la ejecución devuelve `UNAVAILABLE` o recae en el conductor.
- Herdr ya ofrece primitivas de ciclo de vida para abrir panes, iniciar agentes, enviar prompts,
  esperar estados y leer resultados. Su sintaxis efectiva depende del CLI instalado.
- El soporte de worktrees actual es puntual; no existe una decisión de workspace común al inicio
  de cualquier flujo.

## Ideas con respaldo inicial

- Herdr debe ser un transporte intercambiable, no el centro de la arquitectura.
- Las ejecuciones por Herdr y por CLI deben respetar un contrato común de entrada, ciclo de vida
  y salida.
- La política decide cuántos workers usar y con qué propósito; el adaptador solo los ejecuta.
- En una co-exploración, el conductor podría lanzar workers frescos Claude y Codex, recibir dos
  mapas independientes y actuar como árbitro sin hacer una tercera exploración completa.
- Se probará directamente el modo coordinador puro, sin conservar el modelo actual como camino
  principal de la primera prueba.
- La familia del coordinador no restringe la familia de los workers: puede despachar Claude,
  Codex o ambos, incluso si uno coincide con su propia familia.
- La independencia primaria proviene de sesiones y contextos frescos con prompts no anclados.
  Usar familias distintas añade diversidad de puntos ciegos, pero deja de ser una precondición.
- La disponibilidad de una sola familia no debe bloquear el flujo: una ejecución puede continuar
  con un único worker y declarar explícitamente la diversidad reducida.
- La política ideal intenta obtener dos resultados de familias distintas. Usar la misma familia
  es un fallback de disponibilidad, no el caso preferido.
- El ahorro de contexto depende de delegar en sesiones frescas y devolver artefactos acotados; la
  diversidad de familias mejora la independencia de criterio, pero no cambia ese ahorro.
- Cada worker entrega dos capas: un índice compacto que enumera todos los hallazgos y un informe
  estructurado con el detalle y la evidencia. El índice no reemplaza ni resume de forma destructiva
  el informe completo.
- Cada hallazgo debe tener un identificador estable, severidad o impacto, confianza y punteros a
  evidencia. El coordinador abre el detalle cuando hay divergencia, alto riesgo, baja confianza o
  una decisión que arbitrar.
- Se adoptó la lectura selectiva: el coordinador siempre consume el envelope y el índice completo,
  pero no carga ambos informes detallados salvo que se active uno de esos disparadores.
- La cantidad y los IDs del índice deben coincidir con los del detalle; esta paridad debe poder
  validarse mecánicamente.
- Las transcripciones crudas son scratch de diagnóstico; el informe estructurado es el artefacto
  autoritativo.
- El conductor no debe ser un resumidor ciego: puede inspeccionar evidencia puntual para resolver
  divergencias y sigue siendo responsable de la síntesis.
- La capacidad debe ser reutilizable por cualquier skill cross-model y por invocaciones directas;
  `sdd-flow` es un consumidor, no el dueño del runtime.
- El fan-out Claude+Codex no debe ser obligatorio en todos los pasos.
- La implementación conserva un único escritor por defecto.
- La configuración puede definir perfiles por familia y por tipo de tarea, incluyendo modelo y
  esfuerzo, sin acoplar esas decisiones al adaptador Herdr o CLI.
- La configuración compartida seguirá viviendo en `.specify/config.yml`; no se añadirá un archivo
  global independiente.
- Las invocaciones directas de las skills también leerán `.specify/config.yml` desde la raíz del
  repositorio, aunque no exista un flujo SDD activo.
- Precedencia: override conversacional de la corrida > `.specify/config.yml` > defaults de la
  skill. Si el archivo no existe, la capacidad debe seguir funcionando.
- Los defaults de una skill pueden seleccionar roles, cardinalidad y el modelo por defecto del
  proveedor; no deben depender de que el usuario configure perfiles previamente.

## Política de workspace a evaluar

- Resolver antes del dispatch si el flujo usa el checkout actual o un worktree nuevo.
- En `sdd-flow`, la base predeterminada es la rama default detectada del repositorio
  (`main`/`master`); el usuario puede indicar otra.
- Si el flujo inicia desde una rama distinta a la default, preguntar si debe tomar esa rama o la
  default como base.
- El uso de worktree es opcional y configurable en `.specify/config.yml`.
- Permitir un directorio raíz configurable; default propuesto:
  `~/worktrees/{project}/{id-or-slug}`.
- El conductor administra el ciclo de vida del workspace y entrega un `cwd` resuelto a los
  adaptadores.
- Un worktree pertenece al flujo completo: spec, plan, tasks, implementación y verificación viven
  allí.
- Workers read-only pueden compartir un checkout estable.
- Si existen varios escritores, cada uno requiere un worktree aislado; no deben escribir en
  paralelo sobre el mismo árbol.
- Al archivar se pretende eliminar el worktree y la rama local, con política de seguridad y
  configuración todavía por definir.

## Bootstrap hacia un worktree

- Crear un worktree no cambia el `cwd` del proceso Claude/Codex que inició el flujo.
- La creación, sincronización y eliminación del worktree son responsabilidades
  transport-agnostic: usan Git y operaciones de archivos, no dependen de Herdr.
- No se debe intentar continuar silenciosamente desde el proceso anclado al checkout original:
  muchas herramientas y reglas de proyecto se resuelven desde su directorio inicial.
- Flujo recomendado:
  1. El coordinador inicial resuelve base, branch, path y configuración.
  2. Crea o abre el worktree.
  3. Copia los insumos locales relevantes de `.specify/`, porque Git no lleva archivos untracked
     al nuevo checkout.
  4. Escribe un bootstrap/handoff mínimo del flujo dentro del worktree.
  5. Inicia un coordinador fresco con `cwd` igual al worktree mediante Herdr o CLI.
  6. Verifica que el nuevo coordinador retomó antes de cerrar o liberar la sesión inicial.
- Con Herdr, el adaptador puede abrir el worktree, crear la terminal e iniciar el coordinador de
  forma automática.
- Sin Herdr, Git sigue creando el worktree y copiando los archivos locales. Si el entorno CLI no
  puede transferir una sesión interactiva, el fallback seguro es persistir el handoff y pedir
  abrir una nueva sesión desde el worktree; no continuar silenciosamente desde el `cwd` anterior.
- `.plans/<id>/` nace en el worktree nuevo; no se copia el catálogo completo de planes del checkout
  principal.

## Sincronización de archivos locales

- `.specify/config.yml` podrá declarar una allowlist de directorios o archivos untracked para dos
  momentos:
  - `on_create`: checkout principal → worktree del flujo.
  - `on_archive`: worktree del flujo → checkout principal.
- La sincronización no debe ser un `cp -R` ciego. Al crear el worktree se persiste un manifiesto
  con origen, destino y hashes iniciales de cada archivo seleccionado.
- Al archivar:
  - si solo cambió la copia del worktree, se puede copiar al principal;
  - si solo cambió el principal, no se sobrescribe;
  - si ambos cambiaron desde el snapshot inicial, se detiene y se pide resolver el conflicto;
  - si nada cambió, se omite.
- Solo se aceptan rutas relativas a la raíz del repo, sin `..`, y nunca se sobrescriben archivos
  trackeados por Git.
- Los borrados no se propagan por defecto; requerirían una política explícita.
- La eliminación del worktree y de la rama ocurre solo después de una sincronización `on_archive`
  exitosa. Un conflicto o fallo conserva ambos.
- No usar `git worktree remove --force` como camino normal.
- El manifiesto de sincronización debe quedar junto a los artefactos del flujo para que el archive
  sea reanudable y auditable.
- Si aparece un conflicto de sincronización, un worktree sucio o Git rechaza la eliminación, el
  flujo queda en estado reanudable `cleanup-blocked`, registra la causa y conserva intactos el
  worktree y la rama.
- Antes de copiar de regreso se validan todos los conflictos. La promoción debe usar staging
  temporal para evitar una copia parcial si ocurre un fallo inesperado.

## Decisión: perfiles nombrados de workers

- Un perfil describe **cómo ejecutar un worker**, no qué tarea debe hacer:
  familia, modelo solicitado y nivel de esfuerzo.
- La skill conserva la autoridad sobre rol, prompt, permisos y límites de escritura. Un perfil no
  puede elevar permisos por sí mismo.
- Las políticas de cada skill referencian perfiles y definen cardinalidad:
  candidatos, éxitos deseados, mínimo aceptable y preferencia de diversidad entre familias.
- Selector propuesto:
  1. Resolver override conversacional > `.specify/config.yml` > defaults de la skill.
  2. Filtrar perfiles que no estén disponibles.
  3. Preferir familias distintas cuando la política lo solicite.
  4. Lanzar hasta el objetivo configurado.
  5. Continuar si se alcanza el mínimo; declarar degradación parcial cuando no se alcanza el
     objetivo.
- Un modelo explícito que no está disponible vuelve ese perfil `UNAVAILABLE`; no se reemplaza
  silenciosamente por otro modelo. `model: default` sí delega la elección al proveedor.
- El coordinador recibe metadata efectiva por worker: profile, familia, modelo solicitado y
  resuelto, esfuerzo, transporte, estado, duración y rutas de artefactos.
- La semántica exacta de `effort` debe validarse por proveedor. Un adaptador no debe ignorar una
  opción incompatible sin avisar.

Ejemplo conceptual aceptado; los valores concretos todavía deben validarse por proveedor:

```yaml
cross_model:
  schema_version: 1
  coordinator: pure
  transport: auto
  profiles:
    claude-deep:
      family: claude
      model: sonnet
      effort: high
    codex-deep:
      family: codex
      model: default
      effort: high

co_explore:
  workers:
    profiles: [claude-deep, codex-deep]
    target_success: 2
    min_success: 1
    family_diversity: prefer
```

## Decisión: resolución de transporte

- `auto` es el default: prefiere Herdr y degrada silenciosamente a CLI cuando Herdr no está
  instalado, el proceso no corre dentro de Herdr o el runtime no es alcanzable.
- `herdr`: intenta Herdr; si no está disponible o el proceso no está dentro de Herdr, avisa al
  usuario y usa CLI.
- `cli`: usa CLI directamente y no sondea Herdr.
- Separar `desired` de `effective`: cada proceso resuelve su transporte efectivo según su propia
  vista de disponibilidad; no hereda ciegamente el resultado del proceso padre.
- Señales mínimas para considerar Herdr disponible:
  1. binario en `PATH`;
  2. `HERDR_ENV=1`;
  3. socket/runtime alcanzable;
  4. comandos requeridos disponibles en la versión instalada.
- Degradación segura:
  - fallo de preflight o antes de entregar el prompt → se puede usar CLI;
  - fallo después de una entrega posible o confirmada → no relanzar por CLI hasta demostrar que no
    quedó un worker vivo, para evitar ejecución duplicada.
- Se confirmó que `auto` solo es silencioso antes de entregar el prompt. Un dispatch incierto
  siempre se notifica y entra en recuperación/cancelación antes de habilitar otro transporte.

## Decisión: core portable y Herdr opcional

- El core semántico es caller-owned y transport-neutral. Conserva políticas, perfiles, contexto,
  manifest, correlación, output contracts, quorum, recuperación, sincronización y cleanup.
- Herdr es el adaptador operativo preferido, no una dependencia obligatoria. Administra
  workspaces/panes, agentes frescos, prompts, waits, inspección, restore, notificaciones y
  worktrees cuando está disponible.
- Los adaptadores provider CLI ejecutan `claude -p` o `codex exec` como fallback headless con el
  mismo contrato semántico y de salida.
- Sin Herdr, todas las capacidades semánticas siguen disponibles. Solo el traslado interactivo
  hacia un worktree puede requerir abrir una sesión nueva mediante el handoff persistido.
- El primer vertical slice será Herdr CLI-first. Socket API y plugins quedan como mejoras
  posteriores de observabilidad, no como dependencias del core.

## Decisión: ciclo de vida de runs y workers

- Separar tres identidades:
  - `run`: una solicitud del caller, por ejemplo una co-exploración.
  - `worker`: una asignación lógica a un perfil.
  - `attempt`: un lanzamiento concreto de ese worker por Herdr o CLI.
- Un worker puede tener varios attempts por retry o fallback, pero solo uno abierto a la vez.
  Workers distintos sí pueden correr en paralelo.
- La frontera de dispatch se registra como:
  - `dispatchAcknowledgedAt`: el transporte confirmó que envió el prompt al recurso;
  - `executionObservedAt`: opcional, se observó al agente trabajando.
- El acknowledgement no demuestra que el modelo procesó el prompt. Política:
  - fallo confirmado antes de cualquier entrega posible → otro attempt puede usar CLI;
  - acknowledgement recibido → no hay redispatch hasta cerrar o recuperar el attempt;
  - respuesta de acknowledgement perdida → `uncertain`; tampoco hay redispatch, porque el prompt
    pudo haberse entregado.
- Estados canónicos de attempt:
  - abiertos: `starting`, `running`, `blocked`, `cancelling`, `uncertain`;
  - cerrados: `completed`, `failed`, `timed-out`, `cancelled`.
- `completed` exige transporte cerrado correctamente, envelope correlacionado, output parseable y
  paridad entre IDs del índice y del informe. `done`/`idle` de Herdr o exit code 0 del CLI no son
  evidencia suficiente por sí solos.
- Estado derivado del run:
  - `ready`: éxitos >= objetivo;
  - `partial`: mínimo alcanzado, pero no el objetivo;
  - `failed`: hubo dispatches, pero no se alcanzó el mínimo;
  - `unavailable`: ningún worker llegó a dispatch;
  - `cancelled`: cancelación confirmada de todos los recursos;
  - `recovery-required`: existe un attempt posiblemente despachado cuyo cierre no pudo
    demostrarse.
- `recovery-required` tiene precedencia sobre `partial`/`ready`: no se finaliza ni se limpia hasta
  resolver el recurso incierto.
- Persistencia caller-owned:
  - el caller elige el directorio del run;
  - el coordinador es el único escritor del manifest;
  - los workers solo producen resultados;
  - el estado mutable se publica con `tmp → rename`;
  - un manifest parcial nunca equivale a éxito;
  - al cerrar se publica un manifest terminal inmutable.
- El manifest guarda metadata, estados, referencias y hashes de artefactos; no prompts completos,
  razonamiento interno ni transcripciones.
- Se confirmó que `recovery-required` bloquea cierre, cleanup y redispatch aunque otro worker ya
  haya alcanzado `min_success`.

## Decisión: lease del coordinador

- Cada run tiene un único coordinador owner. El lease identifica al owner mediante:
  - `ownerId` UUID;
  - host;
  - PID e instante de inicio del proceso;
  - `generation`.
- El PID es diagnóstico, no autoridad única: puede reutilizarse.
- Defaults aceptados:
  - heartbeat cada 10 segundos;
  - expiración después de 45 segundos sin heartbeat.
- Un owner nunca renueva un lease que ya expiró. Debe detener sus escrituras y dejar el run en
  recuperación.
- La adquisición inicial del lease es exclusiva y atómica.
- Protocolo de takeover:
  1. comprobar que el lease expiró;
  2. verificar la identidad y liveness del coordinador anterior;
  3. si continúa vivo, bloquear el takeover y marcar `recovery-required`;
  4. si está muerto, adquirir el lease de forma exclusiva e incrementar `generation`;
  5. reconstruir attempts y recursos desde los handles durables del manifest antes de cualquier
     redispatch.
- Cada escritura del manifest registra `ownerId` y `generation`. El runtime rechaza una
  publicación cuya identidad no coincida con el lease vigente.
- En la fase 1, el lease solo previene coordinadores simultáneos. El takeover automático y la
  recuperación completa se implementan en la fase 5.
- Se acepta que un coordinador colgado pero todavía vivo requiera intervención. Es más seguro que
  permitir dos coordinadores sobre el mismo run.

## Decisión: paquete de contexto canónico

- Cada `run` crea una versión inmutable del contexto semántico. Todos los workers independientes
  reciben la misma base; los adaptadores solo traducen la forma de entrega para Herdr o cada CLI.
- Separar:
  - `input/task.md`: solicitud canónica legible por humanos;
  - `input/context.json`: metadata, restricciones, referencias y hashes;
  - metadata propia del `attempt`: correlación y transporte, sin alterar el contenido de la tarea.
- `task.md` conserva siempre el texto relevante exacto del usuario, sanitizado, junto con una
  lista numerada de restricciones y decisiones. No incluye la conversación completa.
- `context.json` incluiría:
  - versión del contrato y hash del paquete;
  - `runId`, identidad lógica del worker y datos de correlación del attempt;
  - objetivo, modo, rol, alcance y fuera de alcance;
  - permisos, comandos permitidos, deadline y política de preguntas;
  - snapshot del repositorio: `cwd`/worktree, rama, commit y estado esperado;
  - hechos observados y su procedencia, separados de hipótesis;
  - referencias repo-relative a spec, plan, ticket, logs, ADRs y código relevante;
  - versión del contrato de salida, presupuesto y prueba requerida cuando corresponda.
- Los archivos accesibles desde el mismo checkout se referencian; no se incrustan dumps extensos.
  Una referencia externa que el worker no pueda leer debe copiarse de forma sanitizada.
- Excluir del paquete: razonamiento interno, hipótesis previas del coordinador, resultados de otro
  worker durante una ronda independiente, secretos y contexto irrelevante.
- Anti-anclaje:
  - en una co-exploración, ambos workers reciben el mismo paquete y no conocen otros hallazgos;
  - en `debate`, la ronda inicial es independiente y las rondas posteriores reciben deltas
    explícitos con las posturas que deben contrastar;
  - `cross-review` sí recibe el artefacto a criticar porque forma parte de su tarea.
- Una aclaración o nueva evidencia no muta el paquete en curso: crea una versión nueva con otro
  hash. Si cambia el `HEAD` o el árbol deja de cumplir el snapshot, el run queda obsoleto y debe
  reiniciarse o declararse explícitamente no reproducible.
- El worker devuelve `runId`, `workerId`, `attemptId` y `contextHash`. La correlación válida exige
  además que la salida provenga del recurso de transporte registrado para ese attempt.
- El manifest guarda la ruta y el hash del paquete, no una copia del prompt ni transcripciones.
- Ubicación propuesta:
  - SDD: `.plans/<id>/cross-model/runs/<run-id>/`;
  - uso standalone: directorio scratch elegido por la skill llamadora.

## Decisión: aclaraciones centralizadas por el coordinador

- El coordinador es el único interlocutor con el usuario. Los workers no preguntan directamente
  ni compiten por decisiones desde sus terminales.
- En exploración y revisión, un worker no se bloquea por dudas menores: continúa con supuestos
  explícitos y registra las incógnitas en su informe.
- Una ambigüedad que impide continuar produce `clarification-needed`, con la pregunta concreta,
  su impacto y el supuesto seguro disponible si existe.
- El coordinador intenta resolverla primero desde el paquete de contexto o el repositorio. Si
  requiere una decisión humana, formula la pregunta al usuario.
- La respuesta crea una nueva versión inmutable del paquete de contexto; no modifica el paquete
  que ya recibió el worker. Solo se reanuda el worker afectado cuando corresponda.
- En implementación, una duda estructural indica que el work order no estaba realmente congelado:
  se detiene antes de escribir y se devuelve el control al gate de diseño.

## Decisión: reintentos y degradación parcial

- Un fallo confirmado anterior a cualquier entrega posible permite fallback automático porque no
  existe trabajo semántico duplicado.
- Si el prompt fue despachado y el attempt falla de forma confirmada, no se repite ciegamente toda
  la tarea.
- Si el trabajo terminó pero el reporte no cumple el contrato, se permite una sola ronda de
  reparación de formato en la misma sesión viva; no se rehace la exploración.
- Un attempt incierto entra en `recovery-required` y no habilita retry ni fallback hasta resolver
  el recurso original.
- Si uno de dos workers deseados entrega un resultado válido y se cumple `min_success`, el run
  queda `partial`. El coordinador puede sintetizarlo, pero declara la diversidad reducida y no lo
  presenta como consenso.
- En modo coordinador puro, el coordinador no reemplaza al worker faltante ejecutando su tarea.
- Fallback de transporte, reparación del output y retry semántico son operaciones distintas y
  deben registrarse por separado.

## Decisión: índice paginado sin pérdida

- El presupuesto de salida limita el tamaño de cada entrada y página, no la cantidad total de
  hallazgos. Nunca se truncan hallazgos para cumplir un límite global.
- Cada hallazgo conserva su ID estable, impacto, confianza, resumen y referencias de evidencia.
- Defaults propuestos:
  - resumen por hallazgo: máximo 240 caracteres;
  - página: máximo 25 entradas.
- Al superar el tamaño de una página se crean páginas adicionales. Un metaíndice registra las
  rutas, cantidades e IDs de todas las páginas.
- La skill puede ajustar esos defaults según su tarea, pero no eliminar la paridad entre índice y
  detalle.
- El coordinador consume el índice compacto completo y abre detalles solo mediante los
  disparadores acordados.

## Investigación verificada: frontera de Herdr

- Informe completo: [`herdr-research.md`](./herdr-research.md).
- Herdr resuelve gran parte del plumbing operativo: topología de workspaces/tabs/panes, arranque
  de agentes frescos, entrega de prompts, waits, lectura, snapshots, restore, notificaciones y
  worktrees.
- Sus estados son señales semánticas de la interfaz, no prueba de finalización válida. Para
  Claude y Codex, incluso con sus integraciones, Herdr conserva screen detection como autoridad
  del lifecycle. `idle`/`done` solo habilitan cosecha y validación.
  Fuente: <https://herdr.dev/docs/agents/#status-authority>.
- Los waits observan estado semántico y fijan el ocupante del pane para evitar que un proceso
  reemplazante satisfaga el wait. No validan el resultado del trabajo.
  Fuente: <https://herdr.dev/docs/socket-api/#waiting-for-state>.
- El camino Herdr debe usar `herdr worktree create/open/remove`:
  - `create` crea o reutiliza la rama, crea el checkout y lo abre como workspace;
  - `open` abre un checkout existente;
  - `remove` ejecuta `git worktree remove`, no elimina la rama y exige `--force` si Git rechaza
    un árbol sucio.
  Fuente: <https://herdr.dev/docs/cli-reference/#worktrees>.
- Esto adapta, pero no invalida, la política transport-neutral:
  - adaptador Herdr → primitivas nativas de Herdr;
  - fallback CLI → Git directo;
  - core propio → base/path, allowlist untracked, snapshots, conflictos, branch cleanup y
    `cleanup-blocked`.
- Herdr permite configurar su raíz de worktrees, pero el runtime puede pasar `--path` para
  respetar el valor resuelto desde `.specify/config.yml`.
  Fuente: <https://herdr.dev/docs/configuration/#worktrees>.
- `session.snapshot`, eventos e identidad nativa ayudan a reconstruir recursos tras una
  interrupción, pero no sustituyen el manifest caller-owned ni aportan idempotencia semántica.
- Dispatch recomendado:
  1. `agent prompt` sin wait para obtener el acknowledgement `agent_prompted`;
  2. registrar `dispatchAcknowledgedAt`;
  3. registrar `executionObservedAt` si Herdr observa actividad;
  4. ejecutar `agent wait` por separado, que fija el ocupante resuelto del pane;
  5. cosechar y validar los artefactos estructurados.
- Si se pierde la respuesta del primer paso, el attempt queda `uncertain`: la entrega atómica no
  demuestra que el cliente haya recibido el acknowledgement.
- Registrar por attempt: agent name, `pane_id`, `terminal_id` y native session ref. El nombre del
  agente es efímero y no sirve como identidad durable.
- Herdr no documenta `agent.cancel`; la recuperación debe inspeccionar snapshot/proceso, intentar
  interrupción suave y confirmar la ausencia del recurso antes de redispatch.
- El restore nativo puede reanudar conversaciones Claude/Codex. Una sesión restaurada representa
  el mismo attempt; no es un worker fresco.
  Fuente: <https://herdr.dev/docs/session-state/#native-agent-session-restore>.
- El live handoff es experimental y orientado a updates/remote attach; no conserva requests,
  waits, subscriptions ni mensajes en vuelo. No debe usarse como handoff lógico de un flujo.
  Fuente: <https://herdr.dev/docs/session-state/#live-handoff>.
- Las named sessions crean servidores y runtimes separados. No se necesita una por run; un
  workspace por flujo es suficiente como default.
  Fuente: <https://herdr.dev/docs/persistence-remote/#named-sessions>.
- Corte recomendado por la investigación:
  - core propio: perfiles, políticas, contexto, manifest, correlación, outputs, quorum,
    recuperación, sincronización y cleanup;
  - adaptador Herdr CLI-first: panes/agentes, prompts, waits, inspección, worktrees, restore y
    notificaciones;
  - adaptadores provider CLI: fallback headless con el mismo contrato;
  - socket/plugins: mejora posterior de observabilidad, no dependencia del primer vertical slice.
- El preflight Herdr debe comprobar binario, `HERDR_ENV=1`, servidor y protocolo compatibles, y
  presencia de las capacidades requeridas en el CLI/schema instalado.

## Decisión: etiquetas de diversidad efectiva

- Se conserva `cross-model` como nombre general de la capacidad.
- La diversidad se calcula solo desde los resultados válidos de workers; la familia del
  coordinador puro no añade evidencia independiente.
- Etiquetas:
  - `cross-family`: resultados válidos de al menos dos familias;
  - `same-family`: varios resultados válidos, todos de una familia;
  - `single-worker`: un único resultado válido.
- La etiqueta de diversidad es independiente del estado del run (`ready`, `partial`, etc.).
- La síntesis habla de convergencia o divergencia entre resultados, no de consenso.

## Resultado del debate: convergencias por validar

- El comportamiento común debe vivir en un runtime versionado y ejecutable —CLI o librería—, no
  solo en texto duplicado entre skills. Las skills conservan roles, políticas y prompts.
- Separar dos ejes:
  - `outcome`: `ready`, `partial` o `failed`;
  - `lifecycle`: `settled` o `recovery-required`.
  Un resultado read-only válido puede entregarse aunque su lifecycle exija recuperación; esto no
  autoriza redispatch ni cleanup del run incierto.
- Declarar capacidades por adaptador, al menos: `resumable`, `outputRepair`, `codeAccess` y
  `outputChannel`.
- Camino provider CLI propuesto: worker read-only, resultado por `stdout` y persistencia a cargo
  del coordinador.
- Camino Herdr propuesto: acceso read-only al código y permiso de escritura limitado a un archivo
  o directorio de salida asignado. La pantalla del terminal no es un canal durable.
- Conservar todos los hallazgos en disco, pero entregar al coordinador un metaíndice acotado. Las
  `comparisonKeys` solo generan pares candidatos para comparar: el runtime no declara divergencia.
  Hallazgos de alto riesgo, baja confianza o sin clave siempre deben aparecer.
- Distinguir dentro del paquete de contexto el texto y la evidencia exactos de la interpretación
  derivada por el coordinador. Compartir el mismo framing reduce, pero no elimina, el sesgo común
  entre workers.
- El cleanup de ramas requiere `branchCreatedByRun=true`. Un valor ausente o desconocido se trata
  como `false`.
- Cada run guarda un snapshot de la configuración resuelta para evitar divergencias entre el
  checkout principal y el worktree.
- Los campos de lifecycle quedan provisionales y versionados hasta validar sus equivalencias en
  Herdr y provider CLI.

Estas convergencias provienen del debate arquitectónico. Todavía no se consideran decisiones
aceptadas individualmente, salvo el lease y el rollout por fases descritos en sus secciones.

## Decisión: entrega durable y visible de informes con Herdr

- Esta regla aplica cuando el transporte efectivo es Herdr.
- Antes del dispatch, el core asigna una ruta de informe dentro del directorio durable del run.
- El worker genera el informe completo una sola vez. El archivo es la fuente autoritativa y los
  mismos bytes se proyectan en la terminal para que el usuario pueda observarlos; no se solicita
  al modelo que regenere ni resuma el informe para un segundo canal.
- La respuesta operativa al coordinador es un sobre pequeño con estado o veredicto, ruta,
  cantidad de bytes y hash del informe.
- El coordinador valida identidad, root, ruta, marcadores, tamaño y hash, y luego lee el archivo
  una sola vez. El viewport de Herdr es observabilidad humana, no evidencia durable.
- `/private/tmp` queda reservado para reparación manual o fallback; no es el canal formal de una
  corrida.
- La skill define el rol, prompt, permisos y contrato de salida; el perfil define familia,
  modelo y esfuerzo; el adaptador Herdr impone el canal de salida.
- Las revisiones manuales largas vía Herdr adoptan esta regla desde ahora. La automatización
  reusable del adaptador se implementará en la fase dedicada a Herdr.

## Decisión: ubicación instalable del runtime

- El runtime vivirá en `skills/cross-model-runtime/`.
- Mantendrá la anatomía normal del repositorio (`SKILL.md`, `reference.md`, `README.md`) y sus
  ejecutables vivirán bajo `assets/`.
- Motivo: la unidad de instalación actual es la skill. Un runtime en un directorio raíz separado
  no viajaría al instalar las skills consumidoras.
- Trade-off aceptado: las skills que migren declararán una dependencia explícita hacia
  `cross-model-runtime`.
- La fase foundation crea el paquete y sus assets, pero no migra todavía ninguna skill
  consumidora.

## Preguntas abiertas

- Escritura concurrente: decidir el bloqueo por `working_dir` antes de migrar `cross-implement`.
- Comparación: definir un vocabulario cerrado de `comparisonKeys`; una clave inválida debe
  degradar a hallazgo sin clave y siempre visible.
- Síntesis: con comparación acotada solo puede afirmarse “sin divergencias en los pares
  comparados”, no convergencia total.
- Métricas: definir cómo medir ahorro de contexto, calidad de síntesis, fallos y costo operativo
  antes de promover una fase.

## Decisión: rollout completo por fases

- Se mantiene la visión completa, pero se entrega mediante fases pequeñas y reversibles.
- Invariante de compatibilidad: al cerrar cada fase, todas las skills deben quedar al menos tan
  utilizables como antes. Una migración no puede bloquear el flujo de trabajo actual.
- La selección de backend ocurre antes del dispatch. Después de una entrega posible nunca se
  cambia silenciosamente de adapter ni se duplica el trabajo.
- Orden aceptado:
  1. **Foundation runtime, sin cambio de comportamiento**: walking skeleton con un worker provider
     CLI, paquete de contexto, manifest mínimo con lease, canal de salida y validator. Las skills
     existentes siguen usando su camino actual.
  2. **Provider CLI + `co-explore`**, entregado en tres incrementos utilizables:
     - **2A — Paridad de providers**: agregar el adapter Codex al foundation runtime y verificar
       `caller → Codex worker`, sin migrar skills ni romper el camino Claude.
     - **2B — Fan-out y síntesis**: ejecutar dos workers provider CLI, arbitrar sus resultados y
       registrar etiquetas de diversidad, todavía sin cambiar el comportamiento de `co-explore`.
     - **2C — Primer consumer real**: migrar `co-explore explore` al coordinador puro y conservar
       temporalmente un escape explícito al camino legacy.
  3. **Read-only completo**: migrar los demás modos de `co-explore` y luego `cross-review`.
     - **CRR-FU-1 — resuelto en Fase 3B**: `collect`/`decision` confirman un snapshot inmutable por
       transición, `terminal` referencia esos mismos bytes, los punteros públicos se mueven
       después de ambos commits y handoff rechaza cadenas incompletas. Las regresiones cubren
       crash, reentrada y revalidación multi-round.
  4. **Adapter Herdr**: agregar Herdr como adapter preferido sin retirar provider CLI.
  5. **Recovery y fallback**: incorporar lifecycle incierto, recuperación, resume y fallback
     seguro con equivalencias ya medidas en ambos adapters.
  6. **Worktrees SDD opcionales**: bootstrap, sync, archive y cleanup. Permanecen desactivados por
     default hasta validar el ciclo completo.
  7. **`cross-implement`**: migrar al final, después de definir exclusión de writers, proof y
     recuperación para operaciones con escritura.
- Cada promoción exige métricas y pruebas de compatibilidad. Un gate fallido detiene la promoción
  y mantiene la fase anterior utilizable; no descarta por sí solo la arquitectura completa.
- El runtime ejecutable convierte este repositorio en software con costo de tests, versionado y
  CI. Ese costo debe justificarse desde la fase 1 con mediciones reales.

### Uso progresivo del foundation runtime

- **Fase 2A:** reutiliza inmediatamente request, snapshot, contexto, lease, manifest, envelope,
  captura, validación y control de procesos de la fase 1; solo agrega selección de provider y el
  adapter Codex.
- **Fase 2B:** el coordinador llama dos veces a esa frontera de un worker, con runs independientes,
  y sintetiza los dos resultados sin meter fan-out dentro del runtime.
- **Fase 2C:** `co-explore explore` se convierte en la primera skill consumidora del runtime. Hasta
  entonces, la fase 1 y 2A se usan mediante tests y smokes reales, mientras las skills actuales
  conservan sus caminos legacy.

### Estrategia SDD para esta iniciativa

- Cada fase se ejecuta como un flujo `sdd-flow` independiente, con su propio `spec.md`, `plan.md`,
  `tasks.md`, gates y verificación.
- Excepción explícita para esta iniciativa: todas las fases reutilizan la misma rama
  `feat/herdr-cli-cross-model` y el mismo checkout. No se crea una rama por fase ni se vuelve a
  `main` entre ellas.
- Las fases son estrictamente secuenciales. Antes de iniciar una, la anterior debe estar
  verificada y su estado base debe quedar identificado; no se ejecutan dos fases en paralelo sobre
  la rama compartida.
- El paso `create-branch` de cada flujo se resuelve validando y reutilizando la rama existente.
  Si la rama activa no coincide, el flujo se detiene en vez de crear otra silenciosamente.
- Cada carpeta SDD puede archivarse por separado después de su verificación y aprobación, aunque
  la rama permanezca abierta para las fases posteriores.
- Durante una fase, `sdd-flow` se apoya en la última capacidad promovida como estable. La
  funcionalidad candidata se prueba de forma explícita y no reemplaza el camino estable hasta
  superar sus criterios de aceptación.
- Esta excepción no cambia el comportamiento general futuro de `sdd-flow`: aplica solo al
  desarrollo de la arquitectura cross-model.

## Enfoques descartados o que deben evitarse

- Portar completa la implementación de `feat/cross-model-real-sessions`.
- Acoplar la arquitectura a detalles de terminales, boot o cosecha propios de Orca.
- Confiar en el reporte del worker como evidencia final sin verificación del conductor.
- Convertir al conductor en un simple concatenador de respuestas.
- Obligar a crear worktrees para tareas read-only que pueden compartir un checkout estable.
- Marcar una revisión same-family como equivalente a una revisión entre familias distintas.

## Registro de conversación

### 2026-07-23

- Se decidió avanzar de forma incremental: primero entender el objetivo y los límites; después
  formalizar la spec.
- Se pausó el lanzamiento de `co-explore` hasta aclarar la intención arquitectónica.
- Se identificó como motivación principal reducir el consumo de contexto del conductor mediante
  workers frescos Claude+Codex.
- Se propuso conservar CLI, evaluar Herdr como adaptador más simple y separar la gestión de
  worktrees del transporte.
- Se decidió probar directamente el coordinador puro con selección flexible de workers: misma
  familia, otra familia o ambas según tarea y disponibilidad.
- Si ningún worker inicia, el coordinador puro devuelve `UNAVAILABLE`; no ejecuta silenciosamente
  la tarea.
- Se decidió ejecutar cada fase con un flujo SDD independiente, pero mantener toda esta iniciativa
  sobre la rama compartida `feat/herdr-cli-cross-model`.
