import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ALLOWED_EXTENSIONS,
  OPT_IN_DIRECTORIES,
  isCopiable,
  isReservedDocumentPath,
} from '../../../skills/knowledge-vault/scripts/lib/selection.mjs';

const EXTENSIONS = [
  '.md', '.sh', '.js', '.mjs', '.py', '.ts', '.ps1', '.json', '.yml', '.txt', '.jsonl',
];

test('[KV-SEL AC-1] selector y listas permanecen puros e inmutables', () => {
  assert.deepEqual(ALLOWED_EXTENSIONS, EXTENSIONS);
  assert.deepEqual(OPT_IN_DIRECTORIES, ['evidencia', 'runs', 'decisiones']);
  for (const values of [ALLOWED_EXTENSIONS, OPT_IN_DIRECTORIES]) {
    assert.ok(Object.isFrozen(values));
    assert.throws(() => values.push('otro'), TypeError);
  }
  assert.equal(isCopiable.length, 1);
});

test('[KV-SEL AC-2] scripts admitidos entran en raíz y opt-ins', () => {
  for (const extension of ['.sh', '.js', '.mjs', '.py', '.ts', '.ps1']) {
    assert.equal(isCopiable(`script${extension}`), true, extension);
    assert.equal(isCopiable(`evidencia/run/script${extension.toUpperCase()}`), true, extension);
  }
});

test('[KV-SEL AC-3] Markdown raíz conserva selección y casing', () => {
  for (const path of ['spec.md', 'SPEC.MD', 'Spec.Md']) {
    assert.equal(isCopiable(path), true, path);
  }
});

test('[KV-SEL AC-4] ubicación y sufijo son la única frontera', () => {
  assert.equal(isCopiable('evidencia/result.txt'), true);
  assert.equal(isCopiable('fixtures/result.txt'), false);
  assert.equal(isCopiable('raro\\nombre.md'), true);
});

test('[KV-SEL AC-5] opt-ins exactos admiten profundidad ilimitada y dotfiles', () => {
  for (const path of [
    'evidencia/a/b/c/.result.json',
    'runs/a/b/c/result.md',
    'decisiones/.result.txt',
  ]) {
    assert.equal(isCopiable(path), true, path);
  }
  for (const path of [
    'Evidencia/result.md',
    'evidenciax/result.md',
    'fixtures/result.md',
    'other/evidencia/result.md',
  ]) {
    assert.equal(isCopiable(path), false, path);
  }
});

test('[KV-SEL AC-6] allowlist exacta se comparte entre raíz y opt-ins', () => {
  for (const extension of EXTENSIONS) {
    assert.equal(isCopiable(`a${extension}`), true, extension);
    assert.equal(isCopiable(`runs/deep/a${extension.toUpperCase()}`), true, extension);
  }
  for (const path of [
    '.md',
    'a',
    'a.yaml',
    'a.cjs',
    'a.tsv',
    'a.sample',
    'evidencia/.json',
    'runs/deep/.TXT',
  ]) {
    assert.equal(isCopiable(path), false, path);
  }
});

test('[KV-SEL AC-9] reserva solo Markdown seleccionado con padre inmediato sdd', () => {
  for (const path of ['sdd/index.md', 'sdd/log.md', 'evidencia/sdd/index.md', 'runs/a/sdd/note.md']) {
    assert.equal(isReservedDocumentPath(path), true, path);
  }
  for (const path of [
    'evidencia/sdd/index.MD',
    'evidencia/sdd/data.json',
    'evidencia/sdd/ancestor/note.md',
    'fixtures/sdd/ancestor/note.md',
  ]) {
    assert.equal(isReservedDocumentPath(path), false, path);
  }
});

test('[KV-SEL AC-17] PDF queda omitido en cualquier ubicación y casing', () => {
  for (const path of ['a.pdf', 'A.PDF', 'evidencia/a.pdf', 'runs/a.Pdf']) {
    assert.equal(isCopiable(path), false, path);
  }
});

test('[KV-SEL AC-18] subdirectorios fuera de la lista no pueden habilitar selección', () => {
  assert.equal(isCopiable('decisiones/a/b/result.jsonl'), true);
  assert.equal(isCopiable('decision/a/b/result.jsonl'), false);
});
