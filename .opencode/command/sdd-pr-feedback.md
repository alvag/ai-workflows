---
description: "Procesa feedback de un PR de Bitbucket con clasificación, gate, implementación por repo-worker y revisión cross-model del diff."
agent: conductor
---

Ejecuta `skills/sdd-pr-feedback/SKILL.md` para:

$ARGUMENTS

Reglas de ruteo adicionales:

1. El conductor lee comentarios y diff mediante el MCP de Bitbucket, los materializa y clasifica con evidencia.
2. Si la respuesta requiere una decisión de diseño, usa Claude `design-review` antes de presentar el gate humano.
3. Solo después de aprobar el plan de resolución, despacha `repo-worker` con la Vía B de `sdd-flow` y el work order aprobado.
4. Revisa el diff con la familia opuesta al autor efectivo: Claude `diff` si escribió Codex; `code-reviewer` `diff` si escribió Claude.
5. El conductor conserva los gates de commit, push y respuesta/publicación en Bitbucket. Ningún worker ejecuta esas acciones.
