# cross-implement — Referencia

Detalle operativo de la skill `cross-implement`. El `SKILL.md` apunta acá para el descubrimiento
del implementador, las vías de invocación por familia, el prompt-contrato, la revisión del
conductor, el fix loop, los tiempos y los archivos de trabajo.

## Tabla de contenidos

- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Descubrir el implementador](#descubrir-el-implementador)
- [Vías de invocación](#vías-de-invocación)
- [Matriz de verificación](#matriz-de-verificación)
- [Transporte: rama `orca-session` (escritura acotada, sesión propia)](#transporte-rama-orca-session-escritura-acotada-sesión-propia)
- [Verification contract (normal/complex)](#verification-contract-normalcomplex)
- [Prompt del implementador](#prompt-del-implementador)
- [Formato del reporte](#formato-del-reporte)
- [Revisión del conductor](#revisión-del-conductor)
- [Triage de ownership](#triage-de-ownership)
- [Fix loop](#fix-loop)
- [Instrumentación con manifest](#instrumentación-con-manifest)
- [Latencia, deadlines y banner](#latencia-deadlines-y-banner)
- [Archivos de trabajo (scratch)](#archivos-de-trabajo-scratch)
- [Log de implementación](#log-de-implementación)

---

## Portabilidad entre shells (POSIX / PowerShell)

Mismo criterio que `cross-review/reference.md` → "Portabilidad entre shells": esa sección es
la fuente canónica de las equivalencias (detección de binarios, prompt por archivo a stdin, UUID,
background y kill). No se duplican acá. Regla invariante idéntica: el prompt **se escribe a
archivo con la tool Write** (nunca inline ni `echo`/heredoc) y llega por stdin.

## Descubrir el implementador

El algoritmo canónico de identificación de familia vive en `cross-review/reference.md` →
"Descubrir el revisor" (autor = la familia del agente que conduce, sin importar la superficie).
Acá cambia el rol buscado: no un crítico read-only sino un **implementador con escritura acotada**.

| Familia del autor | Implementador | Cómo detectarlo | Vía |
|---|---|---|---|
| Claude | Codex | `command -v codex` (PowerShell: `Get-Command codex -ErrorAction SilentlyContinue`) | Vía W-B (workspace-write) |
| GPT/Codex | Claude | `command -v claude` | Vía W-C (permisos path-scoped) |

**Prechequeos** — los mismos de `cross-review/reference.md` → "Descubrir el revisor" →
"Prechequeos" (versión del CLI, no pinear `-m`, eco del modelo activo), registrando el modelo en
el `implement-log.md`.

> **Vía A (subagente `codex:codex-rescue`) no aplica acá**: el contrato de ese runtime corre
> read-only para pedidos de review/diagnosis. Para implementar se usa el CLI directo (Vía W-B).

Sin implementador de la otra familia → `UNAVAILABLE` (regla 7 del `SKILL.md`).

## Vías de invocación

Dos reglas invariantes (además de las del `SKILL.md`):

1. **Escritura acotada por construcción, nunca por confianza**: sandbox `workspace-write` en
   Codex, permisos path-scoped en Claude. **Nunca** `--yolo` /
   `--dangerously-bypass-approvals-and-sandbox` / `--dangerously-skip-permissions` /
   `acceptEdits` sin scoping — ver la matriz de verificación: `acceptEdits` escribe fuera del
   working dir.
2. El prompt va por **stdin desde archivo** (tool Write), igual que en las skills hermanas.

### Vía W-B — Codex implementador (autor Claude)

- **Lanzamiento** (sesión fresca; captura del thread id igual que la Vía B de cross-review). El
  prelude `MCP_OFF` apaga por override dinámico los MCP del `config.toml` vigente (mismo prelude
  y racional que la Vía B de cross-review: el implementador no necesita MCPs — escribe con
  shell/archivos dentro del sandbox — y apagarlos ahorra ~la mitad del boot; config ilegible →
  sin overrides, fail-open):
  ```bash
  CODEX_CFG="${CODEX_HOME:-$HOME/.codex}/config.toml"
  # ARRAY, no string: zsh no splitea una variable sin comillas (el string entero llegaba como UN
  # argumento y Codex abortaba); la asignación de array splitea el $() en bash Y zsh:
  MCP_OFF=( $(sed -n 's/^[[:space:]]*\[mcp_servers\.\([A-Za-z0-9_-]*\)[].].*/\1/p' "$CODEX_CFG" 2>/dev/null \
    | sort -u | sed 's/.*/-c mcp_servers.&.enabled=false/') )
  codex exec "${MCP_OFF[@]}" -s workspace-write -C <working_dir> --skip-git-repo-check --json \
    --output-last-message <scratch>/report.txt - < <scratch>/prompt.txt \
    > <scratch>/thread.jsonl 2> <scratch>/impl.err.txt
  grep -m1 -o '"thread_id":"[^"]*"' <scratch>/thread.jsonl | cut -d'"' -f4 > <scratch>/session.txt
  ```
  En **PowerShell** (arreglo `$McpOff` construido igual que en la Vía B de cross-review):
  ```powershell
  $CodexCfg = Join-Path $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { "$HOME\.codex" }) 'config.toml'
  $McpOff = @()
  if (Test-Path $CodexCfg) {
    Select-String -Path $CodexCfg -Pattern '^\s*\[mcp_servers\.([A-Za-z0-9_-]+)[\].]' |
      ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique |
      ForEach-Object { $McpOff += @('-c', "mcp_servers.$_.enabled=false") }
  }
  Get-Content -Raw <scratch>\prompt.txt |
    codex exec @McpOff -s workspace-write -C <working_dir> --skip-git-repo-check --json `
      --output-last-message <scratch>\report.txt - > <scratch>\thread.jsonl 2> <scratch>\impl.err.txt
  (Select-String -Path <scratch>\thread.jsonl -Pattern '"thread_id":"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value > <scratch>\session.txt
  ```
- `-s workspace-write` limita las escrituras al `working_dir` **más `/tmp`** (por diseño del
  sandbox). Caveat: si el repo objetivo vive bajo `/tmp`, el borde efectivo es más laxo.
- **Fix round** (resume del MISMO thread; el override de sandbox es **obligatorio** — el modo de
  la sesión original no es garantía al reanudar, ver `cross-review/reference.md` → Vía B). El
  resume arranca un proceso nuevo (vuelve a bootear MCPs): lleva el mismo prelude `MCP_OFF`:
  ```bash
  SESSION_ID=$(cat <scratch>/session.txt)
  echo "resume → ${SESSION_ID:?vacío}"   # id vacío = sesión fresca silenciosa; cortar acá
  codex exec resume "$SESSION_ID" "${MCP_OFF[@]}" -c sandbox_mode="workspace-write" --skip-git-repo-check --json \
    --output-last-message <scratch>/report.txt - < <scratch>/fix-rN.txt \
    > <scratch>/thread-fix-rN.jsonl 2> <scratch>/impl.err.txt
  ```
  En **PowerShell**: mismo patrón que la Vía B de cross-review (pipe + `$SessionId` con guard),
  cambiando el valor del override a `workspace-write`.

### Vía W-C — Claude implementador (autor GPT/Codex)

La forma canónica acota la escritura con **permisos path-scoped** — `--permission-mode default`
deniega en headless toda tool fuera de `--allowedTools`, y las reglas `Edit(./**)`/`Write(./**)`
limitan la escritura al working dir:

- **Lanzamiento** (sesión fresca, con session id propio para el resume):
  ```bash
  SESSION_ID=$(uuidgen)   # Git Bash en Windows: ver "Portabilidad" de cross-review
  ( cd <working_dir> && claude -p --safe-mode --model sonnet --permission-mode default \
      --allowedTools='Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)' \
      --session-id "$SESSION_ID" \
      < <scratch>/prompt.txt ) > <scratch>/report.txt 2> <scratch>/impl.err.txt
  echo "$SESSION_ID" > <scratch>/session.txt
  ```
  En **PowerShell** (mismo patrón `Start-Process`/pipe que la Vía C de cross-review, con estas
  tools; entrecomillar el `--allowedTools=…` completo para que las comas no se parseen como array).
- **`Bash(<proof_bin>:*)`**: derivar el patrón del primer token de `proof_cmd` (p. ej.
  `proof_cmd: "node check.js"` → `Bash(node:*)`; `npm test` → `Bash(npm:*)`). Sumar los binarios
  de build/lint que el work order exija — la lista mínima que el contrato necesita, nunca `Bash`
  a secas.
- **NUNCA `--permission-mode acceptEdits`** como forma canónica: verificado que escribe **fuera**
  del working dir sin restricción (ver matriz). Tampoco `--dangerously-skip-permissions`.
- Las reglas `Edit(./**)`/`Write(./**)` son relativas al cwd: por eso el `cd <working_dir>`
  previo (o `Push-Location`) es parte del contrato, no cosmético.
- **Modelo**: default `sonnet` para implementación (velocidad; la calidad la garantiza el work
  order congelado + la revisión del conductor). Subir a `opus` es decisión consciente de la
  llamadora para work orders complejos.
- **Fix round** (mismo thread):
  ```bash
  ( cd <working_dir> && claude -p --safe-mode --model sonnet --permission-mode default \
      --allowedTools='Read,Grep,Glob,Edit(./**),Write(./**),Bash(<proof_bin>:*)' \
      --resume "$SESSION_ID" \
      < <scratch>/fix-rN.txt ) > <scratch>/report.txt 2> <scratch>/impl.err.txt
  ```
- Con conductor de exec corto (Codex ~120s): lanzar en background y pollear el `report.txt`
  buscando `STATUS: done` — mismo patrón BACKGROUND de `cross-review/reference.md` → "Latencia
  y timeout (Claude revisor)", con el deadline de esta skill.

## Matriz de verificación

Verificado end-to-end el 2026-07-09 (codex-cli 0.143.0; Claude Code local, `claude -p`):

| Prueba | Resultado |
|---|---|
| Codex `exec -s workspace-write`: implementa fix real, proof en verde, thread id capturado vía `--json` | OK |
| Codex workspace-write, borde (cwd fuera de `/tmp`): escribe adentro / deniega afuera | INSIDE OK · ESCAPE DENIED |
| Codex workspace-write con cwd bajo `/tmp`: `/tmp` entero es escribible (diseño del sandbox) | caveat documentado |
| Codex resume sin flag (config sin `sandbox_mode`): se comportó como la sesión original | OK pero **no garantizado** → override siempre |
| Codex resume + `-c sandbox_mode="workspace-write"` (fix round canónico) | escribe OK |
| Codex resume + `-c sandbox_mode="read-only"` (dirección restrictiva) | deniega OK |
| Claude `-p --permission-mode acceptEdits`: implementa, pero **escribe fuera del cwd** | descartada como forma canónica |
| Claude `-p --permission-mode default` + `Edit(./**),Write(./**),Bash(node:*)` (fresh): escribe adentro / deniega afuera / proof OK | OK |
| Ídem con `--resume` (fix round) | FIX OK · ESCAPE DENIED |
| Ambas vías lanzadas en background con redirección + poll | OK |

Flags pueden variar por versión: ante la duda, `codex exec --help` / `claude --help`.

## Transporte: rama `orca-session` (escritura acotada, sesión propia)

Alternativa a las Vías W-B/W-C de arriba ("Vías de invocación"): en vez de un subproceso headless
efímero, el conductor abre, con la skill-librería `cross-model-orca`, una **sesión interactiva
write propia** de la otra familia vía Orca, la deja implementar dentro del `working_dir`, y
**cosecha su reporte**. Es **aditiva**: las Vías W-B/W-C de arriba y su matriz de verificación no
cambian y siguen siendo el transporte por defecto en cuanto algo de lo de abajo no se pueda
garantizar. A diferencia de las ramas `orca-session` de `co-explore`/`cross-review` (rol
read-only), esta es el **primer** enganche **write-capable** del transporte: el implementador sí
escribe archivos reales dentro del worktree, no solo texto en un transcript.

### Resolver transporte (antes del paso 3 de "Pasos de ejecución")

Antes de armar el prompt-contrato y lanzar, resolver qué transporte usar: `override ?? config ??
auto` — algoritmo canónico, no se reimplementa acá, ver `cross-model-orca/reference.md` →
"Resolver de transporte":

- **`override`** — lo que pasa explícito la skill llamadora. Cuando invoca `sdd-flow`
  (`implement_mode: cross`), propaga solo el `cross_model.transport.desired` configurado (nunca su
  propio `effective` ya resuelto: cada proceso reevalúa su propia reachability de Orca).
- **`config`** — la clave `cross_model.transport` en `.specify/config.yml` (default `auto` cuando
  la clave no está).
- **`auto`** — `orca-session` si el runtime de Orca es alcanzable **desde el proceso del
  conductor** en este momento y se puede crear una sesión write fresca; si no, `cli`.

Ante **cualquier** duda — reachability incierta, sesión no verificable como propia y fresca,
locator ambiguo — el resultado es `cli`, igual que en `co-explore`/`cross-review`.
`cross-implement` no necesita justificar `cli`; sí necesita que las tres condiciones de
`orca-session` (Orca alcanzable, sesión propia/fresca, perfiles de las tres capas de control
instalados) se cumplan explícitamente — y, por ser rol **write**, dos precondiciones propias: el
clean-tree gate (punto 5 abajo) y el escritor único (punto 4).

### Rama `orca-session`

Sustituye, dentro de "Pasos de ejecución" del `SKILL.md`, el paso 3 (lanzar) y parte del 4 (el
implementador ya deja el diff escrito en el worktree; lo que el conductor cosecha es el reporte,
no el código). El implementador sigue tan acotado en su escritura como en la vía `cli`: solo
cambia el transporte, nunca la regla 3 del `SKILL.md` ("Escritura acotada, nunca commit").

1. **Sesión write propia, nunca ajena.** `createOwnedSession({ family, role: 'write', mode,
   worktree: working_dir, ... })` (`cross-model-orca/assets/dispatch-adapter.mjs`) crea una sesión
   **fresca**, dedicada a este dispatch — el conductor **nunca** reutiliza una sesión ajena (una ya
   abierta por el usuario o por otro flujo; privacidad v1, `cross-model-orca/SKILL.md` → sección
   6). Perfil write según familia (`cross-model-orca/assets/launch/profiles.md` → "Claude · write
   (cross-implement)" / "Codex · write (cross-implement)"):
   - Codex: `codex -p cmo-write -s workspace-write -a on-request --disable hooks` (atendido).
   - Claude: `--settings cross-model-orca/assets/launch/claude-write.settings.json`
     (`{disableAllHooks: true, permissions: {allow: ["Edit(./**)", "Write(./**)",
     "Bash(<proof>:*)"]}}`) + `--permission-mode manual` + `--session-id <uuid>`.
2. **Mismo worktree = vigilancia manual, no inventario.** Bajo `--permission-mode manual` (Claude,
   atendido), **todo lo no allowlisteado pregunta**: el humano que mira la sesión aprueba o
   rechaza en la TUI, incluidas las escrituras MCP sensibles. El `allow` de
   `claude-write.settings.json` acota **por construcción** la escritura de archivos al worktree
   (`Edit(./**)`/`Write(./**)`, relativas al cwd — el `cd <working_dir>` previo es parte del
   contrato, igual que en la Vía W-C) y habilita sin fricción el proof binary (`Bash(<proof>:*)`,
   mismo placeholder que la Vía W-C: el conductor deriva el patrón real del primer token de
   `proof_cmd` por sesión). Cualquier otra cosa — MCP, Bash fuera del proof, escritura fuera de
   `./` — cae a aprobación manual. No hay lista `ask`/`deny` de inventario MCP que mantener: mismo
   modelo de vigilancia manual ya aplicado al rol read-only (`claude-readonly.settings.json` =
   solo `disableAllHooks`). Codex: `-a on-request` deja que el modelo decida cuándo pedir
   aprobación, con alguien disponible para responder.
   > **Endurecimiento opcional, desatendido.** Sin humano mirando, `--permission-mode manual` se
   > colgaría esperando una aprobación que nadie da: usar `--permission-mode dontAsk` (Codex:
   > `-a never`) y, si además hace falta acotar MCP sin gate humano, `--strict-mcp-config` + un
   > allowlist write propio — opcional, no se define acá (ver `profiles.md` → "Claude · write
   > (cross-implement)").
3. **`acceptEdits` solo en worktree hermano aislado.** Si el work order corre en un worktree
   hermano descartable (nunca el árbol principal del usuario), `--permission-mode acceptEdits`
   puede reemplazar `dontAsk`/`manual` para aplicar ediciones sin fricción — excepción explícita
   **por sesión**, decidida y documentada en el momento en que se usa, nunca el default. En el
   worktree del usuario, `acceptEdits` sigue descartado como forma canónica: escribe **fuera** del
   cwd sin restricción ("Matriz de verificación" arriba).
4. **Escritor único — nunca dos escritores concurrentes sobre el mismo worktree.** Para recuperar
   una sesión que se colgó o que hay que abortar, `recover({ session, dispatch })` interrumpe
   (`terminal send --interrupt`) y confirma idle (`terminal wait --for tui-idle`) — pero, a
   diferencia del rol read-only de `co-explore`/`cross-review`, idle confirmado **no alcanza** para
   el rol write: hace falta demostrar el **cierre real** de la terminal (`terminal close`). Solo
   con `{ recovered: true }` (cierre confirmado) el conductor puede habilitar un redispatch — y
   siempre por la vía `cli`, nunca reabriendo `orca-session` sobre la sesión ya comprometida.
   `{ recovered: false }` (idle sin cierre confirmado, o cierre fallido) significa: **no**
   redespachar todavía — ni por `orca-session` ni por `cli` — porque no se puede garantizar que el
   escritor anterior dejó de escribir; el conductor decide (reintentar el cierre, escalar a
   intervención manual). Ver `cross-model-orca/reference.md` → "Recuperación". El mismo principio
   aplica a cualquier otro estado donde no se puede confirmar el cierre del turno del escritor
   anterior (no solo a `recover()`) — ver punto 9 para la clasificación completa de fallas con y
   sin riesgo de doble escritor.
5. **Clean-tree gate — sin excepción, antes de cualquier dispatch por esta rama.** La regla 2 del
   `SKILL.md` ya exige `git status` limpio de código sin commitear antes de lanzar; en la rama
   `orca-session` es además la precondición de la que depende el punto 8: si el worktree no está
   limpio, el `git diff` posterior mezcla trabajo ajeno con el del implementador y deja de ser
   enteramente atribuible a él. Ante un árbol sucio: no despachar (o aislar los cambios previos con
   un commit/stash fuera de esta skill) antes de reintentar.
6. **El implementador escribe el código; el conductor cosecha el reporte.** A diferencia de las
   ramas `orca-session` read-only (`co-explore`/`cross-review`, donde el secundario solo produce
   texto en el transcript), acá el implementador **sí** escribe archivos reales en el
   `working_dir` — eso ya queda en el worktree cuando termina su turno, fuera del transcript. Lo
   que el conductor cosecha del transcript es el **informe** ("Formato del reporte": FILES/PROOF/
   DEVIATIONS), no el código. El conductor detecta el fin del turno con `awaitDone({ session,
   dispatch, coordinatorHandle, reportPath, root, deadlineMs })`: Codex señaliza por `worker_done`
   (autoridad validada contra `taskId`/`dispatchId`/`sender` del dispatch activo); Claude no lo
   emite — su fin de turno se detecta por la transición `tui-idle` posterior al dispatch. Con
   autoridad confirmada, `awaitDone` llama a `harvest()`
   (`cross-model-orca/assets/harvest-from-transcript.mjs`), que relee el transcript, desambigua por
   `nonce` (`selectAssistantByNonce` — relevante en el fix loop, donde la sesión se reutiliza ronda
   a ronda con un `nonce` nuevo cada vez) y valida el sentinel (`hasSentinel`) antes de persistir.
7. **Cosecha a un raw único por dispatch, luego promover (sobrescribiendo) `report.txt`.**
   `harvest()` exige que `reportPath` sea un destino **inexistente** (`checkContainment` +
   `writeExclusive` con `wx`) — nunca el `cross-implement/report.txt` estable directamente, porque
   ya existiría a partir de la primera ronda cosechada y la cosecha lo trataría como éxito
   idempotente sin reescribir. En cambio: el raw único vive en el propio scratch del work order
   (`cross-implement/report-<nonce>.raw` en la implementación inicial, `report-fix-r<N>-<nonce>.raw`
   en cada ronda de fix), y el conductor lo promueve —con `rename` atómico— sobre
   `cross-implement/report.txt`, sobrescribiendo el de la ronda anterior. Es el mismo contrato **no
   acumulativo** que documenta `cross-model-orca/reference.md` → "Contención robusta y promoción
   atómica" para el `findings-<familia>.md` de `co-explore`: el raw más reciente reemplaza entero
   al estable, sin concatenar rondas — coherente con que `report.txt` ya hoy "se sobreescribe por
   ronda; queda el último" (ver "Archivos de trabajo (scratch)" abajo). El código, en cambio, no se
   cosecha: ya está en el worktree; lo que sigue es el paso 8.
8. **`git diff` como PR ajeno — sin cambios respecto de la vía cli.** El conductor revisa el `git
   diff` completo del worktree exactamente como documenta "Revisión del conductor" abajo (regla 4
   del `SKILL.md`): FILES declarados vs. `git status --porcelain`, diff completo (correctitud,
   fidelidad al work order, drift), `proof_cmd` corrido **por el conductor** — la salida del
   `report.txt` cosechado es advisory, nunca prueba. El fix loop reanuda la MISMA sesión
   (reutilizada, no una nueva) con el delta de la ronda — mismo mecanismo de "Fix loop" abajo,
   mismo tope `max_fix_rounds`. El commit, tras el gate humano, sigue siendo del conductor.
9. **Degradación a `cli` — dos clases de falla, nunca una sola bolsa.** No toda falla de la rama de
   arriba degrada igual: hay que distinguir si llegó a existir un escritor `orca-session` activo
   sobre el `working_dir`, porque redespachar por `cli` sobre un escritor que podría seguir vivo
   crea dos escritores concurrentes sobre el mismo worktree — la violación exacta que prohíbe el
   punto 4.

   - **Sin riesgo de doble escritor (degradación a `cli` inmediata):** el resolver dio `cli` de
     entrada; Orca no alcanzable ANTES de crear la sesión; runtime `stale_bootstrap` detectado
     antes del dispatch; la sesión write no pudo crearse; o falta un binario/MCP/perfil requerido.
     En ninguno de estos casos llegó a haber un escritor `orca-session` activo sobre el worktree →
     se corre la Vía W-B/W-C de siempre ("Vías de invocación" arriba): mismo prompt-contrato, mismo
     "Formato del reporte", mismo `report.txt`. La llamadora nunca queda bloqueada por la ausencia
     de Orca — degrada y sigue (regla 7 del `SKILL.md`, "Opcional y degradable").
   - **Con riesgo de doble escritor (remite al punto 4 — no redespachar todavía):** `recover()`
     devolvió `{ recovered: false }`; o el turno se despachó pero no se puede confirmar su cierre —
     p. ej. `awaitDone` devuelve `code: 4` (locator de Codex ambiguo tras los reintentos: esa
     resolución es **lazy** y ocurre en la fase de resolución del locator, ANTES de consultar
     `worker_done` — el conductor todavía no sabe si el turno del implementador terminó), o
     cualquier otro estado donde una terminal write propia pueda seguir viva. En estos casos,
     degradar a un `cli` fresco sobre el mismo `working_dir` crearía un segundo escritor
     concurrente: el conductor NO redespacha por NINGUNA vía —ni `orca-session` ni `cli`— hasta
     demostrar el cierre del escritor anterior, exactamente como exige el punto 4 (reintentar
     `recover()` hasta un `terminal close` confirmado, o escalar a intervención manual). "Degrada y
     sigue" no aplica acá tal cual: primero hay que resolver el escritor pendiente.

### Portabilidad

Los comandos de lanzamiento (POSIX + PowerShell, por familia, rol y modo atendido/desatendido)
están completos en `cross-model-orca/assets/launch/profiles.md` — no se copian acá.
`dispatch-adapter.mjs` invoca `orca` con `spawnSync('orca', args, { encoding: 'utf8' })` (arreglo
de argv, sin `shell: true`): no hereda el problema de quoting de un prompt en markdown que sí
afecta a `codex exec`/`claude -p` en las Vías W-B/W-C.

### Escritura acotada preservada

La rama `orca-session` es tan acotada en su escritura como las Vías W-B/W-C: el implementador
escribe SOLO dentro del `working_dir` (regla 3 del `SKILL.md`) — la garantía cambia de mecanismo
(permisos + vigilancia manual de la sesión Orca en vez de `-s workspace-write`/`--allowedTools`
del subproceso), no de invariante. El conductor sigue siendo quien revisa el diff completo, corre
`proof_cmd`, itera el fix loop y commitea tras el gate humano.

## Verification contract (normal/complex)

En work orders **normal/complex no hay dispatch sin un contrato resuelto, validado y congelado**.
Los cambios triviales (~<20 líneas) siguen inline y quedan fuera de este piloto. El artefacto vive
junto al work order:

- SDD: `.plans/<id>/verification-contract.md`.
- Modo directo: `cross-implement/verification-contract.md`.

El archivo es append-only: contiene versiones completas `## v1`, `## v2`, …; la mayor es la
vigente y las anteriores nunca se editan. Esta es la gramática canónica, sin variantes:

```markdown
# Verification contract — <id>

schemaVersion: 1

## v1

| ID | Requirement | Evidence | Command/observation | Expected | Baseline |
|---|---|---|---|---|---|
| <slug> | <AC-n> | <tipo-evidencia> | <comando u observación> | <una línea> | <estado> |

### Baseline

- <slug>: revision `<sha>` · <ISO-8601> · resultado: <una línea>
```

`<tipo-evidencia>` es `test | build | inspección | manual`; `<estado>` es
`RED | GREEN_ALREADY | NOT_APPLICABLE | BLOCKED`. Celdas y resultados ocupan una sola línea y no
contienen `|`. Cada versión cumple todas estas precondiciones antes de congelarse:

1. **Cobertura total y bidireccional:** cada requisito/AC en alcance tiene al menos una fila y
   cada fila referencia un requisito real. Un requisito sin cobertura o una fila huérfana impide
   congelar y despachar.
2. **IDs estables:** cada `ID` es un slug `[a-z0-9-]` de hasta 64 caracteres, único en su versión;
   es el mismo `checkId` del triage. El conjunto de IDs no cambia entre versiones. Cambiar la
   cobertura no es corregir una prueba: es `DESIGN_GAP`.
3. **Baseline ejecutado y auditable:** correr cada comando u observación antes del dispatch sobre
   la revisión pre-dispatch. Cada bullet registra el mismo ID y orden de la tabla, el commit
   evaluado, timestamp ISO-8601 y el resultado observado (salida/exit code u observación). Sin ese
   registro no hay congelamiento.
4. **Estados especiales resueltos:** `NOT_APPLICABLE` suma
   ` · justificación: <por qué>`. `GREEN_ALREADY` se adjudica antes del dispatch y su bullet suma
   ` · adjudicación: already_satisfied — <nota>` una vez resuelto el proceso siguiente.

### Adjudicación de `GREEN_ALREADY`

Un verde previo nunca prueba el cambio. El conductor registra una de estas decisiones antes de
congelar:

| Adjudicación | Efecto |
|---|---|
| `already_satisfied` | La fila queda como chequeo de no-regresión y deja de contar como evidencia del cambio. |
| `weak_check` | Fortalecer la evidencia y repetir el baseline contra la misma revisión pre-dispatch. Si queda `RED`, es evidencia real; si sigue verde, re-adjudicar `already_satisfied`. Nunca fabricar un rojo. |
| `invalid_assumption` | Corregir la fila antes de congelar porque el supuesto original era inválido. |

`weak_check` e `invalid_assumption` son estados del proceso: su rastro queda en
`implement-log.md`, pero una versión congelada solo admite la adjudicación final
`already_satisfied`.

### Validación y congelamiento

El helper valida estructura y registro; no ejecuta las evidencias:

```bash
node skills/cross-model-orca/assets/run-verification-contract.mjs validate \
  <ruta>/verification-contract.md
```

La invocación debe quedar acotada por la primitiva de exec del conductor (30 s; en Claude Code,
el `timeout` de la tool Bash). No depender de `timeout`/`gtimeout`: GNU timeout no forma parte de
macOS base. En PowerShell, cuando la superficie no ofrece un timeout propio, usar el ciclo
completo; `Wait-Job` solo deja de esperar y no mata el proceso:

```powershell
$Job = Start-Job -ScriptBlock {
  param($Contract)
  & node skills/cross-model-orca/assets/run-verification-contract.mjs validate $Contract
  if ($LASTEXITCODE -ne 0) { throw "validador: exit $LASTEXITCODE" }
} -ArgumentList '<ruta>\verification-contract.md'
try {
  if (Wait-Job -Job $Job -Timeout 30) {
    Receive-Job -Job $Job -ErrorAction Stop
  } else {
    Stop-Job -Job $Job
    throw 'validador: timeout de 30 s'
  }
} finally {
  if ($Job.State -eq 'Running') { Stop-Job -Job $Job }
  Remove-Job -Job $Job -Force
}
```

Validación verde + cobertura bidireccional revisada por el conductor + baseline registrado y
adjudicado = versión congelada. El prompt incluye el **contrato completo vigente**, su número de
versión y la prohibición explícita de modificarlo. El mismo contrato define «hecho» durante los
fix rounds y el takeover.

## Prompt del implementador

Contrato completo — el implementador arranca sin contexto de sesión; lo que no esté acá no
existe para él. Escrito a archivo con Write:

```
GOAL: <un párrafo — cómo se ve "terminado">
SPEC: Lee <work_order> en la raíz del repo. Es un contrato CONGELADO y ya aprobado.
  Impleméntalo exactamente. Si un paso es imposible tal como está escrito, implementa la
  versión fiel más cercana y reporta la desviación — no rediseñes.
KEY PATHS: <archivos/dirs a tocar, y los que debe leer primero (reúso identificado)>
CONSTRAINTS: <"no toques X", estilo del repo, dependencias que no deben cambiar.
  Siempre incluir: no commitees, no toques .plans/ ni .specify/ ni cross-implement/>
NON-GOALS: <explícitamente fuera de alcance — del "Out of scope"/AC del work order>
PROOF: El verification contract completo y congelado es <ruta>, versión <vN>, y se incluye
  debajo. No lo modifiques. Ejecuta sus evidencias; incluye la salida completa y exit code de
  `<proof_cmd>` en tu reporte.
OUTPUT: Termina con el reporte del "Formato del reporte" (abajo), cerrando con STATUS: done.

<contenido completo de verification-contract.md, versión vigente identificada>
```

Cuando el work order es SDD (`.plans/<id>/`), derivar GOAL del objetivo de la spec, KEY PATHS de
los campos Archivos de las tasks, CONSTRAINTS/NON-GOALS del alcance, y PROOF del `test_cmd`
acotado (o el Verificar agregado de las tasks).

Para normal/complex, `PROOF` no se reduce al comando global: referencia e incluye el verification
contract completo. El reporte del implementador sigue siendo advisory; la evidencia terminal la
re-ejecuta el conductor fila por fila.

## Formato del reporte

Pedir al implementador exactamente:

```
FILES:
- <path> — <qué cambió y por qué, una línea>

PROOF:
<salida verbatim de proof_cmd + exit code>

DEVIATIONS:
- <desviación del work order + razón>   (o "ninguna")

STATUS: done
```

`STATUS: done` es la señal de fin para el poll en background. Reporte no parseable → el diff
sigue siendo la verdad (regla 4): revisarlo igual; se pierde solo la narrativa.

## Revisión del conductor

Checklist tras cada ronda (regla 4 del `SKILL.md`) — como PR de un contribuidor externo:

1. **FILES vs realidad**: contrastar lo declarado contra `git status --porcelain`. Archivos
   tocados no declarados o declarados no tocados → sospecha, va al fix round.
2. **Diff completo** (`git diff`): correctitud, fidelidad al work order, estilo del repo,
   nada fuera de alcance. **Drift** (hunks que no mapean al work order) → pedir reversión en el
   fix round o declararlo explícitamente (en SDD: `## Extras` de sdd-flow).
3. **Evidencia propia**: re-ejecutar la versión vigente del verification contract fila por fila,
   con evidencia fresca; leer cada salida completa + exit code u observación y comprobar su
   `Expected`. La del reporte no cuenta. `proof_cmd` puede formar parte del contrato, pero no lo
   reemplaza.
4. **En SDD**: atribuir hunks a tasks y marcar `- [x]` solo las efectivamente cubiertas; los AC
   los verifica después el `verify` de sdd-flow (esta revisión no lo reemplaza).
5. **Condición terminal:** `IMPLEMENTED` y manifest `ready` exigen `Expected` cumplido en toda
   fila aplicable, ninguna `BLOCKED` y justificación registrada para cada `NOT_APPLICABLE`.
   Cualquier otro estado va a triage, a suspensión por `DESIGN_GAP` o a cierre no exitoso.
6. Registrar el veredicto, la versión del contrato y la evidencia de la ronda en el log.

## Triage de ownership

Ante una falla de evidencia después de una ronda, el conductor clasifica **cada check antes de
consumir otra ronda**. El `checkId` es el ID estable de la fila:

| Clase | ¿Consume ronda? | Control de flujo |
|---|---:|---|
| `IMPLEMENTATION_DEFECT` | Sí | Agrupar los defectos del delta y reanudar la misma sesión. Una entrada de triage por check; varios checks pueden compartir un único fix round. |
| `VERIFICATION_DEFECT` | No | Corregir el contrato en una versión nueva, recalcular el baseline de la fila contra la revisión pre-dispatch, congelar, propagar la nueva versión y repetir la evidencia. |
| `ENVIRONMENT_FAILURE` | No | Reparar el entorno y repetir. Si no es reparable, marcar la fila `BLOCKED` y cerrar de forma no exitosa. |
| `DESIGN_GAP` | No | Suspender de inmediato en fix loop o takeover, emitir `DESIGN_GAP (suspendida)` y volver a plan/spec; en modo embebido, devolverlo al flujo llamador. |

Toda clasificación queda en `implement-log.md` con check, clase, evidencia y
`consumedRound: true|false`. Antes de clasificar la **segunda falla consecutiva del mismo check**
como `IMPLEMENTATION_DEFECT`, registrar una razón falsable de por qué el contrato no está
defectuoso: una afirmación que una observación concreta pueda refutar, no «seguro es el código».

### Correcciones del contrato y re-baseline aislado

Una corrección nunca edita silenciosamente la versión vigente: se agrega la versión completa
siguiente, se preservan las anteriores y se mantiene el mismo conjunto de IDs. Para recalcular la
fila corregida se usa un worktree temporal sobre el commit pre-dispatch registrado, nunca
`checkout`, `reset` ni `stash` sobre el árbol activo que contiene el diff del implementador:

```bash
TMP_WORKTREE=$(mktemp -d)
git worktree add --detach "$TMP_WORKTREE" <sha-pre-dispatch>
( cd "$TMP_WORKTREE" && <evidencia-de-la-fila> )
git worktree remove --force "$TMP_WORKTREE"
```

```powershell
$TmpWorktree = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid())
git worktree add --detach $TmpWorktree <sha-pre-dispatch>
try {
  Push-Location $TmpWorktree
  try { <evidencia-de-la-fila> } finally { Pop-Location }
} finally {
  git worktree remove --force $TmpWorktree
}
```

Si no se puede crear o limpiar el worktree con garantías, la fila queda `BLOCKED`. El baseline
recalculado vuelve a la adjudicación de `GREEN_ALREADY`; si no puede reconstruirse, también queda
`BLOCKED`. Una vez congelada la nueva versión, el delta al implementador identifica explícitamente
«rige v<N>; cambió la fila <checkId>». Estas reglas siguen vigentes durante takeover.

En el manifest, `ready` se reserva para «hecho» pleno. Si ya existe un attempt `completed` pero el
contrato termina no exitoso, cerrar `aborted`: la FSM rechaza `failed` después de un attempt
exitoso.

## Fix loop

- Antes de preparar un delta, ejecutar el triage de ownership. Solo
  `IMPLEMENTATION_DEFECT` consume ronda del implementador; las otras clases siguen su control de
  flujo sin gastar `max_fix_rounds`.
- El delta de cada ronda es concreto: **qué está mal · en qué archivo · qué prueba debe pasar** —
  no re-mandar el work order completo. Incluir la versión vigente del contrato cuando haya
  cambiado.
- Reanudar la MISMA sesión por la vía que corresponda (comandos arriba; en Codex, el override
  `-c sandbox_mode="workspace-write"` es obligatorio; guard de id vacío siempre).
- Tope `max_fix_rounds` (default 2) → **takeover**: el conductor termina directamente, registrado
  en el log con qué quedó de cada lado (`PARTIAL`). El contrato congelado sigue definiendo hecho;
  toda corrección pasa por triage y versión nueva. `DESIGN_GAP` suspende también en takeover.
- En modo embebido sdd-flow, su tope de diseño manda: 3 fallos de la MISMA falla (aunque queden
  fix rounds) = problema de diseño → volver a `plan`/`specify`, no seguir delegando.

## Instrumentación con manifest

Cada corrida piloto usa un único `runId` bajo `cross-implement/runs/`. La telemetría envuelve el
flujo, pero **no es un gate**:

1. `start` después de congelar el contrato y antes del dispatch.
2. `attempt-start` al despachar por un transporte.
3. `attempt-finish` cuando termina la delegación por ese transporte, incluidos sus fix rounds, o
   cuando ese transporte falla de forma terminal.
4. `finish --ext-file` después de la evidencia final propia del conductor, incluso para un cierre
   no exitoso cuando la FSM lo permita.

Comandos POSIX:

```bash
RUNS_DIR=<dir-del-work-order>/cross-implement/runs
mkdir -p "$RUNS_DIR"
START_JSON=$(node skills/cross-model-orca/assets/run-manifest.mjs start \
  --dir "$RUNS_DIR" --workflow cross-implement --mode implement --role builder \
  --family <familia> --transport-desired <auto|orca-session|cli>)
RUN_ID=$(printf '%s' "$START_JSON" | node -e \
  "let s='';process.stdin.on('data',c=>s+=c).on('end',()=>process.stdout.write(JSON.parse(s).runId))")

node skills/cross-model-orca/assets/run-manifest.mjs attempt-start \
  --dir "$RUNS_DIR" --run-id "$RUN_ID" --transport <transporte> --access write
node skills/cross-model-orca/assets/run-manifest.mjs attempt-finish \
  --dir "$RUNS_DIR" --run-id "$RUN_ID" --outcome <completed|failed|aborted|unterminated> \
  --code <N|null> [--recovered <true|false>]

node skills/cross-model-orca/assets/run-manifest.mjs finish \
  --dir "$RUNS_DIR" --run-id "$RUN_ID" --status <ready|failed|aborted> \
  --ext-file "$RUNS_DIR/ext-final.json"
```

Comandos PowerShell equivalentes:

```powershell
$RunsDir = '<dir-del-work-order>\cross-implement\runs'
New-Item -ItemType Directory -Force $RunsDir | Out-Null
$Start = & node skills/cross-model-orca/assets/run-manifest.mjs start `
  --dir $RunsDir --workflow cross-implement --mode implement --role builder `
  --family <familia> --transport-desired <auto|orca-session|cli> | ConvertFrom-Json
$RunId = $Start.runId

& node skills/cross-model-orca/assets/run-manifest.mjs attempt-start `
  --dir $RunsDir --run-id $RunId --transport <transporte> --access write
& node skills/cross-model-orca/assets/run-manifest.mjs attempt-finish `
  --dir $RunsDir --run-id $RunId --outcome <completed|failed|aborted|unterminated> `
  --code <N|null> --recovered <true|false>

& node skills/cross-model-orca/assets/run-manifest.mjs finish `
  --dir $RunsDir --run-id $RunId --status <ready|failed|aborted> `
  --ext-file (Join-Path $RunsDir 'ext-final.json')
```

`ext-final.json` reemplaza los ceros iniciales con esta forma enumerada:

```json
{
  "cross-implement": {
    "fixRounds": 1,
    "verificationReruns": 2,
    "triage": [
      { "checkId": "pruebas", "class": "IMPLEMENTATION_DEFECT", "consumedRound": true }
    ]
  }
}
```

Semántica normativa:

- Un attempt representa adquisición de transporte: dispatch inicial = primer attempt; fallback
  `orca-session → cli` = segundo. Los fix rounds reanudan la misma sesión lógica y **no** crean
  attempts.
- `fixRounds` cuenta deltas de fix despachados. Un delta que agrupa varios defectos cuenta 1.
- `verificationReruns` cuenta re-ejecuciones **completas** del contrato por el conductor después
  de la primera pasada post-implementación. Baseline y primera pasada no cuentan; sí cuentan las
  repeticiones tras reparar `VERIFICATION_DEFECT`/`ENVIRONMENT_FAILURE` y las revisiones de cada
  fix round.
- `triage[]` tiene una entrada por check clasificado en cada falla. `consumedRound` es `true` solo
  para `IMPLEMENTATION_DEFECT`; por batching, su suma puede superar `fixRounds`.

Si `start` falla antes de crear el partial, la implementación continúa fuera del piloto y el log
registra `manifest: start falló — <motivo>`. Si `start` creó el partial, el conductor intenta dejar
un `run.json` terminal; si otro fallo lo impide, el `.partial.json` queda como marca inequívoca de
corrida incompleta. Cualquier fallo posterior se registra como
`manifest: <operación> falló — <motivo>` y la corrida continúa; no hay retry automático.

## Latencia, deadlines y banner

Una implementación tarda mucho más que una crítica: presupuestos por encima de cross-review.

| Contexto | Modo | Tope |
|---|---|---|
| Work order chico (≤ ~3 tasks), conductor con exec largo | sync (Bash `timeout: 600000`) | 10 min |
| Work order mediano/grande, o cualquier conductor | background + poll de `STATUS: done` en `report.txt` | deadline 1800 s (override conversacional) |
| Conductor de exec corto (Codex ~120s) | background + poll acotado (patrón de cross-review Vía C) | ídem |

- **Tope duro siempre**: al vencer sin `STATUS: done`, matar el proceso (`kill $PID` /
  `Stop-Process`), revisar el diff parcial (degradación 3 del `SKILL.md`) y devolver `UNAVAILABLE`.
- **Banner al terminar un run en background** (obligatorio): la PRIMERA línea del siguiente
  mensaje al usuario es un aviso destacado — `🔔 Implementación cruzada terminada — <work order>
  (ok/fallo) — reviso el diff ahora` — antes de cualquier salida de verificación. El usuario no
  mira las tools; un build terminado nunca se desliza en silencio a la fase de revisión.
- No matar un run background silencioso antes del deadline: las implementaciones legítimamente
  tardan.

## Archivos de trabajo (scratch)

Junto al work order, subdirectorio `cross-implement/` (mismo criterio que `cross-review/`):

```
<dir del work order>/cross-implement/
├─ work-order.md          # solo en modo directo sin archivo: el contrato destilado
├─ prompt.txt             # prompt-contrato (Write, nunca inline)
├─ fix-r1.txt, fix-r2.txt # deltas del fix loop
├─ report.txt             # reporte del implementador (se sobreescribe por ronda; queda el último)
├─ thread.jsonl           # stream JSONL del lanzamiento (Vía W-B) — fuente del thread id
├─ session.txt            # thread/session id capturado
├─ impl.err.txt           # stderr del implementador
└─ implement-log.md       # NO: el log va junto al work order, no en el scratch (abajo)
```

En SDD resuelve a `.plans/<id>/cross-implement/`. Local y untracked, sin autolimpieza — igual
que `cross-review/` y `co-explore/`.

## Log de implementación

`implement-log.md` junto al work order (`.plans/<id>/implement-log.md` en SDD). Registro
auditable de la delegación:

```markdown
# Cross-implement log — <id|work order> (<ISO-8601>)
Implementador: <codex exec | claude -p>  ·  modelo: <model | CLI default>  ·  max_fix_rounds: <n>
Proof: `<proof_cmd>`
Contrato vigente: <vN> · revisión pre-dispatch: `<sha>`
Manifest: <runId | fuera del piloto>

## Ronda 1 — implementación
FILES declarados: <n> · coinciden con git status: <sí/no>
Proof (corrido por el conductor): <PASS/FAIL + evidencia>
Contrato: <vN> · evidencia fila por fila: <PASS/FAIL + checks>
Triage: <ninguno | checkId · clase · consumedRound · razón falsable cuando corresponda>
Veredicto del conductor: <aceptado | fix round: qué corregir>
Drift detectado: <ninguno | lista → revertido/declarado>
manifest: <operación OK | operación falló — motivo>

## Ronda 2 — fix
<ídem>

## Resultado
<IMPLEMENTED | PARTIAL (takeover: qué terminó el conductor) | DESIGN_GAP (suspendida) | UNAVAILABLE> en <n> rondas.
Métricas: fixRounds=<n> · verificationReruns=<n> · triage=<n entradas>.
Desviaciones del work order: <lista o "ninguna">.
```

En modo embebido, sdd-flow referencia este log desde su flujo; el commit y el `verify` siguen
siendo de sdd-flow.
