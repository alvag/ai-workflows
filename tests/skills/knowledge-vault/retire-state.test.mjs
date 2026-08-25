/**
 * La tabla de adopción (AC-7, AC-7b).
 *
 * Las ocho combinaciones van en **ocho tests**, uno cada una, y no en un bucle
 * dentro de uno solo. Es deliberado: un bucle da un único veredicto, así que una
 * combinación mal clasificada se lee igual que las siete correctas, y el conteo
 * por criterio —que es lo que la fila del contrato mide— no distinguiría "las
 * ocho están" de "hay una que las cubre a todas de palabra".
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ACCIONES,
  AUTORIDADES,
  ESTADOS,
  clasificarRetiro,
} from '../../../skills/knowledge-vault/scripts/lib/retire-state.mjs';

const clasificar = (hayObjetivo, hayRemanente, hayManifiesto, extra = {}) =>
  clasificarRetiro({ hayObjetivo, hayRemanente, hayManifiesto, ...extra });

// ── AC-7b · las ocho combinaciones ───────────────────────────────────────────

test('[AC-7b] sin objetivo, sin remanente y sin manifiesto: nada ocurrió', () => {
  const r = clasificar(false, false, false);
  assert.equal(r.estado, ESTADOS.NADA_OCURRIO);
  assert.equal(r.accion, ACCIONES.NADA);
  assert.equal(r.autoridad, AUTORIDADES.PADRE);
});

test('[AC-7b] sin objetivo, sin remanente y con manifiesto: terminal ya alcanzado', () => {
  const r = clasificar(false, false, true);
  assert.equal(r.estado, ESTADOS.TERMINAL_ALCANZADO);
  assert.equal(r.accion, ACCIONES.NADA);
  assert.equal(r.autoridad, AUTORIDADES.MANIFIESTO);
});

test('[AC-7b] sin objetivo, con remanente y sin manifiesto: reclamo sin autorizar, se deshace', () => {
  const r = clasificar(false, true, false);
  assert.equal(r.estado, ESTADOS.RECLAMO_SIN_AUTORIZAR);
  assert.equal(r.accion, ACCIONES.DESHACER);
  assert.equal(r.autoridad, AUTORIDADES.REMANENTE);
});

test('[AC-7b] sin objetivo, con remanente y con manifiesto: destrucción autorizada, se termina', () => {
  const r = clasificar(false, true, true);
  assert.equal(r.estado, ESTADOS.DESTRUCCION_AUTORIZADA);
  assert.equal(r.accion, ACCIONES.TERMINAR);
  // La autoridad es el manifiesto y no el remanente: lo que queda en disco es un
  // subconjunto, y enumerar lo presente daría un conjunto que nadie autorizó.
  assert.equal(r.autoridad, AUTORIDADES.MANIFIESTO);
});

test('[AC-7b] con objetivo, sin remanente y sin manifiesto: sin empezar, se reclama', () => {
  const r = clasificar(true, false, false);
  assert.equal(r.estado, ESTADOS.SIN_EMPEZAR);
  assert.equal(r.accion, ACCIONES.RECLAMAR);
  assert.equal(r.autoridad, AUTORIDADES.OBJETIVO);
});

test('[AC-7b] con objetivo y con manifiesto pero sin remanente: objetivo recreado, detiene', () => {
  const r = clasificar(true, false, true);
  assert.equal(r.estado, ESTADOS.OBJETIVO_RECREADO);
  assert.equal(r.accion, ACCIONES.DETENER);
  assert.equal(r.detalle.remanente, ESTADOS.TERMINAL_ALCANZADO);
});

test('[AC-7b] con objetivo y con remanente sin manifiesto: objetivo recreado, detiene', () => {
  const r = clasificar(true, true, false);
  assert.equal(r.estado, ESTADOS.OBJETIVO_RECREADO);
  assert.equal(r.accion, ACCIONES.DETENER);
  // El estado del remanente viaja como **detalle**, no como un segundo estado en
  // competencia: si compitiera, la salida sería "deshago el reclamo", que toca
  // la ruta original que acaba de reaparecer.
  assert.equal(r.detalle.remanente, ESTADOS.RECLAMO_SIN_AUTORIZAR);
});

test('[AC-7b] con objetivo, con remanente y con manifiesto: objetivo recreado, detiene', () => {
  const r = clasificar(true, true, true);
  assert.equal(r.estado, ESTADOS.OBJETIVO_RECREADO);
  assert.equal(r.accion, ACCIONES.DETENER);
  assert.equal(r.detalle.remanente, ESTADOS.DESTRUCCION_AUTORIZADA);
});

// ── AC-7b · lo que la secuencia no puede producir ────────────────────────────

test('[AC-7b] la ruta original recreada tiene precedencia sobre todo lo demás', () => {
  // Con colisión de nombres y varios remanentes a la vez, sigue ganando el
  // objetivo. Es la precedencia escrita como orden de evaluación, y sin ella la
  // salida dependería de en qué orden se miraron las señales.
  const r = clasificar(true, true, true, { remanentes: 3, colisionDeNombres: true });
  assert.equal(r.estado, ESTADOS.OBJETIVO_RECREADO);
  assert.equal(r.accion, ACCIONES.DETENER);
});

test('[AC-7b] varios remanentes del mismo flujo detienen', () => {
  const r = clasificar(false, true, false, { remanentes: 2 });
  assert.equal(r.estado, ESTADOS.REMANENTES_MULTIPLES);
  assert.equal(r.accion, ACCIONES.DETENER);
  assert.equal(r.detalle.remanentes, 2);
  // Uno solo sigue siendo la celda normal: el detener es por la multiplicidad.
  assert.equal(clasificar(false, true, false, { remanentes: 1 }).estado, ESTADOS.RECLAMO_SIN_AUTORIZAR);
});

test('[AC-7b] la colisión de nombres detiene antes de reclamar', () => {
  const r = clasificar(true, false, false, { colisionDeNombres: true });
  assert.equal(r.estado, ESTADOS.COLISION_DE_NOMBRES);
  assert.equal(r.accion, ACCIONES.DETENER);
  // Sin colisión, el mismo estado observado se reclama.
  assert.equal(clasificar(true, false, false).accion, ACCIONES.RECLAMAR);
});

test('[AC-7b] cada combinación tiene exactamente un estado y una salida', () => {
  const vistas = new Map();
  for (const o of [false, true]) {
    for (const r of [false, true]) {
      for (const m of [false, true]) {
        const clave = `${Number(o)}${Number(r)}${Number(m)}`;
        const salida = clasificar(o, r, m);
        assert.ok(Object.values(ESTADOS).includes(salida.estado), `estado fuera del enum: ${salida.estado}`);
        assert.ok(Object.values(ACCIONES).includes(salida.accion), `acción fuera del enum: ${salida.accion}`);
        assert.ok(Object.values(AUTORIDADES).includes(salida.autoridad));
        vistas.set(clave, `${salida.estado}/${salida.accion}`);
      }
    }
  }
  assert.equal(vistas.size, 8, 'faltan combinaciones');
  // Y ninguna destruye: la tabla clasifica, la destrucción la decide quien la
  // consume. `TERMINAR` es "seguí desde donde quedaste", no "borrá lo que veas".
  assert.deepEqual(
    [...vistas.entries()].sort().map(([k, v]) => `${k} ${v}`),
    [
      '000 NADA_OCURRIO/NADA',
      '001 TERMINAL_ALCANZADO/NADA',
      '010 RECLAMO_SIN_AUTORIZAR/DESHACER',
      '011 DESTRUCCION_AUTORIZADA/TERMINAR',
      '100 SIN_EMPEZAR/RECLAMAR',
      '101 OBJETIVO_RECREADO/DETENER',
      '110 OBJETIVO_RECREADO/DETENER',
      '111 OBJETIVO_RECREADO/DETENER',
    ],
  );
});

// ── AC-7 · el objetivo ausente es un terminal verificable ────────────────────

test('[AC-7] el objetivo ausente se distingue de "nunca incluido" por el manifiesto', () => {
  // La misma ausencia, dos significados. Sin el manifiesto no hay forma de
  // separarlos, y enumerar lo que todavía existe no los distingue: en los dos
  // casos no hay nada que enumerar.
  const retirado = clasificar(false, false, true);
  const nuncaIncluido = clasificar(false, false, false);
  assert.equal(retirado.estado, ESTADOS.TERMINAL_ALCANZADO);
  assert.equal(nuncaIncluido.estado, ESTADOS.NADA_OCURRIO);
  assert.notEqual(retirado.estado, nuncaIncluido.estado);
  assert.equal(retirado.autoridad, AUTORIDADES.MANIFIESTO);
});

test('[AC-7] un terminal alcanzado no vuelve a destruir ni falla', () => {
  const r = clasificar(false, false, true);
  assert.equal(r.accion, ACCIONES.NADA);
  assert.notEqual(r.accion, ACCIONES.DETENER, 'reintentar sobre un terminal no es un error');
});

test('[AC-7] un reclamo caído antes del manifiesto se deshace, no se termina', () => {
  // Es el caso que separa lo reversible de lo irreversible: sin manifiesto no
  // hubo autorización, así que la salida es devolver el flujo, nunca borrar.
  const r = clasificar(false, true, false);
  assert.equal(r.accion, ACCIONES.DESHACER);
  assert.notEqual(r.accion, ACCIONES.TERMINAR);
});
