# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Repositorio de **autoría de Agent Skills** (formato open de https://agentskills.io). No es una app: no hay build ni runtime. El "código" son skills en Markdown que instalás en `~/.claude/skills/` y que Claude Code (u otro cliente compatible) carga bajo demanda. El idioma de todos los artefactos es **español neutro** (ver preferencias globales del usuario).

Las skills forman un ecosistema **cross-model** (Claude ↔ Codex) y de **Spec-Driven Development (SDD)**. El concepto central que atraviesa todo: hay **solo dos familias** de modelos, Claude y GPT/Codex. El modelo que conduce (el "conductor", autor del plan/exploración) delega en un modelo de **la otra familia** para obtener una opinión o implementación independiente, y luego sintetiza o revisa. Nunca decir "otro modelo" a secas: es "la otra familia".

> **Excepción acotada — topología dual de `co-explore`.** En sus modos `explore`, `counter-plan` e `investigate`, `co-explore` despacha **dos workers, uno por familia**, así que uno comparte la del conductor. Es válido **solo ahí**, porque el conductor deja de ser una voz: no produce mapa, arbitra, y la diversidad se conserva entre **los dos mapas que se comparan**. La excepción **no** alcanza al revisor de `cross-review`, al implementador de `cross-implement` ni al modo `debate` de la propia `co-explore` —donde el conductor sí es voz—: ahí hay una sola salida delegada y la familia opuesta es lo único que rompe la correlación de errores.

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
- El baseline de ese verificador vive en `scripts/baseline-sobre-en-vuelo.md`: correr `python3 scripts/verificar-sobre-en-vuelo.py --validar-baseline` para comprobarlo y `--ac 16` para la no-regresión del cierre de los intentos.
- Para verificar el retiro del transporte descartado, correr `python3 scripts/verificar-retiro-transporte.py` con `--ausencia`, `--clave`, `--adaptadores`, `--drenaje`, `--vocabulario`, `--docs` y `--autotest`. El modo `--vias` aún no está implementado y no cuenta como guarda.
- Si la skill toca el cuerpo de un bloque `# @bloque:` que tiene variante `-ps`, correr `python3 scripts/verificar-paridad-powershell.py --reporte`: ejecuta las dos variantes sobre entradas equivalentes y compara clase, eventos, stdout y artefactos. Un cuerpo cambiado **invalida su cobertura** hasta auditar la matriz de casos y renovar el registro con `--registrar-auditoria --par <nombre>`; el alcance cubierto y el declarado sin matriz viven en `scripts/paridad-casos/alcance.json`.

  > **El código de salida de `--reporte` NO es la señal de salud: hoy devuelve 4 y ese es el estado sano.** Un bloque que corta con `exit 99` sobre una entrada inexistente es un error de invocación y no un incumplimiento, pero AC-3 clasifica como `fallo` cualquier código distinto de 0 y 1, y `fallo` domina la precedencia global. La señal es el cuerpo del reporte: **cero `divergencia`, cero `incumplimiento_comun`, cero `no_comprobable`, y `fallo` solo en los pares que declaran un caso de ese tipo** — hoy son cinco (`gate-fase-3`, `integracion-ownership`, `orchestration-contract`, `orchestration-model`, `orchestration-state`), cada uno con sus casos de entrada inexistente y `clase_esperada: fallo`. Un `fallo` en un caso que no lo declara sí es rojo. Las que se leen por código de salida son las **nueve** guardas propias del arnés (`--auditar-catalogo`, `--auditar-matrices` y los **siete** `--autotest-*`): 0 en verde, 4 en rojo. Las banderas `--estricto-mono-causa`, `--exigir-particiones`, `--afirmar-particiones` y `--testigos-centinela` **no** son guardas independientes: corren la suite y devuelven ese mismo 4, así que verificar con ellas exige diffear su reporte contra el de `--reporte` puro.
- Si la skill toca los artefactos de la matriz de despachos o del contrato de fase 0
  (`scripts/matriz-despachos.json`, `scripts/matriz-despachos.schema.json`,
  `docs/superpowers/specs/2026-08-09-subagentes-perfiles-fase-0.md`, `scripts/artefactos-fase-0.json`,
  `scripts/guardas-fase-0.json`, `scripts/nombres-reservados-perfil.json`), correr
  `python3 scripts/verificar-matriz-despachos.py --integracion`. Es un script propio del repo —no un
  modo agregado a ninguno de los cuatro anteriores— y el código de salida sano de esta invocación es
  0. El modo comprueba, contra el árbol real, que la bandera documentada exista y sea invocable, que
  el código de salida declarado coincida con el que devuelve, y que todo baseline acoplado al
  contenido de un archivo que la fase haya alterado quede renovado: hoy el único es
  `scripts/baseline-sobre-en-vuelo.md`, verificado corriendo
  `python3 scripts/verificar-sobre-en-vuelo.py --validar-baseline`.
- Si la skill toca el instrumento de medición de la fase 0 o cualquiera de los artefactos
  que mide (`scripts/instrumento-baseline.py`, `scripts/runner-cohorte.py`, los tres
  schemas `scripts/observacion.schema.json`, `scripts/bundle-corrida.schema.json` y
  `scripts/preregistro.schema.json`, `scripts/metricas-fase-0.json`,
  `scripts/recetas-cohorte.json`, `scripts/superficies-de-egreso.json`,
  `scripts/interfaz-de-reloj.json`, `scripts/dag-procedencia.json`,
  `scripts/preregistro-fase-0.json`, `scripts/intentos-fase-0.json`,
  `scripts/presupuesto-de-recoleccion-fase-0.json`, `scripts/baseline-fase-0.md` o los
  corpus de `scripts/fixtures-baseline/`), correr su batería completa empezando por
  `python3 scripts/instrumento-baseline.py --validar-schemas`. Es un **script propio** del
  repo —no un modo agregado a ninguno de los cinco anteriores— y el código de salida sano
  es 0 en las 34 invocaciones. Los otros tres que leen los datos reales del acto son
  `--vocabulario-metricas`, `--recetas` y `--fixture-historico`. La autocomprobación son
  `--autotest-aislamiento`, `--autotest-bundles`, `--autotest-canonicalizacion`,
  `--autotest-clasificacion`, `--autotest-cobertura`, `--autotest-derivacion`,
  `--autotest-egreso`, `--autotest-escaneo`, `--autotest-generacion`,
  `--autotest-guardas-previas`, `--autotest-hallazgos`, `--autotest-identidad-congelada`,
  `--autotest-identidad-entorno`, `--autotest-integracion`, `--autotest-latencias`,
  `--autotest-ledger`, `--autotest-muestras-intentos`, `--autotest-preregistro`,
  `--autotest-procedencia-dag`, `--autotest-procedencia-portada`, `--autotest-promocion`,
  `--autotest-recetas`, `--autotest-recoleccion`, `--autotest-recomposicion`,
  `--autotest-recursos`, `--autotest-reloj`, `--autotest-sanitizacion`, `--autotest-schemas` y
  `--autotest-vocabulario`. Y `--integracion` comprueba,
  contra el árbol real, que esta misma unidad siga siendo cierta: que la bandera que
  documenta exista, sea invocable y devuelva el código que acá se declara.

  > **La familia de autotests no se puede declarar con comodín en esta unidad, y por eso
  > van nombradas una por una.** La expansión de una familia se deriva de los
  > `add_argument` literales que el parser del script declara, y este instrumento arma el
  > suyo desde una tabla `registrar_modo(...)`: la derivación devuelve el conjunto vacío,
  > así que un comodín acá daría `familia_vacia` y pondría la guarda en rojo. La lista no
  > envejece porque el instrumento está congelado; si alguna vez deja de estarlo, lo que
  > hay que arreglar es la derivación, no esta unidad.

- Si la skill toca los cuatro insumos congelados del oráculo de la Fase 0.5 o cualquiera de sus
  guardas (`scripts/corpus-dossier.json`, `scripts/casos-extraccion.json`,
  `scripts/oraculo-cobertura.json`, sus tres `*.schema.json`, `scripts/oraculo-evidencia/`,
  `scripts/corpus-elegibles.json`, `scripts/pathset-parser.json`,
  `scripts/oraculo-prompt.plantilla.md`, `scripts/verificar-oraculo.py`,
  `scripts/oraculo-elegibilidad.py` o los corpus de `scripts/fixtures-oraculo/`), correr su batería
  completa empezando por `python3 scripts/verificar-oraculo.py --insumos`. Es un **script propio**
  del repo —no un modo agregado a ninguno de los anteriores— y el código de salida sano es 0 en las
  33 invocaciones. Los otros catorce modos productivos son `--consumidor`, `--proyecciones`,
  `--invariantes-corpus`, `--casos`, `--casos-obligatorios`, `--forma-oraculo`, `--exclusiones`,
  `--proxies`, `--adjudicacion`, `--cobertura-deteccion`, `--evidencia`, `--prompt`,
  `--adaptadores` y `--gate-precommit`. La autocomprobación son `--autotest-adaptadores`,
  `--autotest-adjudicacion`, `--autotest-casos`, `--autotest-casos-obligatorios`,
  `--autotest-cobertura-deteccion`, `--autotest-consumidor`, `--autotest-elegibilidad`,
  `--autotest-evidencia`, `--autotest-exclusiones`, `--autotest-forma-oraculo`,
  `--autotest-gate-precommit`, `--autotest-insumos`, `--autotest-invariantes-corpus`,
  `--autotest-lectura-unica`, `--autotest-prompt`, `--autotest-proxies` y
  `--autotest-proyecciones`. La trigésimo tercera es el predicado de elegibilidad, que es su propio
  comando: `python3 scripts/oraculo-elegibilidad.py --listar`, y hoy emite **21** flujos.

  > **`--gate-precommit` y su autotest están declarados y excluidos del manifiesto de guardas, y el
  > motivo va escrito ahí.** Su veredicto depende del working tree, no de la salud del repo: es la
  > comprobación 2 de R9 para el commit de `dossier-oraculo`, que ya ocurrió. En `dossier-arnes`,
  > que **sí** toca el parser, darán rojo por diseño, y dejarlos dentro de la no-regresión ataría
  > una guarda ajena a esa transición legítima. Se corren igual cuando se toca el pathset; lo que
  > no hacen es formar parte del conjunto que la no-regresión ejecuta.

  > **La familia de autotests no se puede declarar con comodín en esta unidad, y por eso van
  > nombradas una por una.** Es el mismo motivo que en el instrumento de la fase 0: la expansión de
  > una familia se deriva de los `add_argument` literales que el parser del script declara, y este
  > validador arma el suyo desde una tabla `registrar_modo(...)`, así que la derivación devuelve el
  > conjunto vacío y un comodín daría `familia_vacia`. La lista envejece con el archivo: cada task
  > que agregue un modo lo agrega también acá.

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

**Escalera de rigor.** Las fronteras dicen *qué* hace cada una; la escalera dice *cuál alcanza*:
respuesta local → `co-explore` (mapa, causa raíz o decisión) → `cross-review` (crítica de una
decisión escrita) → `cross-implement` (construcción desde contrato congelado) → `verify` de
`sdd-flow` (evidencia por AC). La pregunta al elegir no es cuál es la mejor sino **cuál es la más
barata que alcanza**. Canónica en `co-explore/reference.md` → "Escalera de rigor".

Regla de fronteras entre skills (aparece repetida en las descripciones y hay que preservarla): `co-explore` explora/hipotetiza · `cross-review` revisa documentos de diseño · `cross-implement` escribe código · `systematic-debugging` arreglar bugs · code review sobre diffs. No solapar.

## Invocación cross-model (el mecanismo compartido)

Cuando conduce Claude, la otra familia es **Codex**; el detalle canónico vive en cada `reference.md`. La delegación viaja por el **CLI headless**: el worker se lanza como proceso hijo y su salida se cosecha del disco. Patrón:

- **Detección de binario:** POSIX `command -v codex` · PowerShell `Get-Command codex -ErrorAction SilentlyContinue`.
- **Read-only** (co-explore, cross-review): `codex exec -s read-only -C <working_dir> --skip-git-repo-check --json ...`
- **Workspace-write** (cross-implement): `codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json ...`; resume con `codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write" ...`
- **`exec resume` NO acepta las mismas flags que `exec`** — rechaza `-C`, `-s`/`--sandbox`, `--add-dir` y cinco más. Por eso el sandbox viaja como `-c sandbox_mode=...`, y el working dir **es el cwd del proceso**: hay que posicionarse antes de invocar. Copiar el comando de lanzamiento y cambiarle el subcomando falla; y la flag que falta no siempre grita —`-C` de más corta con error, `-C` de menos opera sobre el repo equivocado con exit 0—. Tabla derivada del CLI en `cross-review/reference.md` → "Asimetría de flags entre `exec` y `exec resume`".
- **Prompt por archivo, nunca inline:** el markdown con backticks rompe el quoting del shell. POSIX pasa el prompt por `< prompt.txt`; **PowerShell no soporta `<`** → `Get-Content -Raw prompt.txt | codex exec ... -`. Todo comando nuevo que invoque un CLI debe ofrecer **ambas** variantes (POSIX y PowerShell).
- Degradación elegante: si falta el binario/MCP, avisar y continuar con lo que haya.

## Artefactos en disco (dogfooding)

Las skills SDD escriben artefactos **locales y untracked** (nunca se commitean): `.specify/config.yml` + `constitution.md` por proyecto, y `.plans/<id>/` por flujo. **Este repo se desarrolla a sí mismo con esas skills:** `.superpowers/sdd/` contiene los artefactos SDD (briefs, reports, diffs de review) usados para construir las propias skills, y `docs/superpowers/{specs,plans}/` guarda specs y planes de diseño versionados. Al retomar trabajo, esos archivos son la memoria del flujo.

## Git

- Conventional commits con **scope = nombre de la skill** afectada: `feat(sdd-flow): ...`, `fix(co-explore): ...`, `docs(sdd-flow): ...`. Un commit que toca varias skills lo indica en el cuerpo (ej: `fix: ... (co-explore) y ... (sdd-flow)`).
- Sin líneas `Co-Authored-By` ni firmas al pie (preferencia global del usuario).
