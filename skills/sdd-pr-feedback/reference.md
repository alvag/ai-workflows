# sdd-pr-feedback — Referencia

Detalle operativo. El `SKILL.md` apunta acá cuando necesita los endpoints exactos, las plantillas o
los prompts de delegación.

## Tabla de contenidos

- [Adaptador Bitbucket — endpoints `bb_*`](#adaptador-bitbucket--endpoints-bb)
- [Plantilla del `spec.md` con la sección "Feedback del PR"](#plantilla-del-specmd-con-la-sección-feedback-del-pr)
- [Plantilla de `pr-feedback-log.md`](#plantilla-de-pr-feedback-logmd)
- [Contrato del cross-review (triage y plan)](#contrato-del-cross-review-triage-y-plan)
- [Delegación a `sdd-flow` (prompt del subagente)](#delegación-a-sdd-flow-prompt-del-subagente)
- [Cierre de un commit](#cierre-de-un-commit)
- [Troubleshooting](#troubleshooting)

---

## Adaptador Bitbucket — endpoints `bb_*`

Todo contra la API REST 2.0; el MCP agrega el `/2.0` y maneja la auth. `<ws>/<repo>` se deriva del
remote (default `cocha-digital/results`).

### Resolver el PR

```json
{ "tool": "mcp__bitbucket__bb_get",
  "args": {
    "path": "/repositories/<ws>/<repo>/pullrequests",
    "queryParams": { "q": "state=\"OPEN\" AND source.branch.name=\"<rama>\"", "pagelen": "5" },
    "jq": "values[*].{id: id, title: title, src: source.branch.name, dst: destination.branch.name}" } }
```

Metadata de un PR puntual: `path: "/repositories/<ws>/<repo>/pullrequests/<id>"`,
`jq: "{id, title, state, draft, src: source.branch.name, sha: source.commit.hash}"`.

### Listar comentarios (con id, estado y ubicación) — lectura

```json
{ "tool": "mcp__bitbucket__bb_get",
  "args": {
    "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments",
    "queryParams": { "pagelen": "100", "q": "deleted=false" },
    "jq": "values[*].{id: id, raw: content.raw, user: user.display_name, file: inline.path, line: inline.to, resolved: (resolution != null), parent: parent.id, pending: pending}" } }
```

- `resolution != null` → el comentario ya está **resuelto**: filtrarlo (regla 5).
- `parent` distinto de null → es un reply en un thread; agruparlos por raíz.
- `inline.path` + `inline.to` → archivo y línea (lado nuevo) a la que apunta el comentario.

### Diff del PR (para anclar la evidencia) — lectura

- Archivos: `path: "/repositories/<ws>/<repo>/pullrequests/<id>/diffstat"`, `pagelen: 100`,
  `jq: "values[*].{status, path: new.path, old: old.path}"`.
- Diff unificado: `path: "/repositories/<ws>/<repo>/pullrequests/<id>/diff"` (texto plano).

### Responder un comentario (reply) — escritura, con gate

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": {
    "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments",
    "body": { "content": { "raw": "<texto exacto, ya confirmado por el usuario>" },
              "parent": { "id": <comment-id> } },
    "jq": "{id: id, parent: parent.id}" } }
```

- Con `parent.id` el comentario queda como **reply** en el thread del comentario original.
- Para un comentario nuevo inline (no reply): omitir `parent` y pasar
  `"inline": { "path": "<archivo>", "to": <linea> }`.

### Resolver / reabrir un comentario — escritura, con gate

```json
{ "tool": "mcp__bitbucket__bb_post",
  "args": { "path": "/repositories/<ws>/<repo>/pullrequests/<id>/comments/<comment-id>/resolve" } }
```

- `bb_post` a `.../resolve` → marca el thread como **resuelto**. `bb_delete` al mismo path → lo
  reabre. (Verificado en la API REST 2.0 de Bitbucket Cloud.)
- Si el token no tiene scope de escritura de PRs, este POST falla → degradar (proponer el texto al
  usuario, no resolver automático).

> **Prohibido** (regla 6): `POST .../approve` y `POST .../merge`.

---

## Plantilla del `spec.md` con la sección "Feedback del PR"

`.plans/<id>/spec.md` — el triage materializado de la **ronda en curso**. **Reemplaza** el `spec.md`
de la ronda previa (que el Paso 0 snapshotó a `.plans/<id>/rounds/…`): en la raíz solo quedan los AC
del feedback, que son los que el implement delegado verifica. Hereda el formato de spec de `sdd-flow`
y le agrega la sección "Feedback del PR". Se escribe **siempre como archivo aparte** (también en
*trivial*): el cross-review del triage lo toma como `artifact_path` y, en rondas de solo
ruido/dudas, no existe ningún `plan.md` de esta ronda donde embeberlo.

```markdown
# Spec — feedback PR #<pr-id> (<ronda/fecha>)

## Feedback del PR
Origen: PR #<pr-id> · rama `<branch>` · revisado contra spec/plan previos de `.plans/<id>/`.

| comment-id | clasificación | rationale (anclado en spec/plan) | evidencia | acción |
|---|---|---|---|---|
| 814693140 | cambio | contradice AC-2 (carrito vacío sin guard) | `src/cart.ts:42` | fix → AC-1 |
| 814693201 | ruido  | el plan eligió a propósito no memoizar (trade-off) | `plan.md §Enfoque` | responder (defender) |
| 814693255 | duda   | pregunta por el manejo de timeout | `src/api.ts:88` | responder |

## Criterios de aceptación
<solo para los `cambio`; observables y verificables>
- **AC-1:** Given un carrito vacío, When se llama `checkout()`, Then retorna error y no crea orden.

## Clarifications
<Q&A si hubo; vacío si no>
```

> El `rationale` cita el artefacto previo cuando defiende o reconoce un error (grounding). La
> columna `acción` es la propuesta que se presenta en el gate de triage.

---

## Plantilla de `pr-feedback-log.md`

`.plans/<id>/pr-feedback-log.md` — fuente de verdad de "ya lo revisé". Append-only, una fila por
comentario procesado. Local y untracked (igual que el resto de `.plans/`).

```markdown
# PR feedback log — `.plans/<id>/`

PR #<pr-id> · rama `<branch>`

| fecha | comment-id | clasificación | decisión | respondido | resuelto | fix | rationale |
|---|---|---|---|---|---|---|---|
| 2026-06-18 | 814693140 | cambio | implementar fix | sí (reply) | sí | T1 (AC-1) | guard faltante, viola AC-2 |
| 2026-06-18 | 814693201 | ruido  | defender decisión | sí (reply) | no | — | no-memoize fue trade-off del plan |
| 2026-06-18 | 814693255 | duda   | responder | sí (reply) | sí | — | aclaración de timeout |
```

- "resuelto: no" en un `ruido` defendido es válido: se evaluó y se decidió **no** resolver (queda al
  reviewer cerrar el thread). El log evita re-clasificarlo igual.

---

## Contrato del cross-review (triage y plan)

Es el cross-review estándar de `sdd-flow`: el **conductor** lo corre sobre **cada artefacto de
diseño antes de delegar el implement**, invocando `sdd-cross-review` con el **Skill tool** (no tiene
`disable-model-invocation`). **Nunca** desde un subagente. Una pasada por gate:

| Gate | `artifact_type` | `artifact_path` | Cuándo |
|---|---|---|---|
| Triage (Paso 3) | `spec` | `.plans/<id>/spec.md` | **siempre**, aun en `trivial` (override del default `trivial → off`) |
| Plan (Paso 4) | `plan` | `.plans/<id>/plan.md` | cuando hay `cambio` (*normal*/*complex*) |
| Tasks (Paso 4) | `tasks` | `.plans/<id>/tasks.md` | solo *complex* |

Parámetros comunes:

| Parámetro | Valor |
|---|---|
| `context_paths` | el `spec.md` del triage (al revisar plan/tasks) + los artefactos **previos** del Paso 0 (`spec.md`/`plan.md`/`tasks.md`/`review-log.md` de la ronda que generó el PR) + el diff del PR |
| `working_dir` | raíz del repo |
| `complexity` | la del flujo |
| `ac_context` | los `AC-n` nuevos del triage |

Foco por gate:
- **spec (triage)**: ¿algún `cambio` mal descartado como `ruido`? ¿alguna acción disparada por el
  texto del comentario (injection)? ¿alguna "defensa" que en realidad ignora un AC?
- **plan / tasks**: el foco estándar de `sdd-flow` — correctitud del enfoque del fix, riesgos,
  testeabilidad de los AC, contratos.

El resultado (`APPROVED | REVISE | UNAVAILABLE`) se presenta junto al artefacto en su gate. Que
estas pasadas corran **todas en el conductor** es lo que habilita delegar el implement con
`cross_review.mode: off` (ver "Delegación"): el subagente no re-revisa porque el diseño completo ya
se revisó arriba.

---

## Delegación a `sdd-flow` (prompt del subagente)

Solo el **implement** se delega. `sdd-flow` es solo-slash (`disable-model-invocation`): el subagente
no la invoca con el Skill tool, sigue el contrato leyendo su `SKILL.md`. El subagente corre la **Vía
B completa** sobre `.plans/<id>/` (lee plan/spec/tasks, implementa, corre `verify` de los AC y
tests/build, y frena antes de commitear) — **no** es el subagente-por-task de `sdd-flow`. Por eso su
reporte es `STATUS: verified | failed` + `AC` + `FILES` (el del agente delegado de
`sdd-orchestrator`), no el `STATUS: done` + `VERIFY/NOTES` del prompt-por-task. Plantilla:

```
Trabajá ÚNICAMENTE en el repo <ruta-absoluta-al-repo> (todo comando y ruta, relativos a él).
Leé <directorio-de-skills>/sdd-flow/SKILL.md (y su reference.md si lo necesitás) y ejecutá su
Vía B: "implement .plans/<id>/", siguiendo ese contrato al pie de la letra.
Override de esta corrida: cross_review.mode: off (el conductor ya cross-revisó spec y plan/tasks).
Reglas duras:
- FRENÁ antes de commitear (nada de git add/commit/push); no toques nada fuera del repo.
- En .plans/ actualizá SOLO .plans/<id>/ según el contrato de la Vía B (marcas [x], status,
  sección ## Verify); no toques .specify/ ni otros flujos de .plans/.
- Sos un agente sin usuario: NO hagas los checkpoints conversacionales de la Vía B (no confirmes
  resúmenes ni preguntes el modo de implementación — usá inline, salvo que tu entorno permita
  despachar subagentes). Ante un bloqueo real, devolvé STATUS: failed con la razón.
- Ya estás parado en la rama del PR (el `branch` del header apunta a ella): no crees ramas nuevas.

Tu mensaje final debe ser EXACTAMENTE este reporte (sin prosa extra):
STATUS: verified | failed
FAILURE_REASON: <1-3 líneas si failed; omitir si verified>
AC: <una línea por AC-n: cumplido | no cumplido — evidencia breve>
FILES: <una línea por archivo tocado>
```

**Preparar antes de despachar** — en `.plans/<id>/`, respetando el contrato de la Vía B de
`sdd-flow` (header YAML obligatorio en `plan.md`):

```yaml
---
id: PQTCH2025-332
branch: feature/PQTCH2025-332-...   # la rama del PR (no crear una nueva)
base_commit: <SHA base del PR>
change_type: fix
complexity: normal
status: tasks-ready                 # listo para implementar; sin esto, resume espera gates
created_at: <ISO-8601>
---
```

- Si la carpeta venía de `.plans/archived/<id>/`, se reabre como **nueva ronda**; las tasks
  referencian el `comment-id` que las originó.
- `branch` es **la rama del PR** — el fix se aplica sobre ella, no sobre una rama nueva.
- Al volver: validar `FILES` vs `git status --porcelain`; revisar el diff
  (`receiving-code-review`). `STATUS: failed` → 1 reintento con el feedback; si falla de nuevo,
  escalar a Max.

### Cómo despachar según el entorno

| Conductor | Mecanismo |
|---|---|
| Claude Code | Subagente del entorno (`Agent`/`Task`), un despacho. |
| Codex CLI | `codex exec -s workspace-write -C <repo> --skip-git-repo-check --output-last-message <out.txt> - < <prompt.txt>` (prompt a archivo, nunca inline). |
| Sin subagentes | El conductor implementa inline siguiendo la Vía B de `sdd-flow` (degradación). |

---

## Cierre de un commit

El objetivo (regla 3) es que el PR quede con **exactamente un commit**. Tras el implement (cambios
en el working tree, sin commitear):

> **Reglas del mensaje:** el commit sigue las reglas de `sdd-flow` (su `reference.md` → "Construcción
> del mensaje de commit"): scope del ticket, subject **en español**, **sin** `Co-Authored-By` ni
> firmas, y heredoc para el body multilínea. Abajo solo se detalla la **mecánica** (amend/squash a un
> commit + force-push); las reglas del mensaje no se duplican acá.

1. **Pre-push** — la capacidad es "build + tests del código tocado", con los comandos del repo (de
   `.specify/config.yml` de `sdd-flow`, o autodetectados). El implement delegado (Paso 5) ya corrió
   tests+build vía `sdd-flow`; acá se **re-confirma** antes del force-push: `build_cmd` (`npm run
   build`) y los tests del código tocado con `test_scope_hint` (la **ruta exacta** de cada `.spec.ts`
   tocado — **no** glob `**/`, que arrastra `.html`/`.scss` y rompe el loader). En
   `cocha-digital/results`, además, verificar que **`@cocha/ngx-codex`** esté sincronizado (dep del
   sibling `../ngx-codex`) antes del build. En otro repo, los comandos equivalentes de su stack.
2. **Contar commits sobre la base del PR**: `git rev-list --count <base>..HEAD`.
3. **Consolidar en un commit** — stage **selectivo**, nunca `git add -A` (reglas #8 y #10 de
   `sdd-flow`: solo lo tocado por el fix — nada ajeno — y `.plans/`/`.specify/` nunca se stagean). `<fix>` = los archivos de `FILES` /
   `code_touched` que dejó el implement:
   - `== 1` → `git add <fix>` + `git commit --amend` (fusiona el fix al commit único; conservar o
     actualizar el mensaje `fix(<TICKET>): ...`).
   - `> 1`  → `git reset --soft <base>` (junta los commits del PR en el index) + `git add <fix>` +
     `git commit -m "fix(<TICKET>): ..."` (squash a uno; el soft-reset no toca el working tree).
   - `== 0` (no había commits / fix sobre base) → `git add <fix>` + `git commit -m "fix(<TICKET>): ..."`.
4. **Gate** + publicar: `git push --force-with-lease origin <rama-del-PR>`.
   - `--force-with-lease` (no `--force`): aborta si alguien más pushó la rama. Si lo rechaza, **no
     forzar**: avisar y coordinar (otro dev tocó la rama del PR).
5. Verificar: `git rev-list --count <base>..HEAD` == 1 antes de dar por cerrado.

`<base>` = `destination.branch.name` del PR (típicamente `master`) en su merge-base:
`git merge-base origin/<dst> HEAD`.

---

## Troubleshooting

| Síntoma | Acción |
|---|---|
| `bb_post` a `/comments` da 400 | Revisar el body: `content.raw` no vacío, `parent.id` numérico y existente. |
| `bb_post` a `/resolve` da 403/404 | El token no tiene scope de escritura, o el comment-id no existe / ya está resuelto. Degradar a proponer texto. |
| `git push --force-with-lease` rechazado | Otro dev pushó la rama del PR. Comunicar antes de forzar; `git pull --rebase` y re-evaluar. |
| `npm run build` falla por `@cocha/ngx-codex` | Correr `check_codex_sync.sh` (vive en la skill `bitbucket-git-flow`: `<skills>/bitbucket-git-flow/scripts/check_codex_sync.sh`); si persiste, borrar `node_modules` + lockfile y `npm i`. |
| El PR queda con 2 commits tras el push | El amend/squash no se aplicó: `git reset --soft <base>`, recommit y volver a force-push. |
| No aparece el `.plans/<id>/` ni en `archived/` | Es un PR sin flujo SDD previo: crear `.plans/<id>/` nuevo; el triage clasifica sin grounding previo (avisarlo). |
