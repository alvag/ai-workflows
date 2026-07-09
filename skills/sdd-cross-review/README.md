# sdd-cross-review

**Segunda opinión cross-model** para artefactos de Spec-Driven Development. Antes de que un
humano apruebe una `spec`, `plan`, `tasks`, `master-spec` o `reparto`, un modelo de **otra
familia que el autor** (Codex cuando conduce Claude; Claude cuando conduce Codex) lo critica de
forma adversarial en un loop acotado y read-only. La crítica se
presenta junto al artefacto en el gate de aprobación: la persona decide con esa entrada ya a la
vista.

Es la segunda pieza del trío cross-model: **`co-explore`** (explorar/investigar en paralelo),
**`sdd-cross-review`** (criticar el diseño antes de implementar) y **`cross-implement`**
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
artefacto escrito ──► [sdd-cross-review] ──► artefacto (quizá revisado) + resumen de crítica ──► GATE humano
```

- **Augmenta el gate, no lo reemplaza.** Corre antes del STOP y le da insumo a la persona. Claude
  y el usuario siguen siendo el árbitro final.
- **Read-only.** El revisor nunca escribe en el repo. Si hay algo que aplicar, lo edita Claude.
- **Loop acotado.** Hasta `max_rounds` rondas (default 3), con veredicto `APPROVED`/`REVISE`.
- **Sin sycophancy.** Cada finding del revisor se evalúa técnicamente (vía
  `superpowers:receiving-code-review`): se aplica si es correcto, se rechaza con razón si no.
- **Auditable.** Deja un `review-log.md` con rondas, findings y las decisiones de Claude.
- **Nunca bloquea.** Si no hay revisor o algo falla, degrada al gate humano de siempre.

## Cuándo usarla

- `/sdd-cross-review .plans/<id>/plan.md` → revisa ese artefacto (modo directo).
- Pedidos en lenguaje natural: "revisa este plan con otra opinión", "segunda opinión de la spec",
  "pídele a Codex que critique el reparto" → el modelo puede invocarla directamente.
- `/sdd-cross-review` **sin ruta** (o "stress-test de esta idea", "arma un plan y que Codex lo
  critique") → **modo draft**: redacta un plan ligero desde la conversación + el código, lo somete
  al mismo loop y, al converger, ofrece el handoff a la implementación (inline o cruzada vía
  `cross-implement`, si está instalada). Es el punto de entrada portable, fuera de todo flujo SDD.
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
/sdd-cross-review .plans/PROJ-128/plan.md
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

## Archivos

- `SKILL.md` — el flujo, las reglas y el contrato de invocación.
- `reference.md` — cómo descubrir/invocar el revisor, plantilla del prompt, formato de salida,
  plantilla del `review-log.md`, foco por tipo de artefacto, configuración.
- `README.md` — este archivo.
