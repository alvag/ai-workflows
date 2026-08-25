/**
 * La selección es un predicado, no un motor de reglas.
 *
 * Las nueve reglas que este módulo reemplaza filtraban **salida cruda de máquina**
 * (binarios, volcados, artefactos generados) y por eso dejaban pasar el andamiaje
 * de un flujo SDD, que es texto legítimo: transcripciones de revisión, árboles de
 * prueba, veredictos. Medido sobre los cincuenta flujos archivados, colaban 65 %
 * de material que nadie querría consultar.
 *
 * El corte que sí separa conocimiento de andamiaje resultó ser posicional: lo que
 * el flujo decidió vive en la **raíz** del directorio, y lo que el flujo usó para
 * decidirlo vive en subdirectorios.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { isCopiable } from '../../../skills/knowledge-vault/scripts/lib/selection.mjs';

test('[AC-4] entran los .md de la raíz del flujo', () => {
  for (const ruta of ['spec.md', 'plan.md', 'tasks.md', 'index.md', 'bitacora.md']) {
    assert.equal(isCopiable(ruta), true, ruta);
  }
});

test('[AC-4] no entra lo que no termina en .md', () => {
  for (const ruta of ['alcance.txt', 'resumenes.tsv', 'bitacora', 'plan.mdx', 'md']) {
    assert.equal(isCopiable(ruta), false, ruta);
  }
});

test('[AC-4] no entra nada contenido en un subdirectorio, aunque sea .md', () => {
  for (const ruta of ['cross-review/veredicto.md', 'co-explore/detail-a.md', 'a/b/c.md']) {
    assert.equal(isCopiable(ruta), false, ruta);
  }
});

test('[AC-4] la extensión se compara sin distinguir mayúsculas', () => {
  for (const ruta of ['SPEC.MD', 'Spec.Md', 'plan.mD']) {
    assert.equal(isCopiable(ruta), true, ruta);
  }
});

test('[AC-4] el separador es la barra, la única que el inventario emite', () => {
  // `walkNeutral` arma toda ruta relativa como `${prefijo}/${nombre}`, en cualquier
  // plataforma. Así que en POSIX una barra invertida es un carácter más del nombre
  // y el archivo está en la raíz. Que ese nombre sea portable a otro sistema lo
  // decide `portable-path`, que es otra pregunta y tiene su propio módulo.
  assert.equal(isCopiable('raro\\nombre.md'), true);
});

test('[AC-4] el corte es exactamente la partición medida sobre un flujo real', () => {
  const flujo = [
    'spec.md', 'plan.md', 'tasks.md', 'bitacora.md', 'handoff.md', 'index.md',
    'alcance.txt', 'resumenes.tsv',
    'cross-review/veredicto-1.md', 'cross-review/prompt-1.md',
    'arbol-desechable/fixture/a.md',
  ];
  assert.deepEqual(flujo.filter(isCopiable), [
    'spec.md', 'plan.md', 'tasks.md', 'bitacora.md', 'handoff.md', 'index.md',
  ]);
});

test('[AC-4] el predicado no depende de que exista nada en disco', () => {
  assert.equal(isCopiable('no-existe-en-ningun-lado.md'), true);
});
