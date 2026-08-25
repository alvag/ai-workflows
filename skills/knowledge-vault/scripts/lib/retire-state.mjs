/**
 * La tabla de adopción: `objetivo × remanente × manifiesto → acción`.
 *
 * Sin esto, el estado durable **por presencia** no es implementable: hay dos
 * señales en disco y ningún registro que diga qué significan juntas. La tabla es
 * ese significado, y es una función **pura** a propósito — quien la consulta ya
 * miró el disco; acá no se vuelve a mirar, para que el mismo estado observado
 * siempre dé la misma decisión.
 *
 * **Por qué no hay journal.** El diseño anterior persistía una fase y la leía al
 * reintentar, y esa fase podía contradecir al árbol. Acá la fase se **deriva del
 * estado observable**: el remanente sin manifiesto es un reclamo sin autorizar;
 * con manifiesto es una destrucción autorizada. Ninguna de las dos señales es
 * ambigua, y no hay una tercera que pueda desincronizarse.
 *
 * **La regla que cuesta defectos si se omite: la ruta original recreada tiene
 * precedencia sobre todo lo demás.** Si el flujo reapareció en su sitio mientras
 * el remanente sigue ahí, el original **no se toca nunca** y el estado del
 * remanente viaja como **detalle del mismo resultado**, no como un segundo estado
 * en competencia. Tratarlos como dos estados lleva a "termino la destrucción del
 * remanente y de paso reclamo el original", que destruye sobre una hipótesis.
 *
 * Los tres estados que **detienen** —objetivo recreado, colisión de nombres y
 * varios remanentes del mismo flujo— no son fallos de la secuencia: son estados
 * que la secuencia **no puede producir**, así que su causa es externa. Adivinarla
 * sería destruir sobre una hipótesis.
 */

/** Qué hacer. Enum cerrado: quien lo consuma ramifica sobre esto. */
export const ACCIONES = Object.freeze({
  NADA: 'NADA',
  RECLAMAR: 'RECLAMAR',
  DESHACER: 'DESHACER',
  TERMINAR: 'TERMINAR',
  DETENER: 'DETENER',
});

/** El estado observado. Cada combinación tiene exactamente uno. */
export const ESTADOS = Object.freeze({
  NADA_OCURRIO: 'NADA_OCURRIO',
  SIN_EMPEZAR: 'SIN_EMPEZAR',
  RECLAMO_SIN_AUTORIZAR: 'RECLAMO_SIN_AUTORIZAR',
  DESTRUCCION_AUTORIZADA: 'DESTRUCCION_AUTORIZADA',
  TERMINAL_ALCANZADO: 'TERMINAL_ALCANZADO',
  OBJETIVO_RECREADO: 'OBJETIVO_RECREADO',
  COLISION_DE_NOMBRES: 'COLISION_DE_NOMBRES',
  REMANENTES_MULTIPLES: 'REMANENTES_MULTIPLES',
});

/** De qué señal sale la decisión. Es la mitad del criterio, no una anotación. */
export const AUTORIDADES = Object.freeze({
  OBJETIVO: 'objetivo',
  REMANENTE: 'remanente',
  MANIFIESTO: 'manifiesto',
  PADRE: 'padre-del-objetivo',
});

/** Las cuatro celdas de `remanente × manifiesto`, que es donde vive la secuencia. */
function celda(hayRemanente, hayManifiesto) {
  if (hayRemanente && hayManifiesto) {
    return { estado: ESTADOS.DESTRUCCION_AUTORIZADA, autoridad: AUTORIDADES.MANIFIESTO, accion: ACCIONES.TERMINAR };
  }
  if (hayRemanente) {
    return { estado: ESTADOS.RECLAMO_SIN_AUTORIZAR, autoridad: AUTORIDADES.REMANENTE, accion: ACCIONES.DESHACER };
  }
  if (hayManifiesto) {
    return { estado: ESTADOS.TERMINAL_ALCANZADO, autoridad: AUTORIDADES.MANIFIESTO, accion: ACCIONES.NADA };
  }
  return { estado: ESTADOS.NADA_OCURRIO, autoridad: AUTORIDADES.PADRE, accion: ACCIONES.NADA };
}

/**
 * @param {object} estado
 * @param {boolean} estado.hayObjetivo el flujo está en su ruta original
 * @param {boolean} [estado.hayRemanente] hay un remanente reservado hermano
 * @param {boolean} estado.hayManifiesto el manifiesto está commiteado en el vault
 * @param {number|null} [estado.remanentes] cuántos remanentes de **este** flujo se vieron
 * @param {boolean} [estado.colisionDeNombres] el nombre reservado lo ocupa algo que no es un remanente
 * @returns {{estado: string, autoridad: string, accion: string, detalle: object|null}}
 */
export function clasificarRetiro({
  hayObjetivo,
  hayRemanente,
  hayManifiesto,
  remanentes = null,
  colisionDeNombres = false,
}) {
  const cuantos = remanentes === null ? (hayRemanente ? 1 : 0) : remanentes;
  const conRemanente = cuantos > 0;

  // Precedencia sobre todo lo demás: el original volvió a su sitio, así que no
  // se lo toca nunca. Lo que haya del retiro anterior viaja como detalle.
  if (hayObjetivo && (conRemanente || hayManifiesto)) {
    return {
      estado: ESTADOS.OBJETIVO_RECREADO,
      autoridad: AUTORIDADES.OBJETIVO,
      accion: ACCIONES.DETENER,
      detalle: { remanente: celda(conRemanente, hayManifiesto).estado, remanentes: cuantos },
    };
  }
  if (colisionDeNombres) {
    return {
      estado: ESTADOS.COLISION_DE_NOMBRES,
      autoridad: AUTORIDADES.OBJETIVO,
      accion: ACCIONES.DETENER,
      detalle: null,
    };
  }
  if (cuantos > 1) {
    return {
      estado: ESTADOS.REMANENTES_MULTIPLES,
      autoridad: AUTORIDADES.REMANENTE,
      accion: ACCIONES.DETENER,
      detalle: { remanentes: cuantos },
    };
  }
  if (hayObjetivo) {
    return {
      estado: ESTADOS.SIN_EMPEZAR,
      autoridad: AUTORIDADES.OBJETIVO,
      accion: ACCIONES.RECLAMAR,
      detalle: null,
    };
  }
  return { ...celda(conRemanente, hayManifiesto), detalle: null };
}
