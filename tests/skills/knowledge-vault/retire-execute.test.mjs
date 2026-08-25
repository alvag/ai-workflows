/**
 * Reclamar, verificar, autorizar (AC-1, AC-3b-bis, AC-6, AC-20b).
 *
 * El invariante que ordena este archivo: **antes del commit del manifiesto todo
 * es reversible**. Cada test que hace fallar algo comprueba las dos mitades —que
 * el flujo volvió a su ruta y que su contenido es byte-idéntico—, porque "volvió"
 * sin "idéntico" es exactamente el fallo que este diseño existe para no tener.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import { DurableFs, Recorder } from '../../../skills/knowledge-vault/scripts/lib/durable-fs.mjs';
import { runVaultTransaction } from '../../../skills/knowledge-vault/scripts/lib/engine-vault.mjs';
import {
  PREFIJO_REMANENTE,
  RESULTADOS,
  deshacerReclamo,
  ejecutarRetiro,
  observarEstado,
  reclamar,
  rutaDelManifiesto,
  rutaDelRemanente,
} from '../../../skills/knowledge-vault/scripts/lib/retire-execute.mjs';
import { retireCommand } from '../../../skills/knowledge-vault/scripts/lib/commands/retire.mjs';
import { construirManifiesto, digestManifiesto } from '../../../skills/knowledge-vault/scripts/lib/manifest.mjs';
import { clasificarRetiro } from '../../../skills/knowledge-vault/scripts/lib/retire-state.mjs';
import { serializarRegistroIdentidades } from '../../../skills/knowledge-vault/scripts/lib/identity.mjs';
import { writeIdentitiesFile } from '../../../skills/knowledge-vault/scripts/lib/vault-store.mjs';
import { createSandbox } from './helpers/sandbox.mjs';
import { snapshotTree } from './helpers/tree-snapshot.mjs';

const git = (cwd, ...args) => promisify(execFile)('git', ['-C', cwd, ...args]);
const REPO_ID = 'api-pagos';

const PLAN = [
  '---', 'id: abc-1', 'branch: feature/abc-1', 'status: done',
  'created_at: 2026-03-04T12:00:00-03:00', '---', '', '# Plan', '',
].join('\n');

/** Un flujo archivado y verificable, listo para retirarse. */
async function escena(t, { flowId = 'abc-1', archivar = true } = {}) {
  const caja = await createSandbox(t);
  const repoRoot = await caja.makeRepo('proyecto');
  const raiz = path.join(repoRoot, '.plans', 'archived');
  const vault = await caja.makeVault('dev-memory');
  const objetivo = await caja.makeTree(path.join(raiz, flowId), {
    'spec.md': `# ${flowId}\n\ncriterios\n`,
    'plan.md': PLAN,
    'notas.txt': 'andamiaje que no viaja\n',
    'cross-review/veredicto.md': 'tampoco viaja\n',
  });
  if (archivar) {
    await runVaultTransaction({
      fs: new DurableFs(), vaultRoot: vault, repoSlug: REPO_ID, flowId, flowDir: objetivo,
      summary: `resumen de ${flowId}`,
    });
  }
  return { caja, repoRoot, raiz, vault, objetivo, flowId };
}

/**
 * Declara la identidad del repositorio en el vault. Sólo lo necesitan los tests
 * que pasan por el verbo entero: la secuencia toma el `repoId` ya resuelto.
 */
async function conIdentidad(e) {
  await git(e.repoRoot, 'init', '-q');
  await git(e.repoRoot, 'remote', 'add', 'origin', 'git@github.com:acme/api.git');
  const { stdout } = await git(e.repoRoot, 'rev-list', '--max-parents=0', 'HEAD').catch(() => ({ stdout: '' }));
  await writeIdentitiesFile({
    fs: new DurableFs(),
    vaultRoot: e.vault,
    texto: serializarRegistroIdentidades([{
      repoId: REPO_ID,
      remoto: 'git@github.com:acme/api.git',
      commitRaiz: stdout.trim().split('\n')[0] ?? '',
      rutaObservada: e.repoRoot,
    }]),
  });
  return e;
}

const retirar = (e, opciones = {}) =>
  ejecutarRetiro({
    fs: opciones.fs ?? new DurableFs(),
    vaultRoot: e.vault,
    repoId: REPO_ID,
    raiz: e.raiz,
    flujo: { flowId: e.flowId },
  });

// ── AC-6 · la secuencia, en su orden ─────────────────────────────────────────

test('[AC-6] la secuencia es reclamar, verificar, autorizar y recién entonces destruir', async (t) => {
  const e = await escena(t);
  const grabador = new Recorder();

  const r = await retirar(e, { fs: new DurableFs({ recorder: grabador }) });
  assert.equal(r.estado, RESULTADOS.RETIRADO);

  // El orden no se puede comprobar mirando el árbol final: hay que mirar la
  // traza. Los cuatro pasos, encadenados.
  assert.ok(grabador.happenedBefore('retire.reclamar', 'probe.abc-1.frontier.lstat'),
    'se verificó antes de reclamar');
  // `writeFileAtomic` no deja su propio label en la traza: publica por
  // `<label>.tmp` y `<label>.rename`. Anclar en el label pelado da un predicado
  // que nunca encuentra su marca.
  assert.ok(grabador.happenedBefore('probe.abc-1.frontier.lstat', 'retire.manifiesto.publish.rename'),
    'se autorizó antes de verificar');
  assert.ok(grabador.happenedBefore('retire.manifiesto.publish.rename', 'retire.destruir.archivo'),
    'se destruyó antes de autorizar: eso es destruir sin punto de no retorno');
});

test('[AC-6] terminada la secuencia no queda ni objetivo ni remanente, y sí el manifiesto', async (t) => {
  const e = await escena(t);
  await retirar(e);

  const estado = await observarEstado({
    fs: new DurableFs(), vaultRoot: e.vault, repoId: REPO_ID, raiz: e.raiz, flowId: e.flowId,
  });
  assert.equal(estado.hayObjetivo, false);
  assert.equal(estado.hayRemanente, false);
  assert.equal(estado.hayManifiesto, true);
  assert.deepEqual(await fs.readdir(e.raiz), [], 'quedó algo en la raíz de archivados');

  // Y el manifiesto está **commiteado**, que es lo que lo vuelve autorización.
  const { stdout } = await git(e.vault, 'log', '--format=%s');
  assert.ok(stdout.includes(`retira ${e.flowId}`), `la historia del vault: ${stdout}`);
});

test('[AC-6] un reintento sobre el terminal no destruye de nuevo ni falla', async (t) => {
  const e = await escena(t);
  await retirar(e);
  const antes = await snapshotTree(e.vault);

  const r = await retirar(e);
  assert.equal(r.estado, RESULTADOS.YA_RETIRADO);
  assert.deepEqual(await snapshotTree(e.vault), antes, 'el reintento movió el vault');
});

test('[AC-6] el remanente es hermano y lleva el prefijo reservado', async (t) => {
  const e = await escena(t);
  // Se observa **a mitad de vuelo**: el remanente es un estado intermedio, así
  // que hay que pararlo para verlo. La caída va justo después del reclamo.
  const caido = new DurableFs({ crashAt: 'retire.reclamado' });
  await retirar(e, { fs: caido }).catch(() => {});

  const remanente = rutaDelRemanente(e.raiz, e.flowId);
  assert.equal(path.dirname(remanente), e.raiz, 'el remanente no es hermano del objetivo');
  assert.ok(path.basename(remanente).startsWith(PREFIJO_REMANENTE));
  assert.ok((await fs.lstat(remanente)).isDirectory());
});

test('[AC-6] una caída después de un borrado se reintenta y termina', async (t) => {
  const e = await escena(t);
  // Muere justo después de borrar el primer archivo, con el manifiesto ya
  // commiteado: el estado durable es remanente + manifiesto.
  const caido = new DurableFs({ crashAt: 'retire.destruido.cross-review/veredicto.md' });
  await assert.rejects(() => retirar(e, { fs: caido }));

  const medio = await observarEstado({
    fs: new DurableFs(), vaultRoot: e.vault, repoId: REPO_ID, raiz: e.raiz, flowId: e.flowId,
  });
  assert.equal(medio.hayRemanente, true, 'la caída no dejó remanente');
  assert.equal(medio.hayManifiesto, true, 'la caída ocurrió antes del punto de no retorno');

  // El reintento **continúa** desde donde quedó: no revalida contra un árbol que
  // ya no es idéntico, porque la autoridad es el manifiesto.
  const r = await retirar(e);
  assert.equal(r.estado, RESULTADOS.RETIRADO);
  assert.deepEqual(await fs.readdir(e.raiz), []);
});

test('[AC-6] un reintento sobre un reclamo sin autorizar lo deshace', async (t) => {
  const e = await escena(t);
  const antes = await snapshotTree(e.objetivo);
  // Un reclamo que quedó a medias: el proceso murió entre el renombrado y el
  // commit. Sin manifiesto no hubo autorización, así que se devuelve.
  await reclamar({ fs: new DurableFs(), raiz: e.raiz, flowId: e.flowId });

  const r = await retirar(e);
  assert.equal(r.estado, RESULTADOS.RECLAMO_DESHECHO);
  assert.deepEqual(await snapshotTree(e.objetivo), antes);
});

test('[AC-6] cada transición durable sincroniza el directorio afectado', async (t) => {
  const e = await escena(t);
  const grabador = new Recorder();
  await retirar(e, { fs: new DurableFs({ recorder: grabador }) });

  // Sin estos fsync, el estado **por presencia** no es durable: los tests de
  // caída de proceso pasarían sin cubrir la caída del sistema, que es
  // exactamente la que se lleva puesto un renombrado no sincronizado.
  const etiquetas = grabador.labels();
  for (const [marca, porque] of [
    ['retire.reclamar.fsync-parent', 'el reclamo no sincronizó su padre'],
    ['retire.manifiesto.fsync-abuelo', 'la cadena creada para el manifiesto no se sincronizó'],
    ['retire.manifiesto.publish.fsync-dir', 'el manifiesto no sincronizó su padre inmediato'],
    ['retire.destruir.fsync-parent', 'retirar la raíz del remanente no sincronizó su padre'],
  ]) {
    assert.ok(etiquetas.includes(marca), porque);
  }
  // Y el orden: el abuelo se sincroniza **antes** de publicar el archivo, o el
  // manifiesto se consideraría existente dentro de un directorio que puede no
  // sobrevivir.
  assert.ok(grabador.happenedBefore('retire.manifiesto.fsync-abuelo', 'retire.manifiesto.publish.rename'));
});

test('[AC-6] deshacer un reclamo también sincroniza', async (t) => {
  const e = await escena(t, { archivar: false });
  const grabador = new Recorder();
  await retirar(e, { fs: new DurableFs({ recorder: grabador }) }).catch(() => {});

  assert.ok(grabador.labels().includes('retire.deshacer.fsync-parent'),
    'la vuelta del flujo a su ruta no es durable');
});

// ── AC-1 · aborta sin cambio neto ────────────────────────────────────────────

test('[AC-1] sin copia en el vault aborta nombrando la causa', async (t) => {
  const e = await escena(t, { archivar: false });
  await assert.rejects(() => retirar(e), (error) => {
    assert.equal(error.code, 'VERIFY_FAILED');
    assert.match(error.message, /FRONTIER_MISSING/);
    return true;
  });
});

test('[AC-1] con una discrepancia nombra la primera ruta y su causa', async (t) => {
  const e = await escena(t);
  await fs.writeFile(
    path.join(e.vault, 'projects', REPO_ID, 'sdd', e.flowId, 'spec.md'), '# manoseado\n', 'utf8',
  );

  await assert.rejects(() => retirar(e), (error) => {
    assert.equal(error.code, 'VERIFY_FAILED');
    assert.match(error.message, /VERIFY_FAILED/);
    assert.match(error.message, /spec\.md/);
    return true;
  });
});

test('[AC-1] tras un aborto el origen queda sin cambio neto', async (t) => {
  const e = await escena(t, { archivar: false });
  const antes = await snapshotTree(e.objetivo);

  await assert.rejects(() => retirar(e));

  // Las tres cosas que "sin cambio neto" quiere decir: misma ruta, mismo
  // conjunto y mismos hashes. Y ningún remanente colgado.
  assert.deepEqual(await snapshotTree(e.objetivo), antes);
  assert.equal(await fs.lstat(rutaDelRemanente(e.raiz, e.flowId)).catch(() => null), null);
  assert.deepEqual((await fs.readdir(e.raiz)).sort(), [e.flowId]);
});

test('[AC-1] un aborto no deja rastro en el vault', async (t) => {
  const e = await escena(t, { archivar: false });
  const antes = await snapshotTree(e.vault);
  await assert.rejects(() => retirar(e));
  assert.deepEqual(await snapshotTree(e.vault), antes);
});

// ── AC-3b-bis · el commit fallido no destruye nada ───────────────────────────

test('[AC-3b-bis] si el commit del manifiesto falla, el flujo vuelve y no se destruye nada', async (t) => {
  const e = await escena(t);
  const antes = await snapshotTree(e.objetivo);
  // Un `index.lock` deja a `git add` sin poder tomar el índice: es un fallo real
  // del camino del commit, no una excepción inventada aguas arriba.
  await fs.writeFile(path.join(e.vault, '.git', 'index.lock'), '', 'utf8');

  await assert.rejects(() => retirar(e));

  assert.deepEqual(await snapshotTree(e.objetivo), antes, 'el origen cambió');
  assert.equal(await fs.lstat(rutaDelRemanente(e.raiz, e.flowId)).catch(() => null), null);
});

test('[AC-3b-bis] si falla la escritura del manifiesto, tampoco se destruye nada', async (t) => {
  const e = await escena(t);
  const antes = await snapshotTree(e.objetivo);
  const roto = new DurableFs({ failAt: { label: 'retire.manifiesto.publish.tmp', code: 'EIO' } });

  await assert.rejects(() => retirar(e, { fs: roto }));

  assert.deepEqual(await snapshotTree(e.objetivo), antes);
  assert.equal(await fs.lstat(rutaDelManifiesto(e.vault, REPO_ID, e.flowId)).catch(() => null), null);
});

test('[AC-3b-bis] la frontera es el commit: antes de él nada del vault quedó commiteado', async (t) => {
  const e = await escena(t);
  const { stdout: antes } = await git(e.vault, 'rev-parse', 'HEAD');
  await fs.writeFile(path.join(e.vault, '.git', 'index.lock'), '', 'utf8');

  await assert.rejects(() => retirar(e));
  await fs.rm(path.join(e.vault, '.git', 'index.lock'));

  const { stdout: despues } = await git(e.vault, 'rev-parse', 'HEAD');
  assert.equal(despues.trim(), antes.trim(), 'el vault avanzó sin autorización');
});

// ── AC-20b · la verificación ocurre sobre el remanente ───────────────────────

test('[AC-20b] lo que se verifica es el remanente, no la ruta original', async (t) => {
  const e = await escena(t);
  const grabador = new Recorder();
  await retirar(e, { fs: new DurableFs({ recorder: grabador }) });

  // Toda ruta hasheada durante la sonda cuelga del remanente. Si alguna colgara
  // del objetivo, la ventana que el orden cierra seguiría abierta.
  const remanente = rutaDelRemanente(e.raiz, e.flowId);
  const hasheadas = grabador.entries
    .filter((o) => o.op === 'hashFile')
    .flatMap((o) => o.paths)
    .filter((p) => p.startsWith(e.raiz));
  assert.ok(hasheadas.length > 0, 'la sonda no hasheó nada del origen');
  for (const p of hasheadas) {
    assert.ok(p.startsWith(remanente), `se hasheó por la ruta original: ${p}`);
  }
});

test('[AC-20b] la carrera: lo que se escriba antes del reclamo lo detecta la verificación', async (t) => {
  const e = await escena(t);
  const antesDelCambio = await snapshotTree(e.objetivo);
  assert.ok(antesDelCambio);

  // Otro proceso escribe en el origen **después** de que se archivó y antes del
  // reclamo. La verificación posterior —sobre el remanente— lo detecta.
  await fs.writeFile(path.join(e.objetivo, 'spec.md'), '# lo cambió otro proceso\n', 'utf8');

  await assert.rejects(() => retirar(e), (error) => {
    assert.equal(error.code, 'VERIFY_FAILED');
    return true;
  });
  // Y el flujo volvió, con el cambio ajeno intacto: no se pisa lo que no es
  // nuestro, sólo se deshace el renombrado.
  assert.equal(
    await fs.readFile(path.join(e.objetivo, 'spec.md'), 'utf8'), '# lo cambió otro proceso\n',
  );
});

test('[AC-20b] durante el reclamo la ruta original no existe, que es la exclusión', async (t) => {
  const e = await escena(t);
  const io = new DurableFs();
  // Se para el mundo justo después del reclamo y se mira el disco: no hace falta
  // un lock porque no queda ruta por la que otro proceso alcance el flujo.
  await reclamar({ fs: io, raiz: e.raiz, flowId: e.flowId });

  assert.equal(await fs.lstat(e.objetivo).catch(() => null), null, 'la ruta original sigue viva');
  assert.ok((await fs.lstat(rutaDelRemanente(e.raiz, e.flowId))).isDirectory());

  await deshacerReclamo({ fs: io, raiz: e.raiz, flowId: e.flowId });
  assert.ok((await fs.lstat(e.objetivo)).isDirectory());
});

// ── AC-6b · subconjunto exacto, y de a una entrada ───────────────────────────

/** Deja el flujo en el estado durable "autorizado": remanente + manifiesto. */
async function autorizado(t, opciones) {
  const e = await escena(t, opciones);
  const caido = new DurableFs({ crashAt: 'retire.autorizado' });
  await retirar(e, { fs: caido }).catch(() => {});
  const remanente = rutaDelRemanente(e.raiz, e.flowId);
  assert.ok((await fs.lstat(remanente)).isDirectory(), 'no quedó remanente que reintentar');
  return { ...e, remanente };
}

test('[AC-6b] un archivo que el manifiesto no autoriza falla sin tocar nada', async (t) => {
  const e = await autorizado(t);
  await fs.writeFile(path.join(e.remanente, 'apareció.md'), 'nadie me autorizó\n', 'utf8');
  const antes = await snapshotTree(e.remanente);

  await assert.rejects(() => retirar(e), (error) => {
    assert.equal(error.code, 'PRECONDITION_NOT_MET');
    assert.match(error.message, /no autorizado/);
    assert.match(error.message, /apareció\.md/);
    return true;
  });
  // "Sin tocar nada" literal: ni siquiera los archivos que sí estaban autorizados.
  assert.deepEqual(await snapshotTree(e.remanente), antes);
});

test('[AC-6b] un archivo modificado falla sin tocar nada', async (t) => {
  const e = await autorizado(t);
  await fs.writeFile(path.join(e.remanente, 'spec.md'), '# otro contenido\n', 'utf8');
  const antes = await snapshotTree(e.remanente);

  await assert.rejects(() => retirar(e), (error) => {
    assert.equal(error.code, 'PRECONDITION_NOT_MET');
    assert.match(error.message, /modificado/);
    return true;
  });
  assert.deepEqual(await snapshotTree(e.remanente), antes);
});

test('[AC-6b] un directorio que el manifiesto no autoriza falla sin tocar nada', async (t) => {
  const e = await autorizado(t);
  await fs.mkdir(path.join(e.remanente, 'nuevo-dir'), { recursive: true });
  const antes = await snapshotTree(e.remanente);

  await assert.rejects(() => retirar(e), (error) => {
    assert.equal(error.code, 'PRECONDITION_NOT_MET');
    assert.match(error.message, /nuevo-dir/);
    return true;
  });
  assert.deepEqual(await snapshotTree(e.remanente), antes);
});

test('[AC-6b] faltar entradas sí está permitido: eso es el reintento', async (t) => {
  const e = await autorizado(t);
  // Lo que quedó tras una caída es un **subconjunto**, y tiene que poder
  // terminar. Sin esta mitad, la regla del subconjunto exacto bloquearía todo
  // reintento y el remanente sería imposible de cerrar.
  await fs.rm(path.join(e.remanente, 'spec.md'));

  const r = await retirar(e);
  assert.equal(r.estado, RESULTADOS.RETIRADO);
  assert.deepEqual(await fs.readdir(e.raiz), []);
});

test('[AC-6b] el borrado es de a una entrada, nunca recursivo', async (t) => {
  const e = await autorizado(t);
  const grabador = new Recorder();
  await retirar(e, { fs: new DurableFs({ recorder: grabador }) });

  const ops = grabador.entries.filter((o) => o.paths.some((p) => p.startsWith(e.remanente)));
  const porOp = ops.reduce((acc, o) => ({ ...acc, [o.op]: (acc[o.op] ?? 0) + 1 }), {});
  // Un `rmTree` sobre el remanente destruiría de un saque el archivo sobrante
  // que la regla de arriba existe para atajar.
  assert.equal(porOp.rmTree ?? 0, 0, 'hubo un borrado recursivo del remanente');
  assert.equal(porOp.unlink, 4, `se esperaban 4 unlink y hubo ${porOp.unlink}`);
  assert.ok((porOp.removeEmptyDir ?? 0) >= 2, 'los directorios no se retiraron de a uno');
});

test('[AC-6b] los directorios se retiran en postorden', async (t) => {
  const e = await autorizado(t);
  const grabador = new Recorder();
  await retirar(e, { fs: new DurableFs({ recorder: grabador }) });

  const retirados = grabador.entries
    .filter((o) => o.op === 'removeEmptyDir')
    .map((o) => o.paths[0]);
  // `cross-review` antes que el remanente que lo contiene: al revés, el segundo
  // fallaría con `ENOTEMPTY` y el borrado no podría terminar nunca.
  const iHijo = retirados.findIndex((p) => p.endsWith('cross-review'));
  const iRaiz = retirados.indexOf(e.remanente);
  assert.ok(iHijo >= 0 && iRaiz >= 0, `no se retiraron ambos: ${retirados.join(', ')}`);
  assert.ok(iHijo < iRaiz, 'el padre se retiró antes que el hijo');
});

// ── AC-18 · el camino destructivo no usa el sistema de archivos crudo ────────

test('[AC-18] toda entrada destruida del origen pasó por el inyector', async (t) => {
  const e = await autorizado(t);
  const antes = await snapshotTree(e.remanente);
  const grabador = new Recorder();
  await retirar(e, { fs: new DurableFs({ recorder: grabador }) });

  // Lo que desapareció del disco, contado contra lo que el registro vio
  // desaparecer. Una escritura por la vía cruda no dejaría registro, así que
  // estos dos números sólo coinciden si todo pasó por el inyector.
  // `snapshotTree` devuelve un `Map`: `Object.keys` sobre él da cero y el
  // conteo quedaría comparando cero contra cero, que pasa por vacuidad.
  const desaparecidos = antes.size;
  const registrados = grabador.entries
    .filter((o) => (o.op === 'unlink' || o.op === 'removeEmptyDir') && o.outcome === 'ok')
    .flatMap((o) => o.paths)
    .filter((p) => p.startsWith(e.remanente) && p !== e.remanente).length;
  assert.ok(desaparecidos > 0, 'el remanente estaba vacío: el conteo no probaría nada');
  assert.equal(registrados, desaparecidos, `${desaparecidos} entradas fuera, ${registrados} registradas`);
});

test('[AC-18] una caída inyectada en una primitiva destructiva de verdad la detiene', async (t) => {
  const e = await autorizado(t);
  const antes = await snapshotTree(e.remanente);
  // Si el borrado usara `fs.rm` crudo, la inyección no lo alcanzaría y el árbol
  // quedaría vacío igual: el test pasaría a rojo por la aserción de abajo.
  const caido = new DurableFs({ crashAt: 'retire.destruir.archivo' });

  await assert.rejects(() => retirar(e, { fs: caido }));
  assert.deepEqual(await snapshotTree(e.remanente), antes, 'la caída no detuvo el borrado');
});

// ── AC-20 · la implementación más floja no pasa ──────────────────────────────
//
// Es el control positivo del contrato **entero**. Todo lo anterior comprueba que
// esta implementación cumple; esto comprueba que el contrato **rechaza** a una
// que satisface su letra y no su propósito. Sin él, todas las garantías de arriba
// pueden ser decorativas: un contrato que cualquier cosa cumple no separa nada.
//
// La floja es la del criterio, literal: imprime conteos, recomputa su propio
// digest al ejecutar, enumera sólo lo presente y borra todo lo que verifica.

const flojo = {
  /** "Emite un digest": sobre conteos agregados. */
  async digest(dir) {
    const entradas = await fs.readdir(dir, { recursive: true });
    return `conteo:${entradas.length}`;
  },
  /** "Exige el digest": lo recomputa al ejecutar, así que se aprueba solo. */
  async autoriza(dir, aprobado) {
    void aprobado;
    return (await flojo.digest(dir)) === (await flojo.digest(dir));
  },
  /** "Sabe qué retirar": enumerando lo presente. */
  async conjunto(dir) {
    return (await fs.readdir(dir).catch(() => [])).sort();
  },
  /** "Destruye": todo lo que verificó, de un saque. */
  async destruye(dir) {
    await fs.rm(dir, { recursive: true, force: true });
  },
};

test('[AC-20] el digest sobre conteos no distingue dos árboles: el del manifiesto sí', async (t) => {
  const caja = await createSandbox(t);
  const uno = await caja.makeTree(caja.path('uno'), { 'a.md': 'contenido A\n', 'b.md': 'contenido B\n' });
  const otro = await caja.makeTree(caja.path('otro'), { 'a.md': 'OTRA COSA\n', 'b.md': 'contenido B\n' });

  assert.equal(await flojo.digest(uno), await flojo.digest(otro), 'el conteo debería confundirlos');

  const manifiesto = (dir) => construirManifiesto({
    fs: new DurableFs(), flowDir: dir, aSalvo: ['a.md', 'b.md'],
    identidad: { repoId: REPO_ID, flowId: 'x' }, vaultCommit: 'a'.repeat(40),
  });
  assert.notEqual(
    digestManifiesto(await manifiesto(uno)),
    digestManifiesto(await manifiesto(otro)),
    'el digest del manifiesto también los confunde',
  );
});

test('[AC-20] recomputar el digest al ejecutar se aprueba solo; el real lo exige y lo compara', async (t) => {
  const e = await escena(t);
  assert.equal(await flojo.autoriza(e.objetivo, 'cualquier-cosa'), true, 'la floja debería aprobarse sola');

  // El real: el digest llega por argumento y se compara contra lo remedido. No
  // hay forma de que se apruebe a sí mismo, porque no lo computa para decidir.
  // El verbo entero exige identidad declarada, así que hay que dársela: sin ella
  // se detendría antes y este test mediría otra cosa.
  await conIdentidad(e);
  const antes = await snapshotTree(e.objetivo);
  await assert.rejects(
    () => retireCommand({
      fs: new DurableFs(),
      flags: { root: e.raiz, 'vault-root': e.vault, 'approve-digest': 'f'.repeat(64) },
    }),
    (error) => error.code === 'PRECONDITION_NOT_MET',
  );
  assert.deepEqual(await snapshotTree(e.objetivo), antes);
});

test('[AC-20] enumerar lo presente no distingue el terminal de "nunca incluido"', async (t) => {
  const retirado = await escena(t);
  await retirar(retirado);
  const nunca = await escena(t, { flowId: 'jamas-existio', archivar: false });
  await fs.rm(nunca.objetivo, { recursive: true, force: true });

  // Para la floja, las dos raíces se ven igual: vacías.
  assert.deepEqual(await flojo.conjunto(retirado.raiz), await flojo.conjunto(nunca.raiz));

  // Para el contrato son estados distintos, y la diferencia la hace el
  // manifiesto: uno es un terminal alcanzado y el otro es que nada ocurrió.
  const observar = (e, flowId) => observarEstado({
    fs: new DurableFs(), vaultRoot: e.vault, repoId: REPO_ID, raiz: e.raiz, flowId,
  });
  const a = clasificarRetiro(await observar(retirado, retirado.flowId));
  const b = clasificarRetiro(await observar(nunca, nunca.flowId));
  assert.equal(a.estado, 'TERMINAL_ALCANZADO');
  assert.equal(b.estado, 'NADA_OCURRIO');
  assert.notEqual(a.estado, b.estado);
});

test('[AC-20] borrar todo lo verificado destruye lo que nadie autorizó; el real falla sin tocar', async (t) => {
  const real = await autorizado(t);
  await fs.writeFile(path.join(real.remanente, 'de-otro.md'), 'material ajeno\n', 'utf8');

  // El real se niega, y deja el archivo ajeno donde estaba.
  await assert.rejects(() => retirar(real), (error) => error.code === 'PRECONDITION_NOT_MET');
  assert.equal(await fs.readFile(path.join(real.remanente, 'de-otro.md'), 'utf8'), 'material ajeno\n');

  // La floja lo destruye sin enterarse: su autoridad es el disco, y el disco
  // incluye lo que apareció después de la autorización.
  await flojo.destruye(real.remanente);
  assert.equal(await fs.lstat(path.join(real.remanente, 'de-otro.md')).catch(() => null), null);
});
