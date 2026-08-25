/**
 * El nodo de un flujo: lo único que el vault escribe sobre él.
 *
 * Los documentos copiados **no se tocan**. Agregarles un frontmatter, un
 * encabezado o una nota de procedencia rompería la copia byte-idéntica de AC-1,
 * y con ella la única garantía que hace confiable al vault: que lo que se lee
 * ahí es lo que se escribió en su momento. Todo lo que el vault quiera decir
 * sobre un flujo vive en este archivo, que es hermano del directorio y no forma
 * parte de la frontera verificada.
 *
 * Módulo **puro**: no toca el disco. Y no rellena huecos —un campo ausente en
 * `metadata` es un error del llamador—, porque completar un dato que nadie
 * declaró es exactamente lo que el literal `desconocido` existe para no hacer.
 */

import { emitFrontmatter } from './frontmatter-emit.mjs';

/** Los ocho de AC-9, en el orden en que se emiten. */
const CAMPOS = ['type', 'title', 'project', 'flow', 'branch', 'date', 'provenance', 'state'];

export class NodeBuilderError extends Error {
  constructor(message) {
    super(message);
    this.name = 'NodeBuilderError';
    this.code = 'NODE_INCOMPLETE';
  }
}

/**
 * Enlace relativo desde el nodo hasta un documento.
 *
 * El nodo es `sdd/<flujo>.md` y los documentos viven en `sdd/<flujo>/`, así que
 * la ruta arranca en el nombre del flujo. Se codifica cada segmento: hoy ninguno
 * de los 277 documentos reales tiene un espacio o un paréntesis, pero un solo
 * nombre así rompería el enlace en silencio, y el texto visible se muestra sin
 * codificar para que se lea como el archivo se llama.
 */
function enlace(flowId, documento) {
  const destino = `${encodeURIComponent(flowId)}/${encodeURIComponent(documento)}`;
  return `- [${documento}](${destino})`;
}

/**
 * @param {{metadata: Record<string,string>, documents: string[], summary: string}} entrada
 * @returns {string} el nodo completo.
 */
export function buildNode({ metadata, documents = [], summary }) {
  if (metadata === null || typeof metadata !== 'object') {
    throw new NodeBuilderError('buildNode espera un objeto metadata con los ocho campos');
  }
  for (const campo of CAMPOS) {
    if (typeof metadata[campo] !== 'string') {
      throw new NodeBuilderError(`falta el campo ${campo} en metadata, y el builder no lo completa`);
    }
  }
  if (typeof summary !== 'string' || summary.trim().length === 0) {
    throw new NodeBuilderError(
      'falta el resumen (summary): sin él el índice no tendría nada que agregar sobre la ruta',
    );
  }
  if (!Array.isArray(documents)) throw new NodeBuilderError('documents tiene que ser una lista');

  // `emitFrontmatter` valida y relee: un resumen o un título irrepresentable
  // muere acá, antes de llegar al vault.
  const cabecera = emitFrontmatter({
    ...Object.fromEntries(CAMPOS.map((c) => [c, metadata[c]])),
    summary,
  });

  // Orden estable por nombre, no el de llegada: dos corridas con el mismo
  // conjunto de documentos tienen que producir los mismos bytes.
  const ordenados = [...documents].sort();
  const enlaces = ordenados.map((d) => enlace(metadata.flow, d));

  const cuerpo = [`# ${metadata.title}`, '', summary, ''];
  if (enlaces.length > 0) cuerpo.push('## Documentos', '', ...enlaces, '');
  return `${cabecera}\n${cuerpo.join('\n')}`;
}
