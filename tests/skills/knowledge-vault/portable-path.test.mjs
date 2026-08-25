/**
 * T3 — nombres portables, traversal y clave de colisión (AC-3, AC-7, AC-7b).
 *
 * Los caracteres invisibles se construyen con `String.fromCodePoint`.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  PortablePathError,
  assertCanonicalPath,
  assertNoSiblingCollision,
  assertPortableSegment,
  collisionKey,
  inspectSegment,
  isCanonicalPath,
  isPortableSegment,
  toCanonicalPath,
} from '../../../skills/knowledge-vault/scripts/lib/portable-path.mjs';

const NUL = String.fromCodePoint(0x00);
const LF = String.fromCodePoint(0x0a);
const DEL = String.fromCodePoint(0x7f);
const E_ACUTE_NFC = String.fromCodePoint(0xe9); // é
const E_ACUTE_NFD = `e${String.fromCodePoint(0x301)}`; // e + acento combinante
const E_ACUTE_UPPER = String.fromCodePoint(0xc9); // É

function rejects(fn, code) {
  assert.throws(fn, (err) => {
    assert.ok(err instanceof PortablePathError, `se esperaba PortablePathError, llegó ${err?.name}`);
    assert.equal(err.code, code);
    return true;
  });
}

// ── Repertorio completo: lo que SÍ se archiva (AC-7) ──────────────────────────

test('acepta el repertorio completo de nombres representables', () => {
  const aceptados = [
    'plan.md',
    'spec.md',
    'informe final.md',
    'caf\u00e9.md',
    'cafe\u0301.md',
    '\u4f60\u597d.md',
    '\u0440\u0443\u0441\u0441\u043a\u0438\u0439.md',
    `${String.fromCodePoint(0x1f600)}.md`,
    '.gitignore',
    'a.b.c.tar.gz',
    'CONTEXTO.md',
    'AUXILIAR.md',
    'COM10.md',
    'archivo con espacios .no-final.md',
  ];
  for (const nombre of aceptados) {
    assert.ok(isPortableSegment(nombre), `debería aceptar ${JSON.stringify(nombre)}`);
  }
});

test('un emoji no vuelve no portable a un nombre — el repertorio no se restringe', () => {
  // Restringir a un rango latino habría hecho que un solo emoji dentro de
  // `node_modules` abortara el archivado entero, porque AC-21 obliga a recorrer
  // los directorios omitidos.
  assert.ok(isPortableSegment(`chunk-${String.fromCodePoint(0x1f4e6)}.js`));
});

// ── Cada clase de nombre no portable (AC-7) ───────────────────────────────────

test('rechaza segmentos vacíos y relativos', () => {
  rejects(() => assertPortableSegment(''), 'EMPTY_SEGMENT');
  rejects(() => assertPortableSegment('.'), 'DOT_SEGMENT');
  rejects(() => assertPortableSegment('..'), 'DOT_SEGMENT');
  rejects(() => assertPortableSegment(null), 'INVALID_TYPE');
});

test('rechaza separadores de ruta dentro de un nombre', () => {
  rejects(() => assertPortableSegment('a/b'), 'PATH_SEPARATOR');
  rejects(() => assertPortableSegment('a\\b'), 'PATH_SEPARATOR');
});

test('rechaza caracteres de control, incluido DEL', () => {
  rejects(() => assertPortableSegment(`a${NUL}b`), 'CONTROL_CHARACTER');
  rejects(() => assertPortableSegment(`a${LF}b`), 'CONTROL_CHARACTER');
  rejects(() => assertPortableSegment(`a${DEL}b`), 'CONTROL_CHARACTER');
});

test('rechaza los caracteres reservados de Windows', () => {
  for (const caracter of [...':*?"<>|']) {
    rejects(() => assertPortableSegment(`a${caracter}b.md`), 'RESERVED_CHARACTER');
  }
});

test('rechaza espacio o punto final', () => {
  rejects(() => assertPortableSegment('informe.md '), 'TRAILING_SPACE_OR_DOT');
  rejects(() => assertPortableSegment('informe.'), 'TRAILING_SPACE_OR_DOT');
  rejects(() => assertPortableSegment(' '), 'TRAILING_SPACE_OR_DOT');
  // Un espacio inicial o interno sí es representable.
  assert.ok(isPortableSegment(' informe.md'));
});

test('rechaza los nombres reservados de Windows con cualquier extensión y en cualquier caja', () => {
  for (const nombre of ['CON', 'con', 'Con.md', 'PRN.txt', 'AUX', 'NUL.json', 'COM1', 'com9.tar.gz', 'LPT3.md']) {
    rejects(() => assertPortableSegment(nombre), 'RESERVED_NAME');
  }
  // Solo el tramo anterior al primer punto cuenta como nombre reservado.
  assert.ok(isPortableSegment('mi-CON.md'));
  assert.ok(isPortableSegment('informe.con'));
});

test('rechaza surrogates sueltos', () => {
  rejects(() => assertPortableSegment(String.fromCharCode(0xd83d)), 'LONE_SURROGATE');
  rejects(() => assertPortableSegment(`a${String.fromCharCode(0xdc00)}.md`), 'LONE_SURROGATE');
});

test('`inspectSegment` informa sin lanzar', () => {
  assert.deepEqual(inspectSegment('plan.md'), { ok: true, code: null, detail: null });
  assert.equal(inspectSegment('a|b').code, 'RESERVED_CHARACTER');
  assert.equal(inspectSegment('a|b').detail, '|');
});

// ── Clave de colisión portable (AC-7b) ────────────────────────────────────────

test('la clave de colisión une NFC y NFD del mismo nombre lógico', () => {
  // Coexisten en Linux; en un filesystem con equivalencia canónica son el mismo
  // archivo, y la revisión ya no se podría restaurar fielmente.
  assert.notEqual(E_ACUTE_NFC, E_ACUTE_NFD, 'son bytes distintos — eso lo dice AC-5');
  assert.equal(collisionKey(`caf${E_ACUTE_NFC}.md`), collisionKey(`caf${E_ACUTE_NFD}.md`));
});

test('la clave de colisión une mayúscula y minúscula, ASCII y no ASCII', () => {
  assert.equal(collisionKey('Plan.md'), collisionKey('plan.md'));
  assert.equal(collisionKey(`${E_ACUTE_UPPER}.md`), collisionKey(`${E_ACUTE_NFC}.md`));
  assert.equal(collisionKey(`${E_ACUTE_UPPER}.md`), collisionKey(`${E_ACUTE_NFD}.md`));
});

test('la clave de colisión no depende del locale del proceso', () => {
  // `toLocaleLowerCase('tr')` convierte 'I' en 'ı' y dos máquinas discreparían
  // por configuración regional, no por versión de tabla.
  assert.equal(collisionKey('INDEX.md'), 'index.md');
  assert.notEqual('INDEX.md'.toLocaleLowerCase('tr'), 'index.md');
});

test('rechaza hermanos que colisionan: el par NFC/NFD y el par de cajas', () => {
  rejects(
    () => assertNoSiblingCollision([`caf${E_ACUTE_NFC}.md`, `caf${E_ACUTE_NFD}.md`]),
    'SIBLING_COLLISION',
  );
  rejects(() => assertNoSiblingCollision([`${E_ACUTE_UPPER}.md`, `${E_ACUTE_NFC}.md`]), 'SIBLING_COLLISION');
  rejects(() => assertNoSiblingCollision(['Plan.md', 'plan.md']), 'SIBLING_COLLISION');
});

test('el error de colisión nombra a los dos hermanos', () => {
  assert.throws(
    () => assertNoSiblingCollision(['a.md', 'b.md', 'B.md']),
    (err) => {
      assert.deepEqual(err.detail, ['b.md', 'B.md']);
      return true;
    },
  );
});

test('hermanos distintos no colisionan', () => {
  const nombres = ['plan.md', 'spec.md', 'tasks.md', `caf${E_ACUTE_NFC}.md`, '\u4f60\u597d.md'];
  assert.deepEqual(assertNoSiblingCollision(nombres), nombres);
});

// ── Rutas: traversal y absolutas (AC-3, AC-39) ────────────────────────────────

test('acepta rutas canónicas relativas con separador POSIX', () => {
  assert.deepEqual(assertCanonicalPath('plan.md'), ['plan.md']);
  assert.deepEqual(assertCanonicalPath('input/task.md'), ['input', 'task.md']);
  assert.deepEqual(assertCanonicalPath('a/b/c/d.md'), ['a', 'b', 'c', 'd.md']);
});

test('rechaza traversal en cualquier posición', () => {
  rejects(() => assertCanonicalPath('../fuga.md'), 'DOT_SEGMENT');
  rejects(() => assertCanonicalPath('a/../../fuga.md'), 'DOT_SEGMENT');
  rejects(() => assertCanonicalPath('a/./b.md'), 'DOT_SEGMENT');
  rejects(() => assertCanonicalPath('a/b/..'), 'DOT_SEGMENT');
});

test('rechaza rutas absolutas en sus tres formas', () => {
  rejects(() => assertCanonicalPath('/etc/passwd'), 'ABSOLUTE_PATH');
  rejects(() => assertCanonicalPath('C:/Windows/system.ini'), 'ABSOLUTE_PATH');
  rejects(() => assertCanonicalPath('\\\\servidor\\share\\a.md'), 'ABSOLUTE_PATH');
});

test('rechaza segmentos vacíos por barras dobles o finales', () => {
  rejects(() => assertCanonicalPath('a//b.md'), 'EMPTY_SEGMENT');
  rejects(() => assertCanonicalPath('a/b/'), 'EMPTY_SEGMENT');
  rejects(() => assertCanonicalPath(''), 'EMPTY_PATH');
});

test('rechaza un separador de Windows en medio de la ruta', () => {
  // No se divide por `\`: el segmento entero lo tiene adentro y cae por eso.
  rejects(() => assertCanonicalPath('a\\b.md'), 'PATH_SEPARATOR');
});

test('`isCanonicalPath` no lanza', () => {
  assert.ok(isCanonicalPath('input/task.md'));
  assert.ok(!isCanonicalPath('../fuga.md'));
  assert.ok(!isCanonicalPath('/absoluta'));
});

test('`toCanonicalPath` valida antes de unir', () => {
  assert.equal(toCanonicalPath(['input', 'task.md']), 'input/task.md');
  rejects(() => toCanonicalPath(['input', '..']), 'DOT_SEGMENT');
  rejects(() => toCanonicalPath(['input', 'a|b']), 'RESERVED_CHARACTER');
});
