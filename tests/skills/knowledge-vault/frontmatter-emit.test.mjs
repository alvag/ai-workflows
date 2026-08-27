/**
 * El emisor del frontmatter del nodo.
 *
 * El parser que se conserva **no es YAML y no tiene escapes**: `cleanValue`
 * recorta, descarta un comentario `#` precedido de espacio y saca comillas
 * envolventes, sin ninguna secuencia que revierta esas tres cosas.
 *
 * De ahí la regla del emisor: lo que no puede volver **idéntico** no se escapa,
 * se **rechaza**. Escaparlo produciría un round-trip falso —el archivo se vería
 * bien y el valor leído sería otro—, y este frontmatter es la única sede del
 * resumen y del estado observado, que es justo lo que no puede mutar en silencio.
 *
 * El numeral **sí** se representa, entrecomillando: el parser mira las comillas
 * antes de descartar el comentario, así que un valor citado vuelve literal. El
 * delimitador se elige según el contenido, y la única combinación que queda sin
 * delimitador seguro se rechaza. Las tres clases irrepresentables que quedan
 * están medidas contra el parser, no supuestas.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { emitFrontmatter } from '../../../skills/knowledge-vault/scripts/lib/frontmatter-emit.mjs';
import { parseFrontmatter } from '../../../skills/knowledge-vault/scripts/lib/frontmatter.mjs';

const OCHO = {
  type: 'sdd-flow',
  title: 'Vault de conocimiento consultable',
  project: 'ai-workflows',
  flow: 'vault-consultable',
  branch: 'feature/vault-consultable',
  date: '2026-08-25',
  provenance: '.plans/archived/vault-consultable',
  state: 'implementing',
};

/** Emite y vuelve a leer: la única forma de afirmar round-trip. */
function idaYVuelta(campos) {
  const leido = parseFrontmatter(emitFrontmatter(campos));
  assert.equal(leido.ok, true, 'el bloque emitido no se pudo parsear');
  return leido;
}

test('[AC-9] los ocho campos vuelven idénticos', () => {
  const leido = idaYVuelta(OCHO);
  for (const [k, v] of Object.entries(OCHO)) assert.equal(leido.keys.get(k), v, k);
  assert.equal(leido.duplicated.size, 0);
});

test('[AC-9] el bloque abre y cierra con la marca, y termina en salto', () => {
  const texto = emitFrontmatter(OCHO);
  const lineas = texto.split('\n');
  assert.equal(lineas[0], '---');
  assert.equal(lineas.at(-2), '---');
  assert.ok(texto.endsWith('\n'));
});

test('[AC-9] los dos puntos y las comillas interiores sí vuelven idénticos', () => {
  // Medido: 3 de los 45 títulos reales llevan `:`, y ninguno lleva `#`.
  const campos = { ...OCHO, title: 'Spec: el vault, con "comillas" al medio' };
  assert.equal(idaYVuelta(campos).keys.get('title'), campos.title);
});

test('[AC-9] un valor con salto de línea se rechaza en vez de escaparse', () => {
  assert.throws(() => emitFrontmatter({ ...OCHO, title: 'dos\nlineas' }), /control/i);
});

test('se rechazan las tres clases que el parser no puede devolver', () => {
  // Eran cuatro: las dos del numeral salieron cuando el emisor pasó a
  // entrecomillar. Las tres que quedan no tienen delimitador que las salve.
  const casos = [
    ['"envuelto"', /comillas/i],
    ['  con espacios  ', /espacio/i],
    ['dos\nlineas', /control/i],
  ];
  for (const [valor, patron] of casos) {
    assert.throws(() => emitFrontmatter({ ...OCHO, title: valor }), patron, JSON.stringify(valor));
  }
});

test('un título con numeral vuelve idéntico', () => {
  // Derivado del encabezado del documento: quien archiva no lo elige.
  for (const title of ['Ronda de feedback del PR #1264', '#empieza', 'con # numeral']) {
    assert.equal(idaYVuelta({ ...OCHO, title }).keys.get('title'), title, title);
  }
});

test('un numeral con comillas dobles interiores vuelve idéntico', () => {
  const title = 'Spec: con "comillas" y # numeral';
  assert.equal(idaYVuelta({ ...OCHO, title }).keys.get('title'), title);
  // Sin comilla simple adentro, el delimitador es la simple: YAML no interpreta
  // nada ahí, así que la línea vale para cualquier lector, no solo para este.
  assert.match(emitFrontmatter({ ...OCHO, title }), /^title: '.*'$/m);
});

test('un numeral con comillas simples interiores vuelve idéntico', () => {
  const title = "lo que dice el # y el it's del medio";
  assert.equal(idaYVuelta({ ...OCHO, title }).keys.get('title'), title);
  assert.match(emitFrontmatter({ ...OCHO, title }), /^title: ".*"$/m);
});

test('sin delimitador seguro el valor se rechaza', () => {
  // Con simple adentro la simple no sirve; la doble tampoco si hay barra
  // inversa —YAML la leería como escape— o comilla doble.
  for (const title of ["it's # C:\\ruta", 'it\'s # con "cita"']) {
    assert.throws(() => emitFrontmatter({ ...OCHO, title }), /delimitador/i, title);
  }
});

test('[AC-9] una clave que el parser no reconoce se rechaza', () => {
  for (const clave of ['con espacio', 'con.punto', '', 'con:dospuntos']) {
    assert.throws(() => emitFrontmatter({ [clave]: 'x' }), /clave/i, JSON.stringify(clave));
  }
});

test('[AC-9] un carácter de control se rechaza aunque no sea salto de línea', () => {
  for (const codigo of [0x00, 0x01, 0x09, 0x0d, 0x7f]) {
    const valor = `a${String.fromCharCode(codigo)}b`;
    assert.throws(() => emitFrontmatter({ ...OCHO, title: valor }), /control/i, `U+${codigo}`);
  }
});

test('[AC-9] un valor vacío es válido y vuelve vacío', () => {
  assert.equal(idaYVuelta({ ...OCHO, branch: '' }).keys.get('branch'), '');
});

test('[AC-9] el literal desconocido no recibe trato especial', () => {
  const campos = { ...OCHO, branch: 'desconocido', date: 'desconocido' };
  const leido = idaYVuelta(campos);
  assert.equal(leido.keys.get('branch'), 'desconocido');
  assert.equal(leido.keys.get('date'), 'desconocido');
});
