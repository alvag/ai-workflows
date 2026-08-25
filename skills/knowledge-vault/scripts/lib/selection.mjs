/**
 * Qué documento de un flujo SDD entra al vault.
 *
 * Un predicado y nada más. La versión anterior tenía nueve reglas, un esquema y
 * una partición total con decisiones nombradas; filtraba **salida cruda de
 * máquina** y por eso el andamiaje de proceso —transcripciones de revisión,
 * árboles de prueba, veredictos— pasaba entero, porque es texto legítimo.
 *
 * El corte real es posicional, no de contenido: **lo que el flujo decidió vive en
 * la raíz de su directorio; lo que usó para decidirlo vive en subdirectorios.**
 * Medido sobre cincuenta flujos archivados, copia 277 documentos y omite 10.726.
 *
 * Módulo **puro**: no toca el disco. Recibe la ruta relativa a la raíz del flujo,
 * tal como la emite el inventario de `tree.mjs`, que la arma siempre con `/`.
 */

const EXTENSION = '.md';

/**
 * @param {string} relativePath ruta relativa a la raíz del flujo, con `/`.
 * @returns {boolean} verdadero si y sólo si no contiene separador y termina en `.md`.
 */
export function isCopiable(relativePath) {
  if (typeof relativePath !== 'string') return false;
  if (relativePath.includes('/')) return false;
  if (relativePath.length <= EXTENSION.length) return false;
  // Sólo la extensión se compara sin distinguir mayúsculas, y con `toLowerCase`
  // sobre los tres últimos caracteres ASCII: bajar el nombre entero haría trabajo
  // Unicode sobre texto que no se compara, y el repertorio de nombres es completo.
  return relativePath.slice(-EXTENSION.length).toLowerCase() === EXTENSION;
}
