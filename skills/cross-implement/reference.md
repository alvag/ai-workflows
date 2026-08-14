# cross-implement — Referencia

Detalle operativo de la skill `cross-implement`. El `SKILL.md` apunta acá para el descubrimiento
del implementador, las vías de invocación por familia, el prompt-contrato, la revisión del
conductor, el fix loop, los tiempos y los archivos de trabajo.

## Tabla de contenidos

- [Documentos de esta referencia](#documentos-de-esta-referencia)
- [Portabilidad entre shells (POSIX / PowerShell)](#portabilidad-entre-shells-posix--powershell)
- [Descubrir el implementador](#descubrir-el-implementador)
- [Vías de invocación](#vías-de-invocación)
- [Matriz de verificación](#matriz-de-verificación)
- [Prompt del implementador](#prompt-del-implementador)
- [Formato del reporte](#formato-del-reporte)
- [Revisión del conductor](#revisión-del-conductor)
- [Fix loop](#fix-loop)
- [El delta revisable de un bloque](#el-delta-revisable-de-un-bloque)
- [Secuencia Git entre bloques](#secuencia-git-entre-bloques)
- [Orden de cierre de la secuencia](#orden-de-cierre-de-la-secuencia)
- [Latencia, deadlines y banner](#latencia-deadlines-y-banner)
- [Rutas por invocación](#rutas-por-invocación)
- [Archivos de trabajo (scratch)](#archivos-de-trabajo-scratch)
- [Log de implementación](#log-de-implementación)
- [Cuándo un reporte ilegible no invalida la revisión](#cuándo-un-reporte-ilegible-no-invalida-la-revisión)

---

## Documentos de esta referencia

La referencia de esta skill son **tres** archivos, partidos por el momento en que se los lee, no por
tamaño. Cargar los tres siempre desperdicia contexto en una corrida que sale bien a la primera:

| Archivo | Qué trae | Cuándo se lee |
|---|---|---|
| `reference.md` (este) | descubrimiento, vías de invocación, prompt, reporte, revisión, fix loop, tiempos y scratch | en toda corrida |
| `contrato-verificacion.md` | esquema del contrato, reglas de congelamiento, adjudicación, gate previo al dispatch y sus bloques de validación | al armar y aprobar el contrato, antes de delegar |
| `ownership.md` | las cuatro clases de falla, matriz de cierre por bloque, presupuestos, rollback, re-baseline aislado, takeover y precedencia de topes | al cerrar cualquier bloque, haya fallado o no |

En toda corrida, antes del primer despacho, leer también
`skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación". Ese contrato gobierna el
deadline, el relanzamiento, las rutas de salida y la elección entre aviso y sondeo.

## Portabilidad entre shells (POSIX / PowerShell)

Mismo criterio que `cross-review/reference.md` → "Portabilidad entre shells (POSIX / PowerShell)":
esa sección es
la fuente canónica de las equivalencias (detección de binarios, prompt por archivo a stdin, UUID,
background y kill). No se duplican acá. Regla invariante idéntica: el prompt **se escribe a
archivo con la tool Write** (nunca inline ni `echo`/heredoc) y llega por stdin.

## Descubrir el implementador

El algoritmo canónico de identificación de familia vive en `cross-review/reference.md` →
"Descubrir el revisor" (autor = la familia del agente que conduce, sin importar la superficie).
Acá cambia el rol buscado: no un crítico read-only sino un **implementador con escritura acotada**.

| Familia del autor | Implementador por default | Cómo detectarlo | Vía |
|---|---|---|---|
| Claude | Codex | `command -v codex` (PowerShell: `Get-Command codex -ErrorAction SilentlyContinue`) | Vía W-B (workspace-write) |
| GPT/Codex | Claude | `command -v claude` | Vía W-C (permisos path-scoped) |

<!-- corpus-invariante:inicio:cross-implement.reference.md.7cce0044363c -->

La familia opuesta es el default y la recomendación. `cross_model.families` es la autoridad: si la

<!-- corpus-invariante:fin:cross-implement.reference.md.7cce0044363c -->
allowlist contiene solo la familia del autor, **corre** un implementador fresco de esa familia —
conductor Claude → worker Claude por la Vía W-C; conductor Codex → worker Codex por la Vía W-B—.
La salida debe incluir, en las dos direcciones:

> <!-- corpus-invariante:inicio:cross-implement.reference.md.f0d5e0198799 -->

> `Se recomienda revisión humana adicional: el worker ya no es de otra familia que el autor, por lo

> <!-- corpus-invariante:fin:cross-implement.reference.md.f0d5e0198799 -->
> que no rompe la correlación de errores.`

<!-- inventario-familias:inicio -->
### Inventario de familias

Antes de cualquier preflight, la **raíz** de la corrida resuelve una vez la selección de workers
despachables. El conductor conduce y no entra en `families`; cada worker es un proceso aparte en
sesión fresca. Si el contrato de invocación trae `family_inventory`, **no se resuelve nada**: se
heredan `families` y `selection`, no se relee config y no se vuelve a avisar.

| Paso | Regla |
|---|---|
| 1 — workers **declarados** | comprobar el CLI en PATH de cada familia de `families`, **la del conductor incluida**. Que el conductor esté corriendo por construcción no exime del preflight de su worker |
| 2 — **sin declaración** | solo si no hay declaración, detectar qué CLIs están en PATH para proponer la selección. POSIX: `command -v codex` / `command -v claude`. PowerShell: `Get-Command codex -ErrorAction SilentlyContinue`. Nada más cuenta |

Los dos pasos miden el CLI porque es **condición necesaria de todas las vías**: el runtime del subagente
resuelve su disponibilidad corriendo `codex --version` y `codex app-server --help`, así que exige el
CLI y algo más. No es la intersección restrictiva, es el piso común.

La auditoría **no comprueba versión, auth, aislamiento ni lanzamiento**, y **no afirma capacidad
operativa**: una familia presente puede fallar igual su preflight, y eso sigue siendo un fallo real.

`selection` conserva cómo se resolvió la lista: `full` abarca todas las familias presentes y
`user_choice` declara menos. Se persiste con `families`, se hereda y nunca se reconstruye sondeando.

**Declarado ↔ disponible:**

| Caso | Resultado |
|---|---|
| no declara una familia presente | preferencia válida; no se sondea ni se despacha ese worker |
| declara una familia cuyo CLI está ausente | **error**: nombra la familia y que la auditoría no la encuentra |

`families: []` sigue siendo error. La allowlist admite solo `claude | codex`, sin duplicados y
canonizada a minúsculas.
<!-- inventario-familias:fin -->

**Prechequeos** — los mismos de `cross-review/reference.md` → "Descubrir el revisor" →
"Prechequeos" (versión del CLI, no pinear `-m`, eco del modelo activo), registrando el modelo en
el `implement-log.md`.

> **Vía A (subagente `codex:codex-rescue`) no aplica acá**: el contrato de ese runtime corre
> read-only para pedidos de review/diagnosis. Para implementar se usa el CLI directo (Vía W-B).

Sin CLI para el implementador seleccionado → `UNAVAILABLE` (regla 7 del `SKILL.md`).

## Vías de invocación

Dos reglas invariantes (además de las del `SKILL.md`):

1. **Escritura acotada por construcción, nunca por confianza**: sandbox `workspace-write` en
   Codex, permisos path-scoped en Claude. **Nunca** `--yolo` /
   `--dangerously-bypass-approvals-and-sandbox` / `--dangerously-skip-permissions` /
   `acceptEdits` sin scoping — ver la matriz de verificación: `acceptEdits` escribe fuera del
   working dir.
2. El prompt va por **stdin desde archivo** (tool Write), igual que en las skills hermanas.

Las dos se mantienen en cada intento y reanudación: cambia la ejecución concreta, no qué se le exige.
El manifest de corrida registra la vía efectiva (esquema en `cross-review/reference.md` → "Manifest
de corrida"). Los comandos concretos aparecen en cada vía documentada debajo.

### Vía W-B — Codex implementador (autor Claude)

- **Lanzamiento** (sesión fresca; captura del thread id igual que la Vía B de cross-review):
  ```bash
  codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json \
    --output-last-message <scratch>/report.txt - < <scratch>/prompt.txt \
    > <scratch>/thread.jsonl 2> <scratch>/impl.err.txt
  grep -m1 -o '"thread_id":"[^"]*"' <scratch>/thread.jsonl | cut -d'"' -f4 > <scratch>/session.txt
  ```
  En **PowerShell**:
  ```powershell
  Get-Content -Raw <scratch>\prompt.txt |
    codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json `
      --output-last-message <scratch>\report.txt - > <scratch>\thread.jsonl 2> <scratch>\impl.err.txt
  (Select-String -Path <scratch>\thread.jsonl -Pattern '"thread_id":"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value > <scratch>\session.txt
  ```
- `-s workspace-write` limita las escrituras al `working_dir` **más `/tmp`** (por diseño del
  sandbox). Caveat: si el repo objetivo vive bajo `/tmp`, el borde efectivo es más laxo.
- **Fix round** (resume del MISMO thread). Dos cosas que **no** se heredan del comando de lanzamiento
  y que hay que mirar antes de copiarlo (detalle en `cross-review/reference.md` → "Asimetría de flags
  entre `exec` y `exec resume`"):
  - el **override de sandbox es obligatorio**: el modo de la sesión original no es garantía al
    reanudar, y por eso va `-c sandbox_mode="workspace-write"` y no `-s`, que `resume` **rechaza**;
  - **`-C` tampoco existe en `resume`**: el working dir es el **cwd del proceso**. Lanzar el fix
    round desde otro directorio escribe en el repo equivocado **sin error**. Posicionarse antes.
  ```bash
  SESSION_ID=$(cat <scratch>/session.txt)
  echo "resume → ${SESSION_ID:?vacío}"   # id vacío = sesión fresca silenciosa; cortar acá
  codex exec resume "$SESSION_ID" -c sandbox_mode="workspace-write" --skip-git-repo-check --json \
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

## Prompt del implementador

Contrato completo — el implementador arranca sin contexto de sesión; lo que no esté acá no
existe para él. Escrito a archivo con Write:


El prompt vive en `assets/prompts/implement.md` — es la **entrada exacta** del worker y se escribe a archivo con la tool Write.


Cuando el work order es SDD (`.plans/<id>/`), derivar GOAL del objetivo de la spec, KEY PATHS de
los campos Archivos de las tasks, CONSTRAINTS/NON-GOALS del alcance, y PROOF del `test_cmd`
acotado (o el Verificar agregado de las tasks).

## Handoff destilado, nunca transcript crudo

Al modelo delegado se le pasa un **contrato destilado** —objetivo, contexto necesario, límites—,
nunca el transcript literal de la sesión del conductor. El prompt por archivo que esta skill usa
**ya es** un handoff destilado: no es una convención estética, es la forma correcta, y conviene
saber por qué para que nadie la "optimice" pasándole contexto ambiente al delegado.

El porqué no es solo de diseño. Está documentado un caso real donde reproducir dentro de un modelo
un transcript construido bajo otro activó clasificadores de política de uso y **bloqueó todas las
requests de la sesión** —incluso las triviales—, mientras la misma consulta en una sesión fresca
pasaba sin problema. El diseño barato resultó ser también el seguro.

Consecuencia práctica: si el delegado necesita saber algo, ese algo se **escribe en el prompt**. No
se le reenvía la conversación para que lo deduzca.

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
3. **Prueba propia**: correr `proof_cmd` fresco; leer salida completa + exit code. La del reporte
   no cuenta.
4. **En SDD**: atribuir hunks a tasks y marcar `- [x]` solo las efectivamente cubiertas; los AC
   los verifica después el `verify` de sdd-flow (esta revisión no lo reemplaza).
5. Registrar el veredicto de la ronda en el log (qué pasó, qué va al fix round).

## Cuándo un reporte ilegible no invalida la revisión

El principio: **un reporte que no parsea no invalida la revisión**. Se revisa el artefacto igual y lo
único que se pierde es la narrativa del implementador.

**Condición de aplicación — el principio es falso sin ella:** vale donde el **artefacto es el diff**,
no donde el artefacto **es** el informe.

- Acá el entregable es el diff; el reporte solo lo describe. Si el reporte no parsea, el diff sigue
  estando y se revisa igual: leerlo no depende del formato del texto que lo acompaña.
- En `co-explore` el entregable **es** el informe. Uno que no parsea no deja nada que revisar, y por
  eso esa skill exige informe estructurado o nada: degrada a texto libre si aporta contexto, o
  descarta, y registra la degradación.

Enunciarlo como principio general **sin** su condición contradiría de frente esa regla no negociable,
y dejaría a quien lea las dos eligiendo cuál desobedecer.

La prueba de si aplica es una sola pregunta: **si borro el reporte, ¿queda algo que revisar?** Si sí,
el principio aplica. Si no, el reporte era el artefacto y su formato no es narrativa: es el
entregable.

## Fix loop

> **El delta de fix no tiene asset propio.** No es un prompt con estructura fija sino el contenido
> mínimo de abajo, distinto en cada ronda; congelarlo en una plantilla invitaría a rellenarla en vez
> de escribir lo que esa ronda necesita.

- El delta de cada ronda es concreto: **qué está mal · en qué archivo · qué prueba debe pasar** —
  no re-mandar el work order completo (la sesión lo recuerda).
- Reanudar la MISMA sesión por la vía que corresponda (comandos arriba; en Codex, el override
  `-c sandbox_mode="workspace-write"` es obligatorio; guard de id vacío siempre).
- Tope `max_fix_rounds` (default 2) → **takeover**: el conductor termina directamente, registrado
  en el log con qué quedó de cada lado (`PARTIAL`).
- En modo embebido sdd-flow, su tope de diseño manda: 3 fallos de la MISMA falla (aunque queden
  fix rounds) = problema de diseño → volver a `plan`/`specify`, no seguir delegando.

### El delta revisable de un bloque

La revisión del bloque compara su **commit base del bloque** contra el estado conjunto del index y
el working tree. Para los paths trackeados, el comando base es `git diff "$block_base" --
<pathspec...>`: incluye staged y unstaged respecto de ese commit y no es un rango entre dos commits,
porque el commit de trabajo del bloque todavía no existe.

`git diff` no incorpora archivos untracked. El conductor obtiene su lista con `git status
--porcelain` y `git ls-files --others --exclude-standard -- <pathspec...>`, y revisa además el
contenido completo de cada archivo listado. El conjunto resultante debe coincidir exactamente con el
mismo set `code_dirty` que clasifica `sdd-flow`: excluye `.plans/`, `.specify/` y los
generados reconocidos por el repo. Una diferencia entre ambos conjuntos detiene la aceptación.

### Secuencia Git entre bloques

Antes del primer dispatch, el conductor fija el ancla con `anchor=$(git rev-parse HEAD)` y conserva
ese SHA en el recibo. Cada commit de trabajo lleva los trailers `Cross-Implement-Block: <block_id>` y
`Cross-Implement-Receipt: <fingerprint>`. Para distinguir sus commits de trabajo de commits ajenos,
ejecuta `git rev-list --reverse "$anchor..HEAD"` y, por cada SHA, `git log -1
--format='%(trailers:key=Cross-Implement-Block,valueonly)' <sha>`; un commit sin marca o con una
identidad ajena detiene la secuencia.

El staging se reconstruye para cada bloque con pathspec explícito: `git add -- <pathspec...>`. Antes
del commit, `git diff --cached --name-only` debe coincidir con los paths aceptados del delta; nada que
estuviera staged previamente entra por arrastre. Si un hook falla, el conductor muestra el error y se
detiene sin `--no-verify`. Si un hook modifica el árbol, invalida el delta revisado: se vuelve a
clasificar y revisar el cambio antes de decidir si el bloque todavía puede aceptarse.

Antes de reset, aplastado o rollback, cada SHA marcado se consulta con `git branch -r --contains
<sha>`. Si algún commit de trabajo aparece en un upstream, la guarda detiene sin reescribir la
historia; esos commits solo pueden aplastarse mientras sigan siendo locales.

### Orden de cierre de la secuencia

Tras aceptar el último bloque y confirmar el cese, el orden obligatorio es **delta acumulado →
verificación final → gate → commit final**. Primero se valida la cadena marcada y se ejecuta `git
reset --soft "$anchor"`; así el aplastado reconstruye en el index el delta acumulado de todos los
commits de trabajo. Los extremos del diff presentado son el ancla previa a los bloques y el index más
working tree resultante, inspeccionados con `git diff "$anchor"` y `git diff --cached "$anchor"` e
incluyendo por separado cualquier untracked aceptado.

Sobre ese delta se corre la verificación final. Después se presenta el mismo delta y la evidencia en
el gate humano, y solo tras su aprobación se crea el commit final de contenido. No se aplaza el
aplastado hasta después del gate: hacerlo dejaría el árbol limpio y mostraría un diff vacío al humano.

## Latencia, deadlines y banner

Una implementación tarda mucho más que una crítica: presupuestos por encima de cross-review.

| Contexto | Modo | Tope |
|---|---|---|
| Work order chico (≤ ~3 tasks), conductor con exec largo | sync (Bash `timeout: 600000`) | 10 min |
| Work order mediano/grande, o cualquier conductor | background + poll de `STATUS: done` en `report.txt` | deadline 1800 s (override conversacional) |
| Conductor de exec corto (Codex ~120s) | background + poll acotado (patrón de cross-review Vía C) | ídem |

- **Tope duro siempre**: al vencer sin `STATUS: done`, matar el proceso (`kill $PID` /
  `Stop-Process`), revisar el diff parcial (degradación 3 del `SKILL.md`) y devolver `UNAVAILABLE`.
  La **causa** de ese `UNAVAILABLE` es `deadline_exceeded`, no `runtime_failure`: el implementador
  arrancó bien y el corte lo puso el conductor al fijar el tope de esta tabla. La distinción no es
  cosmética — decide la palanca: ante `runtime_failure` se mira el error, ante `deadline_exceeded` se
  mira el presupuesto (y acá el override conversacional del deadline es justamente esa palanca).
  Enum completo de causas en `cross-review/reference.md` → "Latencia y timeout (Claude revisor)".
- **Banner al terminar un run en background** (obligatorio): la PRIMERA línea del siguiente
  mensaje al usuario es un aviso destacado — `🔔 Implementación cruzada terminada — <work order>
  (ok/fallo) — reviso el diff ahora` — antes de cualquier salida de verificación. El usuario no
  mira las tools; un build terminado nunca se desliza en silencio a la fase de revisión.
- No matar un run background silencioso antes del deadline: las implementaciones legítimamente
  tardan.

### `recovery-required` bloquea retry y fallback

Matar el proceso al vencer el deadline es lo que la tabla manda hacer; esta subsección dice qué pasa
cuando **no** se puede afirmar que quedó muerto.

Un intento cuyo resultado sobre el árbol es **incierto** —no se sabe qué quedó escrito ni si hay un
proceso que siga escribiéndolo— no queda en `UNAVAILABLE` ni en `PARTIAL`: queda en
`recovery-required`, que es estado del **intento**, no un resultado de la corrida. Mientras no se
resuelva **no habilita ni retry ni fallback**: ni una ronda de fix más, ni el despacho del mismo work
order por el otro transporte, ni un implementador nuevo sobre ese árbol.

**Vencer el deadline no prueba que el proceso dejó de trabajar.** No es una precaución teórica: se
observó lo contrario — una espera venció con los agentes todavía produciendo y entregaron **después**
de que la corrida ya se había degradado. El deadline de la tabla es el corte que el conductor se pone
a sí mismo, y `deadline_exceeded` registra esa decisión suya; ninguno de los dos prueba nada sobre el
proceso. Lo único que sirve como prueba es evidencia positiva de que ya no está vivo.

**Y acá las rutas de salida fijas no protegen nada, porque la salida no es una ruta.** Contra un
worker tardío que completa el archivo de una corrida ya degradada, dar a cada intento rutas exclusivas
alcanza; contra un implementador tardío no, porque lo que sigue tocando es el **working tree entero**.
Dos escritores sobre el mismo árbol dejan un diff que no es de ninguno de los dos y un estado del repo
que ninguno explica. Por eso el recovery acá es una pregunta concreta y contestable —qué quedó escrito,
y si hay algo que siga escribiéndolo—, y hasta contestarla no se despacha nada sobre ese árbol. El
contrato general que bloquea el relanzamiento mientras el proceso anterior pueda seguir escribiendo
vive en `skills/cross-review/corridas-en-vuelo.md` → "Invariantes de recuperación"; acá se aplica al
working tree y no se repite.

### Callback o poll: el segundo predicado, una vez en `background`

`execution` es un enum **cerrado de tres valores** (`auto | sync | background`) y el default de esta
skill es `auto`, tanto en modo embebido como directo. Los defaults de las tres skills cross-model
están en un solo lugar, sin copias: `co-explore/reference.md` → "Latencia y deadlines".

**Elegir `background` no dice cómo se espera.** Hacen falta **dos** predicados distintos, y el error
que hay que evitar es tratarlos como uno: que el conductor pueda fijar un timeout de exec largo **no
demuestra** que el host lo vuelva a invocar cuando el comando en background termina. La secuencia
completa, en este orden: `execution: auto` elige `sync` o `background` por el predicado de timeout de
exec y el tamaño del work order de la tabla de arriba —auto → sync con tope largo disponible y work
order chico, auto → background si no—; y **ya dentro de `background`**, un segundo predicado, el de
**re-invocación durable**, elige entre **callback** y el **poll de `STATUS: done`** de esa misma
tabla. Un `background` pedido a mano saltea el primer paso, no el segundo.

**Condición de verdad, positiva.** El predicado de re-invocación durable es verdadero **solo** cuando
el contrato documentado del host **garantiza** volver a invocar al conductor al completar un comando
en background. La **ausencia de garantía —no solo una garantía en contra— lo vuelve falso**; un host
que no documenta el comportamiento cuenta como falso.

**La continuidad la aporta el harness, no el transporte.** El multiplexor de terminales aloja el
proceso del implementador mientras el conductor no está mirando; despertar al conductor cuando el
comando termina es del **host** que lo corre. Alojar procesos bien no vuelve verdadero el predicado.

**Falla cerrado.** Con el predicado en falso, `background` **falla cerrado al poll acotado de hoy**:
el deadline de la tabla, el `kill` al vencer y el `UNAVAILABLE` con causa `deadline_exceeded`. El
banner obligatorio no cambia en ninguno de los dos casos — con callback es lo primero que se escribe
al despertar; con poll, lo primero después de ver `STATUS: done`.

### Rutas por invocación

Cada despacho obtiene un `invocation_id` estable, distinto del `block_id` y de la ronda. Todos sus
artefactos se escriben bajo una ruta exclusiva; una reanudación conserva el mismo identificador y un
nuevo bloque recibe otro.

| Artefacto | Plantilla de ruta |
|---|---|
| prompt | `<dir-del-work-order>/cross-implement/<invocation_id>/prompt.txt` |
| report | `<dir-del-work-order>/cross-implement/<invocation_id>/report.txt` |
| sesión | `<dir-del-work-order>/cross-implement/<invocation_id>/session.txt` |
| registro | `<dir-del-work-order>/implement-log-<invocation_id>.md` |

## Archivos de trabajo (scratch)

Junto al work order, el subdirectorio `cross-implement/<invocation_id>/` conserva el scratch de una
sola invocación (mismo criterio que `cross-review/`):

```
<dir del work order>/cross-implement/<invocation_id>/
├─ work-order.md          # solo en modo directo sin archivo: contrato destilado de esta invocación
├─ prompt.txt             # prompt-contrato (Write, nunca inline)
├─ fix-r1.txt, fix-r2.txt # deltas del fix loop de la misma sesión
├─ report.txt             # reporte vigente de esta invocación
├─ thread.jsonl           # stream JSONL del lanzamiento (Vía W-B) — fuente del thread id
├─ session.txt            # thread/session id capturado
└─ impl.err.txt           # stderr del implementador
```

En SDD resuelve a `.plans/<id>/cross-implement/<invocation_id>/`. Local y untracked, sin
autolimpieza — igual que `cross-review/` y `co-explore/`.

## Log de implementación

`implement-log-<invocation_id>.md` junto al work order
(`.plans/<id>/implement-log-<invocation_id>.md` en SDD). Registro auditable de una delegación que no
sobrescribe las anteriores:

```markdown
# Cross-implement log — <id|work order> (<ISO-8601>)
Implementador: <codex exec | claude -p>  ·  modelo: <model | CLI default>  ·  max_fix_rounds: <n>
Proof: `<proof_cmd>`

## Ronda 1 — implementación
FILES declarados: <n> · coinciden con git status: <sí/no>
Proof (corrido por el conductor): <PASS/FAIL + evidencia>
Veredicto del conductor: <aceptado | fix round: qué corregir>
Drift detectado: <ninguno | lista → revertido/declarado>
Clase de cada falla (`ownership.md`): <IMPLEMENTATION_DEFECT | VERIFICATION_DEFECT | ENVIRONMENT_FAILURE | DESIGN_GAP, una por falla — omitir la línea si el proof pasó>
¿El work order admitía otra lectura?: <no | sí: qué se entendió y qué se quiso decir — solo si hubo falla>

## Ronda 2 — fix
<ídem>

## Resultado
<IMPLEMENTED | PARTIAL (takeover: qué terminó el conductor) | UNAVAILABLE> en <n> rondas.
Desviaciones del work order: <lista o "ninguna">.
```

> **Las dos últimas líneas de cada ronda no piden trabajo nuevo: piden no tirar el que ya se hizo.**
> La clase **ya se decide en toda corrida** —`ownership.md` la exige antes del fix loop, porque de
> ella depende si la falla consume ronda—, pero hasta ahora se decidía y se evaporaba. Escribirla es
> lo que deja un rastro comparable entre corridas.
>
> <!-- corpus-invariante:inicio:cross-implement.reference.md.919a8d9922f4 -->
> **Qué pregunta contestan.** En la ruta recomendada la regla 8 manda a la familia opuesta, y su justificación es
> <!-- corpus-invariante:fin:cross-implement.reference.md.919a8d9922f4 -->
> que un implementador que no comparte los supuestos del autor **detecta la ambigüedad del contrato**
> — un work order que admite dos lecturas se delata cuando alguien elige la otra. Eso es una
> hipótesis, no un hecho medido. Si a lo largo de varias corridas casi todas las fallas son
> `IMPLEMENTATION_DEFECT` con "otra lectura: no", la regla 8 no está comprando ese detector y su
> costo hay que defenderlo por otro lado. La clase sola no alcanza para saberlo: dice **por qué
> falló la prueba**, no **si el contrato era ambiguo**; por eso van las dos.
>
> Es un registro, no un gate: no bloquea la ronda, no cambia la clasificación y no le agrega nada al
> implementador, que ni se entera.

### Qué hacer cuando el registro muestre algo

El hueco que este registro vigila es **estrecho y de una sola clase**: el par *autor del work order
<!-- corpus-invariante:inicio:cross-implement.reference.md.b95da3b4ded1 -->
↔ revisor del diff* es la misma familia, así que un contrato ambiguo lo transcribe fielmente el
<!-- corpus-invariante:fin:cross-implement.reference.md.b95da3b4ded1 -->
implementador y el revisor comparte el punto ciego que lo produjo. Todo lo demás ya cruza familia
(ver `CLAUDE.md` → regla de fronteras). **Hoy no se escribe nada para cubrirlo**, y el motivo es que
está medido en vez de discutido.

**Qué cuenta como señal:** una falla clasificada `VERIFICATION_DEFECT` o `DESIGN_GAP` **con
"¿el work order admitía otra lectura?: sí"**. Un `IMPLEMENTATION_DEFECT` con "otra lectura: no" es lo
contrario de una señal: en una corrida cross-family, es el pipeline funcionando — el implementador hizo algo
distinto de lo pedido y el conductor lo cazó.

> **El campo lo contesta el autor del work order, y eso lo vuelve asimétrico.** El conductor de esta
> skill **es** quien escribió el contrato, así que se le está pidiendo que dictamine si lo escribió
> ambiguo — que es exactamente quien peor puede verlo. No invalida el registro, pero decide cómo se
> lee:
>
> | Lo que dice el log | Cuánto vale |
> |---|---|
> | **"otra lectura: sí"** | **mucho.** Es una admisión contra el propio interés: el autor reconociendo que escribió mal. Cuando aparece, es señal real |
> | **"otra lectura: no"** | **poco.** Es el autor absolviéndose. Puede ser cierto, o puede ser el punto ciego funcionando |
>
> Consecuencia práctica sobre el conteo: **los "sí" se cuentan, los "no" no prueban nada.** Un log
> lleno de "no" no acredita que no haya hueco — es lo que el hueco predice. Por eso la condición de
> abajo cuenta apariciones de la firma y **nunca** su ausencia.
>
> La salida obvia sería que lo conteste otro. No la hay hoy: el único que ve el diff junto al
> contrato es el conductor. Se registra con el sesgo declarado, que es mejor que no registrar o que
> registrar creyéndolo neutral.

**Cuándo se reabre.** A la **primera** aparición se mira el caso; a la **segunda**, se abre flujo
propio. Las dos condiciones van juntas:

1. dos fallas con esa firma, y
2. el proyecto **no** tiene por delante una revisión de PR cross-family (`bitbucket-code-review` o
   equivalente), que cubriría el mismo punto ciego un paso después.

> **El dos es un juicio, no un umbral medido, y conviene que se sepa.** Con cero corridas
> registradas cualquier número es inventado; lo que lo fija en dos y no en diez es que las corridas
> de esta skill son pocas, así que esperar significancia estadística es esperar para siempre. Uno
> puede ser mala suerte; dos ya es un patrón que vale un flujo.

**Qué se abre, si se abre:** sede `cross-implement`, **sin skill nueva**, y con
`final_diff_review.mode` como dueño de configuración. Eso ya está decidido y no se re-litiga: lo
único que faltaba era saber si hace falta.

En modo embebido, sdd-flow referencia este log desde su flujo; el commit y el `verify` siguen
siendo de sdd-flow.
