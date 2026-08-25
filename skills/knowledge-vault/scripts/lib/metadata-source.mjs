/**
 * Los ocho campos que el nodo de un flujo declara, y de dónde sale cada uno.
 *
 * **Nunca se infiere del sistema de archivos.** La tentación concreta es la
 * fecha: el directorio tiene `mtime` y siempre está ahí, así que usarlo parece
 * gratis. Pero copiar el flujo al vault lo reescribe, con lo cual esa fecha sería
 * la de la migración disfrazada de fecha del trabajo — plausible, y falsa. Un
 * campo sin fuente **persistida** vale `desconocido`, que es una afirmación
 * verdadera, y no un dato inventado que nadie va a volver a cuestionar.
 *
 * La cadena de autoridad, por campo:
 *
 * | Campo        | De dónde |
 * |--------------|----------|
 * | `type`       | constante: todo lo que entra por acá nace de un flujo SDD |
 * | `title`      | encabezado `# ` de `spec.md` → el de `plan.md` → el id del flujo |
 * | `project`    | el `repoSlug` que da el llamador |
 * | `flow`       | el `flowId` que da el llamador |
 * | `branch`     | `branch` del frontmatter de `plan.md` → `desconocido` |
 * | `date`       | `created_at` del frontmatter de `plan.md` → `desconocido` |
 * | `provenance` | las dos últimas partes de la ubicación de origen, más el id |
 * | `state`      | `status` del frontmatter de `plan.md`, **literal** → `desconocido` |
 *
 * Medido sobre los cincuenta flujos archivados: 43 tienen `plan.md` y los 43
 * declaran los tres campos; 45 títulos salen de `spec.md` y ninguno de `plan.md`,
 * aunque ese escalón se conserva porque el corpus de otro repositorio no tiene
 * por qué parecerse a éste.
 */

import fs from 'node:fs/promises';
import path from 'node:path';

import { parseFrontmatter } from './frontmatter.mjs';

/** El literal que ocupa el lugar de un campo sin fuente. Nunca se omite el campo. */
export const DESCONOCIDO = 'desconocido';

const TIPO = 'sdd-flow';

async function leerSiExiste(ruta) {
  try {
    return await fs.readFile(ruta, 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'EISDIR') return null;
    throw error;
  }
}

/**
 * Las claves de primer nivel del frontmatter de `plan.md`.
 *
 * Un bloque que no cierra se trata como **ausente**, no como parcial: el parser
 * ya devuelve `ok: false` para ese caso, y leer las claves que alcanzó a ver
 * antes de romperse daría un frontmatter a medias que nadie escribió.
 */
async function clavesDelPlan(flowDir) {
  const texto = await leerSiExiste(path.join(flowDir, 'plan.md'));
  if (texto === null) return null;
  const { ok, keys } = parseFrontmatter(texto);
  return ok ? keys : null;
}

/** El primer encabezado de nivel 1 del documento, sin su marca. */
async function primerEncabezado(ruta) {
  const texto = await leerSiExiste(ruta);
  if (texto === null) return null;
  for (const linea of texto.split('\n')) {
    if (linea.startsWith('# ')) {
      const titulo = linea.slice(2).trim();
      if (titulo.length > 0) return titulo;
    }
  }
  return null;
}

/**
 * La ubicación de origen, sin la ruta absoluta de la máquina.
 *
 * Se queda con los **dos últimos** segmentos del directorio contenedor, que en el
 * caso normal dan `.plans/archived`. Publicar la ruta absoluta metería el home de
 * quien migró dentro de un vault versionado, y publicar sólo el id perdería de
 * qué carpeta salió.
 */
function procedencia(flowDir, flowId) {
  const partes = path.dirname(flowDir).split(path.sep).filter((s) => s.length > 0);
  return [...partes.slice(-2), flowId].join('/');
}

/**
 * @param {{flowDir: string, flowId: string, repoSlug: string}} entrada
 * @returns {Promise<Record<string,string>>} exactamente los ocho campos, en orden.
 */
export async function resolveMetadata({ flowDir, flowId, repoSlug }) {
  const plan = await clavesDelPlan(flowDir);
  // `?? DESCONOCIDO` sólo cubre la clave **ausente**. Una clave declarada vacía
  // se copia vacía: decidir que un valor vacío "en realidad" es desconocido sería
  // normalizar, y el estado se pide explícitamente sin normalizar.
  const declarado = (clave) => plan?.get(clave) ?? DESCONOCIDO;

  const title =
    (await primerEncabezado(path.join(flowDir, 'spec.md'))) ??
    (await primerEncabezado(path.join(flowDir, 'plan.md'))) ??
    flowId;

  return {
    type: TIPO,
    title,
    project: repoSlug,
    flow: flowId,
    branch: declarado('branch'),
    date: declarado('created_at'),
    provenance: procedencia(flowDir, flowId),
    state: declarado('status'),
  };
}
