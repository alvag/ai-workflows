import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const REFERENCE = path.resolve('skills/knowledge-vault/reference.md');
const MARKER = '<!-- kv-literal-content -->';
const reference = await readFile(REFERENCE, 'utf8');

function between(start, end) {
  const from = reference.indexOf(start);
  assert.notEqual(from, -1, `no se encontró ${JSON.stringify(start)}`);
  const to = reference.indexOf(end, from + start.length);
  assert.notEqual(to, -1, `no se encontró ${JSON.stringify(end)}`);
  return reference.slice(from, to);
}

function publishedVerifier() {
  const section = between('### El verificador', '## Casos borde');
  const match = section.match(/```bash\n([\s\S]*?)\n```/);
  assert.ok(match, 'no se encontró el comando publicado del verificador');
  return match[1];
}

function publishedExample() {
  const section = between('Ejemplo fiel y completo', '### El verificador');
  const match = section.match(/`````\n([\s\S]*?)\n`````/);
  assert.ok(match, 'no se encontró el wrapper de ejemplo publicado');
  return Buffer.from(`${match[1]}\n`, 'utf8');
}

function wrap(source, sourcePath = 'reports/informe.md') {
  const text = new TextDecoder('utf-8', { fatal: true }).decode(source);
  const maxRun = Math.max(0, ...(text.match(/`+/g) ?? []).map((run) => run.length));
  const fence = '`'.repeat(Math.max(3, maxRun + 1));
  const sha256 = createHash('sha256').update(source).digest('hex');
  const prefix = [
    `Source path (JSON): ${JSON.stringify(sourcePath)}`,
    'Source format (JSON): "text/markdown"',
    `Source size: ${source.length}`,
    `Source SHA-256: ${sha256}`,
    MARKER,
    `${fence}text`,
    '',
  ].join('\n');
  return Buffer.concat([Buffer.from(prefix, 'utf8'), source, Buffer.from(`\n${fence}\n`, 'utf8')]);
}

async function verify(t, source, wrapper) {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'kv-wrapper-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const sourcePath = path.join(dir, 'source');
  const wrapperPath = path.join(dir, 'wrapper.md');
  await writeFile(sourcePath, source);
  await writeFile(wrapperPath, wrapper);
  return spawnSync('/bin/sh', ['-c', publishedVerifier()], {
    encoding: 'utf8',
    env: { ...process.env, origen: sourcePath, wrapper: wrapperPath },
  });
}

function count(buffer, needle) {
  const token = Buffer.from(needle, 'utf8');
  let total = 0;
  for (let at = buffer.indexOf(token); at !== -1; at = buffer.indexOf(token, at + token.length)) total += 1;
  return total;
}

test('el ejemplo publicado pasa con el verificador publicado', async (t) => {
  const source = Buffer.from('revisar ```bloque``` sin salto final', 'utf8');
  const result = await verify(t, source, publishedExample());
  assert.equal(result.status, 0, result.stderr || result.stdout);
});

test('el verificador publicado detecta un payload alterado', async (t) => {
  const source = Buffer.from('revisar ```bloque``` sin salto final', 'utf8');
  const wrapper = publishedExample();
  const at = wrapper.indexOf(Buffer.from('revisar', 'utf8'));
  assert.notEqual(at, -1);
  wrapper[at] = 'R'.charCodeAt(0);
  const result = await verify(t, source, wrapper);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /payload extraído no coincide byte a byte/);
});

test('el marcador dentro del origen no desplaza el marcador estructural', async (t) => {
  const source = Buffer.from(`el origen menciona ${MARKER} como contenido`, 'utf8');
  const wrapper = wrap(source);
  assert.equal(count(wrapper, MARKER), 2, 'el caso debe contener dos marcadores');
  const result = await verify(t, source, wrapper);
  assert.equal(result.status, 0, result.stderr || result.stdout);
});

test('el marcador dentro de la ruta no desplaza el marcador estructural', async (t) => {
  const source = Buffer.from('contenido', 'utf8');
  const wrapper = wrap(source, `reports/${MARKER}.md`);
  assert.equal(count(wrapper, MARKER), 2, 'el caso debe contener dos marcadores');
  const result = await verify(t, source, wrapper);
  assert.equal(result.status, 0, result.stderr || result.stdout);
});
