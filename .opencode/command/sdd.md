---
description: "Ejecuta sdd-flow en un repo con conductor Codex, fan-out Codex+Claude y revisión opuesta al autor. Uso: /sdd [objetivo | subcomando]"
agent: conductor
---

Ejecuta `skills/sdd-flow/SKILL.md` para:

$ARGUMENTS

Reglas de ruteo adicionales:

1. Usa una sesión fresca del agente `conductor` para esta corrida.
2. Cuando corresponda `co-explore` en `explore` o `counter-plan`, crea el mismo paquete de contexto para ambas familias. Lanza, antes de esperar:
   - una task al agente `explorer` con el modo explícito;
   - `claude_readonly_spawn` con el mismo modo y paquete.
   Recolecta después con `claude_collect`; el conductor lee los dos índices y arbitra.
3. Para `investigate`, usa `investigator` y Claude con rol `investigate`; Claude debe resolver a Opus xhigh.
4. Para cross-review de spec/plan/tasks usa Claude con rol `design-review`; el conductor decide qué crítica incorporar antes del gate humano.
5. En implementación:
   - `inline`: implementa el conductor;
   - `subagent`: una task secuencial a `builder` por task aprobada;
   - `cross`: `claude_implement_spawn` con el work order congelado y la prueba autorizada.
6. La revisión final del diff siempre es de la familia opuesta al autor efectivo:
   - autor Codex (`conductor` o `builder`) → Claude, rol `diff`;
   - autor Claude → agente `code-reviewer`, modo `diff`.
7. Conserva los gates de revisión manual, commit y push definidos por `sdd-flow`. Ningún worker ejecuta esos cierres.
