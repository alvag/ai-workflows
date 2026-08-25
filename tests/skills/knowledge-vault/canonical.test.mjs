/**
 * T2 — serialización canónica y digests (AC-5, AC-6, AC-8).
 *
 * Módulo puro: no necesita sandbox. Todo se prueba con bytes.
 *
 * Los caracteres de control se construyen con `String.fromCodePoint`, nunca
 * escritos crudos: son invisibles en el diff y uno de ellos ya rompió este
 * archivo una vez.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

import {
  CanonicalError,
  canonicalBytes,
  canonicalizeDocument,
  compareCodePoints,
  digestDocument,
  digestOf,
  isKnownSchema,
  knownSchemas,
  parseDocument,
  sha256Hex,
  sortFilesByPath,
  toCodePoints,
} from '../../../skills/knowledge-vault/scripts/lib/canonical.mjs';
import { GOLDEN } from './fixtures/canonical-golden.mjs';

const NUL = String.fromCodePoint(0x00);
const LF = String.fromCodePoint(0x0a);
const ESC = String.fromCodePoint(0x1b);
const US = String.fromCodePoint(0x1f);
const DEL = String.fromCodePoint(0x7f);
const BOM = String.fromCodePoint(0xfeff);
const FULLWIDTH_A = String.fromCodePoint(0xff21);
const EMOJI = String.fromCodePoint(0x1f600);

function rejects(fn, code) {
  assert.throws(fn, (err) => {
    assert.ok(err instanceof CanonicalError, `se esperaba CanonicalError, llego ${err?.name}`);
    assert.equal(err.code, code);
    return true;
  });
}

const utf8 = (value) => canonicalBytes(value).toString('utf8');

// ── Golden fixtures (AC-8) ────────────────────────────────────────────────────

for (const fixture of GOLDEN) {
  test(`golden ${fixture.name}: bytes exactos — ${fixture.why}`, () => {
    assert.equal(utf8(fixture.value), fixture.canonical);
  });

  test(`golden ${fixture.name}: el digest se toma sobre esos bytes y ningún otro`, () => {
    // El esperado sale del fixture, no de `canonicalBytes`: si el serializador
    // cambiara, esto falla aunque el digest siga siendo coherente consigo mismo.
    const esperado = createHash('sha256').update(Buffer.from(fixture.canonical, 'utf8')).digest('hex');
    assert.equal(digestOf(fixture.value), esperado);
    assert.equal(digestOf(fixture.value), fixture.digest, 'digest congelado con shasum -a 256');
  });

  test(`golden ${fixture.name}: sin BOM y sin salto final`, () => {
    const bytes = canonicalBytes(fixture.value);
    assert.notEqual(bytes[0], 0xef);
    assert.notEqual(bytes.at(-1), 0x0a);
  });
}

test('el par NFC/NFD produce digests distintos, cada uno estable (AC-5, AC-8)', () => {
  const nfc = GOLDEN.find((f) => f.name === 'nfc');
  const nfd = GOLDEN.find((f) => f.name === 'nfd');

  // Sanidad del propio fixture: si alguien normalizara el archivo al guardarlo,
  // esto lo delata antes de que el test de digests quede verde por la razón
  // equivocada — dos copias del mismo caso.
  assert.notEqual(nfc.value.files[0].path, nfd.value.files[0].path);
  assert.equal(nfc.value.files[0].path.length, 7, 'caf + U+00E9 + .md');
  assert.equal(nfd.value.files[0].path.length, 8, 'cafe + U+0301 + .md');

  assert.notEqual(digestOf(nfc.value), digestOf(nfd.value));
  assert.equal(digestOf(nfc.value), digestOf(structuredClone(nfc.value)));
  assert.equal(digestOf(nfd.value), digestOf(structuredClone(nfd.value)));
});

// ── Orden de claves ───────────────────────────────────────────────────────────

test('el orden de inserción de las claves no cambia los bytes', () => {
  const directo = {
    schema: 'kv-manifest/1',
    source_id: 'a-0123456789ab/b',
    repo_identity: 'manual:x',
    files: [],
  };
  const invertido = {
    files: [],
    repo_identity: 'manual:x',
    source_id: 'a-0123456789ab/b',
    schema: 'kv-manifest/1',
  };

  assert.equal(utf8(directo), utf8(invertido));
  assert.equal(
    utf8(directo),
    '{"files":[],"repo_identity":"manual:x","schema":"kv-manifest/1","source_id":"a-0123456789ab/b"}',
  );
});

test('ordena por punto de código, no por unidad UTF-16', () => {
  // U+FF21 (65313) va antes que U+1F600 (128512) por punto de código. Por unidad
  // UTF-16, la surrogate alta 0xD83D (55357) pondría el emoji primero.
  assert.equal(compareCodePoints(FULLWIDTH_A, EMOJI), -1);
  assert.ok(EMOJI < FULLWIDTH_A, 'la comparación nativa de JS los invierte — por eso no se usa');

  assert.equal(utf8({ [EMOJI]: 1, [FULLWIDTH_A]: 0 }), `{"${FULLWIDTH_A}":0,"${EMOJI}":1}`);
});

test('el orden de claves no depende del locale', () => {
  // `localeCompare` pone 'a' antes que 'B'; el orden por punto de código, al revés.
  assert.equal(compareCodePoints('B', 'a'), -1);
  assert.equal(utf8({ a: 0, B: 1 }), '{"B":1,"a":0}');
});

// ── Escapes ───────────────────────────────────────────────────────────────────

test('escapa solo la comilla doble, la barra invertida y C0', () => {
  assert.equal(utf8('a"b'), '"a\\"b"');
  assert.equal(utf8('a\\b'), '"a\\\\b"');
  assert.equal(utf8(NUL + US), '"\\u0000\\u001f"');
  assert.equal(utf8(LF), '"\\u000a"');
  assert.equal(utf8(ESC), '"\\u001b"', 'el hex va en minúscula');
});

test('deja literales la barra, DEL y el Unicode imprimible', () => {
  assert.equal(utf8('a/b'), '"a/b"', 'la barra no se escapa');
  assert.equal(utf8(DEL), `"${DEL}"`, 'U+007F no es C0');
  assert.equal(utf8(FULLWIDTH_A + EMOJI), `"${FULLWIDTH_A}${EMOJI}"`);
});

test('rechaza surrogates sueltos en vez de colapsarlos a U+FFFD', () => {
  const solitario = String.fromCharCode(0xd83d);
  // La prueba de que el rechazo hace falta: el encoder nativo lo destruiría.
  assert.equal(Buffer.from(solitario, 'utf8').toString('utf8'), String.fromCodePoint(0xfffd));

  rejects(() => canonicalBytes(solitario), 'LONE_SURROGATE');
  rejects(() => canonicalBytes({ [solitario]: 1 }), 'LONE_SURROGATE');
  rejects(() => toCodePoints(`a${String.fromCharCode(0xdc00)}`), 'LONE_SURROGATE');

  // El par bien formado sí pasa, y cuenta como un solo punto de código.
  assert.equal(toCodePoints(EMOJI).length, 1);
});

// ── Números ───────────────────────────────────────────────────────────────────

test('acepta enteros no negativos seguros en decimal ASCII', () => {
  assert.equal(utf8(0), '0');
  assert.equal(utf8(9007199254740991), '9007199254740991');
  assert.equal(utf8(1e3), '1000', 'sin notación exponencial');
});

test('rechaza -0, negativos, fracciones y todo lo que pase MAX_SAFE_INTEGER', () => {
  rejects(() => canonicalBytes(-0), 'UNSUPPORTED_NUMBER');
  rejects(() => canonicalBytes(-1), 'UNSUPPORTED_NUMBER');
  rejects(() => canonicalBytes(1.5), 'UNSUPPORTED_NUMBER');
  rejects(() => canonicalBytes(9007199254740992), 'UNSUPPORTED_NUMBER');
  rejects(() => canonicalBytes(Number.NaN), 'UNSUPPORTED_NUMBER');
  rejects(() => canonicalBytes(Number.POSITIVE_INFINITY), 'UNSUPPORTED_NUMBER');
});

// ── Tipos ─────────────────────────────────────────────────────────────────────

test('rechaza tipos no canonizables y valores ausentes', () => {
  rejects(() => canonicalBytes(undefined), 'UNSUPPORTED_TYPE');
  rejects(() => canonicalBytes(() => {}), 'UNSUPPORTED_TYPE');
  rejects(() => canonicalBytes(10n), 'UNSUPPORTED_TYPE');
  rejects(() => canonicalBytes(new Date(0)), 'UNSUPPORTED_TYPE');
  rejects(() => canonicalBytes(new Map()), 'UNSUPPORTED_TYPE');
  // Un `undefined` como valor se descartaría en silencio y movería el digest.
  rejects(() => canonicalBytes({ a: undefined }), 'UNSUPPORTED_TYPE');
  rejects(() => canonicalBytes({ [Symbol('x')]: 1, a: 1 }), 'UNSUPPORTED_TYPE');
});

test('rechaza ciclos', () => {
  const objeto = { a: 1 };
  objeto.self = objeto;
  rejects(() => canonicalBytes(objeto), 'CYCLE');

  const lista = [1];
  lista.push(lista);
  rejects(() => canonicalBytes(lista), 'CYCLE');
});

test('los objetos vacíos y los null se serializan explícitos', () => {
  assert.equal(utf8({}), '{}');
  assert.equal(utf8([]), '[]');
  assert.equal(utf8({ a: null }), '{"a":null}');
  assert.equal(utf8(true), 'true');
  assert.equal(utf8(false), 'false');
  assert.equal(utf8(null), 'null');
});

// ── Schema versionado (AC-6) ──────────────────────────────────────────────────

test('los schemas canónicos registrados son exactamente estos', () => {
  assert.deepEqual(knownSchemas(), [
    'kv-manifest/1',
    'kv-source-inventory/1',
    'kv-attempt/1',
    'kv-selection/1',
    'kv-source-inventory/2',
    'kv-attempt/2',
    'kv-retirement/2',
    'kv-retirement-manifest/1',
  ]);
  assert.ok(isKnownSchema('kv-manifest/1'));
  // `kv-manifest/2` sigue sin existir: subir de versión es un acto deliberado,
  // no algo que se acepte por parecerse a uno conocido.
  assert.ok(!isKnownSchema('kv-manifest/2'));
  assert.ok(!isKnownSchema('kv-selection/2'));
});

test('un documento con schema desconocido, ausente o de otra versión se rechaza', () => {
  rejects(() => canonicalizeDocument({ schema: 'kv-manifest/2', files: [] }), 'UNKNOWN_SCHEMA');
  rejects(() => canonicalizeDocument({ files: [] }), 'UNKNOWN_SCHEMA');
  rejects(() => canonicalizeDocument({ schema: 7, files: [] }), 'UNKNOWN_SCHEMA');
  rejects(() => canonicalizeDocument('no soy un objeto'), 'UNSUPPORTED_TYPE');
});

test('cada campo nuevo entra al digest: cambiarlo lo mueve', () => {
  // AC-25 dice que `attempt_id` es el digest del receipt canónico COMPLETO. Los
  // golden prueban que la forma es la esperada; esto prueba lo otro, que es lo que
  // realmente importa: que los campos nuevos no estén ahí de adorno. Sin este test,
  // una implementación podría escribirlos en el documento y excluirlos del cálculo
  // —dos intentos materialmente distintos colisionarían— y todo seguiría verde.
  const base = GOLDEN.find((f) => f.name === 'intento-v2').value;
  const original = digestOf(base);

  const mover = (mutar) => {
    const copia = structuredClone(base);
    mutar(copia);
    return digestOf(copia);
  };

  assert.notEqual(mover((d) => { d.selection_digest = 'f'.repeat(64); }), original, 'selection_digest');
  assert.notEqual(mover((d) => { d.completeness.provenance = 'asserted'; }), original, 'provenance');
  assert.notEqual(mover((d) => { d.completeness.predicate = null; }), original, 'predicate');
  assert.notEqual(mover((d) => { d.inventory[0].reason = 'regla 9'; }), original, 'reason del inventario');
  assert.notEqual(mover((d) => { d.inventory[0].disposition = 'omitted'; }), original, 'disposition');

  // Y el inverso: una copia sin mutar da el mismo digest. Sin esto, un `notEqual`
  // pasaría también si el digest fuera aleatorio.
  assert.equal(mover(() => {}), original, 'el digest es determinístico');
});

test('un directorio vacío mueve el `source_fingerprint`', () => {
  // Es la razón de que `directories` entre al fingerprint: si no entrara, un
  // directorio vacío creado entre el escaneo y el retiro no movería el digest y se
  // destruiría sin aparecer en ningún receipt.
  const base = GOLDEN.find((f) => f.name === 'inventario-v2-con-directorio-vacio').value;
  const sinDirectorio = structuredClone(base);
  sinDirectorio.directories = [];

  assert.notEqual(digestOf(sinDirectorio), digestOf(base));
});

test('`kv-selection/1` verifica el orden de `entries`', () => {
  const seleccion = (entries) => ({ schema: 'kv-selection/1', source_fingerprint: 'a'.repeat(64), entries });
  const inc = (path) => ({ path, decision: 'include', reason: null });

  canonicalizeDocument(seleccion([inc('a.md'), inc('b.md')]));

  // Su digest entra al `attempt_id`: sin verificar el orden, la misma selección
  // emitida en otro orden abriría un intento distinto sobre el mismo trabajo.
  rejects(() => canonicalizeDocument(seleccion([inc('b.md'), inc('a.md')])), 'UNORDERED_FILES');
});

test('`kv-source-inventory/2` verifica el orden de `directories`, no solo de `files`', () => {
  const inventario = (directories) => ({
    schema: 'kv-source-inventory/2',
    files: [],
    directories,
  });

  // Ordenado: pasa.
  canonicalizeDocument(inventario([{ path: 'a', type: 'directory' }, { path: 'b', type: 'directory' }]));

  // Desordenado: rechaza. El array nuevo entra al `source_fingerprint`, así que
  // si no se verificara su orden dos inventarios del mismo árbol darían digests
  // distintos según en qué orden los emitió el escaneo.
  rejects(
    () => canonicalizeDocument(inventario([{ path: 'b', type: 'directory' }, { path: 'a', type: 'directory' }])),
    'UNORDERED_FILES',
  );
});

test('`expectSchema` acepta una lista corta, no cualquier schema', () => {
  const bytes = (schema) => new TextEncoder().encode(JSON.stringify({ schema, inventory: [] }));
  const dobles = ['kv-attempt/2', 'kv-attempt/1'];

  // Las dos versiones del lector doble entran.
  assert.equal(parseDocument(bytes('kv-attempt/1'), { expectSchema: dobles }).schema, 'kv-attempt/1');
  assert.equal(parseDocument(bytes('kv-attempt/2'), { expectSchema: dobles }).schema, 'kv-attempt/2');

  // Y un tercero conocido NO: aceptar dos versiones no es aceptar cualquiera.
  // Pasar `null` para leer v1 y v2 abriría también los schemas ajenos.
  rejects(() => parseDocument(bytes('kv-selection/1'), { expectSchema: dobles }), 'SCHEMA_MISMATCH');

  // La forma de string suelto sigue funcionando igual que antes.
  rejects(() => parseDocument(bytes('kv-attempt/2'), { expectSchema: 'kv-attempt/1' }), 'SCHEMA_MISMATCH');
});

test('parseDocument rechaza schema desconocido en vez de interpretarlo (AC-6)', () => {
  const conocido = Buffer.from('{"files":[],"schema":"kv-source-inventory/1"}', 'utf8');
  assert.equal(parseDocument(conocido).schema, 'kv-source-inventory/1');

  rejects(() => parseDocument(Buffer.from('{"schema":"kv-manifest/9"}', 'utf8')), 'UNKNOWN_SCHEMA');
  rejects(() => parseDocument(Buffer.from('{"files":[]}', 'utf8')), 'UNKNOWN_SCHEMA');
  rejects(() => parseDocument(conocido, { expectSchema: 'kv-manifest/1' }), 'SCHEMA_MISMATCH');
});

test('parseDocument rechaza bytes que no son UTF-8, BOM y JSON roto', () => {
  rejects(() => parseDocument(Buffer.from([0xff, 0xfe, 0x00])), 'INVALID_ENCODING');
  rejects(
    () => parseDocument(Buffer.from(`${BOM}{"schema":"kv-manifest/1"}`, 'utf8')),
    'INVALID_ENCODING',
  );
  rejects(() => parseDocument(Buffer.from('{roto', 'utf8')), 'INVALID_JSON');
  rejects(() => parseDocument(Buffer.from('[]', 'utf8')), 'UNSUPPORTED_TYPE');
});

test('el ida y vuelta de un documento conserva los bytes', () => {
  const documento = GOLDEN[0].value;
  const bytes = canonicalizeDocument(documento);
  assert.equal(canonicalizeDocument(parseDocument(bytes)).toString('utf8'), bytes.toString('utf8'));
  assert.equal(digestDocument(documento), sha256Hex(bytes));
});

// ── Orden de las listas de archivos ───────────────────────────────────────────

test('verifica el orden de las listas de archivos en vez de arreglarlo', () => {
  const desordenado = {
    schema: 'kv-source-inventory/1',
    files: [
      { path: 'b.md', type: 'file', size: 0, sha256: 'a'.repeat(64) },
      { path: 'a.md', type: 'file', size: 0, sha256: 'b'.repeat(64) },
    ],
  };
  // Reordenar en silencio dejaría pasar un inventario mal construido con un
  // digest válido, y el bug viviría hasta que alguien comparara dos árboles.
  rejects(() => canonicalizeDocument(desordenado), 'UNORDERED_FILES');

  desordenado.files = sortFilesByPath(desordenado.files);
  assert.deepEqual(
    desordenado.files.map((f) => f.path),
    ['a.md', 'b.md'],
  );
  assert.ok(canonicalizeDocument(desordenado).length > 0);
});

test('rechaza paths repetidos, al ordenar y al canonicalizar', () => {
  const entrada = { path: 'a.md', type: 'file', size: 0, sha256: 'a'.repeat(64) };
  rejects(() => sortFilesByPath([entrada, { ...entrada }]), 'DUPLICATE_PATH');
  rejects(
    () => canonicalizeDocument({ schema: 'kv-source-inventory/1', files: [entrada, { ...entrada }] }),
    'DUPLICATE_PATH',
  );
});

test('el orden de las listas usa el mismo comparador por punto de código', () => {
  const files = [
    { path: `${EMOJI}.md`, type: 'file', size: 0, sha256: 'a'.repeat(64) },
    { path: `${FULLWIDTH_A}.md`, type: 'file', size: 0, sha256: 'b'.repeat(64) },
  ];
  assert.deepEqual(
    sortFilesByPath(files).map((f) => f.path),
    [`${FULLWIDTH_A}.md`, `${EMOJI}.md`],
  );
});
