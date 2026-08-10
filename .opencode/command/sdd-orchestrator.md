---
description: "Ejecuta sdd-orchestrator para un objetivo multi-repo. Diseño centralizado, repo-worker por repo y cierre bajo control del conductor."
agent: conductor
---

Ejecuta `skills/sdd-orchestrator/SKILL.md` para:

$ARGUMENTS

Reglas de ruteo adicionales:

1. Usa una sesión fresca de `conductor` y conserva los dos gates de diseño centralizados.
2. En `explore` y `counter-plan` globales, lanza en paralelo `explorer` y `claude_readonly_spawn` con un paquete común e índices separados.
3. Revisa `master-spec` y `reparto` con Claude, rol `design-review`, antes de cada gate humano.
4. Tras aprobar el reparto, despacha un `repo-worker` por repo listo, respetando el DAG. Cada worker ejecuta la Vía B completa `sdd-flow implement <plan-aprobado>` y se detiene antes de commit/push.
5. Para cada diff, revisa con la familia opuesta al autor efectivo: Claude `diff` si escribió Codex; `code-reviewer` `diff` si escribió Claude.
6. Solo el conductor integra estados globales y presenta revisión, commit y push por repo. Nunca publiques ni cierres automáticamente.
