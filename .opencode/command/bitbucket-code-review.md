---
description: "Revisa un PR de Bitbucket con panel Codex+Claude, refutación cruzada y publicación exclusiva del conductor."
agent: conductor
---

Ejecuta `skills/bitbucket-code-review/SKILL.md` para:

$ARGUMENTS

Reglas de ruteo adicionales:

1. El conductor obtiene metadatos, diff, comentarios y contexto mediante el MCP de Bitbucket y materializa un snapshot inmutable antes de delegar.
2. Lanza el panel sin bloquear entre despachos:
   - revisión propia del conductor;
   - `claude_readonly_spawn` con rol `pr` (Opus xhigh);
   - una task a `code-reviewer` con `MODE: pr`.
3. Refuta cada hallazgo con la familia opuesta a quien lo originó:
   - hallazgo Codex → Claude con rol `refute`;
   - hallazgo Claude → `code-reviewer` con `MODE: refute`.
4. El conductor deduplica, verifica contra el snapshot y descarta review theater.
5. Solo el conductor puede publicar comentarios y únicamente después del gate exacto exigido por la skill. Los reviewers nunca escriben en Bitbucket.
