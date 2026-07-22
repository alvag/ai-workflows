// ENTRYPOINT CLI (guardless) del manifest caller-owned. Cada invocación ejecuta
// una transición discreta sobre `<runId>.partial.json`; las estructuras viajan
// siempre por archivos JSON para evitar ambigüedad de quoting.
//
// Contrato:
//   node run-manifest.mjs start --dir D --workflow W --mode M --role R
//     --family F --transport-desired T [--ext-file ext.json]
//   node run-manifest.mjs attempt-start --dir D --run-id ID --transport T
//     --access read-only|write
//   node run-manifest.mjs attempt-finish --dir D --run-id ID --outcome O
//     [--code N|null] [--recovered true|false]
//   node run-manifest.mjs resolve-writer --dir D --run-id ID --resolved-by QUIEN
//   node run-manifest.mjs finish --dir D --run-id ID --status S
//     [--usage-file u.json] [--artifacts-file a.json]
import fs from 'node:fs';
import {
  attemptFinish,
  attemptStart,
  createRun,
  finishRun,
  resolveWriter,
} from './manifest-core.mjs';

const COMMANDS = {
  start: {
    required: ['dir', 'workflow', 'mode', 'role', 'family', 'transport-desired'],
    optional: ['ext-file'],
  },
  'attempt-start': {
    required: ['dir', 'run-id', 'transport', 'access'],
    optional: [],
  },
  'attempt-finish': {
    required: ['dir', 'run-id', 'outcome'],
    optional: ['code', 'recovered'],
  },
  'resolve-writer': {
    required: ['dir', 'run-id', 'resolved-by'],
    optional: [],
  },
  finish: {
    required: ['dir', 'run-id', 'status'],
    optional: ['usage-file', 'artifacts-file'],
  },
};

/** Parser mínimo de `--clave valor`, consistente con los otros runners. */
function parseCliArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      throw new Error(`argumento posicional inesperado: ${token}.`);
    }
    const key = token.slice(2);
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith('--')) {
      out[key] = next;
      i++;
    } else {
      out[key] = null;
    }
  }
  return out;
}

function validateCommandArgs(command, args) {
  const contract = COMMANDS[command];
  if (!contract) {
    throw new Error(`operación desconocida: ${String(command)}.`);
  }
  const missing = contract.required.filter((flag) => !args[flag]);
  if (missing.length > 0) {
    throw new Error(`faltan argumentos para ${command}: ${missing.join(', ')}.`);
  }
  const allowed = new Set([...contract.required, ...contract.optional]);
  const unknown = Object.keys(args).filter((flag) => !allowed.has(flag));
  if (unknown.length > 0) {
    throw new Error(`flags desconocidos para ${command}: ${unknown.join(', ')}.`);
  }
  const missingOptionalValues = contract.optional.filter((flag) => args[flag] === null);
  if (missingOptionalValues.length > 0) {
    throw new Error(`faltan valores para: ${missingOptionalValues.join(', ')}.`);
  }
}

function readJsonFile(filePath, flag) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new Error(`no se pudo leer --${flag} "${filePath}": ${err.message}`);
  }
  try {
    return JSON.parse(content);
  } catch (err) {
    throw new Error(`--${flag} no contiene JSON válido: ${err.message}`);
  }
}

function parseCode(value) {
  if (value === undefined || value === 'null') return null;
  if (!/^(0|[1-9][0-9]*)$/.test(value)) {
    throw new Error('--code debe ser un entero mayor o igual que 0, o null.');
  }
  return Number(value);
}

function parseBoolean(value, flag) {
  if (value === 'true') return true;
  if (value === 'false') return false;
  throw new Error(`--${flag} debe ser true o false.`);
}

function emit(result) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

function main() {
  const [command, ...argv] = process.argv.slice(2);
  if (!command) throw new Error('falta la operación start|attempt-start|attempt-finish|resolve-writer|finish.');
  const args = parseCliArgs(argv);
  validateCommandArgs(command, args);

  if (command === 'start') {
    const ext = args['ext-file'] ? readJsonFile(args['ext-file'], 'ext-file') : undefined;
    emit(createRun({
      dir: args.dir,
      workflow: args.workflow,
      mode: args.mode,
      role: args.role,
      family: args.family,
      transportDesired: args['transport-desired'],
      ext,
    }));
    return;
  }

  if (command === 'attempt-start') {
    attemptStart({
      dir: args.dir,
      runId: args['run-id'],
      transport: args.transport,
      access: args.access,
    });
    emit({ ok: true, runId: args['run-id'] });
    return;
  }

  if (command === 'attempt-finish') {
    const options = {
      dir: args.dir,
      runId: args['run-id'],
      outcome: args.outcome,
      code: parseCode(args.code),
    };
    if (Object.hasOwn(args, 'recovered')) {
      options.recovered = parseBoolean(args.recovered, 'recovered');
    }
    attemptFinish(options);
    emit({ ok: true, runId: args['run-id'] });
    return;
  }

  if (command === 'resolve-writer') {
    resolveWriter({
      dir: args.dir,
      runId: args['run-id'],
      resolvedBy: args['resolved-by'],
    });
    emit({ ok: true, runId: args['run-id'] });
    return;
  }

  const usage = args['usage-file'] ? readJsonFile(args['usage-file'], 'usage-file') : undefined;
  const artifacts = args['artifacts-file']
    ? readJsonFile(args['artifacts-file'], 'artifacts-file')
    : undefined;
  emit(finishRun({
    dir: args.dir,
    runId: args['run-id'],
    status: args.status,
    usage,
    artifacts,
  }));
}

// Guardless a propósito: este módulo es solo entrypoint y nunca se importa.
try {
  main();
} catch (err) {
  process.stderr.write(`error: ${err && err.message}\n`);
  process.exitCode = 2;
}
