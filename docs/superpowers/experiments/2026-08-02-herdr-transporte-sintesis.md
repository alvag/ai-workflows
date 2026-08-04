# Herdr como transporte de workers cross-model — informe de síntesis

**Fecha:** 2026-08-02 · **Rama:** `exp/herdr-panes-transport` · **Para revisión de Max**

Documento único acordado entre los dos conductores de los ejercicios:

- **Ejercicio A** — conductor Claude Opus 5. Desambiguar `status: planned` en `sdd-flow`.
  Informe propio: `docs/superpowers/experiments/2026-08-01-herdr-como-transporte.md`.
- **Ejercicio B** — conductor Codex gpt-5.6-sol. Guarda para los bloques `## Referencias internas`.
  Informe propio: `.plans/herdr-native-sdd-contract-audit/conclusion.md`.

Los dos corrieron en el mismo repo y la misma rama, en paralelo y **sin verse**, hasta dos rondas
de debate cruzado. Lo que sigue es el consenso; donde quedó desacuerdo, está marcado como tal.

> **Sobre las referencias.** El informe del ejercicio A se versiona junto a este documento. El del
> ejercicio B y todos los artefactos de trabajo —las dos rondas de debate, los datos verificados,
> el análisis de los tres temas nuevos— vivieron en `.plans/`, que por convención de este repo es
> **local y untracked**: son efímeros por diseño y pueden no existir cuando leas esto. Lo que había
> que conservar de ellos está incorporado acá.

---

## 1. Veredicto ejecutivo

> **Herdr sustituye el transporte, no la semántica.** La integración es una rama pequeña dentro de
> las skills existentes. No hace falta recrear el runtime anterior.

Las dos corridas llegaron a esa tesis por separado y ninguna encontró evidencia en contra.
Cuantificado: **0 scripts de orquestación, 0 launchers, 0 state machine, 0 archivos de correlación
de procesos, 0 worktrees creados por el transporte** — en los dos ejercicios.

Lo que **no** sustituye, y sigue siendo íntegramente de las skills: work orders, independencia
entre familias, rutas exclusivas de salida, políticas de deadline, validación de artefactos, gates
humanos, límite de rondas, clasificación de fallos, single-writer y revisión del diff.

**La convergencia más fuerte no está en ninguno de los dos informes originales:** los dos flujos
terminaron en `status: implementing` y **ninguno falseó `verified`**. Dos conductores de familias
distintas, con problemas distintos, se detuvieron ante una fila de contrato sin cerrar. El
contrato de verificación funciona.

---

## 2. Los dos experimentos

| | Ejercicio A (Claude) | Ejercicio B (Codex) |
|---|---|---|
| Panes | 7 (uno por fase) | 2 (reutilizados) |
| Agentes nombrados | 8 | 5 |
| Rondas de cross-review | 5 (3 spec + 2 plan) | 4 (spec) |
| Veredicto de spec | `APPROVED` en r3 ✅ | `REVISE` en las 4 ✅ |
| Counter-plan | éxito en 480 s | `map_failure` con deadline de 300 s |
| Implementación | 3 archivos, +45/−11, 1 fix | 11 archivos, +704/−53, 0 fixes, 23 m 58 s |
| Estado final | `implementing` (T9 sin hacer) | `implementing` (V9 rojo) ✅ |
| Artefactos | 28 archivos (23 en `planned-desambiguacion/` + 5 del tramo inicial) ✅ | 28 archivos / 408 K ✅ |

✅ = verificado contra el disco por el otro conductor, no tomado del informe.
Snapshot de los conteos: 2026-08-02T17:28. Los dos ejercicios produjeron exactamente 28 archivos.

**Sobre la topología: el patrón de B es mejor.** Un pane por *slot de familia* reutilizado
reemplazando el proceso, no un pane por fase. Menos churn de layout, y el pane es barato de
reutilizar.

---

## 3. El patrón mínimo probado

```bash
# 1. Activación (ver §9.1): explícita una vez por flujo, más HERDR_ENV=1
test "${HERDR_ENV:-}" = 1

# 2. Crear el pane — NUNCA encadenado con el paso 3
herdr pane split --current --direction right --cwd "$PWD" --no-focus
#    → leer .result.pane.pane_id del JSON

# 3. Arrancar el agente, flags nativos después de --
herdr agent start <rol>-<familia>-<sufijo> --kind codex --pane <id> --timeout 60000 \
  -- --ask-for-approval never --sandbox workspace-write

# 4. Despachar TODOS antes de esperar a ninguno, con la ruta del prompt
herdr agent prompt <nombre> 'Tu tarea está en <ruta>. Leelo y ejecutalo.'

# 5. Esperar — SIN --until (ver §4.2)
herdr agent wait <pane-id> --timeout 900000

# 6. Cosechar del archivo y validarlo. El archivo es la autoridad, no el lifecycle.

# 7. Cerrar solo los panes propios, y solo tras validar el artefacto
herdr pane close <id>
```

**Geometría.** Split a la derecha si el pane es ancho, abajo si es angosto; nunca dos splits
seguidos en la misma dirección.

### 3.1 Por qué el prompt va por ruta

Dos razones independientes, ambas verificadas:

1. **Quoting.** El `CLAUDE.md` del repo advierte que el markdown con backticks rompe el quoting del
   shell, y de ahí sale la bifurcación POSIX (`< prompt.txt`) contra PowerShell
   (`Get-Content -Raw | ... -`). Por la línea de comando viaja una sola oración de texto plano:
   **no hay quoting que romper**, y la bifurcación desaparece del problema.
2. **Alternate screen.** Los agentes TUI pintan sobre la pantalla alternativa; las filas que salen
   del viewport **no entran al scrollback del host**. Subir `--lines` no recupera nada. Un informe
   de 24 KB es irrecuperable desde el pane.

La segunda razón convierte la cosecha por archivo en **la única vía uniforme y robusta probada en
las dos familias** — no en la única técnicamente posible: el Codex instalado expone
`--no-alt-screen`, que no se ejercitó en ninguno de los dos ejercicios. Y es exactamente lo que `co-explore` y `cross-review` ya hacen con sus rutas de
informe: **el contrato de artefactos de las skills ya estaba listo para Herdr.**

### 3.2 Dos reglas operativas que costaron descubrir

**`pane split` y `agent start` son dos pasos.** Encadenarlos con `&&` falla: el pane existe pero su
shell todavía no llegó al prompt interactivo, y `agent start` exige un pane disponible. El
reintento funciona. *Consenso sobre cómo describirlo:* es una **carrera de readiness observada**,
no un fallo determinista de toda composición; el reintento es recuperación de transporte, no una
corrida semántica nueva.

**Los nombres necesitan un sufijo de corrida.** Herdr exige nombres únicos entre agentes vivos.
`reviewer-plan` funciona con un flujo; dos flujos concurrentes chocan. La forma acordada es
`reviewer-plan-a17f` — un sufijo corto de run, sin convertirlo en estado durable.

---

## 4. Lifecycle, continuidad y modo desacoplado

### 4.1 Despachar todos antes de esperar a ninguno

Medido en el ejercicio A: dos `agent prompt --wait` en el mismo bloque de llamadas se ejecutaron en
serie (21:03 y 21:11, **16 minutos**). Con el disparo separado de la espera, los dos prompts
salieron en el mismo segundo y los workers terminaron juntos (**8 minutos**).

*Consenso sobre la formulación:* **no** es "Herdr serializa dos prompts". Lo que serializó fue el
harness al esperar la primera llamada antes de ejecutar la segunda. La regla portable sí es
inequívoca, y el ahorro de reloj es lo de menos: serializados, **el segundo worker arranca cuando
el artefacto del primero ya existe**, lo que rompe la independencia que `co-explore` exige.

### 4.2 `--until idle --until blocked` es un bug, no una buena práctica

**Los dos conductores llegaron a esto por caminos independientes**, y es el hallazgo más útil de
la ronda de debate.

| Forma | Estados que satisfacen la espera |
|---|---|
| `agent wait <t>` sin `--until` | `idle`, `done`, `blocked` ✅ |
| `agent wait <t> --until idle --until blocked` | `idle`, `blocked` — **falta `done`** ❌ |

La documentación de Herdr lo explica: `idle` significa listo para input **y que su tab fue vista en
la UI enfocada**; `done` es el mismo estado subyacente cuando termina trabajo de fondo **no
visto**; y las lecturas por CLI **no** marcan como visto. Por lo tanto **un worker desacoplado que
nadie mira termina en `done`**, y una espera que omite `done` no puede cumplirse.

*Evidencia del ejercicio A, en vivo durante este mismo debate:* Codex terminó a las 17:12:16 con su
artefacto de 20.821 bytes en disco. El conductor siguió creyendo que trabajaba, y se enteró a las
17:16 **porque Max se lo dijo**. El wait no salió ahí: **quedó colgado hasta las 17:36:53**, o sea
**24 m 37 s después de que el trabajo estuviera terminado**, y salió reportando `idle` —no `done`—
justo porque Max había mirado la tab, lo que marcó el estado como visto. Sin esa mirada habría
corrido hasta el timeout de 30 minutos.

**Lo contraintuitivo:** el `--until` explícito **empeoró** el comportamiento. `blocked` ya estaba
en los defaults; el `--until` no lo agregó, solo quitó `done`.

**Regla:** para "avisame cuando termine", **no pasar `--until`**. Reservarlo para workflows que
esperan un estado específico, como `--until blocked` para detectar que un agente ya corriendo pide
input.

### 4.3 El modo desacoplado funciona, y la pieza que lo hace posible no es Herdr

Validado en vivo: con el wait lanzado en background del harness, el conductor escribió tres
documentos completos mientras el worker trabajaba. **Ningún turno quedó tomado**, y al terminar el
background el harness re-invocó al conductor solo.

**Herdr no hace push hacia el conductor.** Lo que une las dos cosas es el harness: un comando
lanzado en background sobrevive entre turnos y re-invoca al agente. Sin esa capacidad del host, el
fallback correcto es espera síncrona o polling explícito — **no** asumir una continuidad que el
host no ofrece.

`herdr notification show` funciona (`--body`, `--position`, `--sound`) y sirve para avisarle al
usuario aunque el conductor esté ocupado. *Consenso:* mejora la experiencia humana pero **no debe
participar en la corrección del flujo**.

### 4.4 El comando en background debe ser un verificador, no un disparador

Primer intento, mal:

```bash
herdr agent wait <t> >/dev/null 2>&1; herdr notification show "Terminó"
```

El wait falló —el target era un **nombre** y el agente había sido reemplazado, lo que limpia el
nombre— pero el `;` siguió adelante: **notificó a Max un trabajo terminado que no había
terminado**, y el harness re-invocó con la misma señal que un final legítimo. El `;` en vez de
`&&` y el `2>&1` a `/dev/null` borraron la evidencia.

Es el patrón de una guarda que no puede ponerse roja: **el aviso reportó verde sin comprobar
nada**. Forma correcta: distinguir tres estados —wait fallido / terminó sin artefacto / terminó
bien— y que los tres lleguen al conductor.

Dos corolarios que cierran el círculo entre los dos informes:

- `done` **no prueba** que el artefacto exista *(ejercicio B)*.
- La ausencia de `done` **no prueba** que el artefacto no exista *(ejercicio A)*.

**El lifecycle es una señal de conveniencia; la autoridad es el archivo.** Un wait desacoplado
robusto vigila las dos cosas — pero **despertarse no es lo mismo que declarar éxito**: la mera
aparición del archivo puede estar observando una escritura a medias. El verificador puede
despertarse por lifecycle o por filesystem, y recién declara éxito tras **publicación atómica**
(el worker escribe a temporal y renombra) o **validación completa** del artefacto. Un `test -f`
suelto no da esa garantía.

### 4.5 El descriptor efímero de corrida

*Aporte del ejercicio B, adoptado.* El re-invoque del harness no debe depender de memoria
conversacional implícita. Antes del dispatch se persiste un **sobre mínimo e idempotente**: run ID,
skill y modo, nombres de agentes, panes propios, prompt y outputs esperados, deadline, estados
terminales, gate pendiente y próxima acción. Al despertar, el conductor relee el descriptor, los
artefactos y `agent get`, y cosecha **una sola vez**. Sin descriptor válido, falla cerrado.

**No es la state machine anterior**: es el sobre de una corrida activa, y muere con ella. También
resuelve dos huecos: la lista de panes propios (para no cerrar ajenos) y la **idempotencia del
callback**, porque el harness puede re-invocar dos veces o reanudar tras una interrupción.

### 4.6 Los gates son una barrera dura

El desacople vuelve fácil de violar por accidente una regla que antes se cumplía sola. **Se puede
solapar trabajo del conductor; no se puede adelantar el gate.**

Mientras una revisión está pendiente, el gate queda marcado `review-pending`: no se presenta y no
se contabiliza una aprobación humana prematura. El gate existe recién después de cosechar, validar
y aplicar o disputar el veredicto.

En `co-explore` el límite es más estricto todavía: el conductor puede hacer administración,
preflight determinista y verificaciones locales, pero **no** construir un tercer mapa, **no** leer
el informe del primero antes de que ambos terminen y **no** sintetizar anticipadamente. El
conductor es árbitro, no explorador.

---

## 5. Seguridad, permisos y ownership

### 5.1 Perfiles por fase — nunca bypass

| Fase | Codex | Claude |
|---|---|---|
| Read-only (explore, review) — **⚠ diseño, no probado** | ver la advertencia debajo de la tabla | `--permission-mode auto` + allowlist de lectura, escritura solo al veredicto |
| Implementación | `--ask-for-approval never --sandbox workspace-write` | `--permission-mode auto`, `Edit(./**)`/`Write(./**)`, **Bash/web/delegación deshabilitados** |

> **⚠ La fila read-only no es un consenso probado.** Codex con `--sandbox read-only` **no puede
> escribir su propio informe** en el repo; darle `workspace-write` lo habilita a escribir todo el
> working dir. La combinación "repo read-only + un único output writable" **no se ejercitó en
> ninguno de los dos ejercicios**: B lanzó explore con bypass y A usó `workspace-write`. Lo probado
> es **comportamiento** read-only por contrato, no **aislamiento** de permisos. Queda como diseño
> pendiente de validar (§10).

Tres precisiones acordadas:

1. **`--permission-mode default` se comporta como manual** dentro de Herdr en Claude Code v2.1.220:
   el worker queda `blocked` en la primera aprobación. `auto` es la solución **para Claude
   interactivo dentro de Herdr**, no un reemplazo global de `default` en la vía headless, que
   documenta `default` con allowlist path-scoped.
2. **Los permisos path-scoped no bastan si Bash está habilitado sin una allowlist igual de
   estrecha.** `Edit(./**)`/`Write(./**)` fueron una frontera real en el ejercicio B *porque* Bash
   estaba deshabilitado. Shell arbitrario vuelve poroso el límite.
3. **`--safe-mode` va por perfil de fase, no como default universal.** Aísla plugins, hooks y MCP
   —lo que obliga a un prompt autocontenido— pero esas extensiones pueden ser capacidades legítimas
   de una exploración.

*Nota sobre el clasificador:* en el ejercicio A, `--dangerously-bypass-approvals-and-sandbox` fue
bloqueado por el clasificador de auto-mode del **conductor**, no por Herdr. El ejercicio B nunca lo
intentó porque `cross-implement` ya prohíbe los tres bypass peligrosos. Se registra como evidencia
de *ese harness*, no como propiedad de Herdr ni como diferencia demostrada entre conductores.

### 5.2 El límite de escritura se sostiene, pero por dos cosas juntas

En el ejercicio A el worker tocó exactamente los tres archivos versionados del work order: no tocó
la bitácora del conductor, ni otros flujos, ni otras skills, ni commiteó. En el B, los once
declarados y ninguno más.

Ninguna de las dos mitades habría alcanzado sola: **el sandbox permite todo el working dir, y el
contrato sin sandbox es una promesa.**

### 5.3 Ownership entre skills

- **`sdd-flow`** decide *si* usar Herdr y conserva gates y `status`.
- **`co-explore`** decide independencia, fan-out, informes, síntesis y degradación.
- **`cross-review`** decide sesión reutilizable, rondas y veredicto.
- **`cross-implement`** decide clean-tree/worktree, escritura, diff, fix loop y proof.
- **La skill `herdr`** ejecuta operaciones de panes y agentes, y expone lifecycle.

No conviene copiar los comandos de Herdr dentro de `sdd-flow`: eso vuelve a mezclar orquestación
semántica con transporte.

---

## 6. Resultados y fallos observados

### 6.1 El counter-plan de B falló por política, no por transporte

**Consenso.** Los dos workers seguían `working`, ninguno `blocked`, Herdr permitió observarlos y
cancelarlos: no hay evidencia de que fallara el transporte. Faltaron los dos artefactos al vencer
**300 s**, cuando la propia fase de exploración de B ya había superado **600 s** y la corrida
equivalente de A entregó en **480 s**.

Dos matices que el debate precisó:

- **`map_failure` sigue siendo el outcome contractual correcto**: `co-explore` exige dos mapas o
  ninguno. Lo incorrecto es explicarlo como límite de Herdr o esconder la causa bajo
  `runtime_failure`. Fue `deadline_exceeded`.
- **No hay un piso universal.** Defaults iniciales medidos, configurables y sin extensiones
  silenciosas: **900 s para read-only xhigh en este repo, 1800 s para implementación**. Son valores
  empíricos de estas corridas, no una propiedad de Herdr.

### 6.2 El mismo error de formato, dos veces, en ejercicios independientes

Los dos conductores rompieron la tabla del contrato de verificación con un `|` dentro de una celda
Markdown, y los dos tuvieron que recalcular el hash. Dos ocurrencias independientes dejan de ser
anécdota: **un contrato generado debe validar su propia estructura antes del dispatch**, y hoy lo
detecta el revisor, tarde.

### 6.3 Timeout no equivale a proceso colgado

En el ejercicio B un `agent wait` de 600 s venció con los workers todavía produciendo, y terminaron
entregando informes válidos. **La política de deadline es de la skill, no de Herdr**, y la decisión
de extender, cancelar o degradar también.

### 6.4 El work order congelado se copia con sus errores incluidos

En el ejercicio A el implementador transcribió fielmente un `(D1)` que el conductor había congelado
mal —una referencia a un artefacto SDD dentro de una skill, que el repo prohíbe—. **La fidelidad
del implementador amplifica lo que el conductor escribió, sea bueno o malo.**

La consecuencia no es flexibilizar el work order sino **endurecer su preflight**: ejecutar
predicados, validar rutas y buscar fugas de IDs antes del dispatch.

Su contracara también se observó y es correcta: cuando la task T9 apuntó a un artefacto que se
había archivado mientras el worker corría, el implementador **falló ruidosamente** en vez de
buscarlo por su cuenta. Una task que se auto-repara sobre una ruta que nadie autorizó es peor que
una que falla a la vista.

---

## 7. Qué desaparece y qué permanece

**Desaparece:**

- Captura y persistencia del `SESSION_ID` del proveedor, y su recuperación. El agente sigue vivo en
  su pane: reanudar es mandarle otro prompt. Usado 6 veces en A (3 rondas de spec, 2 de plan, 1 fix
  loop) y en las 4 rondas de B.
- La bifurcación POSIX/PowerShell para pasar el prompt por stdin.
- Launchers por proveedor, polling propio sobre procesos, archivos de correlación.
- La contabilidad **persistente** de IDs: los nombres de agente alcanzan como handles para el loop
  interactivo. Los **IDs de pane sí se conservan**, como estado efímero de la corrida —los necesitan
  el wait desacoplado estable (§4.4) y el ownership del cleanup (§4.5)—; lo que no se persiste son
  los session IDs del proveedor.

**Permanece, y no debe confundirse con plumbing:**

- Los artefactos auditables que SDD produce por diseño. El ejercicio B terminó con 28 archivos y
  408 K; el A con 26. **Eliminar runtime no elimina evidencia.** Si además se quiere reducir
  artefactos, esa es una simplificación separada, y Herdr no debe usarse como argumento para borrar
  lo que los gates necesitan.
- Validación de artefactos, manifests, recovery y gates.

---

## 8. Errores de los conductores

Sección deliberada: un informe sobre plomería puede dar la falsa impresión de que la plomería era
el problema. **No lo era.**

**Ejercicio A** — causa común: afirmaciones verificables que no se verificaron.

1. Declaró los quince baselines del contrato en `RED` **sin ejecutarlos**. Dos ya pasaban.
2. Escribió un predicado que **nacía verde** por coincidir con una línea ajena del repo.
3. Arbitró mal el counter-plan: descartó el `status_version` que proponía Codex con un argumento
   que la revisión refutó dos rondas después.
4. Inventó un hash en vez de calcularlo.
5. Congeló un `(D1)` que se filtró a una skill.
6. Registró como "evidencia inexistente" unos manifests que Max había borrado por accidente. **"No
   está en disco" y "nunca existió" son cosas distintas**, y es la segunda vez en el ejercicio que
   el mundo cambió entre la afirmación y la comprobación.

**Ejercicio B** — errores de calibración, no de verificación.

1. Eligió una feature ficticia demasiado grande: 704 inserciones para probar transporte.
2. Fijó 300 s de deadline para un counter-plan xhigh **después** de que explore ya había superado
   600 s.
3. Continuó con aprobación humana tras cuatro `REVISE`, sin `APPROVED` independiente.
4. Aceptó un waiver de clean-tree que no debe volverse default.
5. Lanzó el primer implementador con un perfil de permisos incompatible con ejecución autónoma.

Ninguno de los once es atribuible al transporte.

---

## 9. Integración mínima recomendada

### 9.1 Activación — dos preguntas distintas

**Desacuerdo resuelto.** El conductor A proponía `HERDR_ENV=1` como única señal; el B exigía además
pedido explícito. **Consenso:**

> `HERDR_ENV=1` responde *"¿puedo usar Herdr?"* — es capacidad, no consentimiento.
> *"¿debo usar Herdr en este flujo?"* lo responde una **intención explícita y durable**.

Mecánica acordada: activación explícita **una vez por sesión o flujo** —por `$herdr`, por pedido
del usuario, o por `transport: herdr` en la config del flujo—. A partir de ahí, y si además hay
`HERDR_ENV=1`, **todas las fases delegadas de ese flujo usan panes por default**, el conductor lo
anuncia antes de abrir el primer pane, y el usuario conserva un opt-out claro. No se vuelve a pedir
permiso en cada `co-explore`.

### 9.2 Dónde vive la documentación

**Desacuerdo resuelto.** A proponía una sección por skill; B una guía compartida; A objetó que un
link duro hacia otra skill se rompe cuando se instala una sola. **Consenso en tres capas:**

1. La **mecánica canónica del CLI** vive con la skill `herdr`: el binario instalado es la autoridad
   y la propia skill exige consultar su ayuda actual.
2. Cada skill llamadora conserva un **adaptador semántico pequeño y autocontenido**: activación,
   perfil de permisos, paths de entrada y salida, independencia, deadline, continuidad, validación
   y cleanup. **No copia la sintaxis de Herdr.**
3. La distribución declara Herdr como **capacidad opcional**. Si su skill no está, la vía de panes
   **no se improvisa**: se degrada al transporte CLI vigente.

Repetir invariantes semánticos está bien —su dueño es cada skill—; duplicar comandos, no.

### 9.3 ¿Hace falta invocar la skill `herdr` primero?

**Técnicamente no.** Verificado: las cinco variables (`HERDR_ENV`, `HERDR_PANE_ID`, `HERDR_TAB_ID`,
`HERDR_WORKSPACE_ID`, `HERDR_SOCKET_PATH`) las inyecta **el proceso Herdr al crear el pane**, no la
skill. El binario está en `PATH`. La skill no exporta nada: es un manual.

**Pero "no es necesaria para que el CLI funcione" no equivale a "no es necesaria como fuente de
contrato operativo".** Consenso: la skill sigue siendo la autoridad de uso —comprobar `HERDR_ENV`,
consultar el CLI instalado, leer IDs y estados de las respuestas en vez de predecirlos—, y la
activación explícita del flujo debe **cargarla como capacidad** sin que el usuario tenga que
invocarla con una fórmula especial cada vez.

Consultar `herdr --help` y el grupo pertinente **una vez por sesión** es la mitigación necesaria y
barata contra la desactualización, y debe estar prescrita por la skill `herdr`, no congelada como
conocimiento copiado en cada referencia SDD.

### 9.4 Cierre de panes

**El pane se cierra cuando su artefacto fue cosechado y validado**, no cuando el agente queda
`idle`.

`cleanup: auto` por default para panes creados por la corrida, y solo tras artefacto válido,
outcome terminal, **manifest escrito o su intento fallido reportado** —un fallo al escribir el manifest nunca bloquea la corrida— y ausencia de rondas o recovery pendientes. Ante éxito se
anuncia el cierre sin pedir permiso.

`cleanup: keep` —con el pane anunciado y esperando decisión— ante `blocked`, fallo, cancelación,
incertidumbre, o cuando la corrida es un ejercicio de observabilidad. **Nunca** se cierra un pane
que la corrida no creó, y no se construye un recolector automático global.

Mientras haya rondas o fix loop pendientes, el pane vive: es lo que hace gratis el resume.

### 9.5 Taxonomía de manifests

`herdr` **no** está entre los transports canónicos, que hoy admiten `subagent`, `cli-exec` y
`cli-resume`. Hay que agregarlo.

Y hace falta una causa propia para deadline: hoy un deadline vencido queda oculto bajo
`runtime_failure`, que sugiere una falla de infraestructura que no ocurrió. Se propone
**`deadline_exceeded`**.

---

## 10. Límites, deuda y huecos que ninguno cubrió

**No probado:**

- **PowerShell.** Los dos corrieron en macOS/zsh; en B no existía `pwsh` ni `powershell`. La vía
  Herdr debería ser *más* portable que el CLI —no hay redirección de stdin— pero no está verificado.
- **Recovery tras reinicio de Herdr**, y reanudación desde otro equipo.
- **Multi-repo / multi-workspace.** Un solo repo y un solo tab en ambos ejercicios.
- **Escrituras paralelas y worktrees.**

**Huecos identificados en el debate, sin resolver:**

1. **Cancelación y escritura tardía.** Vencer el deadline no basta: hay que confirmar que el
   proceso dejó de trabajar antes de aceptar un output ausente o parcial. Si no, un worker tardío
   puede completar un archivo que ya pertenece a una corrida degradada. Los outputs deben ser
   exclusivos por run/attempt.
2. **Integridad entre prompt y despacho.** En background, una ruta de prompt compartida que cambia
   después del dispatch introduce una carrera. Cada intento necesita prompt y output exclusivos,
   con hash cuando el contrato dependa de contenido exacto.
3. **Presupuesto de layout.** Un pane por worker funciona con dos workers; varias corridas o un
   `sdd-orchestrator` multi-repo agotan la geometría útil. Hace falta un máximo de panes visibles y
   un fallback a tabs, workspaces o headless.
4. **La frontera read-only interactivo + output por archivo, especialmente en Codex.** Un worker
   con `--sandbox read-only` no puede escribir su propio informe; con `workspace-write` puede
   escribir todo el working dir. Ninguno de los dos ejercicios probó el punto intermedio.
   Resolverlo puede requerir una salida writable dedicada, cosecha de scrollback con
   `--no-alt-screen`, o una capacidad que hoy no existe. **Es el hueco más concreto que dejó el
   contraste**, porque afecta al perfil de permisos de las dos fases read-only.

**Próximo paso recomendado, y es chico:** documentar la vía Herdr según §9, pilotarla sobre **una
tarea real** y medir fallos. No construir más infraestructura hasta que aparezca una limitación
concreta.

---

## 11. Matriz de confianza

| Afirmación | Estado | Evidencia |
|---|---|---|
| Fan-out con **comportamiento** read-only por contrato | probado | A y B |
| **Aislamiento de permisos** read-only con escritura exclusiva al informe | **no probado** | ninguno lo ejercitó |
| Prompt por ruta y cosecha por archivo | probado | A y B |
| Cross-review multi-ronda reusando el agente | probado | A (5 rondas), B (4) |
| Sesiones frescas en panes reutilizados | probado | B |
| Detección de bloqueo interactivo | probado | B |
| Cancelación al vencer deadline | probado | B |
| Cleanup selectivo de panes | probado | A y B |
| Implementación cross single-writer | probado | A limpio; B con waiver de clean-tree |
| Modo desacoplado con re-invocación del harness | probado | A, en vivo durante el debate |
| `notification show` independiente del conductor | probado | A |
| El bug de `--until` sin `done` | probado | A (empírico) + B (documental) |
| Defaults de deadline 900 s / 1800 s | propuesto | derivado de A y B, sin validar |
| Descriptor efímero de corrida | propuesto | no implementado |
| PowerShell | no probado | — |
| Recovery tras reinicio | no probado | — |
| Multi-repo / multi-workspace | no probado | — |
| Escrituras paralelas / worktrees | no probado | — |

---

## Apéndice — evidencia

**Versionado, junto a este documento:**

- `2026-08-01-herdr-como-transporte.md` — informe original del ejercicio A. Se conserva por su
  narrativa de cómo se descubrió cada hallazgo. **Cuatro de sus afirmaciones fueron corregidas por
  la validación cruzada y este documento manda sobre él**: el perfil de permisos read-only
  (presentado ahí como probado, es diseño sin validar), el conteo de artefactos, "el archivo es la
  única vía" y la desaparición de los IDs de pane.

**Efímero, en `.plans/` (untracked, puede no existir):**

- `herdr-panes-transport/debate-r1.md` · `debate-r1-codex.md` · `debate-r2.md` ·
  `debate-r2-codex.md` — las dos rondas de debate cruzado.
- `herdr-panes-transport/datos-verificados.md` — comprobaciones contra el disco.
- `herdr-panes-transport/n1-n2-analisis.md` · `n3-desacople-evidencia.md` — los tres temas nuevos.
- `herdr-native-sdd-contract-audit/conclusion.md` — informe del ejercicio B.
- `planned-desambiguacion/` — artefactos SDD del ejercicio A.
