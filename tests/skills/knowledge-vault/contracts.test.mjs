/**
 * La tabla de verbos, estados y códigos de salida.
 *
 * Es una tabla y no una función porque su valor está en ser **estable**: un
 * consumidor que ramifica sobre el código de salida se rompe si un estado cambia
 * de familia. Lo que se verifica acá es que la tabla sea consistente consigo
 * misma —ningún estado en dos códigos, ningún verbo sin estados— y que los seis
 * verbos sean exactamente los que el vault ofrece.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  FLAGS_BY_VERB, STATUSES, SUCCESS_STATUSES, VERBS, exitCodeFor, isStatus, statesForVerb,
} from '../../../skills/knowledge-vault/scripts/lib/contracts.mjs';

test('[AC-8] los verbos son exactamente seis, y ninguno de los retirados sobrevive', () => {
  assert.deepEqual([...VERBS], ['archive', 'migrate', 'index', 'config', 'retire', 'identity']);
  for (const retirado of ['restore', 'doctor', 'inventory']) {
    assert.ok(!VERBS.includes(retirado), retirado);
  }
});

test('[AC-8] el quinto verbo declara sus cuatro estados sin renumerar ningún código', () => {
  assert.deepEqual(
    [...statesForVerb('retire')],
    ['DRY_RUN', 'BATCH_OK', 'BATCH_PARTIAL', 'BATCH_FAILED'],
  );
  // Los códigos que ya existían conservan su número y su significado: el verbo
  // nuevo reusa la tabla en vez de ampliarla.
  assert.equal(exitCodeFor('DRY_RUN'), 0);
  assert.equal(exitCodeFor('BATCH_OK'), 0);
  assert.equal(exitCodeFor('BATCH_PARTIAL'), 1);
  assert.equal(exitCodeFor('BATCH_FAILED'), 1);
  assert.equal(exitCodeFor('VERIFY_FAILED'), 9, 'un 9 que ya significaba algo cambió de sentido');
  assert.equal(exitCodeFor('PRECONDITION_NOT_MET'), 4);
});

test('cada verbo declara sus estados, y todos existen en la tabla', () => {
  for (const verbo of VERBS) {
    const estados = statesForVerb(verbo);
    assert.ok(estados.length > 0, verbo);
    for (const e of estados) assert.ok(isStatus(e), `${verbo} declara ${e}, que no está en la tabla`);
  }
});

test('ningún estado aparece con dos códigos de salida', () => {
  const vistos = new Map();
  for (const s of STATUSES) {
    assert.ok(!vistos.has(s), `${s} duplicado`);
    vistos.set(s, exitCodeFor(s));
  }
});

test('el éxito es cero y sólo cero', () => {
  for (const s of STATUSES) {
    assert.equal(exitCodeFor(s) === 0, SUCCESS_STATUSES.has(s), s);
  }
  for (const s of ['ARCHIVED', 'ALREADY_ARCHIVED', 'INDEX_OK', 'BATCH_OK', 'DRY_RUN']) {
    assert.equal(exitCodeFor(s), 0, s);
  }
});

test('los estados de lote reportan fallo con código distinto de cero', () => {
  // Migrar 49 de 50 no puede salir 0: ningún criterio distinguiría ese vault de
  // uno completo.
  assert.equal(exitCodeFor('BATCH_PARTIAL'), 1);
  assert.equal(exitCodeFor('BATCH_FAILED'), 1);
});

test('un estado desconocido no se inventa un código', () => {
  assert.equal(isStatus('NO_EXISTE'), false);
  assert.throws(() => exitCodeFor('NO_EXISTE'), /NO_EXISTE/);
});

test('[AC-13] la identidad ambigua es una precondición, no un error interno', () => {
  // Sin esto, `retire` sobre un repositorio sin identidad declarada salía
  // `INTERNAL_ERROR`: le decía a quien automatiza que encontró un bug en vez de
  // que le falta declarar la identidad. Medido antes de arreglarlo.
  assert.ok(isStatus('AMBIGUOUS_IDENTITY'));
  assert.equal(exitCodeFor('AMBIGUOUS_IDENTITY'), exitCodeFor('PRECONDITION_NOT_MET'));
  assert.notEqual(exitCodeFor('AMBIGUOUS_IDENTITY'), exitCodeFor('INTERNAL_ERROR'));
  // Los códigos vacantes —6 y 7— pertenecieron a verbos retirados y siguen
  // vacantes: darles un sentido nuevo se lo reescribiría a un guion viejo.
  for (const s of STATUSES) assert.ok(![6, 7].includes(exitCodeFor(s)), `${s} ocupó un código vacante`);
});

test('[AC-13] el sexto verbo declara sus estados y ninguno es nuevo en la familia del éxito', () => {
  assert.deepEqual(
    [...statesForVerb('identity')],
    ['IDENTITY_PROPOSED', 'IDENTITY_DECLARED', 'IDENTITY_ALREADY_DECLARED'],
  );
  for (const e of statesForVerb('identity')) assert.equal(exitCodeFor(e), 0);
});

test('[AC-8] la tabla de banderas cubre exactamente los seis verbos', () => {
  assert.deepEqual(Object.keys(FLAGS_BY_VERB).sort(), [...VERBS].sort());
});

// Sobre un objeto normal —incluso congelado— `fila['constructor']` devuelve una
// función: con acceso directo, `archive --constructor x` se aceptaría y se
// descartaría en silencio, que es el defecto que la validación existe para cerrar.
test('[AC-8] ninguna fila hereda banderas de la cadena de prototipos', () => {
  for (const verbo of VERBS) {
    for (const heredada of ['constructor', 'toString', 'valueOf', 'hasOwnProperty']) {
      assert.equal(FLAGS_BY_VERB[verbo][heredada], undefined, `${verbo}.${heredada}`);
      assert.equal(Object.hasOwn(FLAGS_BY_VERB[verbo], heredada), false, `${verbo}.${heredada}`);
    }
  }
});

test('[AC-8] cada bandera declara su forma, y solo esas dos', () => {
  for (const verbo of VERBS) {
    for (const [bandera, forma] of Object.entries(FLAGS_BY_VERB[verbo])) {
      assert.ok(['valor', 'booleana'].includes(forma), `${verbo} --${bandera}: ${forma}`);
    }
  }
});
