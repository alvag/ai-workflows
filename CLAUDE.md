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

**Escalera de rigor.** Las fronteras dicen *qué* hace cada una; la escalera dice *cuál alcanza*:
respuesta local → `co-explore` (mapa, causa raíz o decisión) → `cross-review` (crítica de una
decisión escrita) → `cross-implement` (construcción desde contrato congelado) → `verify` de
`sdd-flow` (evidencia por AC). La pregunta al elegir no es cuál es la mejor sino **cuál es la más
barata que alcanza**. Canónica en `co-explore/reference.md` → "Escalera de rigor".

Regla de fronteras entre skills (aparece repetida en las descripciones y hay que preservarla): `co-explore` explora/hipotetiza · `cross-review` revisa documentos de diseño · `cross-implement` escribe código · `systematic-debugging` arreglar bugs · code review sobre diffs. No solapar.

## Invocación cross-model (el mecanismo compartido)

Cuando conduce Claude, la otra familia es **Codex**; el detalle canónico vive en cada `reference.md`. **Hay dos transportes** por los que puede viajar esa delegación, y el default es el **CLI headless**: el worker se lanza como proceso hijo y su salida se cosecha del disco. Patrón:

- **Detección de binario:** POSIX `command -v codex` · PowerShell `Get-Command codex -ErrorAction SilentlyContinue`.
- **Read-only** (co-explore, cross-review): `codex exec -s read-only -C <working_dir> --skip-git-repo-check --json ...`
- **Workspace-write** (cross-implement): `codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json ...`; resume con `codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write" ...`
- **Prompt por archivo, nunca inline:** el markdown con backticks rompe el quoting del shell. POSIX pasa el prompt por `< prompt.txt`; **PowerShell no soporta `<`** → `Get-Content -Raw prompt.txt | codex exec ... -`. Todo comando nuevo que invoque un CLI debe ofrecer **ambas** variantes (POSIX y PowerShell).
- Degradación elegante: si falta el binario/MCP, avisar y continuar con lo que haya.

**El segundo transporte es la vía de panes:** el worker se aloja en un pane de un multiplexor de terminales en vez de lanzarse headless. Cuatro principios, ninguno de los cuales baja a comandos:

- **Sustituye el transporte, no la semántica.** Las dos familias, quién revisa a quién, los estados del worker, los artefactos y la escalera de degradación siguen siendo los mismos y viven donde ya viven: cambia por dónde viaja el prompt y dónde vive el proceso, nada más.
- **Capacidad distinta de intención.** Que se pueda alojar un worker en un pane no significa que este flujo deba hacerlo: hacen falta las dos en verdadero, y la intención tiene sede durable en el config del proyecto, no en la conversación. Sin las dos, la vía de panes no se intenta y la corrida sigue por el CLI.
- **La sintaxis pertenece a la skill externa.** Este repo **no** copia los comandos del multiplexor: la autoridad son la skill externa `herdr` y el binario instalado, que se consultan en la sesión. El binario además **imprime su propia copia de esa skill** (`herdr --skill`), que es la forma de obtenerla ya apareada con la versión que corre en vez de con la que alguien instaló alguna vez. Copiar los comandos acá los congelaría desactualizados.
- **Adaptador por skill, sin copiar comandos.** Cada skill que delega tiene su `transporte-herdr.md`, hermano de `reference.md`, con lo único que cambia por el transporte; se lee **solo** cuando la activación resolvió a esta vía.

## Artefactos en disco (dogfooding)

Las skills SDD escriben artefactos **locales y untracked** (nunca se commitean): `.specify/config.yml` + `constitution.md` por proyecto, y `.plans/<id>/` por flujo. **Este repo se desarrolla a sí mismo con esas skills:** `.superpowers/sdd/` contiene los artefactos SDD (briefs, reports, diffs de review) usados para construir las propias skills, y `docs/superpowers/{specs,plans}/` guarda specs y planes de diseño versionados. Al retomar trabajo, esos archivos son la memoria del flujo.

## Git

- Conventional commits con **scope = nombre de la skill** afectada: `feat(sdd-flow): ...`, `fix(co-explore): ...`, `docs(sdd-flow): ...`. Un commit que toca varias skills lo indica en el cuerpo (ej: `fix: ... (co-explore) y ... (sdd-flow)`).
- Sin líneas `Co-Authored-By` ni firmas al pie (preferencia global del usuario).
