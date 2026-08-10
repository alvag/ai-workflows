# `.opencode/` — orquestación SDD Codex + Claude

Configuración de OpenCode para ejecutar las skills de este repositorio con un conductor Codex fijo y Claude Code como segunda familia mediante su CLI oficial.

## Topología

Todos los nombres son planos:

```text
.opencode/
├── agents/
│   ├── conductor.md          # primary: GPT-5.6 Sol xhigh
│   ├── explorer.md           # Codex Terra high: explore/counter-plan
│   ├── investigator.md       # Codex Terra xhigh: causa raíz
│   ├── builder.md            # Codex Terra high: task aprobada
│   ├── code-reviewer.md      # Codex Terra high: diff/pr/refute
│   └── repo-worker.md        # Codex Terra high: sdd-flow Vía B por repo
├── command/
│   ├── sdd.md
│   ├── sdd-orchestrator.md
│   ├── sdd-pr-feedback.md
│   └── bitbucket-code-review.md
├── roles/                    # contratos Claude que no tienen agente nativo
├── tools/                    # custom tools cargadas por OpenCode
├── lib/claude-runner.ts      # política, validación, perfiles y recibos
├── lib/claude-worker.mjs     # proceso desacoplado con deadline duro
└── tests/
```

No existe roster ni detección dinámica de familias. Los cuatro comandos usan el mismo agente `conductor`; se recomienda iniciar una sesión fresca por corrida para no mezclar contexto entre flujos.

## Política de modelos

| Trabajo | Perfil |
|---|---|
| Conductor | `openai/gpt-5.6-sol`, `xhigh` |
| Explore / counter-plan nativo | `openai/gpt-5.6-terra`, `high` |
| Investigación nativa | `openai/gpt-5.6-terra`, `xhigh` |
| Builder / reviewer / repo-worker nativo | `openai/gpt-5.6-terra`, `high` |
| Claude explore / counter-plan normal | `claude-sonnet-5`, `medium` |
| Claude implementación normal | `claude-sonnet-5`, `high` |
| Claude investigación, debate, diseño, diff, PR, refutación o high-risk | `claude-opus-5`, `xhigh` |

Claude se invoca directamente desde el conductor o `repo-worker`; no existe un subagente OpenCode que actúe como wrapper. Así, OpenCode solo consume los tokens necesarios para orquestar la tool y procesar su recibo, no una segunda conversación de modelo dedicada a ejecutar el CLI.

## Custom tools Claude

- `claude_readonly_spawn`: lanza un worker read-only y devuelve inmediatamente un handle.
- `claude_implement_spawn`: lanza un writer desde un work order congelado.
- `claude_resume`: continúa la misma sesión Claude con un delta en archivo.
- `claude_collect`: consulta o espera el resultado y produce un recibo compacto.

Los procesos usan:

```text
claude -p --safe-mode --permission-mode default --output-format json
```

El prompt viaja por stdin y stdin se cierra explícitamente. Las ejecuciones frescas usan `--session-id`; las siguientes, `--resume`. No se usan `--bare`, `acceptEdits`, `plan`, bypass ni `--no-session-persistence` por defecto.

Antes de lanzar se eliminan del entorno hijo `ANTHROPIC_*`, `MERIDIAN_*` y overrides de proveedores alternos. Se conserva `CLAUDE_CODE_OAUTH_TOKEN` si el entorno oficial lo usa. El collector solo acepta un resultado como `READY` cuando la telemetría JSON declara `provider: firstParty`; sin login oficial, con proveedor distinto o sin evidencia, devuelve `UNAVAILABLE` y no hace fallback.

### Permisos

- Read-only: `Read,Grep,Glob`.
- Writer: `Read,Grep,Glob,Edit(./**),Write(./**)` y solo `Bash(<proof_bin>:*)` para los binarios del `proof_cmd` aprobado.
- El writer rechaza callers distintos de `conductor` y `repo-worker`.
- Un work order ad hoc fuera de `.plans/` pide permiso con `context.ask`.
- Ningún worker de Claude puede hacer commit, push, merge o rebase por contrato.

Cada intento deja recibos locales en:

```text
.cross-model/opencode-cli/<run_id>/<attempt_uuid>/
```

Incluyen manifest, hash del prompt, PID, sesión, stdout, stderr, status y timestamps. Se reutiliza el vocabulario existente `cli-exec` / `cli-resume` cuando la skill proyecta estos recibos a sus envelopes; no se introduce un transporte nuevo.

## Uso

Dentro del repo:

```text
/sdd <objetivo>
/sdd-orchestrator <objetivo multi-repo>
/sdd-pr-feedback <PR>
/bitbucket-code-review <PR>
```

Para exponerlo globalmente, enlaza los archivos planos de `agents/`, `command/` y `tools/` a sus carpetas homónimas bajo `~/.config/opencode/`. Mantén `lib/` y `roles/` junto al checkout original: las tools resuelven esos archivos desde su propia ubicación real. Reinicia OpenCode después de cambiar agentes, comandos o tools.

## Verificación

Las dependencias y su lockfile sí se versionan; solo `node_modules/` se ignora.

```bash
cd .opencode
npm test
```

La suite verifica perfiles, saneamiento de entorno, proveedor first-party, restricciones del proof command, layout plano y un spawn/collect no bloqueante con un CLI falso.
