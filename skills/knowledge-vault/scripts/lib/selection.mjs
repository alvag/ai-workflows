/**
 * Qué documentos de un flujo SDD forman la frontera verificada del vault.
 *
 * La versión anterior clasificaba por contenido con nueve reglas y un esquema.
 * Dejó pasar andamiaje de proceso —transcripciones, pruebas y veredictos— porque
 * es texto legítimo; por eso el corte que discrimina es posicional, no semántico.
 * Esta versión admite once sufijos en la raíz y recursivamente bajo tres
 * directorios de primer nivel exactos. PDF y otros primeros niveles quedan
 * fuera; no se inspecciona contenido ni tamaño.
 *
 * La medición del selector anterior sobre cincuenta flujos fue de 277 copiados
 * y 10.726 omitidos. Es histórica, no reproducible sin esos orígenes y no mide
 * la frontera ampliada.
 *
 * Módulo puro: recibe rutas relativas POSIX del inventario de `tree.mjs` y
 * no toca disco.
 */

export const ALLOWED_EXTENSIONS = Object.freeze([
  '.md',
  '.sh',
  '.js',
  '.mjs',
  '.py',
  '.ts',
  '.ps1',
  '.json',
  '.yml',
  '.txt',
  '.jsonl',
]);

export const OPT_IN_DIRECTORIES = Object.freeze([
  'evidencia',
  'runs',
  'decisiones',
]);

/**
 * @param {string} relativePath ruta relativa a la raíz del flujo, con `/`.
 * @returns {boolean} verdadero si la ruta pertenece a la frontera documental.
 */
export function isCopiable(relativePath) {
  if (typeof relativePath !== 'string') return false;

  const segments = relativePath.split('/');
  if (segments.length > 1 && !OPT_IN_DIRECTORIES.includes(segments[0])) return false;

  const basename = segments.at(-1);
  if (!basename) return false;

  const lowercaseBasename = basename.toLowerCase();
  return ALLOWED_EXTENSIONS.some(
    (extension) => basename.length > extension.length && lowercaseBasename.endsWith(extension),
  );
}

/**
 * Detecta Markdown cuyo padre inmediato es el segmento reservado `sdd`.
 * Los llamadores aplican esta guarda solo a rutas seleccionadas en la primera
 * publicación.
 *
 * @param {string} relativePath ruta relativa POSIX.
 * @returns {boolean} verdadero si colisiona con el namespace de nodos.
 */
export function isReservedDocumentPath(relativePath) {
  if (typeof relativePath !== 'string') return false;

  const segments = relativePath.split('/');
  const basename = segments.at(-1);
  return segments.length > 1 && segments.at(-2) === 'sdd' && basename.endsWith('.md');
}
