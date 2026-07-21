// ENTRYPOINT CLI (guardless) del transporte `orca-session`: UN comando que el
// conductor corre para delegar una tarea a una sesión fresca de la otra familia
// vía Orca. La lógica vive en `orca-session.mjs` (`runOrcaSession`); este archivo
// solo parsea argv, lee el spec y emite el resultado.
//
// SIN guard de módulo-main a propósito. La versión anterior decidía "¿me estoy
// ejecutando como script?" comparando `import.meta.url` con `process.argv[1]`. Node
// deriva `import.meta.url` del path FÍSICO (symlinks resueltos) pero `argv[1]`
// conserva el path LITERAL que tecleó el llamador; como las skills se instalan por
// **symlink/junction** (`~/.claude/skills/… → repo`), el conductor invoca el runner
// por su ruta symlinked y la comparación daba `false` → `main()` NO corría → el
// proceso salía con stdout/stderr VACÍOS y exit 0, sin crear la terminal. Peor: el
// exit 0 se confunde con éxito. Ese bug apareció dos veces (symlink en macOS,
// junction en Windows). La cura definitiva es estructural: este archivo NO se
// importa desde ningún lado (el CLI y los tests comparten la lógica vía
// `orca-session.mjs`), así que puede correr `main()` incondicionalmente. Sin
// heurística de path, no hay nada que falle por symlink en ninguna plataforma.
//
// El prompt/spec SIEMPRE se pasa por archivo (`--spec-file`), nunca inline: el
// markdown con backticks rompe el quoting del shell (misma regla que la rama `cli`).
//
// Contrato de salida (una línea JSON en stdout, SIEMPRE — nunca vacío):
//   { transport: "orca-session", code, reportPath?, reason? }
//   code 0  → cosechado; `reportPath` es el informe. exit 0.
//   code !=0 → el conductor DEGRADA a `cli` (lee `reason`). exit == code.
//              4 = no se pudo crear/localizar la sesión propia (degradación limpia);
//              2/3 = fallo de cosecha/contención; 2+usageError = error de invocación.
// El conductor NO debe inferir éxito solo del exit code: debe leer `code`/`reportPath`
// del JSON (y verificar que el informe exista) antes de darlo por cosechado.
import fs from 'node:fs';
import { runOrcaSession } from './orca-session.mjs';

const REQUIRED_FLAGS = ['family', 'role', 'mode', 'worktree', 'spec-file', 'report', 'root'];

/**
 * Parser mínimo de `--clave valor` (sin dependencias, sin `parseArgs` para no
 * atarse a una versión de Node). Un flag sin valor siguiente queda en `"true"`.
 * @param {string[]} argv
 * @returns {Record<string,string>}
 */
function parseCliArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith('--')) {
      out[key] = next;
      i++;
    } else {
      out[key] = 'true';
    }
  }
  return out;
}

function emit(result) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
  process.exitCode = result.code === 0 ? 0 : result.code;
}

async function main() {
  const args = parseCliArgs(process.argv.slice(2));

  const missing = REQUIRED_FLAGS.filter((flag) => !args[flag] || args[flag] === 'true');
  if (missing.length > 0) {
    emit({
      transport: 'orca-session',
      code: 2,
      usageError: true,
      reason:
        `faltan argumentos: ${missing.join(', ')}. Uso: node run-orca-session.mjs ` +
        '--family <codex|claude> --role <read-only|write> --mode <attended|unattended> ' +
        '--worktree <abspath> --spec-file <path> --report <relpath-a-root> --root <dir> ' +
        '[--deadline-ms <n>] [--boot-timeout-ms <n>]',
    });
    return;
  }

  let spec;
  try {
    spec = fs.readFileSync(args['spec-file'], 'utf8');
  } catch (err) {
    emit({
      transport: 'orca-session',
      code: 2,
      usageError: true,
      reason: `no se pudo leer --spec-file "${args['spec-file']}": ${err && err.message}`,
    });
    return;
  }

  const result = await runOrcaSession({
    family: args.family,
    role: args.role,
    mode: args.mode,
    worktree: args.worktree,
    spec,
    reportPath: args.report,
    root: args.root,
    deadlineMs: args['deadline-ms'] ? Number(args['deadline-ms']) : undefined,
    bootTimeoutMs: args['boot-timeout-ms'] ? Number(args['boot-timeout-ms']) : undefined,
  });
  emit(result);
}

// Se ejecuta SIEMPRE al invocar el archivo (este módulo nunca se importa). No hay
// guard de módulo-main: ver el encabezado (bug de symlink/junction, macOS + Windows).
try {
  await main();
} catch (err) {
  emit({ transport: 'orca-session', code: 2, reason: `error inesperado: ${err && err.message}` });
}
