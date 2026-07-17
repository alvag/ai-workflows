# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Repositorio de **autoría de Agent Skills** (formato open de https://agentskills.io). No es una app: no hay build ni runtime. El "código" son skills en Markdown que instalás en `~/.claude/skills/` y que Claude Code (u otro cliente compatible) carga bajo demanda. El idioma de todos los artefactos es **español neutro** (ver preferencias globales del usuario).

Las skills forman un ecosistema **cross-model** (Claude ↔ Codex) y de **Spec-Driven Development (SDD)**. El concepto central que atraviesa todo: hay **solo dos familias** de modelos, Claude y GPT/Codex. El modelo que conduce (el "conductor", autor del plan/exploración) delega en un modelo de **la otra familia** para obtener una opinión o implementación independiente, y luego sintetiza o revisa. Nunca decir "otro modelo" a secas: es "la otra familia".

## Anatomía de una skill (patrón obligatorio del repo)

Cada `skills/<nombre>/` tiene tres archivos, alineados con la **divulgación progresiva** de agentskills.io:

- **`SKILL.md`** — frontmatter + instrucciones que se cargan al **activar** la skill. Es lo que el agente lee y ejecuta.
- **`reference.md`** — detalle técnico pesado (matrices de detección, invocación de CLIs, casos borde, PowerShell vs POSIX). Se carga **solo cuando el SKILL.md lo indica explícitamente** ("ver `reference.md` → sección X"). Acá va lo que no se necesita en cada corrida.
- **`README.md`** — documentación para humanos (qué hace, cuándo usarla, instalación). No lo lee el agente en ejecución.

Al crear o editar skills, seguí las buenas prácticas de agentskills.io (referencia pedida explícitamente):
- **Specification:** https://agentskills.io/specification — `name` (== nombre del directorio, minúsculas/números/guiones, sin guion inicial/final ni `--`), `description` (máx 1024 chars, tercera persona, qué hace **y cuándo** usarla, con keywords de trigger).
- **Best practices:** https://agentskills.io/skill-creation/best-practices — SKILL.md idealmente <500 líneas / <5000 tokens; mover el detalle a `reference.md`; dar **un default, no un menú**; secciones "Gotchas" y "red flags"; procedimientos reutilizables, no respuestas puntuales.
- Validar con `skills-ref validate ./skills/<nombre>` (de https://github.com/agentskills/agentskills).

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

Regla de fronteras entre skills (aparece repetida en las descripciones y hay que preservarla): `co-explore` explora/hipotetiza · `cross-review` revisa documentos de diseño · `cross-implement` escribe código · `systematic-debugging` arreglar bugs · code review sobre diffs. No solapar.

## Invocación cross-model (el mecanismo compartido)

Cuando conduce Claude, la otra familia es **Codex**; el detalle canónico vive en cada `reference.md`. Patrón:

- **Detección de binario:** POSIX `command -v codex` · PowerShell `Get-Command codex -ErrorAction SilentlyContinue`.
- **Read-only** (co-explore, cross-review): `codex exec -s read-only -C <working_dir> --skip-git-repo-check --json ...`
- **Workspace-write** (cross-implement): `codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json ...`; resume con `codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write" ...`
- **Prompt por archivo, nunca inline:** el markdown con backticks rompe el quoting del shell. POSIX pasa el prompt por `< prompt.txt`; **PowerShell no soporta `<`** → `Get-Content -Raw prompt.txt | codex exec ... -`. Todo comando nuevo que invoque un CLI debe ofrecer **ambas** variantes (POSIX y PowerShell).
- Degradación elegante: si falta el binario/MCP, avisar y continuar con lo que haya.

## Artefactos en disco (dogfooding)

Las skills SDD escriben artefactos **locales y untracked** (nunca se commitean): `.specify/config.yml` + `constitution.md` por proyecto, y `.plans/<id>/` por flujo. **Este repo se desarrolla a sí mismo con esas skills:** `.superpowers/sdd/` contiene los artefactos SDD (briefs, reports, diffs de review) usados para construir las propias skills, y `docs/superpowers/{specs,plans}/` guarda specs y planes de diseño versionados. Al retomar trabajo, esos archivos son la memoria del flujo.

## Git

- Conventional commits con **scope = nombre de la skill** afectada: `feat(sdd-flow): ...`, `fix(co-explore): ...`, `docs(sdd-flow): ...`. Un commit que toca varias skills lo indica en el cuerpo (ej: `fix: ... (co-explore) y ... (sdd-flow)`).
- Sin líneas `Co-Authored-By` ni firmas al pie (preferencia global del usuario).
