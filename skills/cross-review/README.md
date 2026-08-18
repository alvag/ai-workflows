# cross-review

**Segunda opinión cross-model** para artefactos de Spec-Driven Development. Antes de que un
humano apruebe una `spec`, `plan`, `tasks`, `master-spec`, `reparto` o la `sintesis` de una co-exploración, un modelo de **otra
familia que el autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) lo critica de
forma adversarial en un loop acotado y read-only. La crítica se
presenta junto al artefacto en el gate de aprobación: la persona decide con esa entrada ya a la
vista.

Es la segunda pieza del trío cross-model: **`co-explore`** (explorar/investigar en paralelo),
**`cross-review`** (criticar el diseño antes de implementar) y **`cross-implement`**
(implementación cruzada: uno planifica, el otro implementa, el primero revisa el diff). Las tres
son opcionales, degradables y encadenables — dentro de SDD vía sus gates, o fuera como pipeline
portable (draft → crítica → implementación cruzada).

## Por qué existe

En el flujo SDD, el mismo modelo que escribe la spec/plan/tasks es —hoy— el único que los revisa
antes del gate humano. Eso deja errores correlacionados: el revisor comparte los puntos ciegos
del autor. Un modelo de **otra familia** rompe esa correlación y caza lo que el primero no ve: un
AC faltante, un enfoque frágil, un riesgo no considerado, un contrato entre servicios que no
cierra. Cazarlo en el plan cuesta minutos; cazarlo después de implementar, horas.

## Qué hace

```
artefacto escrito ──► [cross-review] ──► artefacto (quizá revisado) + resumen de crítica ──► GATE humano
```

- **Augmenta el gate, no lo reemplaza.** Corre antes del STOP y le da insumo a la persona. Claude
  y el usuario siguen siendo el árbitro final.
- **Read-only.** El revisor nunca escribe en el repo. Si hay algo que aplicar, lo edita Claude.
- **Loop acotado, con salida en manos de la persona.** `max_rounds` (default 3) es el presupuesto de
  **una tanda**, no de la corrida entera: al agotarse no se cierra sola — se abre un checkpoint donde
  elegís entre continuar así, conceder otra tanda, seguir hasta `APPROVED` (con un tope total) o
  cerrar la revisión. El loop nunca corre sin tope, y quien lo extiende sos vos.
- **Y en ese checkpoint resolvés las disputas.** Un finding queda `en-disputa` cuando el loop no
  puede resolverlo solo: el conductor lo escaló, o sostuvo un rechazo que el revisor había
  defendido, o el revisor insistió sobre algo ya corregido. Ninguna ronda adicional lo destraba
  —por eso el checkpoint corta apenas quedan sólo disputas—, así que lo arbitrás vos, **antes** de
  elegir qué hacer con la revisión: para cada uno, o le das la razón al revisor y la corrección se
  aplica, o sostenés el rechazo por su mérito y el finding se cierra. Podés resolver de una vez
  varios que compartan motivo; el registro guarda igual la decisión de cada uno, con su porqué.
- **La revisión no converge sobre ediciones que nadie miró.** Aplicar un finding es un cambio nuevo y
  sin revisar, y puede introducir un defecto propio: por eso una edición aplicada **impide** el
  `APPROVED` **hasta** que una ronda posterior la observe con el artefacto actualizado delante. No
  crea rondas fuera del presupuesto —el tope sigue mandando—, pero si la tanda se agota con ediciones
  sin mirar, el checkpoint te lo dice y con cuáles, para que decidas sabiéndolo.
- **Sin sycophancy, en las dos direcciones.** Cada finding del revisor se evalúa técnicamente (vía
  `superpowers:receiving-code-review`): se aplica si es correcto, se rechaza **con motivo** si no —
  un rechazo sin motivo es un estado inválido. Y el revisor puede **defender** un rechazo una vez,
  si trae un argumento nuevo; una defensa admisible obliga a re-arbitrar, no a aceptar.
- **Auditable.** Deja un `review-log.md` con un **ledger append-only** de todo lo que le pasó a cada
  finding, y un `Resultado` que separa los **eventos de arbitraje** (cuántos se aplicaron, cuántos se
  rechazaron, cuántas defensas hubo y cuántas eran admisibles) de los **estados finales**. Es lo que
  hace visible el escrutinio y no solo el desenlace.
- **Nunca bloquea.** Si no hay revisor o algo falla, degrada al gate humano de siempre.

## Cuándo usarla

- `/cross-review .plans/<id>/plan.md` → revisa ese artefacto (modo directo).
- Pedidos en lenguaje natural: "revisa este plan con otra opinión", "segunda opinión de la spec",
  "pídele a Codex que critique el reparto" → el modelo puede invocarla directamente.
- `/cross-review` **sin ruta** (o "stress-test de esta idea", "arma un plan y que Codex lo
  critique") → **modo draft**: redacta un plan ligero desde la conversación + el código, lo somete
  al mismo loop y, al converger, ofrece el handoff a la implementación (inline o cruzada vía
  `cross-implement`, si está instalada). Es el punto de entrada portable, fuera de todo flujo SDD.
  Regla rápida frente a `co-explore`: **¿mapa o veredicto?** — el draft ataca un enfoque **ya
  elegido** (veredicto); si el terreno sigue abierto y falta entender qué existe y dónde tocar,
  antes va `co-explore` (mapa).
- La invocan `sdd-flow` y `sdd-orchestrator` en sus gates (modo embebido, vía Skill tool), si está
  instalada y la config no la desactiva.

No se dispara espontáneamente: su description la restringe a pedidos explícitos del usuario o a la
invocación desde una skill SDD (y nunca sobre diffs/PRs/código). "sin cross-review" la salta.

## Requisitos

Ninguno obligatorio: es una **capacidad opcional**. Para que la revisión efectivamente ocurra,
hace falta un **segundo modelo de otra familia que el autor** (el agente que conduce la skill),
descubierto por capacidad:

- Autor Claude → el subagente `codex:codex-rescue` (plugin codex) — camino
  preferido; **no** usa `/codex:review` (ese es solo para git diff/código), usa el camino `task`
  en read-only. O el CLI `codex exec` en el PATH (portable, fuera del plugin).
- Autor GPT/Codex → el CLI `claude -p` en el PATH, restringido a tools de lectura.

Sin el revisor de la otra familia disponible, la skill devuelve `UNAVAILABLE` y el flujo SDD
continúa con su gate humano.

## Integración con sdd-flow y sdd-orchestrator

La dependencia es **blanda**: `sdd-flow`/`sdd-orchestrator` chequean si esta skill está instalada
y, si no, omiten la revisión. Por eso siguen siendo portables y standalone sin este helper.

- **sdd-flow** la invoca en los gates `specify`/`plan`/`tasks`. Default por complejidad: `trivial`
  off, `normal` opt-in, `complex` on.
- **sdd-orchestrator** la invoca en los gates `master-spec`/`reparto` (Fase 1). Los plan/tasks
  por-repo quedan cubiertos ahí; la Fase 2 no re-revisa.

Configuración bajo `cross_review` en `.specify/config.yml` (sdd-flow) o en el `manifest.yml`
(sdd-orchestrator). Ver `reference.md`.

## Ejemplos de uso

**1. Revisar un plan complejo antes de implementar:**
```
/cross-review .plans/PROJ-128/plan.md
```
→ descubre el revisor, corre el loop read-only, edita el plan con lo aplicado, deja `review-log.md`
y presenta el resumen de la crítica.

**2. Desde sdd-flow, automático en complejo:** al llegar al gate de `plan` de un cambio
clasificado *complejo*, sdd-flow invoca esta skill, y presenta el plan **con** la crítica en el
mismo STOP de aprobación.

**3. Saltarla para una corrida:**
```
/sdd-flow empezar PROJ-128: …, sin cross-review
```
→ `mode: off` para esa corrida; gate humano directo.

## Qué escribe en tu repo

Además del `review-log.md` y el scratch junto al artefacto, cada corrida deja un **manifest**: un
JSON de unos 300 bytes en `.cross-model/runs/` con modo, familias, transporte, duración, veredicto y
degradación. Existe para poder mirar cien corridas juntas y decidir si la segunda opinión se gana su
costo — sin datos, esa decisión es intuición. Se escriben **los tres veredictos**, no solo los
`APPROVED`: una serie que omite las corridas que fallaron no puede contestar la pregunta.

Es local y untracked, y ninguna skill toca tu `.gitignore`: agrega `.cross-model/` a
`.git/info/exclude` si prefieres que git deje de nombrarlo. Se apaga con
`cross_model.manifest.mode: "off"`. Esquema y recorte en `reference.md` → "Manifest de corrida",
que es también la sede canónica para `co-explore`, `cross-implement` y `bitbucket-code-review`.

Bajo la misma raíz, pero en `.cross-model/active/`, vive el otro registro: el **sobre de la corrida
en vuelo**, un archivo por revisión despachada con el revisor que salió, dónde escribe, por qué
transporte viaja, hasta cuándo se lo espera y si su resultado ya se cosechó. Los dos directorios
dicen cuánto vive lo que guardan: `runs/` acumula lo que ya pasó, y `active/` contiene únicamente lo
que sigue corriendo —el archivo se retira cuando la corrida llega a un final comprobado y su crítica
quedó adjudicada—. Es lo que permite que una sesión nueva encuentre la revisión en vuelo en vez de
arrancar otra encima, y no se deduce del checkpoint durable ni al revés: aquel registra un STOP
esperando que **tú** decidas, y el sobre, un worker del que todavía se espera un resultado.

**`cross_model.manifest.mode` no lo apaga.** Esa clave gobierna el manifest y solo el manifest; el
sobre es obligatorio e **independiente** de ella, porque un proyecto que decidió no medir sus
revisiones sigue necesitando saber cuál tiene despachada. Tampoco existe una clave propia para
desactivarlo: lo único que habilitaría un interruptor del sobre es justamente la pérdida de hilo que
el sobre existe para cerrar.

El contrato del sobre está en `corridas-en-vuelo.md`, y **esta skill es su sede canónica**: las otras
seis copias se generan de la de aquí, byte a byte. De ahí sale un riesgo que solo aparece del lado de
la instalación — si actualizas unas skills y no otras, te queda un directorio de skills con versiones
**mezcladas** del contrato, y nada en tu entorno lo verifica, porque el chequeo de identidad vive en
el repo de autoría. Por eso la **primera línea** de cada copia nombra su sede: abre la copia
sospechosa, mira contra qué archivo dice que hay que compararla, y actualiza la que quedó atrás.

## Archivos

- `SKILL.md` — el flujo, las reglas y el contrato de invocación.
- `reference.md` — cómo descubrir/invocar el revisor, plantilla del prompt, formato de salida,
  plantilla del `review-log.md`, dimensiones de inspección, configuración.
- `corridas-en-vuelo.md` — el contrato del sobre, y la **sede canónica** de la que se generan las
  copias de las otras seis skills que despachan.
- `README.md` — este archivo.
