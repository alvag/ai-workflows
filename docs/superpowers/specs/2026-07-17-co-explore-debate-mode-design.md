# Diseño: modo `debate` en `co-explore` (soporte a decisiones cross-model)

Fecha: 2026-07-17
Estado: aprobado (pendiente de plan de implementación)
Skills afectadas: `co-explore` (nuevo modo), `sdd-flow` (config + disparadores)

## Contexto y objetivo

Inspirado en la skill `debate` de omnigent (`debby`). Hoy tenemos:

- `co-explore`: dos exploraciones **independientes** cross-model (una ronda) — modos `explore`
  (pre-spec), `counter-plan` (pre-plan) e `investigate` (causa raíz de un bug).
- `cross-review`: crítica adversarial de un artefacto escrito (asimétrico: autor vs revisor).

Ninguno cubre un **ida-y-vuelta iterado** entre las dos familias para **ayudar a decidir cuando
el usuario no está seguro** de qué opción tomar. Ese es el objetivo de `debate`: ante una decisión
abierta ("¿enfoque X o Y?"), las dos familias forman posturas independientes, se critican en varias
rondas, y el conductor entrega una **síntesis neutral atribuida** para que el usuario decida.

**Principio rector: `debate` no decide, afila la decisión.** Sigue el ethos de árbitro humano de
`cross-review` (regla 3): la síntesis nunca elige un ganador; presenta las posturas para que el
usuario arbitre.

## Decisiones de diseño (resueltas en brainstorming)

- **Dónde vive:** un **modo nuevo `debate` en `co-explore`** (no una skill nueva). Reusa la
  maquinaria de despacho a la otra familia, la independencia y la síntesis que co-explore ya tiene.
  Descartado: skill `cross-debate` standalone (duplica superficie).
- **Estructura del debate:** el **conductor es una voz + la otra familia es la otra**. El conductor
  participa y sintetiza de forma neutral; el usuario es el árbitro. Descartado (por ahora):
  moderador neutral con dos sub-agentes al estilo debby (más fiel pero 2 despachos por ronda; queda
  como evolución futura si el sesgo del conductor molesta).
- **No reintroduce personas por rol** (decisión previa ya tomada): las dos voces son las dos
  familias de siempre (Claude y GPT/Codex), no personajes inventados.

## Alcance

**Incluye:**
- Nuevo modo `debate` en `co-explore` (standalone + embebido).
- Enganche en `sdd-flow` en los pasos `clarify` y `plan`.
- Config `co_explore.debate` (`mode`, `max_rounds`) en `.specify/config.yml`.
- Degradación y router.

**No incluye (fuera de alcance / evolución futura):**
- Moderador neutral con dos sub-agentes (Model 2 del brainstorming).
- Modo `on` que corra el debate automáticamente sin ofrecer (por ahora **siempre** ofrece).
- Enganche en `sdd-orchestrator` (se puede sumar después con el mismo patrón; no en v1).

## La mecánica del debate

### Entrada — el paquete de decisión

El conductor arma:
- La **decisión a resolver** + las **opciones en juego** (si el usuario las dio; si no, el conductor
  las deriva y las declara).
- El **contexto** relevante: lee el código del repo (como los otros modos de co-explore) y, en
  sdd-flow, la ambigüedad de `clarify` o el trade-off contestable del `plan` + spec/plan como
  contexto.

### El loop (independencia primero, crítica cruzada después)

- **R0 — posturas independientes.** El conductor escribe su propia postura; en paralelo despacha a
  la otra familia con el **mismo** planteo (paquete de decisión, **sin** la postura del conductor)
  para que forme la suya a ciegas. Ambos arrancan sin verse — regla de independencia de co-explore
  (anti-anclaje).
- **R1..N — crítica cruzada.** Se cruzan las posturas: cada familia recibe la del otro, la critica y
  actualiza la propia. Cada ronda registra el **delta** (qué concedió, qué sostuvo cada uno). El
  cruce siempre enfrenta la postura del otro, nunca la propia.
- **Convergencia + anti-desperdicio.** Default **3 rondas** de cruce; tope duro `max_rounds`
  (default 3). Si una ronda no mueve nada (ninguno concede ni refina), **converge temprano** y lo
  dice — no quema rondas.

### Salida — síntesis neutral (decide el usuario)

El conductor presenta:
- **Postura final de cada familia**, atribuida y **sin fusionar** en una sola voz.
- **Dónde convergieron** y **qué queda en disputa**.
- **Los trade-offs afilados**: qué compra y qué cuesta cada opción, según salió del cruce.
- **No elige ganador** — se presenta para que el usuario decida.

### Artefactos

Locales/untracked, en el subdir de co-explore:
- `debate.md` — la síntesis + las posturas finales atribuidas.
- Los intercambios crudos por ronda van al scratch de co-explore (auditoría).
- En sdd-flow: `.plans/<id>/co-explore/`. Standalone: el dir local del modo directo de co-explore.

### Los artefactos SDD no citan el debate

Si la decisión alimenta una respuesta de `clarify` o un trade-off del `plan`, la `spec.md`/`plan.md`
se escriben de forma autónoma: sin mencionar el debate, sus artefactos, ni el vocabulario del método
(conductor/revisor/familias/rondas). Misma regla que co-explore ya aplica a la co-exploración. La
trazabilidad queda en `.plans/<id>/co-explore/debate.md`.

## Integración con sdd-flow

### Config

En `.specify/config.yml`, un sub-bloque `debate` dentro de `co_explore` (cohesión), **independiente**
de `co_explore.mode` (se puede querer debate sin haber corrido la exploración pre-spec):

```yaml
co_explore: {mode: auto, deadline: 600, debate: {mode: auto, max_rounds: 3}}
```

- `mode: off | on | auto` — controla **cuándo se ofrece** el debate (ver umbrales abajo).
- `max_rounds: 3` — tope de rondas de cruce (default 3).
- Entra en el **eco del checkpoint de inicio** de sdd-flow (p. ej. `… co_explore.debate auto →
  ofrezco debate en decisiones complejas`).

### Disparadores (`clarify` y `plan`)

- **`clarify`:** cuando una pregunta es una decisión abierta real (no algo que el código responde)
  y `debate.mode` es `on`/`auto`, el flujo **ofrece**: *"esta decisión (X vs Y) es contestable —
  ¿la someto a debate cross-model antes de que decidas?"*. Si el usuario acepta → corre el modo
  `debate` → presenta la síntesis → el usuario decide → la respuesta se registra en
  `## Clarifications`. Si no → clarify normal.
- **`plan`:** cuando hay un trade-off contestable (los que ya se nombran en "Decisiones y
  trade-offs"), ofrece someter *ese* trade-off a debate antes del gate del plan.

### Siempre ofrece, nunca corre solo

Aun en `on`/`auto`, el debate **pregunta primero** (gasta despachos, y es el UX pedido). El modo
controla el **umbral del ofrecimiento**:

- `off` — nunca ofrece.
- `auto` — ofrece solo si la decisión es compleja / high-stakes (auth, pagos, migraciones de datos o
  schema, concurrencia, cambios difíciles de revertir) **o** el conductor está genuinamente inseguro.
- `on` — ofrece en cualquier decisión contestable de `clarify`/`plan`.

## Standalone y router

Invocación directa fuera de todo flujo:
- `/co-explore debate <decisión>`, "no sé si X o Y, que Codex y tú lo debatan", "somete esto a
  debate", "debatan si conviene X o Y".
- co-explore ya infiere el modo por intención (bug → `investigate`, etc.); se agrega: **decisión
  abierta / "no sé qué elegir" → `debate`**.

Fila nueva en el router de co-explore y ajuste de la fila de desambiguación (mapa vs veredicto vs
**decisión**): `explore` mapea terreno abierto, `cross-review` ataca un enfoque ya elegido,
`debate` ayuda a **elegir** entre opciones cuando el usuario está inseguro.

## Degradación (nunca bloquea)

Si la otra familia no está disponible (con las reglas de **pared confirmada** vs **flake
transitorio** ya incorporadas a co-explore): el debate no corre; el conductor presenta su
**análisis de una sola voz** y avisa en una línea que el debate no estuvo disponible. En sdd-flow,
el flujo sigue al gate normal de `clarify`/`plan`. Misma filosofía que el resto de co-explore.

## Reglas no negociables / salvaguardas

1. **No auto-elige.** La síntesis presenta posturas atribuidas; el usuario decide (ethos regla 3 de
   cross-review).
2. **Independencia en R0.** La otra familia forma su postura sin ver la del conductor.
3. **Atribución, no fusión.** Nunca colapsar las dos voces en una; la divergencia es el valor.
4. **Anti-desperdicio.** Converger temprano si una ronda no aporta; tope duro `max_rounds`.
5. **Siempre ofrece, nunca corre sin un "sí".** El debate gasta despachos; se pide confirmación.
6. **Los artefactos SDD no citan el método.** spec/plan autónomos; trazabilidad solo en
   `co-explore/`.
7. **Dos familias, no personas.** Las voces son Claude y GPT/Codex, no roles inventados.
8. **Degradación blanda.** Sin la otra familia, análisis de una voz + aviso; nunca bloquea.

## Evolución futura (anotada, fuera de v1)

- **Model 2 (moderador neutral + dos sub-agentes):** si el sesgo del conductor-participante molesta,
  mover a un moderador que se queda afuera y despacha dos sub-agentes (uno por familia). Cuesta 2
  despachos por ronda.
- **`on` con auto-run:** un modo que corra el debate sin ofrecer, para quien lo quiera siempre.
- **Enganche en `sdd-orchestrator`:** ofrecer debate en decisiones de la Fase 1 (contratos entre
  servicios, reparto) con el mismo patrón.
