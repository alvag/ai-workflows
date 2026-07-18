# Revisión verificada y refinamientos — Sesiones reales Claude ↔ Codex

**Estado:** revisión crítica del diseño de `README.md`, con verificación de interfaz de CLI y
decisiones de mecánica que el README dejaba abiertas. **Sometido a siete rondas de crítica de la
otra familia (cross-model); las correcciones resultantes están incorporadas** (ver "Procedencia").
Veredicto documental del revisor: **APPROVED para ejecutar el Gate 0** (como matriz). La
aprobación habilita correr el spike, no modificar skills; eso último espera a que el Gate 0 pase.

**Fecha:** 2026-07-17

**Relación con el README (precedencia):** el `README.md` define la arquitectura propuesta
(transporte `orca-session`, `worker_done`, degradación a CLI) y se conserva como **diseño original y
contexto histórico**. Este documento lo **verifica, corrige y refina**; **ante cualquier conflicto
normativo, prevalece este documento** —esta regla global cubre incluso los puntos no tabulados (p.
ej. el consentimiento al apropiarse de una terminal ajena, 2.4)—. Los **principales** puntos donde
este documento **supersede** al README —porque el README quedó desactualizado o era inseguro— son:

| Tema | README (original) | Este documento (vigente) |
|---|---|---|
| Hooks | conserva los del entorno como "capacidad" | solo el hook de coordinación; el resto se deshabilita (2.8) |
| Rol del hook `Stop` | red de seguridad / fallback | **mecanismo oficial** de `worker_done`, validando sentinel (2.8) |
| Sentinel de fin | `STATUS: done` (no universal) | **envelope común**: `STATUS: done` como última línea, en todos los modos (2.8) |
| Quién escribe el informe | el secundario escribe `reportPath` | en v1 **el conductor persiste** desde el mensaje final (§5) |
| `reportPath` | archivo existente, `parse_result(reportPath)` | **ruta destino** aún inexistente, validada dentro del área autorizada (2.8) |
| Restricción de MCP | por contrato en el prompt | **allowlist técnica** obligatoria en el lanzamiento (2.7) |
| Read-only de Claude | allowlist de tools | **toolset cerrado** (`--tools`) + MCP + `dontAsk` (§5) |

El README debería actualizarse eventualmente para absorber estos cambios; mientras tanto, esta tabla
—y la regla global de precedencia— son la fuente de verdad. Además de lo anterior, aquí se verifica la interfaz contra el CLI
real, se listan los riesgos abiertos y se resuelven cuatro preguntas de mecánica que en el README
quedaban implícitas o resueltas de forma subóptima:

1. cómo se garantiza read-only **sin** impedir que el secundario escriba su informe;
2. cómo se lanza una sesión secundaria **fresca y a plena capacidad** sin crear un worktree;
3. qué hace `cross-implement` cuando el usuario **ya está trabajando dentro de un worktree**;
4. cómo se resuelve el transporte cuando la skill se invoca **standalone**, fuera de `sdd-flow`
   (sección 8).

---

## 1. Verificación de la interfaz (lo que el README no pudo ejecutar)

El README declara honestamente (sección "Capacidades locales verificadas") que en su corrida
`orca status --json` devolvió `stale_bootstrap` y `app.running: false`, por lo que solo pudo
inspeccionar la interfaz, sin un ciclo extremo a extremo. En esta sesión se verificó esa interfaz
con `--help` sobre los binarios reales.

### Orca — subcomandos de orchestration (confirmados)

| Comando | Flags relevantes confirmados |
|---|---|
| `orchestration task-create` | `--spec`, `--task-title`, `--display-name`, `--deps`, `--parent` |
| `orchestration dispatch` | `--task`, `--to`, `--from`, `--inject`, `--dry-run`, `--return-preamble` |
| `orchestration send` | `--to`, `--subject`, `--type`, `--task-id`, `--dispatch-id`, `--files-modified`, `--report-path`, `--phase`, `--payload` |
| `orchestration check` | `--terminal`, `--unread`/`--peek`/`--all`, `--types`, `--wait`, `--timeout-ms`, `--inject` |
| `orchestration reply` | `--id`, `--body`, `--from` |

Las *Notes* del propio CLI confirman la **semántica de autoridad de finalización** que el README
propone:

- «worker_done and heartbeat must target a concrete coordinator terminal handle» — valida usar
  handle concreto y no `@codex`/`@claude` (README, "Descubrimiento de sesiones").
- «A worker_done with the active task/dispatch IDs completes that task only from the dispatched
  pane … the sender handle must exactly match the dispatch assignee; injected preambles include
  the correct --from value» — valida la composición de autoridad `sender + taskId + dispatchId`
  (README, "Finalización falsa").
- `check --wait` «emits JSON keepalive lines to stderr every 15s» — confirma que la espera del
  principal está pensada para bloquear sin morir por inactividad.

**Conclusión:** el protocolo del README no está inventado. Todos los flags existen tal como se
usan, y la semántica de `worker_done` coincide con la documentada por el CLI.

### Orca — terminales (confirmados)

- `terminal create [--worktree <sel>] [--command <text>] [--title] [--focus]`
- `terminal send [--terminal <h>] [--text] [--enter] [--interrupt]`
- `terminal wait [--terminal <h>] --for exit|tui-idle [--timeout-ms]`
- `terminal read [--terminal <h>] [--cursor <n>] [--limit]`
- `terminal list [--worktree <sel>] --json`

`orca worktree create` admite `--agent`, `--prompt`, `--base-branch`, `--parent-worktree` y
`--no-parent`.

### Codex — sandbox y aprobación (confirmados)

- `-s, --sandbox <read-only | workspace-write | danger-full-access>` — aplica a la TUI
  interactiva, no solo a `exec`.
- `-a, --ask-for-approval <untrusted | on-failure | on-request | never>`.
- `-C, --cd <DIR>` fija la raíz de trabajo; `--add-dir <DIR>` agrega directorios escribibles
  «alongside the primary workspace».
- `-c key=value` para override de config; `exec` además ofrece `-o/--output-last-message <FILE>`.

### Lo que sigue SIN verificar (y por qué importa)

La interfaz existe, pero el **comportamiento dinámico** no se ejecutó porque el runtime estaba
caído. En particular:

- que `dispatch --inject` **haga arrancar un turno nuevo** en un `codex`/`claude` **interactivo ya
  vivo** (no un `exec` nuevo);
- que el **hook de coordinación emita `worker_done`** al terminar, en **ambas familias** — en
  particular en Claude read-only, que no tiene `Bash` para correr el comando (hallazgo 2.8), y en
  Codex read-only, donde la llamada al runtime de Orca puede chocar con la restricción de red del
  sandbox;
- que la **lectura del repo siga disponible** cuando la raíz de trabajo (`-C`) del secundario se
  mueve fuera del repo (ver sección 5);
- que `terminal list --json` **etiquete la familia** (Claude/Codex) de cada terminal, base del
  descubrimiento automático;
- que `terminal read` **extraiga el informe íntegro** desde la TUI del secundario, sin truncar ni
  arrastrar adornos de la interfaz — de esto depende el default de v1 "el conductor persiste"
  (sección 5).

Estos cinco puntos son el verdadero riesgo del diseño y deben resolverse en un spike antes de
tocar las skills (ver sección 2, hallazgo 1).

**Dato empírico (2026-07-18): el estado del runtime depende de dónde se lo consulte.** Al ejercitar
a mano un handoff real (conductor Claude → terminal del revisor Codex, vía `terminal send`/`read`),
se observó que `orca status` devuelve **resultados distintos según el contexto de ejecución**: desde
un shell libre, `app.running: true` / `runtime.state: ready`; desde **dentro del sandbox del agente
Codex**, `app.running: false` / `stale_bootstrap` / `reachable: false` / `terminal list:
runtime_unavailable`. Esto es **evidencia directa del hallazgo 2.8(a)**: el sandbox del secundario
puede no alcanzar el runtime de Orca, lo que pondría en duda que el secundario pueda emitir
`worker_done` por comando y refuerza la vía del **hook de coordinación**. Caracterizar esta
diferencia (¿el hook corre fuera del sandbox y sí alcanza el runtime?) pasa a ser parte del Gate 0.
El estado del runtime debe registrarse siempre como **snapshot fechado**, no como causa permanente.

---

## 2. Revisión crítica del diseño propuesto

Ocho observaciones sobre `README.md`, ordenadas por severidad.

### 2.1 El eslabón que sostiene todo es justo el no verificado (crítico)

Todo el diseño depende de que `dispatch --inject` dispare un turno en una TUI viva y de que el
secundario emita `worker_done`. Ninguna de las dos cosas se probó. **Recomendación:** convertir el
punto 6 de la Fase 1 del README en un **Gate 0 explícito y bloqueante** que demuestre
inject-dispara-turno + worker_done-reactiva-al-principal + `terminal read` extrae el informe
íntegro, **antes de escribir una línea en las skills**. Hoy el plan lo trata como validación
posterior; debe ser precondición. La lista completa a validar son los cinco puntos de la sección 1.

**El Gate 0 debe ser una matriz, no un solo dispatch.** Como el diseño exige validar `worker_done`
por hook **en ambas familias** (sección 1) y el envelope de sentinel se modificó en un modo
concreto (`cross-review`), un único probe Claude→Codex/`explore` **no basta** — solo probaría el
hook de Codex y no ejercitaría el envelope nuevo. La matriz mínima:

1. **Claude principal → Codex secundario** (`explore`): inject, hook de Codex, `terminal read`.
2. **Codex principal → Claude secundario** (`explore`): valida el hook de **Claude** notificando
   sin `Bash` (hallazgo 2.8) y a Claude como secundario.
3. **Al menos un dispatch `cross-review`** (cualquier dirección): valida específicamente el envelope
   `VERDICT: … ` + `STATUS: done` como última línea; un probe solo-`explore` no lo cubre.

### 2.2 Read-only pasa de garantía dura a confianza + detección (regresión)

Hoy `codex exec -s read-only` es un sandbox del sistema operativo: el secundario **no puede**
escribir aunque el modelo se descarríe. El README (sección "Seguridad y aislamiento") reemplaza
esa garantía por contrato en el prompt + verificación de `git status` a posteriori, y lo presenta
como suficiente sin señalar que es **más débil** que el estado actual. La sección 5 de este
documento muestra cómo recuperar la garantía dura sin perder la escritura del informe, moviendo la
frontera del sandbox en lugar de aflojarla.

### 2.3 Reutilizar sesión viva rompe la independencia de co-explore (importante)

El valor central de `co-explore` (explore/counter-plan/debate) son **dos mapas independientes**. El
`codex exec` fresco de hoy garantiza independencia porque arranca de cero. Una sesión secundaria
**persistente reutilizada** ya vio trabajo previo — y si en esa terminal se discutió el enfoque del
principal, el "segundo par de ojos" queda contaminado. El README reconoce el contexto contaminado
en general ("Riesgos") pero no lo conecta con que la independencia es más frágil justo en los modos
de co-explore.

**Recomendación:** el flujo usa **dos sesiones secundarias, no una**, separadas por nivel de
permiso — el sandbox se fija al lanzar el proceso y, aunque elevarlo en caliente es posible en
Codex, esa vía no está verificada vía Orca y no se adopta en v1 (ver 2.6):

- **Sesión dedicada read-only** (`-s read-only`), creada fresca al inicio:
  - `co-explore` explore/counter-plan/debate → **la estrena** (primer uso, sin contaminar →
    preserva la independencia; ver sección 4).
  - `cross-review` → **reutiliza** esa misma sesión read-only. El contexto acumulado *dentro del
    propio flujo SDD* ayuda (el revisor ya conoce la spec cuando critica el plan) y no rompe la
    independencia entre familias, que es la que importa.
- **Sesión write-capable aparte** (`-s workspace-write`), creada solo si el flujo llega a
  `cross-implement`. No reutiliza la read-only (ver 2.6).

"Reutilizar" significa siempre una sesión del flujo, **no** una terminal ajena preexistente del
usuario.

### 2.4 «idle» no es «libre»: falta consentimiento al reutilizar (caso borde)

El descubrimiento del README solo pregunta cuando hay **varios** candidatos. El caso peligroso es
**un único** candidato que resulta ser la sesión de trabajo del usuario, momentáneamente idle
porque está leyendo, no porque esté libre; el `dispatch --inject` le pisa el turno.
**Recomendación:** el consentimiento aplica **solo a terminales ajenas al flujo** — sesiones
preexistentes del usuario que el flujo se propone apropiar. Ahí confirmar una vez aunque el
candidato sea único. Si en cambio fue **el propio flujo** el que creó la sesión secundaria
dedicada, no se vuelve a preguntar en los reusos posteriores (cross-review, cross-implement): ya es
del flujo.

### 2.5 Suposiciones menores sin confirmar

- **Detección de familia** del terminal (README, "Descubrimiento de sesiones", paso 7): asume que
  `terminal list --json` expone qué CLI corre. Si no lo hace, el descubrimiento automático degrada
  a "preguntar siempre".
- **Costo de tokens del principal**: el principal "queda despierto" en el bucle de `check --wait`.
  Con un secundario a plena capacidad (más lento que el `exec` acotado porque usa MCP y más
  razonamiento), el principal puede consumir bastante turno esperando. No es bloqueante, pero el
  README no lo menciona como costo.

### 2.6 Transición de permisos read-only → implementación (bloqueante)

El sandbox de codex se fija **al lanzar el proceso** (`-s read-only` vs `-s workspace-write`); en
Claude, el nivel de permiso sobre archivos se fija por el **toolset de lanzamiento** (`--tools`;
sección 5). Elevar el permiso de una
sesión ya viva **no es imposible en Codex**: el app-server 0.144.5 expone
`ThreadSettingsUpdateParams.sandboxPolicy` y `TurnStartParams.sandboxPolicy`, que cambian el
sandbox de los turnos siguientes (y el override por turno queda como default posterior; ver Codex
App Server, https://learn.chatgpt.com/docs/app-server). Pero esa elevación **no está verificada por
la vía Orca/TUI** (no se sabe si `dispatch --inject` puede acompañarla), y aumenta el riesgo de una
sesión que empezó read-only y termina escribiendo. Por eso **en v1 no se adopta**: la sesión
dedicada read-only de co-explore/cross-review **no se reutiliza para `cross-implement`**, que exige
escritura (`skills/cross-implement/reference.md` la lanza con `workspace-write` o permisos
path-scoped). Unificarlas por elevación de sandbox queda como trabajo futuro con su propio spike,
no como algo descartado por imposible.

**Decisión para v1:** dos sesiones secundarias separadas por permiso.

- **read-only** — co-explore + cross-review (comparten permiso; la reutilización de 2.3 aplica solo
  entre estos dos).
- **write-capable** — `cross-implement`, sesión propia lanzada `-s workspace-write`. Como recibe un
  work order **congelado** y autocontenido, no necesita heredar el contexto conversacional de la
  read-only; puede ser fresca sin pérdida. Corre en el mismo worktree, escritor único (sección 6).

La continuidad de contexto entre revisión e implementación se sacrifica en v1 a cambio de no
mezclar niveles de permiso en una sola sesión. Unificarlas queda como trabajo futuro, tras un
spike dedicado.

### 2.7 El sandbox no cubre los MCP externos (bloqueante)

El sandbox de codex (`read-only` / `workspace-write`) y el toolset cerrado (`--tools`) de Claude
gobiernan
**filesystem y ejecución de comandos**, **no las tools MCP**. Una tool MCP que crea un issue de
Jira, comenta en Confluence, sube a Drive o modifica un PR de Bitbucket **no es un comando de
shell**: se ejecuta por un canal que el sandbox no intercepta y que `git diff` no registra. Por lo
tanto:

- una sesión `-s workspace-write` (cross-implement) puede escribir en sistemas externos aunque el
  working tree quede intacto;
- incluso una sesión `-s read-only` (co-explore/cross-review) puede hacerlo: read-only es sobre el
  **código**, no sobre los MCP.

Esto viola directamente la regla del usuario de **nunca escribir en Atlassian sin pedido
explícito**, y la verificación de `git status` de la sección 6 es ciega a ello. Es el hueco de
seguridad más serio del diseño.

**Requisito duro (ambos tipos de sesión, ambas familias):** el rol del secundario debe habilitar
**solo tools MCP de lectura, enumeradas explícitamente**, y **deshabilitar toda operación MCP de
escritura externa**. Codex soporta control de tools por configuración (`enabled_tools` /
`disabled_tools` y approval por herramienta, según la Configuration Reference,
https://learn.chatgpt.com/docs/config-file/config-reference); Claude, por allowlist enumerada
(sección 5). La **sintaxis exacta** de esa config es uno de los ítems a fijar en el Gate 0, pero el
requisito es innegociable: sin lista blanca de MCP, la sesión no se despacha. "Tener acceso al
servidor MCP no equivale a autorizar sus escrituras."

### 2.8 Notificación y hooks: la tercera superficie de efectos laterales (bloqueante)

Dos problemas conectados que comparten mecanismo.

**(a) El secundario read-only no puede auto-notificar por comando.** El protocolo del README pide
que el secundario ejecute `orca orchestration send --type worker_done`. Pero en la sesión read-only
de Claude el **toolset cerrado no incluye `Bash`** (sección 5, `--tools "Read,Grep,Glob"`) — sin él,
no puede correr ese comando. En Codex read-only la ejecución de comandos podría permitirse, pero una
llamada al runtime de Orca puede requerir red/socket que el sandbox read-only restringe: tampoco
está garantizado.

**(b) Los hooks son una tercera vía de escritura, no cubierta por sandbox ni por MCP.** El README
lista "conservar hooks" como parte de "máxima capacidad". Pero los hooks ejecutan efectos por su
cuenta: Claude admite hooks automáticos de shell, HTTP y MCP; Codex carga hooks de usuario,
proyecto y plugins, y **ejecuta todos los que coinciden** (Hooks de Claude Code,
https://code.claude.com/docs/en/hooks; Hooks de Codex, https://learn.chatgpt.com/docs/hooks). Un
hook del entorno del usuario podría escribir en un sistema externo durante la sesión secundaria, sin
pasar por el filesystem ni por una tool MCP.

**Solución integrada (v1):** el mecanismo **oficial** de `worker_done` es un **hook de coordinación
auditado** —no un comando que el modelo ejecuta, ni un mero fallback—, y ese es **el único hook que
se conserva**:

- El hook de coordinación (Stop en Claude; el evento equivalente en Codex) emite el `worker_done`.
  Esto resuelve (a) sin darle `Bash` al modelo, en ambas familias.
- **Todos los demás hooks se deshabilitan** en las sesiones secundarias. "Máxima capacidad" pasa a
  significar: modelo, config, MCP de lectura e historial — **no** hooks arbitrarios.
- Deshabilitar hooks sin apagar MCP requiere un mecanismo por familia (p. ej. lanzar con un
  `settings`/config dedicado): parte del Gate 0.

**Qué valida el hook antes de emitir `worker_done` (evitar el deadlock informe ↔ notificación).** En
v1 el secundario **no escribe un archivo de informe**; el conductor lo persiste *después*, leyendo
el mensaje final (sección 5). Por lo tanto el hook **no puede** condicionar la notificación a "existe
el archivo del informe" —nunca existiría, y el conductor esperaría un `worker_done` que nunca
llega—. La condición correcta es un **sentinel estructurado en el mensaje final del asistente**
(`last_assistant_message`, expuesto por los Stop hooks de ambas familias).

**El sentinel debe ser universal, y hoy no lo es.** Los formatos de salida difieren por skill:
`co-explore` y `cross-implement` ya cierran con `STATUS: done`
(`skills/co-explore/reference.md`, `skills/cross-implement/reference.md`), pero `cross-review`
cierra con `VERDICT: APPROVED | REVISE` (`skills/cross-review/reference.md`), **sin** `STATUS:
done`. Un hook que exija `STATUS: done` **nunca notificaría en cross-review**. La solución es un
**envelope común para el transporte Orca**: la salida específica del modo seguida de una línea
sentinel única:

```text
<salida específica del modo — hallazgos, o VERDICT: …, o reporte>

STATUS: done
```

El hook exige `STATUS: done` como **última línea no vacía** (no "que aparezca en alguna parte", para
que un `STATUS: done` citado en el cuerpo no dispare una notificación falsa). Esto implica un cambio
menor en `cross-review`: agregar la línea sentinel tras su `VERDICT:` cuando el transporte es
`orca-session` (registrado en la sección 7). Secuencia:

1. el secundario termina su turno con la salida del modo **en su mensaje final**, cerrada por
   `STATUS: done` como última línea;
2. el hook valida: existe dispatch activo, `taskId`/`dispatchId` coinciden, `STATUS: done` es la
   **última línea no vacía** de `last_assistant_message`, y aún no se envió `worker_done`;
3. el hook emite `worker_done`;
4. recién entonces el conductor lo recibe, **extrae el informe del mensaje final** (`terminal read`)
   y lo persiste en la ruta destino (ver "reportPath" abajo).

Así la notificación depende del sentinel (que sí existe al terminar), no del archivo (que el
conductor escribe después).

**`reportPath` en v1 es una ruta destino, no un archivo existente.** El README histórico valida un
`reportPath` **existente** y ejecuta `parse_result(message.reportPath)` (README "Pseudocódigo de un
dispatch"). En v1 ese archivo **aún no existe** cuando llega `worker_done`: el conductor lo escribe
después. Por lo tanto `reportPath` se redefine como **la ruta destino donde el conductor
persistirá** el informe extraído del mensaje final. Antes de escribir, el conductor valida la ruta
con **contención canónica**, no una simple comprobación de prefijo — porque `reportPath` llega en un
mensaje del secundario y es una entrada no confiable:

- rechazar **rutas absolutas** y cualquier segmento `..`;
- como el destino aún no existe, resolver el **`realpath` del directorio padre** y exigir que quede
  **dentro** de la raíz autorizada del dispatch (`.plans/<id>/…`), de modo que un **symlink** que
  escape también se rechace;
- solo entonces escribir. Un `worker_done` con un `reportPath` que falle la contención se **rechaza,
  no se escribe** (y se reporta como intento de escape).

(Alternativa descartada: omitir `reportPath` y derivarlo del dispatch; se prefiere pasarlo explícito
para que quede auditado.)

**Al Gate 0 se agrega:** validar la vía de `worker_done` para **ambas** familias (hook de
coordinación validando `STATUS: done` como última línea de `last_assistant_message` y disparando el
`send`), e **inventariar y neutralizar** los hooks del entorno salvo el de coordinación.

**Veredicto general:** diseño viable, honesto y bien separado (qué / cuándo / cómo / cómo vuelve).
No se reescribe. Antes de implementar son innegociables la **lista blanca de MCP (2.7)** y la
**política de hooks + notificación por hook de coordinación (2.8)** — sin ellas la sesión no se
despacha. Luego, en orden: (a) el Gate 0 de 2.1; (b) el default de lanzamiento read-only +
conductor persiste de la sección 5; (c) la separación de sesiones por permiso de 2.3 y 2.6.

---

## 3. Corrección sobre worktrees

Aclaración que atraviesa las secciones 4 a 6, porque el usuario suele trabajar **ya dentro de un
worktree** (p. ej. el proyecto `results`).

- **Git no anida worktrees.** Todo `git worktree add`, se lance desde donde se lance, crea un
  **hermano** que cuelga del mismo repositorio (comparten el `.git` común). No existe "un worktree
  del worktree". Orca modela una relación parent/child (`--parent-worktree`) para su UI de
  orquestación, pero en disco siguen siendo pares.
- **Una sesión fresca no requiere un worktree nuevo.** Son ejes independientes: "fresca" es un
  proceso de agente sin historial; "worktree" es un checkout. Se puede tener lo primero sin lo
  segundo (sección 4).
- **Para roles read-only, un worktree separado es innecesario y costoso.** En proyectos pesados
  (`results`: Angular, `node_modules`, build) un checkout nuevo cuesta minutos y disco. Para
  operaciones de solo lectura no aporta nada: el secundario lee el mismo working tree.

---

## 4. Lanzar la sesión secundaria: fresca y a plena capacidad

La pieza que faltaba para conciliar "independiente" con "al 100%" es una terminal real con el rol
acotado en el propio comando de lanzamiento (read-only para co-explore/cross-review):

```bash
orca terminal create --worktree active --command "codex -s read-only -a never"
```

Abre una **terminal nueva en el worktree activo** corriendo el binario `codex` real — con su
config (`~/.codex/config.toml`: modelo y esfuerzo del usuario) y sus MCP autenticados. **No es** una
sesión acotada con `codex exec`: es una sesión interactiva completa. La restricción de rol la dan
tres capas de lanzamiento —sandbox (`-s`), config de tools MCP (2.7) y política de hooks (2.8)—, no
una degradación del modelo. Para Claude, análogo con `--command "claude"` más el toolset cerrado
(`--tools`) y las reglas MCP de la sección 5.

Esa sesión es **fresca** (proceso nuevo, sin historial → recupera la independencia epistémica de
co-explore) **y completa** (config y MCP de lectura) **a la vez**, y en el **mismo worktree** (lee
el mismo código). Las tres propiedades juntas, sin checkout nuevo. Esto corrige el supuesto
implícito de atar "sesión fresca" a "worktree/sandbox nuevo". (Los **hooks** del entorno **no** se
conservan salvo el de coordinación; ver 2.8: "máxima capacidad" no incluye ejecutar hooks
arbitrarios.)

> **Los comandos de este documento son esqueletos, no comandos finales.** Muestran la capa de
> **sandbox/aprobación** (`-s … -a …`) para no cargar cada ejemplo con todo, pero el rol real exige
> las **tres capas** (sandbox + perfil de tools MCP + aislamiento de hooks; 2.7 y 2.8). La sintaxis
> de las capas 2 y 3 se fija en el Gate 0. Hasta entonces, ningún comando de este documento es
> ejecutable tal cual, y ninguna sesión se lanza como `codex`/`claude` pelado ni solo con sandbox.

Modelo mental por modo. La sesión dedicada se **crea una vez** (fresca) y luego se **reutiliza**
dentro del mismo flujo:

| Modo | Sesión secundaria | Permiso | Worktree |
|---|---|---|---|
| co-explore | **crea** la dedicada, fresca (`terminal create --command "codex -s read-only -a never"`) | read-only | **el mismo** (activo) |
| cross-review | **reutiliza** la dedicada read-only | read-only | **el mismo** (activo) |
| cross-implement | **sesión aparte**, write-capable (`-s workspace-write`; ver secciones 2.6 y 6) | workspace-write | **el mismo**, salvo opt-in |

En v1 no se eleva el permiso de una sesión viva: cross-implement usa una sesión propia, no la
read-only (hallazgo 2.6). Una terminal preexistente y ajena al flujo solo se toma con
consentimiento (hallazgo 2.4).

---

## 5. Read-only con escritura del informe: mecánica de lanzamiento

### La contradicción aparente

"Solo lectura" en el mundo cross-review nunca significó "no escribe nada": significó **no tocar el
código del producto**. El informe siempre fue una salida legítima. El problema real es permitirle
escribir **su** archivo sin abrirle la escritura del resto.

### El sandbox es todo-o-nada sobre el "workspace"

Verificado: `read-only` no deja escribir nada (ni el informe); `workspace-write` deja escribir todo
el workspace. **No existe un "escribí solo este archivo"** a nivel sandbox. Pero sí se puede mover
*dónde* está la frontera del workspace.

### Default de v1: el conductor persiste (read-only duro desde la raíz)

Para la **primera versión** se usa el patrón ya probado y de máxima garantía: el secundario corre
`-s read-only` desde la raíz del repo, **no escribe nada**, emite el informe como su mensaje final,
y **el principal** lo vuelca en el artefacto típico (con `terminal read`, o el patrón
`--output-last-message` de `exec`). Es idéntico al comportamiento actual; la única diferencia
respecto de "que el secundario escriba" es *quién teclea el archivo*, y a cambio conserva el
sandbox del SO como garantía dura. Se adopta esto hasta que el Gate 0 valide la forma óptima de
abajo.

```bash
orca terminal create --worktree active --command "codex -s read-only -a never"
```

### Forma óptima (a validar en Gate 0): el workspace escribible ES la carpeta del informe

> **No adoptar en v1.** Depende de que Codex conserve la lectura del código del repo cuando la raíz
> escribible (`-C`) se estrecha a un subdirectorio — uno de los cinco puntos sin verificar
> (sección 1). Habilitarla solo después de que el Gate 0 lo confirme.

En `workspace-write`, la **lectura es amplia** (el agente lee el disco) y solo la **escritura** se
limita al workspace (el `-C`/cwd) más lo agregado con `--add-dir`. La jugada es apuntar `-C` a la
carpeta de artefactos, que **es un subdirectorio del propio repo** (`.plans/…`), no un lugar fuera
de él; así esa carpeta queda como única raíz escribible y el resto del repo, incluido el código,
queda fuera de la **raíz escribible** (pero dentro del repo y legible):

```bash
orca terminal create --worktree active \
  --command "codex -s workspace-write -a never -C .plans/<id>/cross-review"
```

Resultado:

- **Escritura:** solo `.plans/<id>/cross-review/` — ahí escribe su informe (`spec-r1.md`). ✓
- **Código del producto:** queda *fuera de la raíz escribible* → lo **lee pero no lo puede
  escribir**. Read-only sobre el código **por sandbox**, no por promesa. ✓
- **Entrada:** puede leer `spec.md` / `plan.md` (están en `.plans/`, legibles).

`-a never` es esencial en una sesión desatendida: sin él, ante un intento de escritura el codex se
cuelga esperando aprobación en la TUI y no hay nadie mirando; con `never`, el intento falla y el
error vuelve al modelo, que se reencauza, sin bloquear.

**Salvedad:** que la lectura del código siga disponible cuando la raíz escribible se estrecha a
`.plans/…` es el comportamiento normal del seatbelt de codex, pero es justo uno de los cinco puntos
sin verificar (sección 1). Debe confirmarse en el Gate 0.

### Variante más laxa (solo cross-implement)

- **`workspace-write` pleno + `git diff`:** se le permite escribir el repo entero, con contrato
  "solo tu informe/código", y el principal audita con `git status`. Como el informe vive en
  `.plans/` (untracked), cualquier cambio en código *tracked* salta al instante y el informe no
  ensucia el diff. Es confianza + detección, no garantía dura; se reserva para `cross-implement`,
  donde el secundario debe escribir código de verdad.

### Claude secundario

Claude no tiene sandbox del SO como codex, así que el read-only se compone de tres piezas de flags —
y **`--allowedTools` por sí solo NO alcanza**: solo *pre-aprueba* tools, no cierra el toolset; las
no enumeradas siguen disponibles y, en sesión desatendida, o cuelgan pidiendo aprobación o se
ejecutan si otra config las permite (verificado contra `claude --help`).

1. **`--tools "Read,Grep,Glob"`** — cierra el **toolset de built-ins**: `Write`/`Edit`/`Bash`
   dejan de existir para la sesión. Esta es la garantía dura para filesystem/exec, análoga al
   sandbox de codex. (`--tools` gobierna solo built-ins, no MCP.)
2. **Reglas MCP explícitas** — como `--tools` no cubre MCP, las tools MCP se enumeran aparte, solo
   las de lectura. **No usar wildcards de servidor:** `mcp__atlassian__*` habilitaría también las de
   **escritura** (`createJiraIssue`, `addCommentToJiraIssue`, `transitionJiraIssue`), lo que rompe
   el read-only y podría **escribir en Jira/Confluence real**.
3. **`--permission-mode dontAsk`** — para que en una sesión desatendida nada quede colgado esperando
   una aprobación que nadie dará.

```bash
claude --tools "Read,Grep,Glob" --permission-mode dontAsk \
  --allowedTools "mcp__atlassian__getJiraIssue,mcp__atlassian__searchJiraIssuesUsingJql,\
mcp__atlassian__getConfluencePage,mcp__context7__query-docs"
```

> **Esqueleto, no comando final.** La semántica exacta de `dontAsk` frente a tools MCP no
> enumeradas, y la sintaxis de la regla que **deniega** el resto de los MCP, se fijan en el Gate 0.
> Falta además el aislamiento de hooks (2.8). Hasta entonces no es un comando ejecutable tal cual.

Cada MCP habilitado se revisa tool por tool: tener acceso al servidor no equivale a autorizar sus
escrituras. Como este arreglo es más frágil que el seatbelt de codex (una tool MCP de escritura
olvidada basta para romperlo), para Claude secundario el default "el conductor persiste" es el más
seguro.

### Tres superficies de efectos laterales, tres controles (Codex y Claude)

El sandbox de archivos **no es la única frontera**. Un secundario tiene tres vías de causar efectos,
y cada una necesita su propio control en el comando de lanzamiento:

1. **Filesystem / exec** → sandbox (`-s read-only` en codex; **toolset cerrado** `--tools "Read,Grep,Glob"` en
   Claude).
2. **Tools MCP → sistemas externos** (hallazgo 2.7): el sandbox no las gobierna — una sesión
   `-s read-only` igual podría crear un issue de Jira. Se restringen por config:
   - **Codex:** solo tools MCP de lectura, escritura externa deshabilitada (`enabled_tools` /
     `disabled_tools` / approval por herramienta, Configuration Reference de Codex), por `-c` o un
     perfil dedicado; sintaxis exacta al Gate 0.
   - **Claude:** la allowlist enumerada de arriba (no incluir tools MCP de escritura).
3. **Hooks → shell/HTTP/MCP automáticos** (hallazgo 2.8): tampoco los cubre el sandbox ni la lista
   de MCP. Se **deshabilitan todos** salvo el **hook de coordinación** que emite `worker_done`;
   mecanismo por familia a fijar en el Gate 0.

Regla: **sin las tres capas resueltas (sandbox + lista blanca de MCP + política de hooks), la sesión
no se despacha**, sea read-only o write-capable.

### Principio

La restricción del secundario va **en el comando de lanzamiento**, en las **tres capas
independientes** de arriba (filesystem, MCP, hooks), nunca en el prompt: el prompt solo da la tarea
y el formato del informe. En v1 los hallazgos llegan al artefacto típico porque **el conductor los
persiste** (default de v1); la escritura directa por el secundario en la carpeta de artefactos es la
forma óptima, supeditada al Gate 0.

---

## 6. `cross-implement` cuando ya se trabaja dentro de un worktree

### Por default NO se crea un worktree nuevo

Hoy `cross-implement` corre `codex exec -s workspace-write -C <working_dir>` sobre el **mismo
working tree** del principal. La seguridad no viene de aislar en otro worktree sino de la regla de
**escritor único**: mientras el secundario implementa, el principal no toca código; al terminar, el
principal hace `git diff` sobre ese mismo tree y lo revisa como un PR ajeno. Nada se commitea hasta
el gate humano.

Con Orca es igual: el secundario es **otro terminal en el mismo worktree**, no otro worktree —
pero **una sesión distinta de la read-only** de co-explore/cross-review, lanzada con permiso de
escritura (`orca terminal create --worktree active --command "codex -s workspace-write -a never"`),
porque v1 no eleva el permiso de una sesión viva (hallazgo 2.6). En un proyecto como `results` esto
es lo deseable:

- **Cero setup:** el worktree ya tiene `node_modules` y build; el secundario puede correr la prueba
  (`proof_cmd`) de inmediato. Un worktree nuevo arrancaría vacío (`npm install`, minutos, disco) y
  quizá ni pueda ejecutar la prueba.
- **Diff directo:** se revisa `git diff` en el mismo lugar, sin traer nada de vuelta.

### Por qué un worktree hermano molesta en este caso

Además del costo de setup, choca con una regla dura de git:

> Un branch no puede estar checkouteado en dos worktrees a la vez.

El worktree del secundario **no podría estar en el branch del usuario** — necesitaría uno propio
(p. ej. `…-cross`) basado en el mismo commit, y luego habría que **mergear/aplicar ese branch de
vuelta**. Ese paso de integración, más el checkout nuevo, es fricción que rara vez compensa para un
`cross-implement` puntual.

### Cuándo SÍ conviene un worktree hermano (opt-in)

- Se quiere **seguir trabajando en paralelo** mientras el secundario implementa (con el mismo tree
  no se puede: hay un solo escritor).
- El cambio es **grande o riesgoso** y no se quiere que toque el working tree hasta aprobar.
- El tree está **sucio** y no se quiere limpiar (ver siguiente punto).

En esos casos se acepta: branch propio del secundario, setup del worktree e integración del diff.
En `results`, rara vez vale la pena.

### El clean-tree gate importa más en el mismo worktree

Como el secundario escribe en el working tree del usuario, el `git diff` de revisión solo es
legible si se **parte de un tree limpio**. Si se está a mitad de un cambio sin commitear y se pide
`cross-implement`, el diff mezclará los cambios propios con los del secundario y no podrá revisarse
"como PR ajeno". Por eso el README exige un *clean-tree gate antes del dispatch*: commitear o
stashear lo propio primero — o, si no se quiere, ese es exactamente el caso donde el worktree
hermano gana.

### Resumen de política de worktree

| Modo | Escritura del secundario | Worktree |
|---|---|---|
| co-explore / cross-review | **ninguna** en v1: read-only + el conductor persiste el informe (sección 5) | **el mismo** |
| cross-implement (normal) | código, en el working tree, escritor único | **el mismo**, tree limpio |
| cross-implement (aislado, opt-in) | código, en su branch | **hermano** (branch propio + integrar diff) |

Nunca "worktree del worktree": o el mismo worktree, o un hermano del repo con branch propio.

---

## 7. Impacto en el plan de implementación del README

Ajustes recomendados sobre el plan por fases del README, sin cambiar su estructura:

0. **Precondición de seguridad (bloqueante, antes que nada):** definir las **tres capas de control**
   por rol y familia — (a) lista blanca de MCP, solo lectura (2.7); (b) política de hooks: todos
   deshabilitados salvo el de coordinación (2.8); (c) el sandbox de filesystem. Sin las tres,
   ninguna sesión secundaria se despacha. Fijar en el Gate 0 la sintaxis exacta
   (`enabled_tools`/`disabled_tools` de Codex; mecanismo para apagar hooks sin apagar MCP en cada
   familia).
1. **Gate 0 (nuevo, bloqueante) antes de la Fase 1:** **matriz** de dispatches (no uno solo; ver
   hallazgo 2.1) que valide los cinco puntos de la sección 1 — inject-dispara-turno, `worker_done`
   por hook de coordinación, lectura del código con la raíz escribible estrechada, etiquetado de
   familia en `terminal list`, y extracción íntegra con `terminal read`. La matriz mínima:
   **(a)** Claude→Codex `explore`; **(b)** Codex→Claude `explore` (valida el hook de Claude sin
   `Bash`); **(c)** un `cross-review` en cualquier dirección (valida el envelope `VERDICT:` +
   `STATUS: done`). Más la sintaxis de las listas del punto 0, el **inventario/neutralización de
   hooks**, y caracterizar el **acceso al runtime desde dentro del sandbox** (dato empírico de la
   sección 1). Si `--inject` no arranca turno, el diseño no procede.
2. **Fase 1 (co-explore explore):** crear la sesión dedicada **read-only** fresca con `terminal
   create --command "codex -s read-only -a never"` (sección 4) y el conductor persiste el informe
   (sección 5). El `-C`-a-carpeta-del-informe **no** entra en v1.
3. **Reutilización dentro del flujo:** **cross-review** reutiliza la sesión dedicada read-only de la
   Fase 1 (hallazgo 2.3), sin re-preguntar. **cross-implement no la reutiliza**: usa una sesión
   write-capable aparte (hallazgo 2.6). El consentimiento del hallazgo 2.4 aplica **solo** al
   apropiarse de una terminal ajena al flujo (preexistente del usuario).
4. **cross-implement (Fase 4):** lanzar una **sesión write-capable propia** (`-s workspace-write`),
   nunca elevar la read-only; y documentar la política de worktree de la sección 6 (mismo worktree +
   escritor único + clean-tree gate; hermano solo opt-in) y el caso "el usuario ya está en un
   worktree".
5. **Seguridad:** en v1, el read-only fuerte se compone de **tres capas** (hallazgos 2.7 y 2.8): el
   sandbox `-s read-only` desde la raíz para el filesystem, la lista blanca de MCP para los sistemas
   externos, **y** la política de hooks (solo el de coordinación); más el conductor persiste el
   informe. La frontera de sandbox con `workspace = carpeta del informe` se registra como
   optimización **habilitable solo tras el Gate 0**. El `--tools` cierra los built-ins y la
   config de MCP enumera tools de lectura concretas, nunca wildcards de servidor, en ambas familias
   (sección 5).
6. **Envelope de fin común + `reportPath` (protocolo, 2.8):** para el transporte `orca-session`,
   todos los modos cierran su salida con `STATUS: done` como última línea; **`cross-review` debe
   agregar esa línea** tras su `VERDICT:` (hoy no la emite). El hook valida esa última línea antes
   de `worker_done`. `reportPath` se trata como **ruta destino** que el conductor escribe tras
   recibir la notificación, validando que caiga dentro del área autorizada del dispatch.

---

## 8. Invocación standalone (fuera de sdd-flow)

Las secciones anteriores encuadran el transporte dentro de `sdd-flow`, pero `co-explore`
(investigate/debate), `cross-review` (ruta suelta o modo draft) y `cross-implement` (work order
suelto) también se invocan **directamente**, sin flujo SDD. En ese caso no hay `.specify/config.yml`
que consultar. La regla:

**El transporte se infiere; el usuario no tiene que anunciar que está en Orca.** El resolver vive en
cada skill (no solo en `sdd-flow`) y su precedencia es:

```
override explícito en el prompt   >   config (si existe)   >   "auto"
```

Sin config, cae a **`auto`**, que autodetecta el entorno con la misma secuencia de la sección
"Descubrimiento de sesiones": `command -v orca` → `orca status --json` → `orca terminal list --json`
buscando una terminal de la otra familia, idle, en el worktree. Si las tres condiciones se cumplen,
usa la sesión real; si no, cae al CLI headless de hoy (`codex exec` / `claude -p`). El pseudocódigo
`resolve_cross_model_transport` del README ya arranca con `desired = override ?? config ?? "auto"`,
así que la ausencia de config **no rompe nada**.

El usuario solo nombra el transporte para **forzarlo**, nunca para habilitarlo:

- *"que Codex investigue este bug en paralelo **usando Orca**"* → fuerza `orca-session` (avisa si no
  hay runtime o terminal válida).
- *"…**sin Orca / headless**"* → fuerza `cli` aunque Orca esté disponible.

**Dos matices propios del standalone:**

1. **El consentimiento del hallazgo 2.4 pesa más.** En `sdd-flow` la sesión dedicada la crea el
   flujo; en standalone es más probable que el único candidato idle sea la **propia terminal de
   trabajo del usuario** en la otra familia. Por eso, al **reutilizar** una sesión ajena (no creada
   por la invocación), la skill confirma una vez antes de apropiarse, aun con un solo candidato. Si
   prefiere no tocarla, crea una sesión dedicada fresca con `terminal create` (modelo híbrido de la
   sección 4).
2. **Las tres capas de seguridad aplican igual** (secciones 5, 2.7, 2.8): sandbox, lista blanca de
   MCP y política de hooks. Una invocación suelta de `co-explore`/`cross-review` no relaja el rol
   read-only ni habilita hooks arbitrarios por estar fuera del flujo.

En síntesis: standalone y SDD comparten exactamente el mismo resolver y las mismas garantías; la
única diferencia es de **dónde sale el `desired`** (config del flujo vs. default `auto`), y en ambos
casos el usuario puede ignorar por completo el tema del transporte salvo que quiera forzar un
camino.

---

## Apéndice — Comandos verificados en esta sesión

```text
orca --help                          # árbol de comandos (terminal + orchestration)
orca orchestration dispatch --help   # --task --to --from --inject --dry-run --return-preamble
orca orchestration send --help       # --type --task-id --dispatch-id --report-path --files-modified ...
orca orchestration check --help      # --wait --types --timeout-ms --peek/--unread/--all --inject
orca orchestration task-create --help
orca orchestration reply --help
codex --help                         # -s/--sandbox, -a/--ask-for-approval, -C/--cd, --add-dir, -c
codex exec --help                    # -o/--output-last-message
codex sandbox --help                 # --sandbox-state-readable-root, etc.
```

Entorno: Codex CLI 0.144.5 · Claude Code 2.1.214. **Estado de Orca (snapshot 2026-07-18, no
permanente):** operativo desde un shell libre (`app.running: true`, `ready`), pero
`stale_bootstrap` / `runtime_unavailable` desde dentro del sandbox del agente Codex (ver el dato
empírico de la sección 1). Sin ciclo E2E del protocolo `dispatch`/`worker_done`. Volver a comprobar
antes del spike.

---

## Procedencia

Este informe pasó por una ronda de revisión **cross-model** (la otra familia revisó la versión
inicial). Se incorporaron sus cuatro correcciones, todas verificadas como legítimas antes de
adoptarlas:

1. **`-C` a la carpeta del informe pospuesto** — se apoyaba en un supuesto sin verificar; el
   default de v1 pasa a "el conductor persiste" (secciones 5 y 7). *Priorización.*
2. **Allowlist de Claude por tools de lectura concretas, no wildcards de servidor** — corrige un
   riesgo real de escritura en Atlassian (sección 5). *Error de seguridad corregido.*
3. **Coherencia en la reutilización de sesión** — co-explore estrena la sesión dedicada y
   cross-review la reutiliza (secciones 2.3 y 4). *Contradicción corregida.* (La segunda ronda
   refinó esto para cross-implement: ver punto 5.)
4. **Consentimiento acotado a terminales ajenas al flujo** — no re-preguntar por la sesión que el
   propio flujo creó (secciones 2.4 y 7). *Refinamiento de alcance.*

**Segunda ronda** (misma familia revisora, sobre la versión ya corregida):

5. **Transición de permisos read-only → implementación (bloqueante)** — en v1 la sesión read-only
   no se reutiliza para `cross-implement`; se separan en dos sesiones por nivel de permiso (nuevo
   hallazgo 2.6; secciones 4, 6 y 7). *Contradicción de permisos corregida.*
6. **Tabla de la sección 6 alineada con v1** — decía "sandbox = carpeta del artefacto", pero v1
   pospone esa estrategia; ahora dice read-only + conductor persiste. *Consistencia.*
7. **Gate 0 valida también `terminal read`** — la extracción íntegra del informe desde la TUI se
   agrega como quinto punto sin verificar (secciones 1, 2.1 y 7). *Cobertura del spike.*

**Tercera ronda** (misma familia revisora, sobre la versión de la segunda):

8. **MCP externos no cubiertos por el sandbox (bloqueante)** — el sandbox gobierna filesystem/exec,
   no las tools MCP; una sesión (incluso read-only) podría escribir en Jira/Bitbucket/Drive por un
   canal que `git diff` no ve. Se agrega el requisito duro de lista blanca de MCP por rol y familia
   (nuevo hallazgo 2.7; secciones 5 y 7). *Hueco de seguridad cerrado.*
9. **"Elevar permisos es imposible" era demasiado absoluto** — Codex expone
   `sandboxPolicy` por thread/turno en su app-server; la elevación es posible pero no está
   verificada por la vía Orca/TUI, así que v1 sigue con dos sesiones "por no verificado", no "por
   imposible" (hallazgo 2.6). *Precisión técnica.*
10. **Menores** — `codex exec --safe-mode` era incorrecto (`--safe-mode` es de Claude); los comandos
    de la sección 4 ahora muestran el rol acotado; conteos "cuatro→cinco puntos"; "ajena al flujo"
    en vez de "ajena al usuario". *Consistencia.*

**Cuarta ronda** (misma familia revisora, sobre la versión de la tercera):

11. **Claude read-only no puede auto-notificar (bloqueante)** — sin `Bash` no puede correr
    `orchestration send`. El mecanismo oficial de `worker_done` pasa a ser un **hook de coordinación
    auditado** en ambas familias, no un comando del modelo ni un fallback (nuevo hallazgo 2.8;
    secciones 1, 4, 5 y 7). *Contradicción de notificación resuelta.*
12. **Política de hooks (bloqueante)** — los hooks son una **tercera superficie** de efectos
    laterales (shell/HTTP/MCP), aparte de filesystem y MCP; se deshabilitan todos salvo el de
    coordinación, y su inventario entra al Gate 0 (hallazgo 2.8; sección 5 "tres superficies").
    "Máxima capacidad" ya no incluye hooks arbitrarios. *Superficie de riesgo cerrada.*
13. **Menores** — "no se eleva en caliente" → "v1 no lo eleva" (sección 6); "no puede reutilizarse"
    → "no se reutiliza en v1" (Procedencia); se quitó la nota sobre comandos `codex` pelados que ya
    no existían; y se precisó que `.plans/…` está **dentro** del repo (fuera de la *raíz escribible*,
    no del repositorio; sección 5). *Consistencia.*

**Quinta ronda** (misma familia revisora, sobre la versión de la cuarta):

14. **`--allowedTools` no cierra el toolset (bloqueante)** — solo pre-aprueba; las tools no
    enumeradas siguen disponibles. La **capa built-in** de Claude pasa a **`--tools "Read,Grep,Glob"`**
    (toolset cerrado) + reglas MCP explícitas + `--permission-mode dontAsk`, todo verificado contra
    `claude --help` (sección 5). *Capa built-in cerrada; la garantía read-only completa sigue
    dependiendo de las capas MCP y hooks, y del Gate 0.*
15. **Deadlock informe ↔ `worker_done` (bloqueante)** — el hook no puede esperar "existe el archivo
    del informe" si en v1 el conductor lo persiste *después*; se cambia a validar un **sentinel en
    el mensaje final** (`STATUS: done`, que `co-explore` ya usa) y recién ahí notificar (hallazgo
    2.8). *Dependencia circular rota.*
16. **Precedencia sobre el README** — se declara explícitamente que, ante conflicto, prevalece este
    documento, con tabla de puntos superseded ("Relación con el README"). *Ambigüedad normativa
    resuelta.*
17. **Comandos marcados como esqueletos** — se aclara que los ejemplos muestran solo sandbox y no
    son ejecutables hasta fijar MCP+hooks en el Gate 0 (secciones 4 y 5). *Consistencia.*

**Sexta ronda** (misma familia revisora, sobre la versión de la quinta):

18. **`STATUS: done` no es universal (bloqueante)** — verificado en los `reference.md`:
    `co-explore` y `cross-implement` lo usan, pero `cross-review` cierra con `VERDICT:`. Un hook que
    exija `STATUS: done` nunca notificaría en cross-review. Se define un **envelope común** —salida
    del modo + `STATUS: done` como **última línea no vacía**— y cross-review debe agregar esa línea
    (hallazgo 2.8; secciones 7 y tabla de precedencia). *Sentinel hecho universal.*
19. **`reportPath` redefinido** — el README lo trataba como archivo existente
    (`parse_result(reportPath)`); en v1 es la **ruta destino** aún inexistente donde escribe el
    conductor, validada dentro del área autorizada (hallazgo 2.8; tabla de precedencia). *Semántica
    alineada con "conductor persiste".*
20. **Menores** — residuos que decían "allowlist" para filesystem/exec de Claude → "toolset cerrado
    (`--tools`)" (2.6, 2.7, secciones 4 y 5); el punto 14 ahora dice "capa built-in cerrada"; y la
    precedencia dice "principales puntos" con la regla global cubriendo el resto (p. ej. 2.4).
    *Consistencia.*

**Séptima ronda** (misma familia revisora; el texto se le entregó por el handoff Orca real —
`terminal send`— en vez de copiar a mano):

21. **Gate 0 debe ser una matriz bidireccional y mode-aware (bloqueante)** — un solo dispatch
    Claude→Codex/`explore` solo prueba el hook de Codex; se define la matriz mínima (Claude→Codex,
    Codex→Claude, y un `cross-review` para el envelope) (hallazgo 2.1; sección 7). *Cobertura del
    spike completada.*
22. **`reportPath` con contención canónica** — "dentro del área autorizada" se endurece: rechazar
    rutas absolutas y `..`, validar el `realpath` del padre contra la raíz del dispatch para
    bloquear symlinks (hallazgo 2.8). *Path traversal cerrado.*
23. **Estado de Orca como snapshot fechado** — y se registra el **dato empírico** de que el runtime
    responde distinto desde un shell libre (operativo) que desde el sandbox del agente
    (`unavailable`), evidencia directa del hallazgo 2.8(a) (sección 1; apéndice). *Estado transitorio
    correctamente encuadrado.*

Las siete rondas ilustran el propio patrón que el diseño busca habilitar: dos familias produciendo y
criticando de forma independiente, con síntesis del conductor. Notablemente, cada ronda encontró un
problema que la anterior no vio —varias, huecos de seguridad o de protocolo reales (MCP externos,
hooks, toolset abierto de Claude, sentinel no universal, Gate 0 unidireccional)—: evidencia de que
la crítica iterada cross-model aporta más que una sola pasada. La séptima ronda, además, se corrió
sobre el propio transporte que el documento diseña. El veredicto documental del revisor es
**APPROVED para ejecutar el Gate 0** (como matriz) — la aprobación habilita correr el spike, no
modificar skills, que espera a que el Gate 0 pase. Con esto, la iteración documental queda cerrada.
