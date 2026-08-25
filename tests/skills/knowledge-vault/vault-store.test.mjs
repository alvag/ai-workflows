/**
 * El layout legible de AC-10, y la frontera verificada.
 *
 * El layout del que se rescata esto era `raw/<source_id>/<revision_id>/files/`:
 * correcto para un almacén de revisiones inmutables, e ilegible para una persona
 * que abre el vault en un editor de Markdown. Acá la ruta de un documento es la
 * que alguien escribiría a mano.
 *
 * La otra mitad es la **frontera verificada**: `verifyTree` compara conjuntos
 * exactos y reporta `sobrantes`, así que todo lo generado —el nodo del flujo y
 * los índices— tiene que vivir FUERA del directorio que se verifica.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';

import {
  assertFlowNameAllowed,
  formatLogEntry,
  resolveLayout,
} from '../../../skills/knowledge-vault/scripts/lib/vault-store.mjs';
import { PortablePathError } from '../../../skills/knowledge-vault/scripts/lib/portable-path.mjs';

const VAULT = path.join(path.sep, 'vaults', 'dev-memory');

test('[AC-10] la ruta de un documento es legible: sin raw, sin files, sin hexadecimal', () => {
  const { frontier } = resolveLayout(VAULT, 'ai-workflows', 'vault-consultable');
  const documento = path.join(frontier, 'spec.md');
  const relativa = path.relative(VAULT, documento);

  assert.equal(relativa, path.join('projects', 'ai-workflows', 'sdd', 'vault-consultable', 'spec.md'));
  for (const prohibido of ['raw', 'files']) {
    assert.ok(!relativa.split(path.sep).includes(prohibido), `sobra el segmento ${prohibido}`);
  }
  assert.ok(!/[0-9a-f]{12,}/.test(relativa), 'la ruta lleva un identificador hexadecimal');
});

test('[AC-10] el nodo es hermano del directorio, no vive dentro de la frontera', () => {
  const { frontier, nodePath } = resolveLayout(VAULT, 'ai-workflows', 'vault-consultable');
  assert.equal(nodePath, `${frontier}.md`);
  assert.equal(path.dirname(nodePath), path.dirname(frontier));
  assert.ok(!nodePath.startsWith(frontier + path.sep), 'el nodo cae dentro de la frontera');
});

test('[AC-10] los cuatro índices viven fuera de la frontera, de la raíz hacia la hoja', () => {
  const { frontier, indexPaths } = resolveLayout(VAULT, 'ai-workflows', 'vault-consultable');
  assert.deepEqual(indexPaths, [
    path.join(VAULT, 'index.md'),
    path.join(VAULT, 'projects', 'index.md'),
    path.join(VAULT, 'projects', 'ai-workflows', 'index.md'),
    path.join(VAULT, 'projects', 'ai-workflows', 'sdd', 'index.md'),
  ]);
  for (const p of indexPaths) {
    assert.ok(!p.startsWith(frontier + path.sep), `${p} cae dentro de la frontera`);
  }
});

test('[AC-10] un flujo llamado index o log se rechaza en vez de pisar un generado', () => {
  for (const reservado of ['index', 'log']) {
    assert.throws(() => assertFlowNameAllowed(reservado), /reservado/i, reservado);
    assert.throws(() => resolveLayout(VAULT, 'ai-workflows', reservado), /reservado/i, reservado);
  }
});

test('[AC-10] el rechazo del reservado no se escapa cambiando mayúsculas', () => {
  // En un filesystem que no distingue mayúsculas —macOS, Windows— `Index.md`
  // pisa `index.md`. La comparación va por clave de colisión, no por igualdad.
  for (const disfraz of ['Index', 'INDEX', 'Log']) {
    assert.throws(() => assertFlowNameAllowed(disfraz), /reservado/i, disfraz);
  }
});

test('[AC-10] un index.md dentro del flujo de origen se copia y no colisiona', () => {
  const { frontier, indexPaths } = resolveLayout(VAULT, 'ai-workflows', 'un-flujo');
  const copiado = path.join(frontier, 'index.md');
  assert.ok(!indexPaths.includes(copiado), 'el index copiado se confunde con uno generado');
  assert.ok(copiado.startsWith(frontier + path.sep), 'el index copiado quedó fuera de la frontera');
});

test('[AC-10] un segmento no portable se rechaza antes de construir ninguna ruta', () => {
  assert.throws(() => resolveLayout(VAULT, 'ai-workflows', 'con/barra'), PortablePathError);
  assert.throws(() => resolveLayout(VAULT, 'ai-workflows', '..'), PortablePathError);
  assert.throws(() => resolveLayout(VAULT, 'CON', 'un-flujo'), PortablePathError);
});

test('[AC-10] la entrada de log ya no lleva revisión ni intento', () => {
  const linea = formatLogEntry({
    timestamp: '2026-08-25T10:00:00-05:00',
    repoSlug: 'ai-workflows',
    flowId: 'vault-consultable',
    counts: { included: 6, omitted: 214 },
  });
  assert.match(linea, /vault-consultable/);
  assert.match(linea, /6 archivados, 214 omitidos/);
  assert.ok(!/rev |intento /.test(linea), 'la entrada arrastra vocabulario de revisiones');
  assert.ok(linea.endsWith('\n'));
});
