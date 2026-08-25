/**
 * Los ocho campos del nodo y su cadena de autoridad.
 *
 * La regla que ordena todo: **nunca se infiere del sistema de archivos.** La
 * fecha de un flujo sale de lo que su `plan.md` declaró, no del `mtime` del
 * directorio; el `mtime` cambia al copiar, así que usarlo produciría una fecha
 * que se ve plausible y es la de la migración.
 *
 * Medido sobre los cincuenta flujos reales: 43 traen `plan.md` —con `branch`,
 * `created_at` y `status` los 43— y 7 no traen ninguno. Los títulos salen de
 * `spec.md` en 45 casos y de ningún `plan.md`; 5 flujos no tienen encabezado.
 * Los estados observados son cinco valores distintos, y se copian sin normalizar.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

import { DESCONOCIDO, resolveMetadata } from '../../../skills/knowledge-vault/scripts/lib/metadata-source.mjs';
import { createSandbox } from './helpers/sandbox.mjs';

const CAMPOS = ['type', 'title', 'project', 'flow', 'branch', 'date', 'provenance', 'state'];

/** Arma un flujo de origen con la forma real: `<algo>/.plans/archived/<flujo>/`. */
async function flujo(t, flowId, archivos) {
  const caja = await createSandbox(t);
  const dir = path.join(caja.reposDir, 'proyecto', '.plans', 'archived', flowId);
  await fs.mkdir(dir, { recursive: true });
  for (const [nombre, contenido] of Object.entries(archivos)) {
    await fs.writeFile(path.join(dir, nombre), contenido, 'utf8');
  }
  return dir;
}

const PLAN_COMPLETO = [
  '---', 'id: abc-1', 'branch: feature/abc-1-export', 'base_commit: deadbeef',
  'status: done', 'created_at: 2026-03-04T12:00:00-03:00', '---', '', '# Plan — export', '',
].join('\n');

test('[AC-9] con plan.md completo, los ocho campos salen de lo declarado', async (t) => {
  const dir = await flujo(t, 'abc-1', { 'plan.md': PLAN_COMPLETO, 'spec.md': '# Exportar el carrito a CSV\n' });
  const m = await resolveMetadata({ flowDir: dir, flowId: 'abc-1', repoSlug: 'proyecto' });

  assert.deepEqual(Object.keys(m), CAMPOS, 'los campos, en orden y sin sobrantes');
  assert.equal(m.type, 'sdd-flow');
  assert.equal(m.title, 'Exportar el carrito a CSV');
  assert.equal(m.project, 'proyecto');
  assert.equal(m.flow, 'abc-1');
  assert.equal(m.branch, 'feature/abc-1-export');
  assert.equal(m.date, '2026-03-04T12:00:00-03:00');
  assert.equal(m.state, 'done');
});

test('[AC-9] el estado se copia sin normalizar, sea cual sea', async (t) => {
  // Los cinco valores medidos en el corpus real, más uno con otra caja para que
  // quede claro que no hay tabla de traducción ni minusculización.
  for (const estado of ['done', 'committed', 'implementing', 'verified', 'planned', 'En Curso']) {
    const dir = await flujo(t, 'x', { 'plan.md': `---\nstatus: ${estado}\n---\n` });
    const m = await resolveMetadata({ flowDir: dir, flowId: 'x', repoSlug: 'p' });
    assert.equal(m.state, estado, estado);
  }
});

test('[AC-9] sin plan.md, el título sale del encabezado y lo demás es desconocido', async (t) => {
  const dir = await flujo(t, 'sin-plan', { 'spec.md': '# Una investigación suelta\n\ntexto\n' });
  const m = await resolveMetadata({ flowDir: dir, flowId: 'sin-plan', repoSlug: 'p' });
  assert.equal(m.title, 'Una investigación suelta');
  assert.equal(m.branch, DESCONOCIDO);
  assert.equal(m.date, DESCONOCIDO);
  assert.equal(m.state, DESCONOCIDO);
});

test('[AC-9] sin encabezado en spec.md, el título cae al de plan.md y después al directorio', async (t) => {
  const soloPlan = await flujo(t, 'solo-plan', { 'plan.md': '---\nstatus: done\n---\n\n# Título del plan\n' });
  assert.equal((await resolveMetadata({ flowDir: soloPlan, flowId: 'solo-plan', repoSlug: 'p' })).title,
               'Título del plan');

  const pelado = await flujo(t, 'un-flujo-pelado', { 'notas.md': 'sin encabezado\n' });
  assert.equal((await resolveMetadata({ flowDir: pelado, flowId: 'un-flujo-pelado', repoSlug: 'p' })).title,
               'un-flujo-pelado');
});

test('[AC-9] un flujo vacío da los ocho campos, con desconocido donde no hay fuente', async (t) => {
  const dir = await flujo(t, 'vacio', {});
  const m = await resolveMetadata({ flowDir: dir, flowId: 'vacio', repoSlug: 'p' });
  assert.deepEqual(Object.keys(m), CAMPOS);
  assert.deepEqual([m.branch, m.date, m.state], [DESCONOCIDO, DESCONOCIDO, DESCONOCIDO]);
  assert.equal(m.title, 'vacio', 'el nombre del directorio es el último escalón antes de desconocido');
});

test('[AC-9] no se infiere del sistema de archivos: sin created_at la fecha es desconocido', async (t) => {
  // El `mtime` existe y es reciente. Usarlo daría una fecha plausible y falsa:
  // la de la copia, no la del flujo.
  const dir = await flujo(t, 'sin-fecha', { 'plan.md': '---\nstatus: done\nbranch: main\n---\n' });
  const m = await resolveMetadata({ flowDir: dir, flowId: 'sin-fecha', repoSlug: 'p' });
  assert.equal(m.date, DESCONOCIDO);
  assert.equal(m.branch, 'main', 'lo que sí está declarado se lee');
});

test('[AC-9] un frontmatter que no cierra se trata como ausente, no como parcial', async (t) => {
  const dir = await flujo(t, 'roto', { 'plan.md': '---\nstatus: done\nbranch: main\n' });
  const m = await resolveMetadata({ flowDir: dir, flowId: 'roto', repoSlug: 'p' });
  assert.deepEqual([m.branch, m.date, m.state], [DESCONOCIDO, DESCONOCIDO, DESCONOCIDO]);
});

test('[AC-9] la procedencia no filtra la ruta absoluta de la máquina', async (t) => {
  const dir = await flujo(t, 'abc-1', { 'plan.md': PLAN_COMPLETO });
  const m = await resolveMetadata({ flowDir: dir, flowId: 'abc-1', repoSlug: 'proyecto' });
  assert.equal(m.provenance, '.plans/archived/abc-1');
  assert.ok(!m.provenance.includes(dir), 'la procedencia lleva la ruta absoluta adentro');
});

test('[AC-9] todos los valores son cadenas de una línea, que es lo que el emisor admite', async (t) => {
  const dir = await flujo(t, 'abc-1', { 'plan.md': PLAN_COMPLETO, 'spec.md': '# Título\n' });
  const m = await resolveMetadata({ flowDir: dir, flowId: 'abc-1', repoSlug: 'proyecto' });
  for (const [k, v] of Object.entries(m)) {
    assert.equal(typeof v, 'string', k);
    assert.ok(!v.includes('\n'), k);
  }
});
