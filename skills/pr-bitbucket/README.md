# pr-bitbucket

Crea o actualiza el PR de Bitbucket de la rama actual, siempre con el mismo formato. Es la versión
liviana del paso `open-pr` de `sdd-flow`: no usa `.specify/` y no necesita un flujo SDD.

## Qué hace

```
rama pusheada → ¿ya hay PR? → título + descripción desde la spec → revisores (memoria o usuario)
  → vista previa → confirmación → crear o actualizar
```

- **Formato fijo:** `## Ticket` (con el link a la subtarea `SPEC`), `## Problema`, `## Solución` y
  `## Criterios de aceptación` como checklist.
- **Criterios aprobados:** los `AC-n` salen de `odd/tasks/<feature>.md`, el mismo documento que
  arma `spec-jira`. Quien revisa verifica contra lo que aprobó el PO.
- **Revisores que se aprenden:** la primera vez pregunta dónde están; después los toma de la
  memoria (Engram en gentle-shell), asociados a `<workspace>/<repo>`.
- **Seguro:** sin confirmación no escribe nada en Bitbucket, no pushea, no aprueba ni mergea, y
  quita lo local (rutas de la máquina, SHAs, notas internas) de la descripción.
- **Degradación:** sin MCP de Bitbucket, entrega el texto para crear el PR a mano. Sin documento de
  la spec, arma el problema y la solución desde los commits y avisa que falta el checklist.

## Cuándo usarla

«abre el PR», «crea el PR», `/pr-bitbucket` o `/pr-bitbucket <rama destino>` para un PR apilado
sobre otra rama. Para revisar un PR está `bitbucket-code-review`; para procesar comentarios,
`sdd-pr-feedback`.

## Requisitos

- El MCP de Bitbucket (`bb_get`, `bb_post`, `bb_put`). Sin él, el PR se crea a mano.
- Opcional: una memoria persistente para recordar los revisores.

## Instalación

Copiar `skills/pr-bitbucket/` a `~/.claude/skills/` (Claude Code) o a `~/.agents/skills/`
(gentle-shell), y abrir una sesión nueva.
