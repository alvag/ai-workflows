/**
 * Exclusión por flujo, y nada más.
 *
 * El lock que había en el árbol de origen era transaccional: archivo en disco,
 * dueño, expiración, journal y recuperación. Existía porque el retiro borraba el
 * origen y una corrida muerta a mitad de camino podía dejar el mundo sin ninguna
 * copia. **Este flujo no borra nada**, así que ese aparato no tiene qué proteger.
 *
 * Lo que sí queda es un problema real y chico: `discardOrphanStagings` barre por
 * prefijo, y dos archivados del mismo flujo a la vez harían que uno leyera el
 * staging **vivo** del otro como huérfano y lo borrara. Alcanza con serializar,
 * en proceso, las corridas sobre un mismo flujo.
 *
 * Lo que este lock explícitamente **no** hace: no escribe journal, no sobrevive
 * al proceso y no cubre retiro. Dos procesos distintos sobre el mismo vault no
 * se excluyen — y no hace falta, porque no hay operación destructiva que proteger.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { withFlowLock } from '../../../skills/knowledge-vault/scripts/lib/flow-lock.mjs';

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

/** Una promesa que se resuelve desde afuera. */
function diferida() {
  let resolver;
  const promesa = new Promise((r) => { resolver = r; });
  return { promesa, resolver };
}

test('[AC-5] dos corridas sobre el mismo flujo no se solapan', async () => {
  const eventos = [];
  const correr = (etiqueta) =>
    withFlowLock('/v', 'aaa-1', async () => {
      eventos.push(`entra ${etiqueta}`);
      await dormir(20);
      eventos.push(`sale ${etiqueta}`);
    });

  await Promise.all([correr('a'), correr('b')]);
  // Serializadas: cada `entra` va seguido de su propio `sale`.
  assert.deepEqual(eventos, ['entra a', 'sale a', 'entra b', 'sale b']);
});

test('[AC-5] dos flujos distintos no se serializan entre sí', async () => {
  const a = diferida();
  const b = diferida();
  // Cada uno avisa que entró y espera al otro. Si el lock fuera global, ninguno
  // podría salir y esto colgaría; el timeout convierte ese cuelgue en un fallo.
  const corrida = Promise.all([
    withFlowLock('/v', 'aaa-1', async () => { a.resolver(); await b.promesa; }),
    withFlowLock('/v', 'bbb-2', async () => { b.resolver(); await a.promesa; }),
  ]);
  const resultado = await Promise.race([corrida.then(() => 'en paralelo'), dormir(500).then(() => 'colgó')]);
  assert.equal(resultado, 'en paralelo');
});

test('[AC-5] el mismo id en vaults distintos tampoco se serializa', async () => {
  const a = diferida();
  const b = diferida();
  const corrida = Promise.all([
    withFlowLock('/vault-uno', 'aaa-1', async () => { a.resolver(); await b.promesa; }),
    withFlowLock('/vault-dos', 'aaa-1', async () => { b.resolver(); await a.promesa; }),
  ]);
  assert.equal(
    await Promise.race([corrida.then(() => 'en paralelo'), dormir(500).then(() => 'colgó')]),
    'en paralelo',
  );
});

test('[AC-5] el lock se libera aunque la función lance', async () => {
  await assert.rejects(
    () => withFlowLock('/v', 'ccc-3', async () => { throw new Error('falla adentro'); }),
    /falla adentro/,
  );
  // Si no se hubiera liberado, esto colgaría.
  const resultado = await Promise.race([
    withFlowLock('/v', 'ccc-3', async () => 'pasó'),
    dormir(500).then(() => 'colgó'),
  ]);
  assert.equal(resultado, 'pasó');
});

test('[AC-5] devuelve lo que devuelve la función', async () => {
  assert.equal(await withFlowLock('/v', 'ddd-4', async () => 42), 42);
});

test('[AC-5] una tercera corrida espera a las dos anteriores, en orden de llegada', async () => {
  const eventos = [];
  const correr = (etiqueta) =>
    withFlowLock('/v', 'eee-5', async () => { eventos.push(etiqueta); await dormir(5); });
  await Promise.all([correr('1'), correr('2'), correr('3')]);
  assert.deepEqual(eventos, ['1', '2', '3']);
});
