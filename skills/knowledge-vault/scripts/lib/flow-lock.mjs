/**
 * Exclusión en proceso alrededor de un flujo, y nada más.
 *
 * El lock del árbol de origen era transaccional —archivo en disco, dueño,
 * expiración, journal y recuperación— porque el retiro borraba el origen: una
 * corrida muerta a mitad de camino podía dejar el mundo sin ninguna copia. **El
 * archivado no borra nada**, así que ese aparato no tiene qué proteger y se fue
 * con el retiro.
 *
 * Queda un problema real y mucho más chico. `discardOrphanStagings` barre por
 * prefijo, así que dos archivados del **mismo** flujo a la vez harían que uno
 * leyera el staging vivo del otro como huérfano y lo borrara. Serializar las
 * corridas sobre un mismo flujo alcanza para eliminarlo.
 *
 * Lo que este lock **no** hace, dicho para que nadie lo confunda con el anterior:
 * no escribe journal, no sobrevive al proceso, y no excluye a otro proceso sobre
 * el mismo vault. Eso último se justificaba en que sin operación destructiva lo
 * peor entre dos procesos era un reintento, y esa frase dejó de ser verdadera con
 * el verbo de retiro. La conclusión no cambia, pero por otra razón: **el retiro
 * no se apoya en este lock**. Cierra su carrera por el **orden** —reclama el
 * flujo renombrándolo antes de verificarlo, y desde ahí ningún otro proceso lo
 * alcanza por su ruta original—, que es exclusión sin lock.
 */

/** Clave → promesa de la última corrida encolada. */
const colas = new Map();

/** Separador que no puede aparecer en una ruta ni en un id de flujo. */
const SEP = '\u0000';

/**
 * Corre `fn` con exclusión sobre `(vaultRoot, flowId)`.
 *
 * Las corridas se encadenan en orden de llegada, y el eslabón siguiente arranca
 * pase lo que pase con el anterior: si una falla, la que espera no queda colgada.
 *
 * @returns {Promise<*>} lo que devuelva `fn`.
 */
export async function withFlowLock(vaultRoot, flowId, fn) {
  const clave = `${vaultRoot}${SEP}${flowId}`;
  const anterior = colas.get(clave) ?? Promise.resolve();

  // `then(fn, fn)`: el eslabón siguiente arranca haya salido bien o mal el
  // anterior. Encadenar la promesa cruda propagaría al que espera un error que
  // no es suyo.
  const corrida = anterior.then(fn, fn);
  const publicada = corrida.then(() => undefined, () => undefined);
  colas.set(clave, publicada);

  try {
    return await corrida;
  } finally {
    // Sin esto el Map crece una entrada por flujo y no se vacía nunca. Comparar
    // la **identidad** de la promesa es lo que distingue "soy el último de la
    // cola" de "ya hay otro esperando detrás"; borrar sin comparar dejaría a ese
    // otro sin su eslabón y rompería la exclusión.
    if (colas.get(clave) === publicada) colas.delete(clave);
  }
}

/** Cuántas claves tiene la cola. Sirve para comprobar que no crece sin fin. */
export function tamanoDeLaCola() {
  return colas.size;
}
