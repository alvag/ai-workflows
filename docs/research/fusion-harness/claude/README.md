# Análisis de `fusion-harness` (IndyDevDan) e ideas para nuestras skills cross-model

**Estado:** investigación y recomendaciones — nada implementado todavía
**Fecha:** 2026-07-22
**Autor del análisis:** Claude (Opus 4.8), conduciendo
**Fuentes:** repo [`disler/fusion-harness`](https://github.com/disler/fusion-harness) (clonado y leído completo: README, `fusion-harness.ts` 2506 líneas, los 10 prompt files, el run grabado en `live_final_generation/`) + video [YouTube `AQl5Q-0l7FQ`](https://youtu.be/AQl5Q-0l7FQ) (transcripción completa descargada y leída — 5.308 palabras, guardada en [`video-transcript.txt`](./video-transcript.txt); los frames en `images/video-frames/` cubren la parte visual).

---

## 1. Resumen ejecutivo

`fusion-harness` es la **misma tesis que nuestras skills** —"no elijas un modelo, combiná las dos familias"— pero llevada a un harness ejecutable (extensión de [Pi](https://github.com/badlogic/pi-mono)) en vez de skills Markdown portables. Coincidimos en el 70% de la filosofía. La diferencia que importa no es de vocabulario ("architect/builder" ≈ nuestro "conductor / la otra familia"), sino de **dónde ponen el rigor**:

- **Ellos** optimizan **autonomía**: un loop cerrado que se autovalida sin humano en cada paso, con un **gate objetivo ejecutable escrito ANTES de construir**.
- **Nosotros** optimizamos **control humano + portabilidad**: gates humanos en cada artefacto, degradación blanda, sin depender de un runtime propio.

Nuestro punto ciego relativo es exactamente su mayor fortaleza: **el criterio de "done" ejecutable, escrito antes del build, por un rol distinto del que implementa, con baseline que debe fallar en rojo.** Nuestro `cross-implement` corre una prueba (`proof_cmd`) pero no la exige escrita antes ni con baseline rojo; nuestro `verify` de `sdd-flow` es sólido pero corre *después* de implementar.

**Recomendación de rumbo (un default, no un menú):** seguir con nuestro modelo de skills Markdown human-in-the-loop —**no** convertirnos en un harness compilado— e **importar selectivamente tres ideas**, en este orden de impacto:

| # | Idea a importar | A qué skill | Impacto | Esfuerzo |
|---|---|---|---|---|
| **1** | **Gate-first / baseline-rojo**: escribir el criterio de done ejecutable ANTES del build, y exigir que falle en rojo primero | `cross-implement` (+ reforzar `sdd-flow verify`) | **Alto** | Medio |
| **2** | **Escalation → triage → "¿el gate está mal?"**: tras N fallas, dejar de corregir a ciegas y diagnosticar causa raíz, incluida la posibilidad de que el criterio de done esté defectuoso | `cross-implement`, `systematic-debugging` | **Alto** | Bajo |
| **3** | **Peldaño `/opinion` + value ladder explícito**: un modo A/B barato read-only por debajo de `co-explore`, y documentar la escalera opinion→explore→review→implement | `co-explore` (modo nuevo) + doc | Medio | Bajo |

Las secciones 5 y 6 detallan cada una. La sección 7 lista lo que **NO** deberíamos copiar. El apéndice A registra un **hallazgo técnico** (bloqueo del clasificador de usage-policy al reproducir transcripts cross-model) directamente relevante para el trabajo en curso de `cross-model-real-sessions`.

---

## 2. Qué es `fusion-harness`

Una extensión única (`fusion-harness.ts`) que registra tres slash commands sobre Pi. El eslogan es **"AND, not OR"**: en vez de rutear el compute al modelo A **o** al B (seleccionar), lo ruteás a A **+** B (combinar). "Qué modelo es mejor" es una pregunta de benchmark; "qué **rol**" es la pregunta de ingeniería. **Role ≠ model**: los roles son estables, los modelos rotan cada trimestre y entran por un flag.

Dos roles fijos y duramente etiquetados:
- **ARCHITECT** (por defecto `claude-fable-5`): planifica, fusiona y valida.
- **BUILDER** (por defecto `gpt-5.6-sol`): construye. **El host de Pi corre sobre el builder** — el chat crudo *es* el builder; un slash command forkea la sesión del host (copy-on-write, hereda tu contexto).

### Los tres comandos — una "value ladder" sobre los mismos 2 agentes

| Comando | Agentes | Qué hace |
|---|---|---|
| `/opinion <prompt>` | 2 | Ambas familias responden en paralelo, **read-only**, **sin merge**. Un panel las alinea: modelo, latencia, tokens, costo, y las dos respuestas completas. A/B puro. *"Relativity is the best benchmark."* |
| `/fusion "<prompt>" "<fusion-prompt>"` | 3 | ARCHITECT y BUILDER responden en paralelo **con tools completas** (cualquiera puede construir). Un tercer agente **FUSION** (modelo architect, sesión fresca) mergea las dos respuestas con atribución `[ARCHITECT]`/`[BUILDER]` y cierra con **"Consensus & Divergence"**. |
| `/auto-validate <prompt>` | 2 + gate | El loop de autovalidación: un **VALIDATOR diseña un gate de aceptación ANTES de que se construya nada**, el baseline debe fallar en rojo, el BUILDER construye, el gate corre, los fallos vuelven verbatim como instrucciones de corrección hasta verde o halt. |

La escalera es un micro-SDLC: `/opinion` (scout, dos tomas) → `/fusion` (planificar, un plan merged) → `/auto-validate` (construir + probar con gate).

### El loop de autovalidación (el corazón técnico)

Rojo → verde, con el gate diseñado **antes** del build (`SYSTEM_PROMPT_VALIDATOR.md`, `README` §"The auto-validation loop"):

1. **El VALIDATOR diseña el gate primero.** Inspecciona el proyecto read-only y escribe **un script Python `uv` single-file (PEP 723)** que sale 0 *si y sólo si* lo que pediste es lo que se construyó. Cada requisito explícito mapea a un check concreto (`expected X, found Y, at PATH`).
2. **El baseline debe fallar ROJO.** Un baseline que pasa significa gate débil o trabajo ya hecho; en cualquier caso te enterás fuerte.
3. **El BUILDER construye** con tools completas. El gate es visible pero **inmutable** para él.
4. **El gate corre.** Las líneas FAIL vuelven **verbatim** a la sesión del builder como correcciones. PASS termina.
5. **Escalation.** Desde la N-ésima falla (default 3), el VALIDATOR reingresa como **triage diagnostician**: inspecciona read-only y diagnostica *por qué* está atascado (archivo equivocado, interpretación equivocada, oscilación entre dos estados malos, prerequisito faltante, blocker de entorno… o un defecto del gate).
6. **Gate repair.** Si el triage diagnostica `GATE DEFECT` (el gate es insatisfacible o exige algo que nunca se pidió), el VALIDATOR **reescribe su propio gate una vez**, preserva el viejo como `gate.py.rN`, y el gate reparado re-corre **sin gastar una ronda de builder**. El contrato de repair **prohíbe debilitar cualquier check legítimo** — corregís tu bug, no movés el arco.
7. **Halt.** Tras `--max-validations` fallas (default 5), para y renderiza la última salida del gate ruidosamente. **Sin loops infinitos silenciosos.**

Principio de separación de poderes que atraviesa todo: **el builder nunca califica su propia tarea, y el grader nunca toca el código** (ni siquiera el gate repair escribe otra cosa que el único path del gate).

### Patrones técnicos secundarios (todos relevantes para nosotros)

- **Hijos clean-room:** cada spawn lleva `--no-skills --no-extensions --no-context-files` (`fusion-harness.ts:463-465`). El contrato entero del worker viene de sus prompt files → **determinístico y reproducible en cualquier máquina**, sin importar qué skills tengas instaladas.
- **Prompts en archivos, no en código:** todo default vive en `SYSTEM_PROMPT_*.md` / `USER_PROMPT_*.md` con interpolación `{{VAR}}`. *"Tuneás el harness editando archivos, no código."*
- **Artefactos fuera del repo:** cada corrida crea `/tmp/fusion-harness-XXX/` con `prompt.md`, un `<role>.md` por agente, `fused.md`/`gate.py`/`gate-output.txt`, `summary.json`. **Nunca escribe dentro del repo.** Los agentes downstream se anclan en ese dir con **paths exactos**, en vez de escanear el filesystem.
- **File-naming con identidad:** los workers concurrentes en el mismo cwd embeben `role+model` en cada path que crean, para no pisarse (prevención de race entre escritores paralelos).
- **Session keying per-project Y per-model:** el ARCHITECT es un cerebro persistente separado. Reproducir el transcript de un modelo como si fuera otro dispara el clasificador de usage-policy de Anthropic → keying per-model lo evita (ver **Apéndice A**).
- **Two-column DX:** la claridad del output *es* el producto — ARCHITECT a la izquierda, BUILDER a la derecha, labels y color duros por rol, footer con barra de context-window, output nunca interleaved, y los fallos nombran rol + modelo + error exactos.
- **Escape mata todo:** children primero, gate incluido; el panel dice que vos lo paraste, no culpa a los modelos.
- **Honestidad del blind-spot:** el README cierra con una matriz que admite que la fusión *sube* coverage pero no llega a perfección, y **un desconocido compartido entre ambas familias queda desconocido**. El propio run grabado terminó en ROJO por un defecto del gate (`gate.py:61` quitaba underscores de los nombres de estrategia) — y lo dejaron documentado en el `MANIFEST` en vez de esconderlo.

---

## 3. Cómo se mapea contra lo que ya tenemos

Nuestras skills cubren un espacio **más amplio** que los tres comandos de fusion-harness (nosotros revisamos artefactos de diseño; ellos no), pero con **menos rigor de gate objetivo** en el punto de implementación.

| Concepto de fusion-harness | Nuestro equivalente | ¿Qué tenemos / qué nos falta? |
|---|---|---|
| `/opinion` (A/B read-only, sin merge) | — (saltamos directo a `co-explore`) | **Falta el peldaño barato.** `co-explore` produce un mapa estructurado de 7 headings; no hay un "dos tomas rápidas lado a lado" liviano. |
| `/fusion` (2 workers + merge atribuido) | `co-explore` (2 mapas independientes → síntesis con "duelo de enfoques") | **Ya lo tenemos, y bien.** `co-explore/SKILL.md:263-298` ya escribe `findings-<familia>.md` antes de leer al otro y produce `synthesis.md` con divergencias evaluadas en méritos. Diferencia: su FUSION tiene tools completas y *construye* el merge; nuestra síntesis es del conductor. |
| `/auto-validate` (gate-first + loop) | `cross-implement` + `sdd-flow verify` | **Aquí está el gap.** Tenemos el loop de fixes acotado (`cross-implement` `max_fix_rounds`, `sdd-flow` tope de 3) y corremos `proof_cmd`, pero **el gate no se escribe antes del build ni exige baseline rojo**, y el `verify` de AC corre *después* de implementar. |
| Escalation → triage → gate repair | Tope de 3 fallas → "volver a `plan`/`specify`" | Tenemos el **tope**, no el **diagnóstico**. Ante N fallas volvemos a diseño, pero no hay un paso explícito de "diagnosticá *por qué* está atascado" ni "quizás el criterio de done está mal". |
| Separación de poderes (builder ≠ grader) | Parcial en `cross-implement` | El diff lo revisa el conductor (externo por construcción ✅) y corre la prueba él mismo ✅. Pero el criterio de prueba lo puede escribir el mismo conductor que luego hace el takeover — **no hay un rol grader inmutable separado**. |
| Consensus & Divergence con provenance | "Duelo de enfoques" en `co-explore` | **Casi idéntico.** Nos falta formalizar el *cierre* con "qué descarté y por qué" como contrato de output fijo. |
| Hijos clean-room + prompt por archivo | `--safe-mode` + prompt por stdin desde archivo | **Muy alineados ya.** `co-explore/reference.md:440` ya pasa el prompt por archivo, nunca inline; el implementador arranca con cero contexto de sesión (`cross-implement/SKILL.md:49`). |
| Artefactos fuera del repo + grounding por path | `.plans/`, `.cross-review/`, `cross-implement/` scratch (untracked) | **Alineados.** Ya escribimos scratch untracked y pasamos paths exactos. |
| Halt cap sin loop silencioso | Tope de 3 en `sdd-flow` | **Tenemos.** |
| Blind-spot honesty | — | **Falta.** Nuestras síntesis no cierran con "esto sube coverage, no garantiza correctitud; un unknown compartido queda unknown". |

**Conclusión del mapeo:** no necesitamos reescribir nada ni pivotar de rumbo. Necesitamos **cerrar el gap de gate objetivo** (idea 1), **agregar diagnóstico al tope** (idea 2) y **completar la escalera por abajo** (idea 3). El resto son refinamientos de bajo costo.

---

## 4. Diferencia filosófica que conviene tener presente

`fusion-harness` está diseñado para **quitar al humano del loop interno** (host = builder, gate automático, escalation automática) y ponerlo sólo al principio (el prompt) y al final (leer el resultado). Nosotros, deliberadamente, mantenemos **gates humanos en cada artefacto** y **degradación blanda** cuando la otra familia no está disponible.

Eso no es un defecto a corregir: es nuestra identidad y encaja con el uso real de Max (SDD con aprobaciones, Bitbucket, Jira, Orca). Pero tiene un costo que fusion-harness expone con nitidez: **cuando el criterio de aceptación vive sólo en la cabeza del conductor —o se escribe recién al verificar— la revisión depende del ojo humano en vez de un check objetivo.** La cura no es automatizar el humano; es darle al humano y al implementador un **contrato de done ejecutable, escrito antes, que ninguno de los dos pueda ablandar**.

---

## 5. Oportunidades priorizadas

### Oportunidad 1 — Gate-first / baseline-rojo en `cross-implement` (impacto alto)

**El problema hoy.** `cross-implement` congela un work order y resuelve un `proof_cmd` antes de lanzar (`cross-implement/SKILL.md:103-104`), y el conductor corre esa prueba fresca él mismo (`SKILL.md:133-136`). Pero:
- El `proof_cmd` puede ser un test *preexistente* o uno genérico; no se exige que **cada requisito del work order mapee a un check**.
- No hay **baseline rojo**: nada obliga a demostrar que la prueba *falla* contra el estado actual antes de construir. Un `proof_cmd` que ya pasa (o que no toca lo pedido) da falsa confianza — exactamente el "weak gate" que fusion-harness caza en el paso 2.

**La mejora.** Adoptar el contrato del VALIDATOR de fusion-harness como una **fase de "gate" opcional-pero-recomendada** dentro de `cross-implement`, antes del paso de delegación:

1. Antes de delegar, el **conductor** (no el implementador) destila el work order en un **gate ejecutable** —un script o un set de tests— donde *cada requisito explícito del work order mapea a al menos un check concreto* y *nada no-pedido es exigido*. Escrito a scratch (`cross-implement/gate.*`), fuera del repo.
2. **Correr el gate contra el estado actual y exigir ROJO.** Si pasa antes de construir: warning fuerte ("gate débil o trabajo ya hecho") y no delegar hasta resolverlo.
3. Pasar el gate al implementador como **inmutable** dentro del prompt-contrato (ya tenemos el bloque `PROOF`; se refuerza a "este es el criterio de done, no lo toques, no lo juegues").
4. Tras la implementación, el conductor corre el gate; los **FAIL vuelven verbatim** al loop de fixes existente (ya tenemos `codex exec resume` / reanudar la misma sesión, `cross-implement/reference.md:103-105`).

**Por qué encaja con nosotros y no rompe nada:** ya tenemos el loop de fixes, el scratch untracked, el prompt por archivo y el "corré la prueba vos mismo". Sólo agregamos **(a)** escribir el criterio *antes* y **(b)** exigir baseline rojo. Es la pieza que convierte "reviso el diff con buen criterio" en "reviso el diff *contra un criterio objetivo que escribí antes de ver el código*".

**Puente con `sdd-flow`.** El `verify` de `sdd-flow` ya tiene una gate function por AC con **revert-to-confirm** (`sdd-flow/SKILL.md:666-696`) — que es *más* riguroso que el gate de fusion-harness en un aspecto (prueba que el test tiene dientes revirtiendo el hunk). Lo que le falta es el **momento**: correr el esqueleto del gate *antes* de implementar (aunque sea como "estos son los checks que van a definir done, y hoy están todos en rojo"). Recomendación: mover parte de la definición de checks AC-first del `verify` (post) a `tasks`/`plan` (pre), dejando `verify` como la ejecución. No es urgente; la idea 1 sobre `cross-implement` es el mejor punto de entrada.

**Red flag a evitar (que fusion-harness documenta):** un gate mal escrito hace fallar por razones ajenas al pedido (su run real terminó rojo por un `strip('_')` de más). Por eso la idea 2.

---

### Oportunidad 2 — Escalation → triage → "¿el gate está mal?" (impacto alto, esfuerzo bajo)

**El problema hoy.** Nuestro tope es binario: 3 fixes fallidos de la misma falla → "es un problema de diseño, volvé a `plan`/`specify`" (`sdd-flow/SKILL.md:643-644`; `cross-implement` `max_fix_rounds` default 2 → takeover). Bien para no loopear infinito, pero **salta directo de "seguí corrigiendo" a "rendite/rehacé diseño"**, sin el paso intermedio de *entender por qué está atascado*.

**La mejora.** Insertar un **paso de triage** antes del takeover / vuelta-a-diseño, calcado del `SYSTEM_PROMPT_TRIAGE.md`:

- En la ronda de escalación (p. ej. la penúltima antes del tope), el conductor **cambia de modo**: en vez de mandar "corregí estos fallos otra vez", inspecciona el estado real (no las *claims* del implementador) y diagnostica **la causa raíz**: archivo equivocado, interpretación equivocada, **oscilación entre dos estados malos**, prerequisito faltante, blocker de entorno — **o un defecto del propio criterio de done**.
- **Reconocer explícitamente que el gate puede estar mal.** Si el criterio de aceptación es insatisfacible o exige algo nunca pedido, el conductor lo corrige **una vez** (sin debilitar checks legítimos) y re-corre — sin gastar una ronda de fix. Esto le falta por completo a nuestro flujo: hoy asumimos que si falla 3 veces, el código está mal; a veces el criterio está mal.

**Dónde aplica:** `cross-implement` (loop de fixes) y, con más razón, `systematic-debugging` — el principio "una hipótesis de causa raíz, no prueba y error" ya vive ahí; esto le agrega *"y una de las hipótesis válidas es que tu criterio de éxito esté equivocado"*. Es texto de contrato, esfuerzo bajo, y ataca una clase real de bucles improductivos.

---

### Oportunidad 3 — Peldaño `/opinion` + value ladder explícito (impacto medio, esfuerzo bajo)

**El problema hoy.** El escalón más barato que ofrecemos es `co-explore` en modo `explore`, que produce un mapa estructurado de 7 headings con síntesis — potente, pero **pesado** para "che, ¿qué opinan las dos familias de esto, rápido?". No hay un A/B liviano.

**La mejora (a):** agregar a `co-explore` un modo **`opinion`** (o una mini-skill hermana): las dos familias responden la **misma pregunta puntual** en paralelo, read-only, **sin síntesis obligatoria** — sólo las dos respuestas lado a lado + una línea de "en qué coinciden / en qué difieren". Es el scout barato antes de decidir si vale la pena el `explore` completo. Encaja con nuestra infra actual (ya lanzamos codex read-only por archivo; sólo omitimos el paso de síntesis estructurada).

**La mejora (b):** documentar la **escalera cross-model** como narrativa única (hoy las skills se presentan con fronteras estrictas —"esto no es lo otro"— pero sin una escalera que las una):

```
opinion (¿vale la pena?) → co-explore (mapear/investigar) → cross-review (criticar el diseño)
    → cross-implement con gate-first (construir + probar)
```

Fusion-harness vende esto como su killer feature ("chain them and you're running a micro-SDLC"). Nosotros ya tenemos las piezas y mejores fronteras; nos falta el **relato de escalera** en un doc o en el `sdd-flow` como recomendación de "cuánto rigor cross-model aplicar según la etapa/riesgo".

**La mejora (c), casi gratis:** formalizar el cierre de la síntesis de `co-explore` con el contrato de output de fusion-harness — **"Consensus & Divergence" + qué descarté y por qué**. Ya tenemos el "duelo de enfoques"; agregar la sección de descarte explícito (qué hipótesis/hallazgos tiré y por qué) hace auditable lo que hoy queda implícito.

---

## 6. Refinamientos menores (adoptar como principios, sin trabajo de skill dedicado)

- **Blind-spot honesty en los outputs.** Cerrar las síntesis de `co-explore` y las conclusiones de `cross-review` con una nota honesta: *"la segunda familia sube coverage, no garantiza correctitud; un punto ciego compartido entre ambas familias queda sin detectar."* Contrapeso al exceso de confianza en "ya lo revisó la otra familia". Una línea, alto valor anti-sycophancy.
- **Nombrar rol + modelo + error en los fallos.** Cuando la otra familia falla (binario ausente, MCP off, timeout), reportar exactamente *qué rol, qué modelo, qué error* — no "el secundario falló". Ya lo hacemos parcialmente; volverlo contrato.
- **Reforzar clean-room como garantía explícita.** Ya arrancamos con `--safe-mode` y prompt por archivo; vale documentar el *porqué* (determinismo/reproducibilidad) como hace fusion-harness, para que nadie lo "optimice" pasando contexto ambiente al delegado.

---

## 7. Lo que NO deberíamos copiar

Tomar ideas ≠ copiar el diseño. Estas decisiones de fusion-harness **no encajan** con nuestro rumbo:

- **Host = builder / autonomía total del loop.** Su chat crudo *es* el builder y el gate corre sin humano. Nosotros mantenemos gates humanos por diseño (SDD, PRs, Jira). Importamos el *gate objetivo*, no la *autonomía*.
- **Ser un runtime propio (extensión de Pi).** Nuestro valor es ser **portables** (skills Markdown que corren en Claude Code y Codex sin instalar un harness). Un `fusion-harness.ts` de 2506 líneas es lo contrario de portable. No vamos ahí.
- **Roles fijos ARCHITECT/BUILDER acoplados a modelos default.** Nuestra abstracción "conductor / la otra familia" es **simétrica** (funciona conduzca Claude o Codex) y no fija quién planifica vs construye. Es más general que su architect=Claude/builder=GPT. Mantenerla.
- **Two-column TUI.** Es DX de terminal atada a su renderer; nosotros producimos artefactos en disco y texto. No aplica.
- **Gate siempre en Python `uv`/PEP 723.** Buena elección para *ellos* (self-contained). Para nosotros el gate debe ser **el mecanismo nativo del repo target** (los tests/build/lint que ya existen), no imponer Python. Tomamos el *contrato* (cada requisito → un check, baseline rojo, inmutable), no el *lenguaje*.

---

## 8. Recomendación final

**Seguir con el rumbo actual** —skills Markdown cross-model, portables, human-in-the-loop— y ejecutar las tres oportunidades en orden:

1. **Gate-first / baseline-rojo en `cross-implement`** (la joya; cierra nuestro único gap real de rigor).
2. **Triage + "¿el gate está mal?" antes del tope** (barato, ataca bucles improductivos reales).
3. **Modo `opinion` + escalera cross-model documentada + cierre "Consensus & Divergence"** (completa la value ladder por abajo).

Todo lo demás (blind-spot honesty, clean-room documentado, naming de fallos) son principios de una línea que se pueden colar en la próxima edición de cada skill. **No hay nada aquí que justifique un pivote**; hay una pieza —el gate objetivo escrito antes— que vale la pena robar bien.

Si Max quiere, el siguiente paso natural es un `brainstorming` sobre la oportunidad 1 (cómo se ve exactamente el gate-first dentro de `cross-implement`: dónde vive el script, cómo se pasa como inmutable, cómo se reconcilia con `sdd-flow verify`) antes de tocar ninguna skill.

---

## Apéndice A — Hallazgo técnico: bloqueo de usage-policy al reproducir transcripts cross-model

Relevante para el trabajo en curso de **`cross-model-real-sessions`** (sesiones reales Claude↔Codex vía Orca). Del README de fusion-harness, §"Where it can still fail":

> Fable ships stricter safety classifiers, and a long accumulated agent transcript can false-positive — observed when a sonnet-built session (turns saying "you are claude-sonnet-5" + script execution) was replayed into fable-5: **every request blocked at the API**, even `/opinion hello`, while the same prompt on a fresh session passed.

Su mitigación: **keying de sesión per-project Y per-model** — nunca reproducir el transcript construido bajo un modelo como historia propia de otro modelo. El `--architect` y `--builder` acuñan cerebros persistentes separados; cambiar el modelo mint-ea una sesión nueva (`README` §"Raw chat IS the builder", confirmado en `fusion-harness.ts:446-447` — `sessionId` estable per-rol, `fork` copy-on-write del host).

**Implicancia para nosotros:** si `cross-model-real-sessions` alguna vez hace que una familia herede o "continúe" el transcript literal de la otra (no sólo un handoff destilado), puede toparse con este bloqueo del clasificador. El diseño seguro es el que ya favorecemos: **pasar al secundario un contrato destilado / handoff, no el transcript crudo del conductor**. Vale anotarlo como riesgo verificable en ese doc.

---

## Apéndice B — Inventario de lo revisado

- `README.md` (333 líneas) — guion completo del video, cubre los 3 comandos, host-as-builder, gate loop, two-column DX, recetas, failure modes.
- `extensions/fusion-harness/fusion-harness.ts` (2506 líneas) — el harness entero; leídos los bloques de spawn clean-room (`:461-474`), identidad de sesión/fork (`:440-473`), y el envelope de corrección con gate reparado (`:824-846`).
- 10 prompt files (`SYSTEM_PROMPT_{VALIDATOR,TRIAGE}.md`, `USER_PROMPT_{FUSION_WORKER,FUSION_MERGE,FUSION_DEFAULT_INSTRUCTION,OPINION,BUILDER,CORRECTION,VALIDATOR,TRIAGE}.md`) — leídos completos.
- `live_final_generation/` — el run SOTA grabado: `MANIFEST`, `gate.py` (15 checks), `gate-baseline.txt` (rojo requerido), `gate-round-5.txt` (terminó rojo por defecto del gate, documentado con honestidad).
- `justfile`, `.claude/commands/{install,prime}.md` — recetas de modelos (WORKHORSE vs SOTA) y flags.
- Video `AQl5Q-0l7FQ` — transcripción completa descargada con `yt-dlp` (auto-subs EN, limpiada a texto plano en `video-transcript.txt`) y leída íntegra. Matices que agrega respecto del README en el Apéndice C.

---

## Apéndice C — Matices del video que el README no explicita

La transcripción confirma el README casi al pie de la letra, pero cuatro ideas del audio afinan el análisis:

1. **"Esto NO es delegación a subagentes — es un equipo."** El autor lo repite varias veces: *"We're not handing off a task. We have two agents, a really tight-knit team working together… this is where we push further than your classic sub-agent delegation."* Es una distinción útil para nosotros: **`co-explore` ya es "equipo"** (dos mapas independientes que se sintetizan / debaten), pero **`cross-implement` es "delegación"** (handoff de un work order congelado a la otra familia). No es un defecto —el handoff congelado es intencional y más seguro— pero explica *por qué* `cross-implement` es donde más se nota la falta del gate objetivo: en un handoff, el criterio de done tiene que ser explícito y externo, porque no hay un "equipo" deliberando en vivo. Refuerza la **oportunidad 1**.

2. **Los dos constraints de la ingeniería agéntica: planning y review.** El video enmarca `/auto-validate` como el ataque directo al **segundo constraint (review)**: *"any prompt we write can have a validation flow written before the work is even started."* Nuestro stack ataca bien el *planning* (co-explore, cross-review, sdd-flow), pero el *review* lo dejamos casi todo en el ojo humano del gate. El gate-first es, literalmente, "review escrito antes de construir". Es el encuadre que le da urgencia a la oportunidad 1.

3. **El system prompt como leverage point.** *"You have to overwrite the system prompt to really guide your agent to powerful results."* Por eso exponen `--architect-system-prompt` / `--builder-system-prompt`. Nosotros ya inyectamos contratos completos por prompt-archivo al delegado — el principio (el comportamiento del secundario es un artefacto tuneable, no un default heredado) ya lo encarnamos; vale tenerlo consciente al diseñar el prompt del gate/implementador.

4. **Reconoce la crítica del "error-rate stacking" y la contesta.** *"Some engineers keep pointing to the error rates when you stack up these agents… that's only the case when you haven't templated your engineering into your system."* Es honesto a medias: apilar familias multiplica costo y puede multiplicar errores si el contrato es flojo. Para nosotros es un argumento *a favor* de las oportunidades 1 y 2 (gate objetivo + triage): son justamente el "templating" que evita que apilar familias degenere en ruido.

> Aparte no técnico: buena parte del video es tesis de marca de IndyDevDan —"harness ownership", "sovereign AI", "¿los labs se roban tu data?"— pro-Pi y anti-herramientas cerradas. Es tangencial a nuestras skills, con una lectura útil: **nuestras skills Markdown portables *son* harness ownership** sin acoplarnos a un runtime propietario. Coincidimos con su tesis por una vía más portable que la suya.
