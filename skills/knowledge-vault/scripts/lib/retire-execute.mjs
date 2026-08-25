/**
 * Reclamar, verificar, autorizar, destruir.
 *
 * Es el único módulo de la skill autorizado a destruir bajo el origen, y la
 * guarda de la suite lo nombra por su nombre de archivo. Todo lo que hace pasa
 * por el sistema de archivos **inyectado**: una escritura por la vía cruda no
 * dejaría registro, y la prueba de caída pasaría sin ejercer nada.
 *
 * ## Por qué se reclama antes de verificar
 *
 * El orden natural sería verificar y después borrar, y tiene una ventana: entre
 * comprobar que el flujo está a salvo y destruirlo, **otro proceso puede
 * escribir en él**. La salida clásica es un lock, que estaba descartado —el lock
 * transaccional del árbol de origen se retiró con el aparato viejo, y volver a
 * meterlo era volver a meter journal, dueño, expiración y recuperación—.
 *
 * Acá la ventana se cierra por el **orden**: el flujo se **renombra primero** a
 * un nombre reservado hermano, y desde ese instante ningún proceso que lo busque
 * por su ruta original lo alcanza. La verificación autoritativa ocurre **sobre el
 * remanente**. Lo que sí puede pasar es que alguien esté escribiendo justo en el
 * instante del renombrado; ese caso lo detecta la verificación posterior, que
 * falla y devuelve el flujo a su lugar.
 *
 * El costo está asumido y escrito: el aborto ya no es "sin tocar nada" sino
 * **sin cambio neto** — mismo conjunto de archivos, mismos hashes, misma ruta.
 *
 * ## El punto de no retorno
 *
 * Es el **commit del manifiesto**, y es la frontera exacta entre lo reversible y
 * lo irreversible. Antes de él, cualquier fallo devuelve el flujo a su ruta y no
 * se destruye un byte. Después de él, el estado durable ya no es "el flujo
 * existe" sino "hay un remanente y hay un manifiesto que dice qué se autorizó
 * destruir", y el reintento **continúa** en vez de revalidar contra un árbol que
 * ya no es idéntico.
 */

import path from 'node:path';

import { ContractError } from './contracts.mjs';
import { canonicalizeDocument, parseDocument } from './canonical.mjs';
import { SCHEMA_MANIFIESTO, construirManifiesto } from './manifest.mjs';
import { ACCIONES, ESTADOS as ESTADOS_TABLA, clasificarRetiro } from './retire-state.mjs';
import { estaASalvo } from './safety-probe.mjs';
import { isCopiable } from './selection.mjs';
import { scanInventory } from './tree.mjs';
import { isInjectedCrash } from './durable-fs.mjs';
import { commitFlow, headDelVault } from './vault-git.mjs';

/**
 * El prefijo del remanente. Es **reservado**: ningún flujo puede llamarse así, y
 * todo barrido de la raíz de archivados tiene que saltearlo o va a tratar un
 * reclamo en curso como si fuera material del usuario.
 *
 * Empieza con punto por la misma razón que el staging del vault: queda fuera de
 * los listados casuales y no se confunde con un flujo.
 */
export const PREFIJO_REMANENTE = '.kv-retirando-';

export const esNombreDeRemanente = (nombre) => nombre.startsWith(PREFIJO_REMANENTE);
export const flowIdDeRemanente = (nombre) => nombre.slice(PREFIJO_REMANENTE.length);
export const rutaDelRemanente = (raiz, flowId) => path.join(raiz, `${PREFIJO_REMANENTE}${flowId}`);

/**
 * Dónde vive el manifiesto dentro del vault.
 *
 * Bajo `.kv/` y no junto al nodo: Obsidian ignora los directorios con punto, la
 * regeneración de índices no los recorre, y Git sí los versiona. Meterlo dentro
 * de la frontera haría fallar cada rearchivado, porque esa comparación es de
 * conjuntos exactos.
 */
export const rutaDelManifiesto = (vaultRoot, repoId, flowId) =>
  path.join(vaultRoot, '.kv', 'retiros', repoId, `${flowId}.json`);

/** Estados que devuelve un retiro. Enum cerrado. */
export const RESULTADOS = Object.freeze({
  RETIRADO: 'RETIRADO',
  AUTORIZADO: 'AUTORIZADO',
  YA_RETIRADO: 'YA_RETIRADO',
  RECLAMO_DESHECHO: 'RECLAMO_DESHECHO',
  NADA: 'NADA',
  FALLO: 'FALLO',
});

async function existe(fs, ruta, label) {
  return (await fs.lstat(ruta, label)) !== null;
}

/**
 * Observa el disco y clasifica. Separado de la decisión a propósito: la tabla es
 * pura, así que el mismo estado observado siempre da la misma salida.
 */
export async function observarEstado({ fs, vaultRoot, repoId, raiz, flowId, label = 'retire' }) {
  const objetivo = path.join(raiz, flowId);
  const remanente = rutaDelRemanente(raiz, flowId);
  const manifiesto = rutaDelManifiesto(vaultRoot, repoId, flowId);

  const infoRemanente = await fs.lstat(remanente, `${label}.remanente.lstat`);
  // Varios remanentes del mismo flujo: no los produce la secuencia, así que su
  // causa es externa. Se cuentan por prefijo, que es como se los reconoce.
  const hermanos = await fs.readDirNames(raiz, `${label}.readdir`);
  const remanentes = hermanos.filter(({ name }) => name.startsWith(`${PREFIJO_REMANENTE}${flowId}`)).length;

  return {
    objetivo,
    remanente,
    manifiesto,
    hayObjetivo: await existe(fs, objetivo, `${label}.objetivo.lstat`),
    hayRemanente: infoRemanente !== null && infoRemanente.isDirectory(),
    hayManifiesto: await existe(fs, manifiesto, `${label}.manifiesto.lstat`),
    remanentes,
    // El nombre reservado ocupado por algo que no es un directorio: no es un
    // remanente nuestro y no se puede reclamar encima.
    colisionDeNombres: infoRemanente !== null && !infoRemanente.isDirectory(),
  };
}

/**
 * Saca el flujo de la ruta por la que cualquier otro proceso lo alcanzaría.
 *
 * Es la primera mutación de todo el camino, y es **reversible**: mientras no haya
 * manifiesto, un remanente es un reclamo sin autorizar y se deshace.
 */
export async function reclamar({ fs, raiz, flowId, label = 'retire' }) {
  const objetivo = path.join(raiz, flowId);
  const remanente = rutaDelRemanente(raiz, flowId);
  await fs.rename(objetivo, remanente, `${label}.reclamar`);
  await fs.fsyncDir(raiz, `${label}.reclamar.fsync-parent`);
  fs.checkpoint(`${label}.reclamado`);
  return remanente;
}

/** Devuelve el flujo a su ruta. Deja el origen **sin cambio neto**. */
export async function deshacerReclamo({ fs, raiz, flowId, label = 'retire' }) {
  const objetivo = path.join(raiz, flowId);
  await fs.rename(rutaDelRemanente(raiz, flowId), objetivo, `${label}.deshacer`);
  await fs.fsyncDir(raiz, `${label}.deshacer.fsync-parent`);
  fs.checkpoint(`${label}.deshecho`);
  return objetivo;
}

/**
 * El punto de no retorno: escribe el manifiesto en el vault y lo commitea.
 *
 * Ese commit cumple **tres** papeles a la vez, y por eso no hay una marca aparte
 * que mantener sincronizada: es la autorización durable, la autoridad del
 * conjunto en el reintento, y el registro de que el origen fue retirado.
 */
export async function autorizar({ fs, vaultRoot, repoId, flowId, manifiesto, label = 'retire' }) {
  const destino = rutaDelManifiesto(vaultRoot, repoId, flowId);
  const padre = path.dirname(destino);
  await fs.mkdir(padre, `${label}.manifiesto.mkdir`, { recursive: true });
  // El `mkdir` recursivo crea una cadena de directorios y **ninguno queda
  // sincronizado**: tras una caída del sistema el archivo podría existir en un
  // directorio que no. `writeFileAtomic` sincroniza el padre inmediato del
  // archivo; lo que falta es el abuelo, que es el que contiene al padre recién
  // creado. Sin esto, el manifiesto se considera existente antes de serlo.
  await fs.fsyncDir(path.dirname(padre), `${label}.manifiesto.fsync-abuelo`);
  await fs.writeFileAtomic(destino, canonicalizeDocument(manifiesto), `${label}.manifiesto.publish`);

  const { committed, commit } = await commitFlow({
    vaultRoot,
    flowId,
    paths: [path.relative(vaultRoot, destino)],
    subject: `retira ${flowId}`,
  });
  if (!committed) {
    throw new ContractError(
      'PRECONDITION_NOT_MET',
      `el manifiesto de ${flowId} no produjo commit: sin punto de no retorno no se destruye nada`,
      { path: destino },
    );
  }
  fs.checkpoint(`${label}.autorizado`);
  return { commit, path: destino };
}

/** Las rutas copiables del remanente, que son las que el vault tiene a salvo. */
async function rutasASalvo({ fs, root, label }) {
  const inventario = await scanInventory({ fs, root, label: `${label}.copiables` });
  return inventario.files.filter((e) => isCopiable(e.path)).map((e) => e.path);
}

/**
 * La secuencia completa sobre un flujo.
 *
 * Se le pasa a `retireCommand` como `ejecutor`. Cada salida es un estado del enum
 * y ninguna es "hice algo parecido": un reintento sobre un terminal no es un
 * error, y un estado que la secuencia no puede producir **detiene**.
 */
export async function ejecutarRetiro({ fs, vaultRoot, repoId, raiz, flujo, label = 'retire' }) {
  const flowId = flujo.flowId;
  const estado = await observarEstado({ fs, vaultRoot, repoId, raiz, flowId, label });
  const decision = clasificarRetiro(estado);

  if (decision.accion === ACCIONES.DETENER) {
    throw new ContractError(
      'PRECONDITION_NOT_MET',
      `${flowId}: ${decision.estado} — la secuencia no produce este estado, así que su causa es externa`,
      { path: estado.objetivo, detail: decision },
    );
  }
  if (decision.accion === ACCIONES.NADA) {
    return {
      flowId,
      estado: decision.estado === ESTADOS_TABLA.TERMINAL_ALCANZADO ? RESULTADOS.YA_RETIRADO : RESULTADOS.NADA,
    };
  }
  if (decision.accion === ACCIONES.DESHACER) {
    await deshacerReclamo({ fs, raiz, flowId, label });
    return { flowId, estado: RESULTADOS.RECLAMO_DESHECHO };
  }
  if (decision.accion === ACCIONES.TERMINAR) {
    // La destrucción ya está autorizada: continúa desde donde quedó, con el
    // manifiesto como autoridad del conjunto.
    return { flowId, estado: await terminarDestruccion({ fs, vaultRoot, repoId, raiz, flowId, label }) };
  }

  // RECLAMAR: la secuencia completa desde cero.
  const remanente = await reclamar({ fs, raiz, flowId, label });
  let autorizado = false;
  try {
    // **Sobre el remanente**, que es el punto entero del orden: acá el flujo ya
    // salió de la ruta por la que otro proceso lo alcanzaría.
    const sonda = await estaASalvo({ fs, vaultRoot, repoId, flowId, flowDir: remanente });
    if (!sonda.aSalvo) {
      throw new ContractError(
        'VERIFY_FAILED',
        `${flowId}: la verificación sobre el remanente falló (${sonda.causa})` +
          (sonda.faltantes?.length ? `: ${sonda.faltantes[0]}` : ''),
        { path: remanente, detail: sonda },
      );
    }

    const vaultCommit = await headDelVault(vaultRoot);
    const manifiesto = await construirManifiesto({
      fs,
      flowDir: remanente,
      aSalvo: await rutasASalvo({ fs, root: remanente, label }),
      identidad: { repoId, flowId },
      vaultCommit,
      label: `${label}.manifest`,
    });
    await autorizar({ fs, vaultRoot, repoId, flowId, manifiesto, label });
    autorizado = true;
  } catch (error) {
    // Dos condiciones, y las dos hacen falta.
    //
    // **Sólo antes del commit.** Después del punto de no retorno el estado
    // durable es remanente + manifiesto; deshacer el reclamo ahí dejaría el
    // flujo de vuelta en su ruta **con** el manifiesto commiteado, que es
    // `OBJETIVO_RECREADO` y detiene para siempre.
    //
    // **Nunca ante una caída.** `InjectedCrash` representa que el proceso dejó
    // de existir: si se ejecutara algo después, no estaría representando eso. La
    // recuperación la hace el reintento leyendo el disco, que es justamente lo
    // que la tabla de adopción sabe clasificar.
    if (!autorizado && !isInjectedCrash(error)) {
      await deshacerReclamo({ fs, raiz, flowId, label });
    }
    throw error;
  }

  return { flowId, estado: await terminarDestruccion({ fs, vaultRoot, repoId, raiz, flowId, label }) };
}

/**
 * Después del punto de no retorno: destruir, con el **manifiesto** como autoridad.
 *
 * Tres reglas, y las tres vienen de un modo de fallar concreto:
 *
 * 1. **La autoridad es el manifiesto, no lo que hay en disco.** Enumerar lo
 *    presente daría el remanente —lo que sobrevivió a la caída anterior—, no el
 *    conjunto que alguien aprobó. Es la diferencia entre continuar y decidir de
 *    nuevo.
 * 2. **Lo que queda tiene que ser un subconjunto exacto**: mismos hashes y **sin
 *    sobrantes**. Un archivo nuevo o modificado aparecido entre la autorización y
 *    el reintento hace fallar **sin tocar nada**, porque nadie lo autorizó.
 * 3. **De a una entrada, nunca recursivo.** Un `rm -r` del remanente destruiría
 *    ese archivo sobrante en silencio, que es exactamente lo que la regla 2 viene
 *    a impedir. Los directorios se retiran en **postorden**, del más profundo al
 *    más superficial, porque uno sólo se puede quitar cuando ya está vacío.
 */
async function terminarDestruccion({ fs, vaultRoot, repoId, raiz, flowId, label }) {
  const remanente = rutaDelRemanente(raiz, flowId);
  const manifiesto = parseDocument(
    await fs.readFile(rutaDelManifiesto(vaultRoot, repoId, flowId), `${label}.manifiesto.read`),
    { expectSchema: SCHEMA_MANIFIESTO },
  );

  const presente = await scanInventory({ fs, root: remanente, label: `${label}.restante` });
  const autorizados = new Map(manifiesto.inventario.map((e) => [e.path, e.sha256]));
  const dirsAutorizados = new Set(manifiesto.directorios.map((d) => d.path));

  const sobrantes = [];
  for (const e of presente.files) {
    if (!autorizados.has(e.path)) { sobrantes.push(`${e.path} (no autorizado)`); continue; }
    if (autorizados.get(e.path) !== e.sha256) sobrantes.push(`${e.path} (modificado)`);
  }
  for (const d of presente.directories) {
    if (!dirsAutorizados.has(d.path)) sobrantes.push(`${d.path}/ (no autorizado)`);
  }
  if (sobrantes.length > 0) {
    throw new ContractError(
      'PRECONDITION_NOT_MET',
      `${flowId}: el remanente no es un subconjunto exacto del manifiesto: ${sobrantes.join(', ')}`,
      { path: remanente, detail: { sobrantes } },
    );
  }

  // De a uno, y un checkpoint por borrado: es lo que hace que la caída inyectada
  // caiga **entre** dos borrados y no sólo al principio o al final.
  for (const e of presente.files) {
    await fs.unlink(path.join(remanente, e.path), `${label}.destruir.archivo`);
    fs.checkpoint(`${label}.destruido.${e.path}`);
  }

  // Postorden: el más profundo primero. Se toman del manifiesto —la autoridad—
  // y no del escaneo, que sólo ve los que todavía existen.
  const enPostorden = [...dirsAutorizados].sort(
    (a, b) => b.split('/').length - a.split('/').length || (a < b ? 1 : -1),
  );
  for (const rel of enPostorden) {
    const abs = path.join(remanente, rel);
    if (!(await existe(fs, abs, `${label}.destruir.dir.lstat`))) continue;
    await fs.removeEmptyDir(abs, `${label}.destruir.dir`);
    fs.checkpoint(`${label}.destruido.dir.${rel}`);
  }

  await fs.removeEmptyDir(remanente, `${label}.destruir.raiz`);
  await fs.fsyncDir(raiz, `${label}.destruir.fsync-parent`);
  fs.checkpoint(`${label}.destruido`);
  return RESULTADOS.RETIRADO;
}
