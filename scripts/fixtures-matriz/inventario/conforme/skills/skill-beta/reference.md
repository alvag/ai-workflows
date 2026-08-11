# Referencia de skill-beta (sintética)

Detalle de invocación de los tres puntos que el inventario de `SKILL.md` declara.

## Revisor por ronda

La ronda 1 lo lanza con `codex exec -s read-only -C <working_dir> --skip-git-repo-check --json` y las
siguientes reanudan el mismo hilo.

## Refutador por hallazgo

Cada hallazgo en disputa se delega con `claude -p` a la familia opuesta, uno por hallazgo.

## Sintetizador final

La consolidación se despacha con `codex exec -s read-only` sobre los veredictos ya cosechados.
