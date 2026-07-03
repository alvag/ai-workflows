# co-explore — generalización + modo `investigate` (diseño)

**Fecha:** 2026-07-03
**Estado:** implementado.
**Antecedente:** `docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md` (diseño original,
SDD-only, dos modos).

## Problema

`sdd-co-explore` nació como pieza interna del flujo SDD: exploración paralela cross-model
**pre-spec** (`explore`) y contra-enfoque **pre-plan** (`counter-plan`). Su modo directo solo
presentaba *un* mapa (el del revisor), sin síntesis.

Se quiere usar la misma capacidad —dos mapas independientes read-only que convergen— para
**investigar bugs fuera de todo flujo SDD**: describís el bug (o `/co-explore <bug>`), dos
modelos de familias distintas investigan la causa raíz en paralelo, y el conductor sintetiza las
dos investigaciones en hipótesis rankeadas. Como SDD pasa a ser *un consumidor más* y no la
identidad, el prefijo `sdd-` deja de tener sentido.

## Decisiones

1. **Una sola skill generalizada + rename**: `sdd-co-explore` → `co-explore`. SDD es consumidor.
   Modos: `explore | counter-plan | investigate`. (Descartado: skill hermana duplicada.)
2. **Convergencia = síntesis del conductor, una pasada, sin rondas.** No hay deliberación
   multi-ronda; respeta el contrato de una-pasada de los modos existentes. (Descartado:
   deliberación multi-ronda entre modelos.)
3. **El modo directo corre la síntesis completa** (conductor escribe su mapa → lee el del revisor
   → sintetiza y presenta la conclusión), en vez del único mapa que presentaba antes.
4. **No-convergencia**: hereda el comportamiento de co-explore — si los dos mapas divergen en la
   causa raíz, se presentan **ambas posiciones** (checkpoint de divergencia), sin forzar consenso.
5. **Alcance de `investigate`**: termina en **hipótesis sintetizadas + plan de verificación**. NO
   verifica ejecutando como parte de la skill, NO arregla. El valor cross-model vive en el espacio
   de hipótesis (dos lentes con puntos ciegos distintos); verificar es determinístico y
   single-model.
6. **Capacidades asimétricas**:
   - **Conductor: L0/L1.** Lee (L0) y, opt-in, **ejecuta** (L1) —reproducir, correr tests, logging
     efímero— en un **worktree descartable**. Invariante: *nunca persiste cambios en el árbol del
     usuario*. L1 rinde sobre todo en la síntesis, para **adjudicar divergencias**.
   - **Revisor: L0 read-only siempre.** Headless/fire-and-capture; su valor es la lente
     independiente al leer. Lee un checkout **estable**, no el worktree que el conductor muta.
7. **Handoff a verificación/fix**: lo ofrece el **conductor** invocando
   `superpowers:systematic-debugging`, no co-explore. La skill entrega hipótesis + plan.
8. **Nombre**: `co-explore`. **Config key**: se queda `cross_review.co_explore` (config de
   callers SDD; `investigate` standalone no usa config).

### Fuera de alcance
- **L2 (editar / intentar fixes)**: sería una "carrera de fixes cross-model" — otra skill futura
  (tipo `co-fix`), no este modo.
- Deliberación multi-ronda.
- Cambiar el comportamiento de `explore`/`counter-plan`.

## Contrato del modo `investigate`

- **`context_package`**: síntoma reportado del bug + evidencia de reproducción observada
  (consola/red/stacktrace/pasos) si la hubo + prompt del usuario. Sin ticket ni AC necesariamente.
- **Prompt del revisor** (bug-shaped, read-only, no ejecuta): rastrear causa raíz, rankear
  hipótesis, decir cómo confirmar cada una; no proponer el arreglo.
- **Informe** (`investigate-<familia>.md`): `## Síntoma` / `## Mapa de código` /
  `## Hipótesis de causa raíz` (rankeadas: evidencia · confianza · cómo confirmarla) /
  `## Incógnitas` / `## Supuestos` / `## Plan de verificación`.
- **Síntesis** (bug-shaped): convergencias/divergencias + **duelo de hipótesis de causa raíz** +
  hipótesis líder + plan de verificación. Divergencia no resuelta → presentar ambas.
- **Deadline**: 600s default (como `explore`); override conversacional (no config).
- **Scratch root**: sin `.plans/<id>/`, un dir local untracked `.co-explore/<slug>/` (o temp).

## Archivos tocados
- `skills/co-explore/{SKILL,reference,README}.md` — rename, modo `investigate`, invariante de
  capacidades (regla 1), síntesis generalizada, alcance, prompt/informe/síntesis bug-shaped,
  capacidades y worktree.
- Callers: `skills/sdd-flow/{SKILL,reference}.md`, `skills/sdd-orchestrator/{SKILL,reference}.md`,
  `skills/sdd-cross-review/{SKILL,reference}.md` — refs de nombre/invocación (`cross_review.co_explore`
  sin cambios).
- Symlinks a scope usuario: `~/.claude/skills/co-explore` (Claude Code), `~/.agents/skills/co-explore`
  (Codex). Removido el symlink por-proyecto de Cocha.
- `docs/superpowers/specs/2026-07-03-sdd-co-explore-design.md` — banner apuntando a este doc.
