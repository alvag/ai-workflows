// Tests de harvest-core.mjs: sentinel, envelope+nonce, contención robusta,
// parser de transcript/rollout y dedup-FSM crash-idempotent.
// Cada test que usa el filesystem trabaja dentro de un directorio temporal propio
// (fs.mkdtempSync) para no dejar residuos ni interferir entre corridas.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  hasSentinel,
  stripSentinel,
  parseEnvelope,
  parseTranscript,
  selectAssistantByNonce,
  checkContainment,
  writeExclusive,
  makeDedupFsm,
} from '../harvest-core.mjs';

const TEST_DIR = path.dirname(new URL(import.meta.url).pathname);
const CODEX_FIXTURE = path.join(TEST_DIR, 'fixtures/codex-rollout.jsonl');
const CLAUDE_FIXTURE = path.join(TEST_DIR, 'fixtures/claude-transcript.jsonl');

function mkTmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// ---------------------------------------------------------------------------
// hasSentinel
// ---------------------------------------------------------------------------

test('hasSentinel: true cuando la última línea no vacía es STATUS: done', () => {
  const msg = 'Cuerpo del informe.\nX-CMO: nonce=ABC\nSTATUS: done';
  assert.equal(hasSentinel(msg), true);
});

test('hasSentinel: true con líneas en blanco finales tras STATUS: done', () => {
  const msg = 'Cuerpo.\nSTATUS: done\n\n';
  assert.equal(hasSentinel(msg), true);
});

test('hasSentinel: false si STATUS: done aparece citado en el cuerpo y hay más líneas después', () => {
  const msg = 'El secundario reportó "STATUS: done" en su resumen.\nPero esto sigue.';
  assert.equal(hasSentinel(msg), false);
});

test('hasSentinel: false sin sentinel', () => {
  const msg = 'Informe sin cerrar correctamente.';
  assert.equal(hasSentinel(msg), false);
});

// ---------------------------------------------------------------------------
// stripSentinel
// ---------------------------------------------------------------------------

test('stripSentinel: quita solo la línea sentinel y preserva el resto (incluida X-CMO:)', () => {
  const msg = 'Cuerpo del informe.\nX-CMO: nonce=ABC\nSTATUS: done';
  const stripped = stripSentinel(msg);
  assert.match(stripped, /Cuerpo del informe\./);
  assert.match(stripped, /X-CMO: nonce=ABC/);
  assert.doesNotMatch(stripped, /STATUS: done/);
});

test('stripSentinel: sin sentinel devuelve el mensaje intacto', () => {
  const msg = 'Informe sin cerrar.';
  assert.equal(stripSentinel(msg), msg);
});

// ---------------------------------------------------------------------------
// parseEnvelope
// ---------------------------------------------------------------------------

test('parseEnvelope: extrae nonce, taskId y dispatchId cuando los tres están presentes', () => {
  const msg = 'Cuerpo.\nX-CMO: taskId=T1 dispatchId=D1 nonce=NONCE-1\nSTATUS: done';
  const envelope = parseEnvelope(msg);
  assert.equal(envelope.nonce, 'NONCE-1');
  assert.equal(envelope.taskId, 'T1');
  assert.equal(envelope.dispatchId, 'D1');
});

test('parseEnvelope: taskId/dispatchId son null cuando el secundario solo copia el nonce', () => {
  const msg = 'Cuerpo.\nX-CMO: nonce=NONCE-2\nSTATUS: done';
  const envelope = parseEnvelope(msg);
  assert.equal(envelope.nonce, 'NONCE-2');
  assert.equal(envelope.taskId, null);
  assert.equal(envelope.dispatchId, null);
});

test('parseEnvelope: nonce null si no hay línea X-CMO:', () => {
  const msg = 'Cuerpo sin envelope.\nSTATUS: done';
  const envelope = parseEnvelope(msg);
  assert.equal(envelope.nonce, null);
  assert.equal(envelope.taskId, null);
  assert.equal(envelope.dispatchId, null);
});

test('parseEnvelope: no lanza ante mensajes vacíos o degenerados', () => {
  assert.doesNotThrow(() => parseEnvelope(''));
  assert.equal(parseEnvelope('').nonce, null);
});

// ---------------------------------------------------------------------------
// parseTranscript
// ---------------------------------------------------------------------------

test('parseTranscript("codex", ...) devuelve el texto del último assistant (dispatch ACTUAL)', () => {
  const text = parseTranscript('codex', CODEX_FIXTURE);
  assert.notEqual(text, null);
  assert.match(text, /Informe del dispatch ACTUAL\./);
  assert.doesNotMatch(text, /ANTERIOR/);
  assert.equal(parseEnvelope(text).nonce, 'NONCE-ACTUAL');
  assert.equal(hasSentinel(text), true);
});

test('parseTranscript("claude", ...) devuelve el texto del último assistant (dispatch ACTUAL)', () => {
  const text = parseTranscript('claude', CLAUDE_FIXTURE);
  assert.notEqual(text, null);
  assert.match(text, /Informe del dispatch ACTUAL\./);
  assert.doesNotMatch(text, /ANTERIOR/);
  assert.equal(parseEnvelope(text).nonce, 'NONCE-ACTUAL');
  assert.equal(hasSentinel(text), true);
});

test('parseTranscript: devuelve null si el archivo no existe', () => {
  const missing = path.join(mkTmpDir('harvest-core-missing-'), 'no-existe.jsonl');
  assert.equal(parseTranscript('codex', missing), null);
});

test('parseTranscript: ignora líneas JSON inválidas o a medio escribir sin romper', () => {
  const dir = mkTmpDir('harvest-core-partial-');
  const original = fs.readFileSync(CODEX_FIXTURE, 'utf8');
  const withPartialLine = `${original}\n{"type":"response_item","payload":{"role":"assist`;
  const tmpFile = path.join(dir, 'codex-rollout-partial.jsonl');
  fs.writeFileSync(tmpFile, withPartialLine);
  const text = parseTranscript('codex', tmpFile);
  assert.notEqual(text, null);
  assert.match(text, /Informe del dispatch ACTUAL\./);
});

// ---------------------------------------------------------------------------
// selectAssistantByNonce
// ---------------------------------------------------------------------------

test('selectAssistantByNonce: con NONCE-VIEJO devuelve el mensaje del dispatch anterior (codex)', () => {
  const text = selectAssistantByNonce('codex', CODEX_FIXTURE, 'NONCE-VIEJO');
  assert.notEqual(text, null);
  assert.match(text, /ANTERIOR/);
});

test('selectAssistantByNonce: con NONCE-ACTUAL devuelve el mensaje del dispatch actual (codex)', () => {
  const text = selectAssistantByNonce('codex', CODEX_FIXTURE, 'NONCE-ACTUAL');
  assert.notEqual(text, null);
  assert.match(text, /ACTUAL/);
});

test('selectAssistantByNonce: con un nonce inexistente devuelve null (codex)', () => {
  const text = selectAssistantByNonce('codex', CODEX_FIXTURE, 'NONCE-NO-EXISTE');
  assert.equal(text, null);
});

test('selectAssistantByNonce: desambigua por nonce también en transcripts de Claude', () => {
  const viejo = selectAssistantByNonce('claude', CLAUDE_FIXTURE, 'NONCE-VIEJO');
  const actual = selectAssistantByNonce('claude', CLAUDE_FIXTURE, 'NONCE-ACTUAL');
  assert.match(viejo, /ANTERIOR/);
  assert.match(actual, /ACTUAL/);
});

// ---------------------------------------------------------------------------
// checkContainment
// ---------------------------------------------------------------------------

test('checkContainment: rechaza rutas absolutas', () => {
  const root = mkTmpDir('harvest-core-root-');
  const result = checkContainment('/etc/passwd', root);
  assert.equal(result.ok, false);
  assert.equal(typeof result.reason, 'string');
});

test('checkContainment: rechaza rutas con segmentos ".."', () => {
  const root = mkTmpDir('harvest-core-root-');
  const result = checkContainment('../fuera-del-root.md', root);
  assert.equal(result.ok, false);
});

test('checkContainment: rechaza symlink en el directorio padre que escapa del root', () => {
  const root = mkTmpDir('harvest-core-root-');
  const outside = mkTmpDir('harvest-core-outside-');
  fs.symlinkSync(outside, path.join(root, 'escape'), 'dir');
  const result = checkContainment('escape/report.md', root);
  assert.equal(result.ok, false);
});

test('checkContainment: rechaza cuando el destino ya existe', () => {
  const root = mkTmpDir('harvest-core-root-');
  fs.writeFileSync(path.join(root, 'ya-existe.md'), 'contenido previo');
  const result = checkContainment('ya-existe.md', root);
  assert.equal(result.ok, false);
});

test('checkContainment: caso feliz dentro del root', () => {
  const root = mkTmpDir('harvest-core-root-');
  fs.mkdirSync(path.join(root, 'reports'));
  const result = checkContainment('reports/ok.md', root);
  assert.equal(result.ok, true);
  assert.equal(result.resolved, path.join(fs.realpathSync(root), 'reports', 'ok.md'));
});

test('checkContainment: canonicaliza root cuando root en sí es un symlink', () => {
  const realRoot = mkTmpDir('harvest-core-realroot-');
  const rootLink = path.join(os.tmpdir(), `harvest-core-rootlink-${process.pid}-${Date.now()}`);
  fs.symlinkSync(realRoot, rootLink, 'dir');
  try {
    const result = checkContainment('ok.md', rootLink);
    assert.equal(result.ok, true);
    assert.equal(result.resolved, path.join(fs.realpathSync(realRoot), 'ok.md'));
  } finally {
    fs.unlinkSync(rootLink);
  }
});

// ---------------------------------------------------------------------------
// writeExclusive
// ---------------------------------------------------------------------------

test('writeExclusive: escribe el archivo cuando no existe', () => {
  const root = mkTmpDir('harvest-core-root-');
  const target = path.join(root, 'nuevo.md');
  writeExclusive(target, 'contenido');
  assert.equal(fs.readFileSync(target, 'utf8'), 'contenido');
});

test('writeExclusive: falla si el archivo aparece entre el check y la escritura (TOCTOU)', () => {
  const root = mkTmpDir('harvest-core-root-');
  const target = path.join(root, 'ya-estaba.md');
  fs.writeFileSync(target, 'contenido original');
  assert.throws(() => writeExclusive(target, 'contenido nuevo'), /EEXIST/);
  assert.equal(fs.readFileSync(target, 'utf8'), 'contenido original');
});

// ---------------------------------------------------------------------------
// makeDedupFsm
// ---------------------------------------------------------------------------

test('makeDedupFsm: transiciona received -> harvested -> promoted', () => {
  const dir = mkTmpDir('harvest-core-fsm-');
  const statePath = path.join(dir, 'state.json');
  const fsm = makeDedupFsm(statePath);
  const key = 'D1:NONCE-ACTUAL';

  assert.equal(fsm.state(key), null);

  fsm.markReceived(key);
  assert.equal(fsm.state(key).status, 'received');
  assert.equal(fsm.isPromoted(key), false);

  fsm.markHarvested(key);
  assert.equal(fsm.state(key).status, 'harvested');
  assert.equal(fsm.isPromoted(key), false);

  fsm.markPromoted(key, 'hash-canonico-1');
  assert.equal(fsm.state(key).status, 'promoted');
  assert.equal(fsm.isPromoted(key), true);
});

test('makeDedupFsm: el estado sobrevive a un "crash" (releer statePath desde disco)', () => {
  const dir = mkTmpDir('harvest-core-fsm-');
  const statePath = path.join(dir, 'state.json');
  const key = 'D2:NONCE-ACTUAL';

  const fsmAntesDelCrash = makeDedupFsm(statePath);
  fsmAntesDelCrash.markReceived(key);
  fsmAntesDelCrash.markHarvested(key);
  fsmAntesDelCrash.markPromoted(key, 'hash-canonico-2');

  // Simula un proceso nuevo tras un crash: instancia fresca sobre el mismo statePath.
  const fsmDespuesDelCrash = makeDedupFsm(statePath);
  assert.equal(fsmDespuesDelCrash.isPromoted(key), true);
  assert.equal(fsmDespuesDelCrash.state(key).desiredCanonicalHash, 'hash-canonico-2');
});

test('makeDedupFsm: una segunda promoción con el mismo hash es idempotente (no duplica)', () => {
  const dir = mkTmpDir('harvest-core-fsm-');
  const statePath = path.join(dir, 'state.json');
  const fsm = makeDedupFsm(statePath);
  const key = 'D3:NONCE-ACTUAL';

  fsm.markReceived(key);
  fsm.markHarvested(key);
  fsm.markPromoted(key, 'hash-canonico-3');
  assert.doesNotThrow(() => fsm.markPromoted(key, 'hash-canonico-3'));

  assert.equal(fsm.isPromoted(key), true);
  assert.equal(fsm.state(key).desiredCanonicalHash, 'hash-canonico-3');

  const rawState = JSON.parse(fs.readFileSync(statePath, 'utf8'));
  assert.equal(Object.keys(rawState).length, 1);
});

test('makeDedupFsm: un key distinto (nonce nuevo tras un fallo) se procesa de forma independiente', () => {
  const dir = mkTmpDir('harvest-core-fsm-');
  const statePath = path.join(dir, 'state.json');
  const fsm = makeDedupFsm(statePath);
  const keyFallido = 'D4:NONCE-FALLIDO';
  const keyNuevo = 'D4:NONCE-REINTENTO';

  fsm.markReceived(keyFallido);
  // El dispatch anterior nunca llegó a promoted (se abandona tras el fallo).

  fsm.markReceived(keyNuevo);
  fsm.markHarvested(keyNuevo);
  fsm.markPromoted(keyNuevo, 'hash-canonico-4');

  assert.equal(fsm.state(keyFallido).status, 'received');
  assert.equal(fsm.isPromoted(keyFallido), false);
  assert.equal(fsm.isPromoted(keyNuevo), true);
});

test('makeDedupFsm: markReceived/markHarvested no regresan un estado ya más avanzado', () => {
  const dir = mkTmpDir('harvest-core-fsm-');
  const statePath = path.join(dir, 'state.json');
  const fsm = makeDedupFsm(statePath);
  const key = 'D5:NONCE-ACTUAL';

  fsm.markReceived(key);
  fsm.markHarvested(key);
  fsm.markPromoted(key, 'hash-canonico-5');

  fsm.markReceived(key);
  assert.equal(fsm.state(key).status, 'promoted');
  assert.equal(fsm.isPromoted(key), true);
});
