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
import { parseFrontmatter } from './frontmatter.mjs';
import { assertContainedPath, encodeRelativePath } from './portable-path.mjs';

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
 * la ruta arranca en el nombre del flujo. En el corpus histórico de 277
 * documentos del selector anterior no había espacios ni paréntesis; esa cifra
 * no es reproducible sin los orígenes ni extrapolable a la frontera ampliada.
 * Un solo nombre así rompería el enlace si no se codifica. Se codifica cada
 * segmento sin codificar las barras, y la etiqueta visible conserva el nombre.
 */
function enlace(flowId, documento) {
  const destino = encodeRelativePath(`${flowId}/${documento}`);
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

export class PublishedNodeError extends Error {
  constructor(message) {
    super(message);
    this.name = 'PublishedNodeError';
    this.code = 'NODE_UNREADABLE';
  }
}

/**
 * Lee los metadatos del nodo que necesitan archivado e índices.
 * Cuando se conoce el id del flujo, exige que `flow` coincida: la sonda y la
 * reconstrucción histórica lo necesitan. El indexador no impone esa igualdad
 * retroactivamente a nodos ya publicados; conserva las tres claves requeridas.
 */
export function parsePublishedNodeMetadata(text, flowId) {
  const { ok, keys } = parseFrontmatter(text);
  const required = ['title', 'summary', 'flow'];
  const missing = required.filter((key) => !ok || !keys.has(key));
  if (missing.length > 0) {
    throw new PublishedNodeError(`el nodo no declara ${missing.join(', ')} en su frontmatter`);
  }
  if (flowId !== undefined && keys.get('flow') !== flowId) {
    throw new PublishedNodeError(
      `el nodo declara el flujo ${JSON.stringify(keys.get('flow'))}, se esperaba ${JSON.stringify(flowId)}`,
    );
  }
  return Object.fromEntries(required.map((key) => [key, keys.get(key)]));
}

/** Recupera el conjunto exacto de documentos declarado por un nodo publicado. */
export function parsePublishedNode(text, flowId) {
  const metadata = parsePublishedNodeMetadata(text, flowId);
  const lines = text
    .replace(/^\uFEFF/, '')
    .split('\n')
    .map((line) => (line.endsWith('\r') ? line.slice(0, -1) : line));
  const headings = lines.flatMap((line, index) => (line === '## Documentos' ? [index] : []));
  if (headings.length === 0) return { metadata, documents: [] };
  if (headings.length !== 1) {
    throw new PublishedNodeError('el nodo declara más de una sección ## Documentos');
  }

  const start = headings[0] + 1;
  const nextHeading = lines.findIndex((line, index) => index >= start && /^##(?:\s|$)/.test(line));
  const body = lines.slice(start, nextHeading === -1 ? undefined : nextHeading).filter((line) => line.trim() !== '');
  if (body.length === 0) {
    throw new PublishedNodeError('la sección ## Documentos está presente pero vacía');
  }

  const encodedFlow = encodeURIComponent(flowId);
  const documents = body.map((line) => {
    const match = /^- \[(.*)\]\((.+)\)$/.exec(line);
    if (match === null) {
      throw new PublishedNodeError(`contenido inválido en ## Documentos: ${JSON.stringify(line)}`);
    }

    // La etiqueta es presentación; el target es la autoridad del documento.
    // Exigir igualdad ahora invalidaría nodos históricos con etiquetas propias.
    const targetSegments = match[2].split('/');
    if (targetSegments.length < 2 || targetSegments.shift() !== encodedFlow) {
      throw new PublishedNodeError(`target fuera del flujo ${JSON.stringify(flowId)}: ${JSON.stringify(match[2])}`);
    }

    let decoded;
    try {
      decoded = targetSegments.map(decodeURIComponent).join('/');
      assertContainedPath(decoded);
    } catch {
      throw new PublishedNodeError(`target no recuperable en ## Documentos: ${JSON.stringify(match[2])}`);
    }
    if (encodeRelativePath(decoded) !== targetSegments.join('/')) {
      throw new PublishedNodeError(`target no canónico en ## Documentos: ${JSON.stringify(match[2])}`);
    }
    return decoded;
  });

  if (new Set(documents).size !== documents.length) {
    throw new PublishedNodeError('la sección ## Documentos repite un target');
  }
  return { metadata, documents };
}
