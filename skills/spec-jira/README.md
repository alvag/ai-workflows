# spec-jira

Escribe la spec de un cambio, la publica en Jira para que la apruebe el PO o el TL y concilia los
cambios que vuelven. Es la versión liviana del paso `publish-spec` de `sdd-flow`: no escribe plan
ni tasks de SDD. La implementación sigue el flujo del agente; en gentle-shell, ODD.

## Qué hace

```
contexto (ticket + código) → dudas Q<n> → spec local (gate) → subtarea "SPEC: …" en Jira
  → ¿modo?  A: espera la aprobación  ·  B: implementa en paralelo
  → concilia: editorial · AC cambiado · alcance · aprobado
```

- **Un solo documento:** la spec vive en `odd/tasks/<feature>.md`. Cada criterio de aceptación
  es a la vez un `AC-n` de Jira y un `S<n>` de ODD, con el mismo número. Si el PO cambia el AC-3,
  se sabe qué tarea, qué test y qué código tocar.
- **Resumen para PO en el documento:** la spec lleva un resumen en lenguaje de negocio, con un
  punto por cada AC, que se aprueba junto con la parte técnica antes de publicar. A Jira se copia
  tal cual: el PO lee exactamente lo que aprobaste.
- **Origen de cada criterio:** `pedido`, `clarify` o `repositorio`. Así, «esto no se pidió»
  tiene contra qué compararse.
- **Dos modos, elegidos en cada spec:** A espera la aprobación antes de escribir código. B
  implementa en paralelo y, si cambia un AC, reabre solo lo afectado: agrega el cambio al Log,
  reescribe el `S<n>`, ajusta el test y después el código. Un cambio de alcance o de enfoque frena
  y pregunta.
- **Escrituras confirmadas:** nada se publica en Jira sin mostrar antes el recurso y el contenido.
  Lo local (rutas, ramas, SHAs, comandos, la mecánica del agente) se quita antes de publicar.
- **Degradación:** sin MCP de Atlassian con escritura, entrega el texto listo para pegar.

## Cuándo usarla

- «crea la spec», «arma la spec de PROJ-123», «sube la spec a Jira», `/spec-jira PROJ-123`.
- «ya aprobaron la spec», «revisa las observaciones del PO», `/spec-jira retoma <feature>`.

No usarla para un flujo SDD completo con plan, tasks y verify; para eso está `sdd-flow`. Tampoco
para code review.

## Requisitos

- Opcional: el MCP de Atlassian con permiso de escritura. Sin él, se trabaja copiando y pegando.

## Instalación

Copiar `skills/spec-jira/` a la carpeta de skills del runtime: `~/.claude/skills/` para Claude
Code o `~/.agents/skills/` para gentle-shell (Pi).
