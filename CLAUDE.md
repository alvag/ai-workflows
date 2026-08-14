# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Repositorio de **autoría de Agent Skills** (formato open de https://agentskills.io). No es una app: no hay build ni runtime. El "código" son skills en Markdown que instalás en `~/.claude/skills/` y que Claude Code (u otro cliente compatible) carga bajo demanda. El idioma de todos los artefactos es **español neutro** (ver preferencias globales del usuario).

Las skills forman un ecosistema **cross-model** (Claude ↔ Codex) y de **Spec-Driven Development (SDD)**. El concepto central que atraviesa todo: hay **solo dos familias** de modelos, Claude y GPT/Codex. El modelo que conduce (el "conductor", autor del plan/exploración) delega en un modelo de **la otra familia** para obtener una opinión o implementación independiente, y luego sintetiza o revisa. Nunca decir "otro modelo" a secas: es "la otra familia".

> **Familia opuesta y salida consciente.** La familia opuesta sigue siendo la **doctrina y el
> default** de `cross-review`, `cross-implement` y `debate`: es la que rompe la correlación de
> errores. `cross_model.families` puede elegir explícitamente un worker fresco de la misma familia
> que el conductor. Esa **salida consciente** conserva independencia de proceso, pero pierde
> diversidad de familia; la corrida debe nombrar ese costo y recomendar revisión humana. En la
> topología dual de `co-explore`, la diversidad se mide entre los workers seleccionados y el
> conductor solo arbitra.

## El techo de la verificación (tres reglas, no negociables)

El producto de este repo son las skills. La verificación es **medio**, no producto. Sin un techo
explícito, el endurecimiento de guardas no tiene condición de salida: cada guarda barata que resulta
mentirosa se responde endureciéndola, endurecer produce Python, Python produce fixtures, fixtures
producen sellos, y los sellos producen guardas que verifican sellos. Estas tres reglas son ese techo.
Cada una lleva **disparador, efecto y excepción**: un enunciado sin las tres no es aplicable.

### Regla 1 — escalera de evidencia

> **Disparador:** al escribir una fila del contrato de verificación.
> **Efecto:** usar el escalón más barato que alcance —inspección documentada → `grep`/`rg` de una
> línea → bloque de shell → script—. El default es `grep`.
> **Excepción:** subir un escalón exige escribir **por qué el anterior no alcanza**, y no vale
> "podría fallar": vale *falló, acá está el caso*.

### Regla 2 — techo de proporción

> **Disparador:** al cerrar `implement`, **antes** del gate de revisión manual.
> **Efecto:** si `numerador > denominador`, **el flujo se detiene**.
> **Excepción:** continúa solo con excepción aprobada por el usuario en ese gate, con el cálculo y
> el motivo a la vista.

- **Numerador** — líneas **agregadas** a `scripts/`, más las agregadas a cualquier archivo cuyo
  propósito declarado sea verificar. **Las líneas agregadas a un script existente cuentan igual que
  un archivo nuevo**: si no, la regla 3 se evade engordando lo que ya está.
- **Denominador** — líneas **agregadas** a `skills/` en el mismo diff.
- **Borrados** — no entran al numerador. Retirar andamiaje nunca puede violar el techo.
- **Denominador cero** — si el flujo no agrega ni una línea a `skills/`, el numerador debe ser
  **cero**.
- **Cuándo se mide** — con `git diff --numstat <base_commit>` **después de implementar**. Medirlo en
  el gate de tasks daría cero en ambos términos: ahí todavía no se tocó una línea.
- **Por qué bloquea** — un techo que solo obliga a declarar es un techo **sin condición de salida**,
  que es exactamente la causa que estas reglas vienen a cortar.

### Regla 3 — ningún archivo nuevo en `scripts/` dentro de un flujo de skills

> **Disparador:** al crear un archivo bajo `scripts/` durante un flujo cuyo objeto son las skills.
> **Efecto:** no se crea. Si de verdad hace falta, es un **flujo aparte**, con su propio gate y con
> la evidencia de que la guarda barata falló.
> **Excepción:** ninguna dentro del flujo en curso. La escalada es una decisión con gate propio, no
> un atajo a mitad de una task.

## Anatomía de una skill (patrón obligatorio del repo)

Cada `skills/<nombre>/` tiene tres archivos, alineados con la **divulgación progresiva** de agentskills.io:

- **`SKILL.md`** — frontmatter + instrucciones que se cargan al **activar** la skill. Es lo que el agente lee y ejecuta.
- **`reference.md`** — detalle técnico pesado (matrices de detección, invocación de CLIs, casos borde, PowerShell vs POSIX). Se carga **solo cuando el SKILL.md lo indica explícitamente** ("ver `reference.md` → sección X"). Acá va lo que no se necesita en cada corrida.
- **`README.md`** — documentación para humanos (qué hace, cuándo usarla, instalación). No lo lee el agente en ejecución.

**La capa de referencia puede ser más de un archivo.** Cuando el detalle de una skill se lee en
**momentos distintos**, se parte en varios `.md` hermanos de `reference.md` (el patrón `pptx` de
agentskills.io, con su `pptxgenjs.md` y su `ooxml.md`). El criterio de corte es el momento de
lectura, no el tamaño: cargar en cada corrida un documento que solo hace falta cuando algo falla es
desperdiciar contexto. `cross-implement` es el caso vivo — `reference.md` (toda corrida),
`contrato-verificacion.md` (antes de delegar) y `ownership.md` (cuando una ronda falla)—, y su
`reference.md` abre con una tabla que dice cuál se lee cuándo. `SKILL.md` y `README.md` siguen
siendo **uno** por skill.

Al crear o editar skills, seguí las buenas prácticas de agentskills.io (referencia pedida explícitamente):
- **Specification:** https://agentskills.io/specification — `name` (== nombre del directorio, minúsculas/números/guiones, sin guion inicial/final ni `--`), `description` (máx 1024 chars, tercera persona, qué hace **y cuándo** usarla, con keywords de trigger).
- **Best practices:** https://agentskills.io/skill-creation/best-practices — SKILL.md idealmente <500 líneas / <5000 tokens; mover el detalle a `reference.md`; dar **un default, no un menú**; secciones "Gotchas" y "red flags"; procedimientos reutilizables, no respuestas puntuales.
- Validar con `skills-ref validate ./skills/<nombre>` (de https://github.com/agentskills/agentskills).
- Si la skill toca `config-ejemplo.md` o `manifest-ejemplo.md`, o el esquema/"Configuración" de alguno de sus cinco dueños (`sdd-flow`, `sdd-orchestrator`, `cross-review`, `co-explore`, `cross-implement`), correr `python3 scripts/verificar-vistas-config.py`: valida que esas vistas sigan fieles a sus dueños (claves, enums, valores, marcas `[def]`/`[ej]`/`[obl]` y comillas en `on`/`off`).
- Si la skill toca `corridas-en-vuelo.md`, correr `python3 scripts/verificar-sobre-en-vuelo.py --sincronizar` y después `--ac 13`. Ese archivo es **contenido replicado**: la sede canónica es `skills/cross-review/corridas-en-vuelo.md` y las otras seis son copias byte-idénticas generadas. **Editar una copia a mano es una divergencia silenciosa**; el generador la evita y el hash la detecta.
- El baseline de ese verificador vive en `scripts/baseline-sobre-en-vuelo.md`: correr `python3 scripts/verificar-sobre-en-vuelo.py --validar-baseline` para comprobarlo y `--ac 16` para la no-regresión del cierre de los intentos. Su identidad se ata al `sha256` del propio verificador, así que **tocar el `.py` obliga a re-emitir el bloque `#### Baseline de vN`** —el validador lee la versión mayor— con el commit evaluado y los estados **medidos**, no asumidos.
- Si la skill toca la sección "Corridas delegadas en vuelo" de algún `SKILL.md` —donde vive el inventario de los **once** puntos de despacho—, correr además `python3 scripts/verificar-sobre-en-vuelo.py --ac 12`: verifica biyección entre lo declarado en el árbol y el inventario del verificador, así que agregar o retirar un punto de despacho sin actualizarlo la pone roja.
- **Un retiro corre la batería completa, no el subconjunto documentado.** `verificar-sobre-en-vuelo.py` tiene **19 modos `--ac`** y las unidades de arriba nombran **tres**; los otros dieciséis existen, corren y pueden ponerse rojos sin que ningún procedimiento los invoque. Al **retirar** algo —una vía, un modo, una capacidad— hay que correr los diecinueve (`for m in 1 1b 2 2b 3 3b 4 5 6 7 8 9 10 11 12 13 14 15 16`), porque retirar es la operación que **arrastra cláusulas ajenas**: el texto que rodea a lo que se va se lleva puesto lo que no era suyo, y lo que queda **se lee perfecto**. Ya pasó: el retiro del transporte por panes borró una cláusula de doctrina que vivía dentro de un párrafo sobre esa vía, `--ac 1b` la cazó en el acto, y estuvo roja **noventa commits** porque nadie la corría.
- Las **cinco** invocaciones de `verificar-sobre-en-vuelo.py` que se leen por código de salida son `--validar-baseline`, `--ac 12`, `--ac 13`, `--ac 16` y `--autotest`: **0 en verde**. Las de `verificar-vistas-config.py` (sin banderas) y las **nueve** propias de `verificar-paridad-powershell.py` (`--auditar-catalogo`, `--auditar-matrices` y los siete `--autotest-*`), lo mismo. La única que **no** se lee por código de salida es `--reporte`, abajo.
- Si la skill toca el cuerpo de un bloque `# @bloque:` que tiene variante `-ps`, correr `python3 scripts/verificar-paridad-powershell.py --reporte`: ejecuta las dos variantes sobre entradas equivalentes y compara clase, eventos, stdout y artefactos. Un cuerpo cambiado **invalida su cobertura** hasta auditar la matriz de casos y renovar el registro con `--registrar-auditoria --par <nombre>`; el alcance cubierto y el declarado sin matriz viven en `scripts/paridad-casos/alcance.json`.

  > **El código de salida de `--reporte` NO es la señal de salud: hoy devuelve 4 y ese es el estado sano.** Un bloque que corta con `exit 99` sobre una entrada inexistente es un error de invocación y no un incumplimiento, pero AC-3 clasifica como `fallo` cualquier código distinto de 0 y 1, y `fallo` domina la precedencia global. La señal es el cuerpo del reporte: **cero `divergencia`, cero `incumplimiento_comun`, cero `no_comprobable`, y `fallo` solo en los pares que declaran un caso de ese tipo** — hoy son cinco (`gate-fase-3`, `integracion-ownership`, `orchestration-contract`, `orchestration-model`, `orchestration-state`), cada uno con sus casos de entrada inexistente y `clase_esperada: fallo`. Un `fallo` en un caso que no lo declara sí es rojo. Las que se leen por código de salida son las **nueve** guardas propias del arnés (`--auditar-catalogo`, `--auditar-matrices` y los **siete** `--autotest-*`): 0 en verde, 4 en rojo. Las banderas `--estricto-mono-causa`, `--exigir-particiones`, `--afirmar-particiones` y `--testigos-centinela` **no** son guardas independientes: corren la suite y devuelven ese mismo 4, así que verificar con ellas exige diffear su reporte contra el de `--reporte` puro.

> Nota: varios SKILL.md de este repo (p. ej. `sdd-flow`) exceden holgadamente el presupuesto de tokens sugerido. Es una tensión conocida por la complejidad del flujo; al editar, empujá contenido hacia `reference.md` antes que engordar el SKILL.md.

## Convenciones de frontmatter propias del repo

Más allá del spec, estas skills usan patrones consistentes que hay que respetar:

- **`description` como router:** describe modos, frases de invocación literales ("/co-explore ...", "que Codex explore esto"), **scoping negativo** ("NO es code review: eso es X") y casi siempre la cláusula **"No invocarla espontáneamente: solo ante pedido explícito del usuario o invocada por <skill>"**. Es deliberado: evita auto-triggers no deseados.
- **`disable-model-invocation: true`** (clave real de Claude Code) en las skills que deben ser **solo-slash** (`sdd-flow`, `sdd-orchestrator`, `sdd-pr-feedback`): bloquea la invocación vía Skill tool porque sus triggers son genéricos ("arma el plan", "implementa") y competirían por el auto-trigger. Consecuencia asumida y documentada en el propio frontmatter: otras skills no pueden invocarlas programáticamente (delegan leyendo sus archivos).
- **`argument-hint`** documenta la gramática de sub-comandos del router (init / implement / retoma / estado / doctor…).

## El ecosistema de skills

- **`sdd-flow`** — SDD de un solo repo, punta a punta: `constitution → gather-context → specify → clarify → create-branch → plan → tasks → implement → verify`, con gates escalados por complejidad (trivial/normal/complejo). Es la skill más grande y el hub del que dependen las demás.
- **`sdd-orchestrator`** — SDD multi-repo: un objetivo que cruza 2+ repos bajo una carpeta contenedora; arma spec madre, reparte un sub-plan por repo y delega cada uno a `sdd-flow`.
- **`sdd-pr-feedback`** — procesa comentarios de review de PRs de **Bitbucket** (MCP `bb_*`).
- **`co-explore`** — exploración paralela cross-model (read-only). Modos: `explore`, `counter-plan`, `investigate`, `debate`. La invocan `sdd-flow`/`sdd-orchestrator` cuando `co_explore` está activo; `investigate`/`debate` son standalone.
- **`cross-review`** — segunda opinión adversarial sobre **artefactos de diseño** (spec/plan/tasks), no sobre código. Modo `draft` cuando hay idea pero no artefacto.
- **`cross-implement`** — delega la implementación de un work order **congelado** a la otra familia; el conductor revisa el diff como un PR ajeno y commitea tras el gate humano.
- **`bitbucket-code-review`** — code review de PRs de **Bitbucket** (MCP `bb_*`): panel de revisores externos **uno por familia disponible**, author-aware, sobre el diff del PR; publica la decisión con gate. Es la sede de "code review sobre diffs" de la regla de fronteras.
- **`sdd-incident-intake`** — admisión del registro de incidentes: verifica un incidente contra el árbol, agrupa los que se resolverían en el mismo diff, abre un worktree sembrado con la config ignorada, despacha un `sdd-flow` y recién entonces retira los incidentes tomados. **No corrige la skill** —eso es el `sdd-flow` que despacha—: es el único punto donde `.plans/incidentes-skills.md` se vacía.

**Escalera de rigor.** Las fronteras dicen *qué* hace cada una; la escalera dice *cuál alcanza*:
respuesta local → `co-explore` (mapa, causa raíz o decisión) → `cross-review` (crítica de una
decisión escrita) → `cross-implement` (construcción desde contrato congelado) → `verify` de
`sdd-flow` (evidencia por AC). La pregunta al elegir no es cuál es la mejor sino **cuál es la más
barata que alcanza**. Canónica en `co-explore/reference.md` → "Escalera de rigor".

Regla de fronteras entre skills (aparece repetida en las descripciones y hay que preservarla): `co-explore` explora/hipotetiza · `cross-review` revisa documentos de diseño · `cross-implement` escribe código · `systematic-debugging` arreglar bugs · code review sobre diffs. No solapar.

> **«Code review sobre diffs» sí tiene skill —`bitbucket-code-review`— y el único punto ciego que sobrevive es el del autor del contrato.** Conviene tenerlo preciso porque es fácil enunciarlo de más. Quién mira un diff, y contra qué familia:
>
> | Revisor | ¿De otra familia que quien escribió el código? |
> |---|---|
> | `bitbucket-code-review` · panel externo del Paso 7 | **sí** — author-aware por contrato, uno por familia disponible. Requiere PR de Bitbucket y su MCP: es post-push |
> | `cross-implement` · el conductor (regla 4) | **sí** — la regla 8 manda que implemente la otra familia, así que el conductor revisa código que no escribió su familia |
> | `sdd-flow` · revisión final de diff | **no** — mismo modelo, y su sección lo declara |
>
> Lo que **ninguno** cubre es el par **autor del work order ↔ revisor del diff**, que en `cross-implement` es la misma familia: si el contrato se escribió ambiguo o mal, el implementador lo transcribe fielmente y el revisor comparte el punto ciego que lo produjo. Es un hueco **estrecho y de una sola clase** —no "nadie revisa diffs cross-family"—, y **hoy no se escribe nada para cubrirlo**: se mide en vez de discutirse. El log de `cross-implement` registra la clase de cada falla y si el work order admitía otra lectura, y **la condición exacta para reabrirlo vive ahí mismo**, junto al registro que la alimenta (`cross-implement/reference.md` → "Qué hacer cuando el registro muestre algo"). No se repite acá a propósito: una condición escrita en dos lados se desincroniza. Lo que sí queda decidido de este lado, porque es lo que esta regla gobierna: si alguna vez se cubre, la sede es `cross-implement` y **no se crea una skill nueva** — sería una frontera nueva contra esta misma regla y competiría con `bitbucket-code-review`.

## Invocación cross-model (el mecanismo compartido)

Cuando conduce Claude, la otra familia es **Codex**; el detalle canónico vive en cada `reference.md`. La delegación viaja por el **CLI headless**: el worker se lanza como proceso hijo y su salida se cosecha del disco. Patrón:

- **Detección de binario:** POSIX `command -v codex` · PowerShell `Get-Command codex -ErrorAction SilentlyContinue`.
- **Read-only** (co-explore, cross-review): `codex exec -s read-only -C <working_dir> --skip-git-repo-check --json ...`
- **Workspace-write** (cross-implement): `codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json ...`; resume con `codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write" ...`
- **`exec resume` NO acepta las mismas flags que `exec`** — rechaza `-C`, `-s`/`--sandbox`, `--add-dir` y cinco más. Por eso el sandbox viaja como `-c sandbox_mode=...`, y el working dir **es el cwd del proceso**: hay que posicionarse antes de invocar. Copiar el comando de lanzamiento y cambiarle el subcomando falla; y la flag que falta no siempre grita —`-C` de más corta con error, `-C` de menos opera sobre el repo equivocado con exit 0—. Tabla derivada del CLI en `cross-review/reference.md` → "Asimetría de flags entre `exec` y `exec resume`".
- **Prompt por archivo, nunca inline:** el markdown con backticks rompe el quoting del shell. POSIX pasa el prompt por `< prompt.txt`; **PowerShell no soporta `<`** → `Get-Content -Raw prompt.txt | codex exec ... -`. Todo comando nuevo que invoque un CLI debe ofrecer **ambas** variantes (POSIX y PowerShell).
- Degradación elegante: si falta el binario/MCP, avisar y continuar con lo que haya.

> **El CLI headless es el transporte, y cambiarlo exige medirlo — no que la arquitectura sea más linda.** Cada tanto aparece un runtime que promete resolver esto mejor (paneles de terminal, IDEs agénticos con threads y salida estructurada, hosts multi-máquina). Encajan: el transporte está detrás de una abstracción en los `reference.md` de `co-explore` y `cross-implement`, así que sustituirlo es posible. El criterio para juzgarlos es **transporte contra criterio**: esos runtimes resuelven el transporte —lanzar, esperar, cosechar, reanudar, aislar—, y **ninguno tiene el criterio**: no saben si les están pidiendo un mapa o una crítica, y sobre todo **no tienen el invariante de familia opuesta** (se pueden lanzar dos workers del mismo proveedor y no se enteran). De ahí que lo único que se porta bien sea plomería, nunca doctrina.
>
> **La condición para adoptar uno:** una corrida real de `co-explore` con ese transporte contra la misma corrida por CLI, comparando **latencia, fidelidad de la cosecha y líneas de plomería**. Sin ese delta medido, no se adopta. El precedente que fija la regla: la vía de paneles costó **1.245 líneas y nunca se activó** —6 de 6 corridas se fueron por CLI— y se cerró con evidencia, no con opinión. Tampoco esperar un ahorro económico: todos corren sobre la misma suscripción vía CLI headless.

## Artefactos en disco (dogfooding)

Las skills SDD escriben artefactos **locales y untracked** (nunca se commitean): `.specify/config.yml` + `constitution.md` por proyecto, y `.plans/<id>/` por flujo. **Este repo se desarrolla a sí mismo con esas skills:** `.superpowers/sdd/` contiene los artefactos SDD (briefs, reports, diffs de review) usados para construir las propias skills, y `docs/superpowers/{specs,plans}/` guarda specs y planes de diseño versionados. Al retomar trabajo, esos archivos son la memoria del flujo.

### Registro de incidentes con las skills

**Todo incidente que tengas usando las skills SDD `sdd-flow` y sus skills hermanas (`cross-review`, `cross-implement`,
`co-explore`, `bitbucket-code-review`, `sdd-pr-feedback`) se registra en
`.plans/incidentes-skills.md`, en el momento en que ocurre.** Alcanza a las skills mismas, a los
artefactos que generan y a las instrucciones erróneas que contengan: una instrucción que produce
un artefacto que otra skill rechaza, un gate que se dispara sin salida practicable, una plantilla que no
coincide con lo que su validador exige, un paso cuyo orden vuelve imposible cumplir el siguiente.

**Siempre el archivo del árbol principal del repo, nunca el del worktree en el que estés
corriendo.** Como `.plans/` es local y untracked, un worktree no lo hereda: escribir ahí crea un
segundo registro que nadie lee y que desaparece cuando el worktree se remueve, y el archivo único es
justamente lo que permite ver que un incidente se repite. Si la sesión corre en un worktree, el
árbol principal se resuelve con `git worktree list` —es la primera entrada— y el registro va a
`<árbol-principal>/.plans/incidentes-skills.md`.

El destinatario del archivo es **el agente que va a corregir la skill**, no quien trabaja en el
proyecto donde se usó: nada de rutas ni artefactos del proyecto, sí la skill, la sección o regla
concreta, qué instruía frente a qué pasó, por qué el defecto es de la skill, la consecuencia y qué
habría que cambiar.

**Una reincidencia se agrega, nunca se edita.** Si el mismo defecto vuelve a aparecer, igual o
parecido, va un registro nuevo cruzado con el anterior por su fecha y hora en el campo
`Relacionado`. Editar el registro viejo para "actualizarlo" borra la frecuencia, que es lo único que
distingue una trampa estructural de la skill de un descuido puntual. Las reglas completas del
formato viven en la cabecera del propio archivo.

## Git

- Conventional commits con **scope = nombre de la skill** afectada: `feat(sdd-flow): ...`, `fix(co-explore): ...`, `docs(sdd-flow): ...`. Un commit que toca varias skills lo indica en el cuerpo (ej: `fix: ... (co-explore) y ... (sdd-flow)`).
- Sin líneas `Co-Authored-By` ni firmas al pie (preferencia global del usuario).
