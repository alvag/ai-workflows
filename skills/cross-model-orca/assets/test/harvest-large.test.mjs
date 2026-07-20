// Test de cosecha con transcript >1 MB: prueba que la cosecha lee el mensaje del
// asistente siempre desde el ARCHIVO, nunca de argv -- por eso un informe tan
// grande que jamás cabría en ARG_MAX se cosecha igual (parseTranscript /
// selectAssistantByNonce abren el archivo y lo parsean). El fixture grande se
// genera en runtime (os.tmpdir() + fs.mkdtempSync): nunca se commitea un
// archivo >1 MB al repo.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { parseEnvelope, hasSentinel, selectAssistantByNonce } from '../harvest-core.mjs';
import { harvest } from '../harvest-from-transcript.mjs';

// Con margen sobre el mínimo de 1 MB pedido en el brief.
const MIN_SIZE_BYTES = 1_100_000;
const FILLER = 'Relleno de prueba para el transcript grande: se lee siempre del archivo, nunca de argv. ';

function mkTmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

/**
 * Texto ASCII de al menos `minBytes` bytes, repitiendo `FILLER`.
 * @param {number} minBytes
 * @returns {string}
 */
function bigText(minBytes) {
  const repeats = Math.ceil(minBytes / FILLER.length) + 1;
  return FILLER.repeat(repeats);
}

/**
 * Escribe, en un directorio temporal propio, un fixture JSONL con la forma real
 * de `family` (mismo shape que fixtures/claude-transcript.jsonl y
 * fixtures/codex-rollout.jsonl): un mensaje del asistente ANTERIOR (nonce viejo,
 * chico, para probar la desambiguación) y uno ACTUAL cuyo texto supera 1 MB y
 * cierra con el envelope + sentinel reales.
 * @param {'claude'|'codex'} family
 * @returns {string} ruta del fixture generado.
 */
function writeLargeFixture(family) {
  const dir = mkTmpDir(`harvest-large-${family}-`);
  const filePath = path.join(dir, `${family}-transcript-large.jsonl`);

  const oldText =
    'Informe del dispatch ANTERIOR (no debe cosecharse).\n\n' +
    'X-CMO: taskId=T0 dispatchId=D0 nonce=NONCE-VIEJO\n\n' +
    'STATUS: done';
  const largeBody = bigText(MIN_SIZE_BYTES);
  const newText =
    `${largeBody}\n\n` + 'X-CMO: taskId=T1 dispatchId=D1 nonce=NONCE-ACTUAL\n\n' + 'STATUS: done';

  const lines =
    family === 'claude'
      ? [
          {
            type: 'assistant',
            sessionId: 'claude-large-fixture-0000-0000-000000000001',
            cwd: '/repo/ai-workflows',
            gitBranch: 'docs/cross-model',
            message: { role: 'assistant', model: 'claude-opus-4-8', content: [{ type: 'text', text: oldText }] },
          },
          {
            type: 'assistant',
            sessionId: 'claude-large-fixture-0000-0000-000000000001',
            cwd: '/repo/ai-workflows',
            gitBranch: 'docs/cross-model',
            message: { role: 'assistant', model: 'claude-opus-4-8', content: [{ type: 'text', text: newText }] },
          },
        ]
      : [
          {
            timestamp: '2026-07-19T02:00:00.000Z',
            type: 'response_item',
            payload: { type: 'message', id: 'm0', role: 'assistant', content: [{ type: 'output_text', text: oldText }] },
          },
          {
            timestamp: '2026-07-19T02:00:09.000Z',
            type: 'response_item',
            payload: { type: 'message', id: 'm1', role: 'assistant', content: [{ type: 'output_text', text: newText }] },
          },
        ];

  fs.writeFileSync(filePath, `${lines.map((obj) => JSON.stringify(obj)).join('\n')}\n`);
  return filePath;
}

for (const family of ['claude', 'codex']) {
  test(`selectAssistantByNonce("${family}", ...) cosecha el mensaje ACTUAL >1 MB desde el archivo (no argv)`, () => {
    const filePath = writeLargeFixture(family);
    const fileSize = fs.statSync(filePath).size;
    assert.ok(fileSize > MIN_SIZE_BYTES, `el fixture debe superar 1 MB (midió ${fileSize} bytes)`);

    const actual = selectAssistantByNonce(family, filePath, 'NONCE-ACTUAL');
    assert.notEqual(actual, null);
    assert.ok(Buffer.byteLength(actual, 'utf8') > 1_000_000, 'el mensaje cosechado debe superar 1 MB');
    assert.equal(parseEnvelope(actual).nonce, 'NONCE-ACTUAL');
    assert.equal(hasSentinel(actual), true);

    const viejo = selectAssistantByNonce(family, filePath, 'NONCE-VIEJO');
    assert.notEqual(viejo, null);
    assert.notEqual(viejo, actual);
    assert.ok(Buffer.byteLength(viejo, 'utf8') < 1000, 'el mensaje del nonce viejo debe ser chico (desambiguación real, no casualidad)');
  });

  test(`harvest() cosecha y persiste el informe >1 MB (${family}) leyendo del archivo, respetando la contención`, async () => {
    const filePath = writeLargeFixture(family);
    const root = mkTmpDir(`harvest-large-root-${family}-`);

    const result = await harvest({
      family,
      transcriptPath: filePath,
      nonce: 'NONCE-ACTUAL',
      reportPath: 'informe-grande.md',
      root,
      deadlineMs: 2000,
    });

    assert.equal(result.code, 0);
    assert.equal(result.reportPath, path.join(fs.realpathSync(root), 'informe-grande.md'));

    const written = fs.readFileSync(result.reportPath, 'utf8');
    assert.ok(Buffer.byteLength(written, 'utf8') > 1_000_000, 'el informe persistido debe superar 1 MB');
    assert.match(written, /NONCE-ACTUAL/);
    assert.doesNotMatch(written, /ANTERIOR/);
  });
}
