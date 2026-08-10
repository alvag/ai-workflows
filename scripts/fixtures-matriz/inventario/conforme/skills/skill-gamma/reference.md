# Referencia de skill-gamma (sintética)

Detalle de invocación de los dos puntos escritores del inventario de `SKILL.md`.

## Implementador inicial

Se lanza con `codex exec -s workspace-write -C <working_dir> --skip-git-repo-check --json` y el
prompt-contrato por archivo.

## Ronda del fix loop

Cada ronda reanuda la sesión del implementador con `codex exec resume "$SESSION_ID"` y el delta de
findings.
