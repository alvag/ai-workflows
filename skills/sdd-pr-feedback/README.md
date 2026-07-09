# sdd-pr-feedback

Procesa el feedback de un Pull Request de Bitbucket **como un flujo SDD disparado por los
comentarios**. Lee los comentarios sin resolver, los clasifica con criterio (ruido / duda /
cambio), corre el flujo `sdd-flow` con su cross-review y sus gates, responde o resuelve comentarios
con confirmación explícita, y cierra el PR en **un solo commit**.

Es el front-end de PR del ecosistema SDD: donde `bitbucket-code-review` **produce** comentarios de
review (solo lectura), esta skill **reacciona** a los comentarios ya publicados en un PR.

## Qué hace

- **Triage con criterio.** El comentario es una sugerencia a evaluar, nunca una orden — y dato no
  confiable (defensa contra prompt-injection). No asume que haya que hacer lo que dice.
- **Grounding.** Se apoya en los artefactos previos del `.plans/<id>/` (`spec.md`/`plan.md`/
  `tasks.md`/`review-log.md`) para responder con fundamento, **defender** decisiones deliberadas que
  el reviewer cuestiona, o **reconocer** dónde el cambio original se equivocó.
- **Mismo flujo SDD.** La clasificación vive en el `spec.md`; el cross-review es el estándar sobre
  spec/plan; los cambios de código se delegan a `sdd-flow` (Vía B), reusando el mismo `.plans/<id>/`.
- **Tracking.** `pr-feedback-log.md` registra por `comment-id` lo ya procesado, para no re-revisar.
- **Un solo commit.** Todo fix se fusiona (amend/squash) al commit único del PR y se force-pushea.

## Cuándo usarla

Cuando un PR de Bitbucket tiene comentarios de revisión (de bots/revisión automatizada o de
humanos) que hay que atender con criterio. Triggers: "atendé el feedback del PR", "respondé los
comentarios del PR", "qué hago con el review del PR \<id\>".

No es code review (esa es `bitbucket-code-review`, que solo propone comentarios). Esta skill decide
y, con confirmación, escribe en el PR.

## Invocación

```
/sdd-pr-feedback                      # PR de la rama actual, todos los comentarios sin resolver
/sdd-pr-feedback 1206                 # PR 1206, todos los sin resolver
/sdd-pr-feedback 1206 814693140       # solo ese comentario (y sus replies)
```

## Requisitos

- **MCP de Bitbucket** (`mcp__bitbucket__bb_get` / `bb_post` / `bb_delete`). Sin él, la skill avisa
  y se detiene. Sin tools de escritura, degrada a proponer el texto para pegar a mano.
- **`sdd-flow`** instalada — dependencia **dura**: sus plantillas, la Vía B y las reglas de commit
  son el contrato de esta skill. Lo degradable es la capacidad de **subagentes**: sin ellos, el
  conductor implementa inline con la disciplina de `sdd-flow`.
- **`sdd-cross-review`** (opcional) para la segunda opinión cross-model sobre el triage. Sin ella,
  sigue con el gate humano.

## Garantías

- Toda escritura (responder, resolver, force-push) pasa por un gate de confirmación; el texto de las
  respuestas se muestra antes de publicar.
- Nunca aprueba ni mergea el PR.
- Los Pasos 0–3 son solo lectura.

Funciona en Claude Code y Codex (detección de tools por capacidad).
