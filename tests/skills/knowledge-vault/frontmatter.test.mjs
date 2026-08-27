/**
 * T7 — precondición fail-closed (AC-16, AC-17).
 *
 * Los cinco casos de rechazo se prueban **por separado**: cada uno es un estado
 * nombrado, no la rama `else` de los otros.
 *
 * El predicado lo declara **quien llama**. Estos tests usan `plan.md:status=done`
 * porque es el que pide `sdd-flow`, pero nada de eso vive en `kv`: el mismo código
 * recorre `README.md:estado=cerrado` sin una línea distinta.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import { parseFrontmatter } from '../../../skills/knowledge-vault/scripts/lib/frontmatter.mjs';

const PLAN_DONE = ['---', 'id: knowledge-vault', 'status: done', 'branch: feat/kv', '---', '', '# Plan'].join('\n');

/** Evalúa el predicado de siempre, para no repetirlo en cada caso. */

// ── El parser mínimo ──────────────────────────────────────────────────────────

test('lee claves escalares de primer nivel', () => {
  const { ok, keys } = parseFrontmatter(PLAN_DONE);
  assert.equal(ok, true);
  assert.equal(keys.get('id'), 'knowledge-vault');
  assert.equal(keys.get('status'), 'done');
  assert.equal(keys.get('branch'), 'feat/kv');
});

test('parseFrontmatter no lanza ante entradas raras', () => {
  assert.equal(parseFrontmatter(null).ok, false);
  assert.equal(parseFrontmatter(undefined).ok, false);
  assert.equal(parseFrontmatter(42).ok, false);
});

// ── Recuperados del árbol de origen ───────────────────────────────────────────
//
// Estos seis verificaban el parser **a través** del evaluador de predicados, que
// este flujo retira. La conducta que comprueban es del parser y sigue viva, así
// que se reexpresan contra `parseFrontmatter` en vez de perderse con la máquina
// que las envolvía. Es exactamente lo que `metadata-source` necesita fiable: lee
// el `plan.md` de cada flujo de origen con este mismo parser.

test('ignora líneas indentadas: un status anidado no es el del plan', () => {
  const texto = ['---', 'meta:', '  status: done', 'id: kv', '---'].join('\n');
  const { ok, keys } = parseFrontmatter(texto);
  assert.equal(ok, true);
  assert.ok(!keys.has('status'), 'una clave anidada se leyó como de primer nivel');
  assert.equal(keys.get('id'), 'kv');
});

test('ignora comentarios y líneas en blanco sin invalidar el documento', () => {
  const texto = ['---', '# un comentario', '', 'status: done', '', '---'].join('\n');
  const { ok, keys } = parseFrontmatter(texto);
  assert.equal(ok, true);
  assert.equal(keys.get('status'), 'done');
});

test('una línea de forma desconocida no invalida el documento', () => {
  // Ignorarla no puede producir un falso sí: aceptar exige el hallazgo positivo.
  const { ok, keys } = parseFrontmatter(['---', '- suelto', 'status: done', '---'].join('\n'));
  assert.equal(ok, true);
  assert.equal(keys.get('status'), 'done');
});

test('saca comillas envolventes y comentarios al final del valor', () => {
  assert.equal(parseFrontmatter('---\nstatus: "done"\n---\n').keys.get('status'), 'done');
  assert.equal(parseFrontmatter("---\nstatus: 'done'\n---\n").keys.get('status'), 'done');
  assert.equal(parseFrontmatter('---\nstatus: done  # ya cerrado\n---\n').keys.get('status'), 'done');
  // Un `#` pegado al valor es parte del valor, como en YAML: el corte de
  // comentario exige un espacio delante. Entre comillas ni siquiera hace falta
  // ese espacio, porque ahí el `#` nunca abre comentario — ver el caso de abajo.
  assert.equal(parseFrontmatter('---\nstatus: done#x\n---\n').keys.get('status'), 'done#x');
  // Y un valor que es SOLO comentario queda vacío, no se lee a sí mismo.
  assert.equal(parseFrontmatter('---\nstatus:   # pendiente\n---\n').keys.get('status'), '');
});

test('un valor entrecomillado conserva su numeral', () => {
  // En YAML un `#` entre comillas es literal, y el corte de comentario mira las
  // comillas primero: entrecomillar es salida real para un título que cita un PR.
  const con = (v) => parseFrontmatter(`---\nt: ${v}\n---\n`).keys.get('t');
  assert.equal(con('"PR #1264"'), 'PR #1264');
  assert.equal(con("'PR #1264'"), 'PR #1264');
  // El comentario de AFUERA se descarta igual, sin partir por el `#` de adentro.
  assert.equal(con('"valor # literal" # comentario'), 'valor # literal');
});

test('tolera BOM y finales de línea de Windows', () => {
  const bom = String.fromCodePoint(0xfeff);
  assert.equal(parseFrontmatter(`${bom}---\nstatus: done\n---\n`).keys.get('status'), 'done');
  assert.equal(parseFrontmatter('---\r\nstatus: done\r\n---\r\n').keys.get('status'), 'done');
});

test('acepta ... como cierre, y no lee el cuerpo de afuera del bloque', () => {
  assert.equal(parseFrontmatter('---\nstatus: done\n...\n').keys.get('status'), 'done');
  const conCuerpo = ['---', 'id: kv', '---', '', 'status: done', ''].join('\n');
  assert.ok(!parseFrontmatter(conCuerpo).keys.has('status'));
});

test('un bloque que no cierra es ilegible, y una clave duplicada se señala', () => {
  assert.equal(parseFrontmatter('---\nstatus: done\n').ok, false);
  const dup = parseFrontmatter('---\nstatus: done\nstatus: otro\n---\n');
  assert.ok(dup.duplicated.has('status'));
  assert.equal(dup.keys.get('status'), 'done', 'gana la primera aparición');
});
