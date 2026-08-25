/**
 * El nodo de un flujo: su frontmatter y sus enlaces.
 *
 * El nodo es lo único que el vault **escribe** sobre un flujo. Los documentos
 * copiados no se tocan —alterarlos rompería la copia byte-idéntica de AC-1—, así
 * que todo lo que el vault quiera decir sobre un flujo vive acá: los ocho campos
 * de metadatos, el resumen de una línea, y un enlace por documento.
 *
 * Es un módulo **puro**. Recibe los metadatos ya resueltos y falla si le falta un
 * campo, en vez de completarlo: un builder que rellena huecos convierte un dato
 * ausente en uno inventado, que es justo lo que `desconocido` existe para evitar.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { buildNode } from '../../../skills/knowledge-vault/scripts/lib/node-builder.mjs';
import { parseFrontmatter } from '../../../skills/knowledge-vault/scripts/lib/frontmatter.mjs';

const META = {
  type: 'sdd-flow',
  title: 'Exportar el carrito a CSV',
  project: 'ai-workflows',
  flow: 'abc-1',
  branch: 'feature/abc-1-export',
  date: '2026-03-04T12:00:00-03:00',
  provenance: '.plans/archived/abc-1',
  state: 'done',
};
const DOCS = ['spec.md', 'plan.md', 'tasks.md'];
const RESUMEN = 'Exportación del carrito a CSV con separador configurable.';

test('[AC-9] el frontmatter declara los ocho campos más el resumen', () => {
  const nodo = buildNode({ metadata: META, documents: DOCS, summary: RESUMEN });
  const { ok, keys } = parseFrontmatter(nodo);
  assert.equal(ok, true);
  for (const [k, v] of Object.entries(META)) assert.equal(keys.get(k), v, k);
  assert.equal(keys.get('summary'), RESUMEN);
  assert.equal(keys.size, 9, 'sobran o faltan claves');
});

test('[AC-9] el cuerpo enlaza cada documento, con la ruta relativa desde el nodo', () => {
  const nodo = buildNode({ metadata: META, documents: DOCS, summary: RESUMEN });
  // El nodo vive en `sdd/abc-1.md` y los documentos en `sdd/abc-1/`, así que la
  // ruta relativa arranca en el nombre del flujo.
  for (const doc of DOCS) assert.ok(nodo.includes(`(abc-1/${doc})`), doc);
  assert.equal((nodo.match(/^- \[/gm) ?? []).length, DOCS.length, 'un enlace por documento, ni uno más');
});

test('[AC-9] el orden de los enlaces es estable, no el de llegada', () => {
  const a = buildNode({ metadata: META, documents: ['tasks.md', 'spec.md', 'plan.md'], summary: RESUMEN });
  const b = buildNode({ metadata: META, documents: ['spec.md', 'plan.md', 'tasks.md'], summary: RESUMEN });
  assert.equal(a, b, 'el mismo conjunto de documentos da dos nodos distintos');
});

test('[AC-9] un campo faltante es error del llamador, no un hueco que el builder rellena', () => {
  for (const campo of Object.keys(META)) {
    const incompleto = { ...META };
    delete incompleto[campo];
    assert.throws(
      () => buildNode({ metadata: incompleto, documents: DOCS, summary: RESUMEN }),
      new RegExp(campo),
      campo,
    );
  }
});

test('[AC-9] un flujo sin documentos en la raíz da un nodo válido y sin enlaces', () => {
  const nodo = buildNode({ metadata: META, documents: [], summary: RESUMEN });
  assert.equal(parseFrontmatter(nodo).ok, true);
  assert.equal((nodo.match(/^- \[/gm) ?? []).length, 0);
});

test('[AC-9] un nombre con espacio se codifica para que el enlace resuelva', () => {
  const nodo = buildNode({ metadata: META, documents: ['notas de la reunión.md'], summary: RESUMEN });
  assert.ok(nodo.includes('(abc-1/notas%20de%20la%20reuni'), 'el espacio quedó crudo en el enlace');
  assert.ok(nodo.includes('[notas de la reunión.md]'), 'el texto visible se codificó de más');
});

test('[AC-11] el resumen vive en el frontmatter, que es de donde el índice lo deriva', () => {
  const nodo = buildNode({ metadata: META, documents: DOCS, summary: RESUMEN });
  const { keys } = parseFrontmatter(nodo);
  assert.equal(keys.get('summary'), RESUMEN);
  // Y sin resumen no se construye: el índice quedaría sin nada que agregar
  // sobre la ruta, que es exactamente lo que AC-8 existe para evitar.
  assert.throws(() => buildNode({ metadata: META, documents: DOCS }), /resumen|summary/i);
  assert.throws(() => buildNode({ metadata: META, documents: DOCS, summary: '  ' }), /resumen|summary/i);
});

test('[AC-11] un resumen irrepresentable se rechaza en vez de deformarse', () => {
  assert.throws(
    () => buildNode({ metadata: META, documents: DOCS, summary: 'con # numeral' }),
    /#/,
  );
});
