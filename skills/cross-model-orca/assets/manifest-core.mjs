// Núcleo del manifest caller-owned para corridas cross-model. La única fuente
// mutable es `<runId>.partial.json`; el terminal se publica por rename atómico y
// queda inmutable. Este módulo no integra ninguna skill ni toca el kernel.
import fs from 'node:fs';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';

const SCHEMA_VERSION = 1;
const SLUG_PATTERN = /^[a-z0-9-]{1,64}$/;
const TRANSPORTS = new Set(['orca-session', 'cli']);
const DESIRED_TRANSPORTS = new Set(['auto', ...TRANSPORTS]);
const ACCESS_LEVELS = new Set(['read-only', 'write']);
const ATTEMPT_OUTCOMES = new Set(['completed', 'failed', 'aborted', 'unterminated']);
const TERMINAL_STATUSES = new Set(['ready', 'failed', 'aborted']);
const TRIAGE_CLASSES = new Set([
  'IMPLEMENTATION_DEFECT',
  'VERIFICATION_DEFECT',
  'ENVIRONMENT_FAILURE',
  'DESIGN_GAP',
]);
const DEFAULT_USAGE = Object.freeze({
  inputTokens: null,
  outputTokens: null,
  costUsd: null,
  source: 'unavailable',
});

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function assertPlainObject(value, label) {
  if (!isPlainObject(value)) throw new Error(`${label} debe ser un objeto.`);
}

function assertExactKeys(value, expectedKeys, label) {
  assertPlainObject(value, label);
  const expected = new Set(expectedKeys);
  const actual = Object.keys(value);
  const unknown = actual.filter((key) => !expected.has(key));
  const missing = expectedKeys.filter((key) => !Object.hasOwn(value, key));
  if (unknown.length > 0 || missing.length > 0) {
    const details = [];
    if (unknown.length > 0) details.push(`campos desconocidos: ${unknown.join(', ')}`);
    if (missing.length > 0) details.push(`campos faltantes: ${missing.join(', ')}`);
    throw new Error(`${label} no cumple el schema v1 (${details.join('; ')}).`);
  }
}

function assertSlug(value, label) {
  if (typeof value !== 'string' || !SLUG_PATTERN.test(value)) {
    throw new Error(`${label} debe ser un slug de 1 a 64 caracteres [a-z0-9-].`);
  }
}

function assertEnum(value, allowed, label) {
  if (typeof value !== 'string' || !allowed.has(value)) {
    throw new Error(`${label} inválido: ${String(value)}.`);
  }
}

function assertDirectory(dir) {
  if (typeof dir !== 'string' || dir.length === 0) {
    throw new Error('dir debe ser una ruta no vacía.');
  }
  const resolved = path.resolve(dir);
  let stat;
  try {
    stat = fs.statSync(resolved);
  } catch (err) {
    throw new Error(`No se pudo acceder a dir "${dir}": ${err.message}`);
  }
  if (!stat.isDirectory()) throw new Error(`dir no es un directorio: ${dir}.`);
  return resolved;
}

function toIsoTimestamp(now = Date.now) {
  if (typeof now !== 'function') throw new Error('now debe ser una función de reloj.');
  const raw = now();
  const date = raw instanceof Date ? raw : new Date(raw);
  if (Number.isNaN(date.getTime())) throw new Error('now devolvió un timestamp inválido.');
  return date.toISOString();
}

function pathsFor(dir, runId) {
  assertSlug(runId, 'runId');
  const resolvedDir = assertDirectory(dir);
  return {
    resolvedDir,
    partialPath: path.join(resolvedDir, `${runId}.partial.json`),
    manifestPath: path.join(resolvedDir, `${runId}.json`),
  };
}

function readJson(filePath, label) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new Error(`No se pudo leer ${label}: ${err.message}`);
  }
  try {
    return JSON.parse(content);
  } catch (err) {
    throw new Error(`${label} no contiene JSON válido: ${err.message}`);
  }
}

/**
 * Persiste JSON por tmp+rename en el mismo directorio. El `finally` elimina solo
 * el temporal propio si la publicación falla antes del rename.
 * @param {string} targetPath
 * @param {Record<string, *>} data
 */
function writeJsonAtomic(targetPath, data) {
  const tmpPath = `${targetPath}.${process.pid}.${randomUUID()}.tmp`;
  try {
    fs.writeFileSync(tmpPath, `${JSON.stringify(data, null, 2)}\n`);
    fs.renameSync(tmpPath, targetPath);
  } finally {
    try {
      fs.unlinkSync(tmpPath);
    } catch (err) {
      if (err.code !== 'ENOENT') throw err;
    }
  }
}

function defaultExt(workflow) {
  if (workflow !== 'cross-implement') {
    throw new Error(`workflow sin schema registrado en v1: ${workflow}.`);
  }
  return {
    'cross-implement': {
      fixRounds: 0,
      verificationReruns: 0,
      triage: [],
    },
  };
}

function validateCrossImplementExt(value) {
  assertExactKeys(value, ['fixRounds', 'verificationReruns', 'triage'], 'ext.cross-implement');
  if (!Number.isInteger(value.fixRounds) || value.fixRounds < 0) {
    throw new Error('ext.cross-implement.fixRounds debe ser un entero mayor o igual que 0.');
  }
  if (!Number.isInteger(value.verificationReruns) || value.verificationReruns < 0) {
    throw new Error('ext.cross-implement.verificationReruns debe ser un entero mayor o igual que 0.');
  }
  if (!Array.isArray(value.triage)) {
    throw new Error('ext.cross-implement.triage debe ser un array.');
  }
  const triage = value.triage.map((entry, index) => {
    const label = `ext.cross-implement.triage[${index}]`;
    assertExactKeys(entry, ['checkId', 'class', 'consumedRound'], label);
    assertSlug(entry.checkId, `${label}.checkId`);
    assertEnum(entry.class, TRIAGE_CLASSES, `${label}.class`);
    if (typeof entry.consumedRound !== 'boolean') {
      throw new Error(`${label}.consumedRound debe ser booleano.`);
    }
    return {
      checkId: entry.checkId,
      class: entry.class,
      consumedRound: entry.consumedRound,
    };
  });
  return {
    fixRounds: value.fixRounds,
    verificationReruns: value.verificationReruns,
    triage,
  };
}

function validateExt(workflow, ext) {
  if (workflow !== 'cross-implement') {
    throw new Error(`workflow sin schema registrado en v1: ${workflow}.`);
  }
  const candidate = ext === undefined ? defaultExt(workflow) : ext;
  assertExactKeys(candidate, [workflow], 'ext');
  return { [workflow]: validateCrossImplementExt(candidate[workflow]) };
}

function validateUsage(usage = DEFAULT_USAGE) {
  assertExactKeys(usage, ['inputTokens', 'outputTokens', 'costUsd', 'source'], 'usage');
  assertEnum(usage.source, new Set(['unavailable', 'provider']), 'usage.source');

  if (usage.source === 'unavailable') {
    if (usage.inputTokens !== null || usage.outputTokens !== null || usage.costUsd !== null) {
      throw new Error('usage.source unavailable exige que tokens y costo sean null.');
    }
  } else {
    if (!Number.isInteger(usage.inputTokens) || usage.inputTokens < 0) {
      throw new Error('usage.inputTokens provider debe ser un entero mayor o igual que 0.');
    }
    if (!Number.isInteger(usage.outputTokens) || usage.outputTokens < 0) {
      throw new Error('usage.outputTokens provider debe ser un entero mayor o igual que 0.');
    }
    if (typeof usage.costUsd !== 'number' || !Number.isFinite(usage.costUsd) || usage.costUsd < 0) {
      throw new Error('usage.costUsd provider debe ser un número mayor o igual que 0.');
    }
  }

  return {
    inputTokens: usage.inputTokens,
    outputTokens: usage.outputTokens,
    costUsd: usage.costUsd,
    source: usage.source,
  };
}

function hashFileSha256(filePath) {
  const hash = createHash('sha256');
  const buffer = Buffer.allocUnsafe(64 * 1024);
  const fd = fs.openSync(filePath, 'r');
  try {
    while (true) {
      const bytesRead = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (bytesRead === 0) break;
      hash.update(buffer.subarray(0, bytesRead));
    }
  } finally {
    fs.closeSync(fd);
  }
  return hash.digest('hex');
}

function resolveExistingArtifact(relativePath, resolvedDir) {
  if (typeof relativePath !== 'string' || relativePath.length === 0) {
    throw new Error('artifacts[].path debe ser una ruta relativa no vacía.');
  }
  if (path.isAbsolute(relativePath)) {
    throw new Error('artifacts[].path no puede ser una ruta absoluta.');
  }

  const rootReal = fs.realpathSync(resolvedDir);
  const target = path.resolve(rootReal, relativePath);
  let targetReal;
  try {
    targetReal = fs.realpathSync(target);
  } catch (err) {
    throw new Error(`El artifact debe existir para calcular sha256: ${err.message}`);
  }
  const relativeToRoot = path.relative(rootReal, targetReal);
  if (relativeToRoot === '..' || relativeToRoot.startsWith(`..${path.sep}`) || path.isAbsolute(relativeToRoot)) {
    throw new Error('artifacts[].path escapa de dir por ruta o symlink.');
  }
  if (!fs.statSync(targetReal).isFile()) {
    throw new Error('artifacts[].path debe referenciar un archivo existente.');
  }
  return targetReal;
}

function validateArtifacts(artifacts = [], resolvedDir) {
  if (!Array.isArray(artifacts)) throw new Error('artifacts debe ser un array.');
  return artifacts.map((artifact, index) => {
    const label = `artifacts[${index}]`;
    assertExactKeys(artifact, ['kind', 'path'], label);
    assertSlug(artifact.kind, `${label}.kind`);
    const filePath = resolveExistingArtifact(artifact.path, resolvedDir);
    return {
      kind: artifact.kind,
      path: artifact.path,
      sha256: hashFileSha256(filePath),
    };
  });
}

function assertMutableRun(dir, runId) {
  const paths = pathsFor(dir, runId);
  if (fs.existsSync(paths.manifestPath)) {
    throw new Error(`La corrida ${runId} ya es terminal e inmutable.`);
  }
  if (!fs.existsSync(paths.partialPath)) {
    throw new Error(`No existe el partial de la corrida ${runId}.`);
  }
  return { ...paths, partial: readJson(paths.partialPath, 'el partial') };
}

function openAttempt(partial) {
  return partial.attempts.find((attempt) => !Object.hasOwn(attempt, 'finishedAt')) ?? null;
}

function hasUnresolvedWriter(partial) {
  return partial.attempts.some((attempt) => (
    attempt.access === 'write'
    && attempt.outcome !== 'completed'
    && attempt.recovered === false
    && !Object.hasOwn(attempt, 'writerResolution')
  ));
}

function assertNoUnresolvedWriter(partial) {
  if (hasUnresolvedWriter(partial)) {
    throw new Error('Hay un escritor cuyo cierre no fue demostrado; se exige resolve-writer.');
  }
}

function deriveFallbackUsed(attempts) {
  let sawFailedOrca = false;
  for (const attempt of attempts) {
    if (attempt.transport === 'orca-session' && attempt.outcome !== 'completed') {
      sawFailedOrca = true;
    }
    if (attempt.transport === 'cli' && sawFailedOrca) return true;
  }
  return false;
}

function deriveClosure(attempts, status) {
  assertEnum(status, TERMINAL_STATUSES, 'status');
  const successfulAttempt = attempts.find((attempt) => attempt.outcome === 'completed') ?? null;

  if (attempts.length === 0 && status !== 'aborted') {
    throw new Error('Con cero attempts solo se permite status aborted.');
  }
  if (status === 'ready' && successfulAttempt === null) {
    throw new Error('status ready exige un attempt completed.');
  }
  if (status === 'failed' && successfulAttempt !== null) {
    throw new Error('status failed no es coherente con un attempt completed.');
  }

  const codeSource = successfulAttempt ?? attempts.at(-1) ?? null;
  return {
    effective: successfulAttempt?.transport ?? null,
    fallbackUsed: deriveFallbackUsed(attempts),
    outcome: {
      status,
      code: codeSource?.code ?? null,
    },
  };
}

/**
 * Crea el estado inicial de una corrida antes del primer intento.
 * @returns {{runId: string, partialPath: string}}
 */
export function createRun({
  dir,
  workflow,
  mode,
  role,
  family,
  transportDesired,
  ext,
  now = Date.now,
}) {
  if (workflow !== 'cross-implement') {
    throw new Error(`workflow sin schema registrado en v1: ${workflow}.`);
  }
  assertSlug(workflow, 'workflow');
  assertSlug(mode, 'mode');
  assertSlug(role, 'role');
  assertSlug(family, 'family');
  assertEnum(transportDesired, DESIRED_TRANSPORTS, 'transportDesired');
  const validatedExt = validateExt(workflow, ext);
  const resolvedDir = assertDirectory(dir);
  const runId = randomUUID();
  const partialPath = path.join(resolvedDir, `${runId}.partial.json`);
  const manifestPath = path.join(resolvedDir, `${runId}.json`);
  if (fs.existsSync(partialPath) || fs.existsSync(manifestPath)) {
    throw new Error(`La corrida aleatoria ${runId} ya existe.`);
  }

  const partial = {
    schemaVersion: SCHEMA_VERSION,
    runId,
    workflow,
    mode,
    role,
    family,
    model: null,
    transport: { desired: transportDesired },
    attempts: [],
    timing: { startedAt: toIsoTimestamp(now) },
    usage: { ...DEFAULT_USAGE },
    ext: validatedExt,
  };
  writeJsonAtomic(partialPath, partial);
  return { runId, partialPath };
}

/** Inicia un attempt nuevo si la FSM y el guard de escritor lo permiten. */
export function attemptStart({ dir, runId, transport, access, now = Date.now }) {
  assertEnum(transport, TRANSPORTS, 'transport');
  assertEnum(access, ACCESS_LEVELS, 'access');
  const { partialPath, partial } = assertMutableRun(dir, runId);
  if (openAttempt(partial) !== null) throw new Error('Ya existe un attempt abierto.');
  assertNoUnresolvedWriter(partial);
  if (partial.attempts.some((attempt) => attempt.outcome === 'completed')) {
    throw new Error('No se permite iniciar otro attempt después de completed.');
  }
  if (transport === 'orca-session' && partial.attempts.some((attempt) => attempt.transport === 'cli')) {
    throw new Error('La secuencia cli → orca-session no existe en la FSM v1.');
  }

  partial.attempts.push({
    transport,
    access,
    startedAt: toIsoTimestamp(now),
  });
  writeJsonAtomic(partialPath, partial);
}

/** Cierra de forma explícita el único attempt abierto. */
export function attemptFinish(options) {
  const {
    dir,
    runId,
    outcome,
    code = null,
    now = Date.now,
  } = options;
  assertEnum(outcome, ATTEMPT_OUTCOMES, 'outcome');
  if (code !== null && (!Number.isInteger(code) || code < 0)) {
    throw new Error('code debe ser un entero mayor o igual que 0, o null.');
  }
  const recoveredWasProvided = Object.hasOwn(options, 'recovered');
  if (recoveredWasProvided && typeof options.recovered !== 'boolean') {
    throw new Error('recovered debe ser booleano cuando está presente.');
  }

  const { partialPath, partial } = assertMutableRun(dir, runId);
  const attempt = openAttempt(partial);
  if (attempt === null) throw new Error('No existe un attempt abierto para cerrar.');
  if (attempt.access === 'write' && outcome === 'unterminated' && !recoveredWasProvided) {
    throw new Error('Un attempt write unterminated exige recovered explícito.');
  }

  attempt.finishedAt = toIsoTimestamp(now);
  attempt.outcome = outcome;
  attempt.code = code;
  if (recoveredWasProvided) attempt.recovered = options.recovered;
  writeJsonAtomic(partialPath, partial);
}

/** Registra la intervención que demuestra el cierre sin alterar recovered. */
export function resolveWriter({ dir, runId, resolvedBy, now = Date.now }) {
  assertSlug(resolvedBy, 'resolvedBy');
  const { partialPath, partial } = assertMutableRun(dir, runId);
  if (openAttempt(partial) !== null) {
    throw new Error('No se puede resolver el escritor mientras hay un attempt abierto.');
  }
  const attempt = [...partial.attempts].reverse().find((candidate) => (
    candidate.access === 'write'
    && candidate.outcome !== 'completed'
    && candidate.recovered === false
    && !Object.hasOwn(candidate, 'writerResolution')
  ));
  if (!attempt) throw new Error('No existe un escritor no recuperado pendiente de resolución.');

  attempt.writerResolution = {
    resolvedBy,
    resolvedAt: toIsoTimestamp(now),
  };
  writeJsonAtomic(partialPath, partial);
}

/**
 * Lee una corrida con precedencia del terminal sobre el partial.
 * @returns {{state: 'incomplete'|'terminal', data: Record<string, *>}}
 */
export function readRun({ dir, runId }) {
  const { partialPath, manifestPath } = pathsFor(dir, runId);
  if (fs.existsSync(manifestPath)) {
    return { state: 'terminal', data: readJson(manifestPath, 'el manifest terminal') };
  }
  if (fs.existsSync(partialPath)) {
    return { state: 'incomplete', data: readJson(partialPath, 'el partial') };
  }
  throw new Error(`No existe la corrida ${runId}.`);
}

/**
 * Publica el terminal por tmp+rename y elimina el partial solo después del commit.
 * Si terminal y partial coexisten, actúa como limpiador idempotente.
 * @returns {{manifestPath: string}}
 */
export function finishRun({
  dir,
  runId,
  status,
  usage = DEFAULT_USAGE,
  artifacts = [],
  ext,
  now = Date.now,
}) {
  const { resolvedDir, partialPath, manifestPath } = pathsFor(dir, runId);
  if (fs.existsSync(manifestPath)) {
    try {
      fs.unlinkSync(partialPath);
    } catch (err) {
      if (err.code !== 'ENOENT') throw err;
    }
    return { manifestPath };
  }
  if (!fs.existsSync(partialPath)) throw new Error(`No existe el partial de la corrida ${runId}.`);

  const partial = readJson(partialPath, 'el partial');
  if (openAttempt(partial) !== null) throw new Error('No se puede terminar: existe un attempt abierto.');
  assertNoUnresolvedWriter(partial);
  const closure = deriveClosure(partial.attempts, status);
  const validatedUsage = validateUsage(usage);
  const validatedArtifacts = validateArtifacts(artifacts, resolvedDir);
  const validatedExt = ext === undefined ? partial.ext : validateExt(partial.workflow, ext);
  const finishedAt = toIsoTimestamp(now);
  const durationMs = Date.parse(finishedAt) - Date.parse(partial.timing.startedAt);
  if (!Number.isFinite(durationMs) || durationMs < 0) {
    throw new Error('El reloj produjo una duración terminal inválida.');
  }

  const terminal = {
    schemaVersion: partial.schemaVersion,
    runId: partial.runId,
    workflow: partial.workflow,
    mode: partial.mode,
    role: partial.role,
    family: partial.family,
    model: partial.model,
    transport: {
      desired: partial.transport.desired,
      effective: closure.effective,
      fallbackUsed: closure.fallbackUsed,
    },
    attempts: partial.attempts,
    timing: {
      startedAt: partial.timing.startedAt,
      finishedAt,
      durationMs,
    },
    outcome: closure.outcome,
    usage: validatedUsage,
    artifacts: validatedArtifacts,
    ext: validatedExt,
  };

  writeJsonAtomic(manifestPath, terminal);
  fs.unlinkSync(partialPath);
  return { manifestPath };
}
