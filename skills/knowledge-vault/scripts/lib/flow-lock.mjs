/**
 * Exclusión en proceso alrededor de un flujo, y nada más.
 *
 * El lock del árbol de origen era transaccional —archivo en disco, dueño,
 * expiración, journal y recuperación— porque el retiro borraba el origen: una
 * corrida muerta a mitad de camino podía dejar el mundo sin ninguna copia. **El
 * archivado no borra nada**, así que ese aparato no tiene qué proteger y se fue
 * con el retiro.
 *
 * Queda un problema real y mucho más chico.
 * La identidad de flujo no distingue corridas concurrentes: dos archivados del
 * **mismo** flujo a la vez harían que uno recuperara el staging vivo del otro
 * como propio y lo borrara. Serializar las corridas sobre un mismo flujo
 * alcanza para eliminarlo.
 *
 * Lo que este lock **no** hace, dicho para que nadie lo confunda con el anterior:
 * no escribe journal, no sobrevive al proceso, y no excluye a otro proceso sobre
 * el mismo vault. Ese límite ya no se justifica en "sin operación destructiva lo
 * peor es un reintento": la recuperación acotada sí borra staging, y dos procesos
 * sin este lock pueden borrarse el staging vivo el uno al otro. Es un límite
 * aceptado: la corrida afectada aborta después en su tramo de copia,
 * verificación o publicación, el origen queda intacto porque el archivado nunca
 * lo toca, y un reintento puede reconstruir lo perdido. El retiro **no se apoya
 * en este lock** y conserva su propia defensa por **orden** —reclama el flujo
 * renombrándolo antes de verificarlo, y desde ahí ningún otro proceso lo
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
