/**
 * El subconjunto de YAML que este verbo necesita: localizar una sección de primer
 * nivel, emitir un escalar citado y calcular una inserción de líneas.
 *
 * **No es un parser de YAML y no aspira a serlo.** Se reconoce lo que hace falta y
 * se **rechaza** todo lo demás, porque la alternativa —adivinar— cambiaría el
 * archivo del usuario. La lista de rechazos es la parte importante del módulo.
 *
 * Puro: no toca el filesystem. Quien lee y escribe es `commands/config.mjs`.
 */

export const SECTION_KEY = 'knowledge-vault';
export const VALUE_KEY = 'path_vault';

export class ConfigYamlError extends Error {
  constructor(message, { detail = null } = {}) {
    super(message);
    this.name = 'ConfigYamlError';
    this.code = 'CONFIG_INVALID';
    this.detail = detail;
  }
}

/** Las formas de la clave que YAML considera **la misma** que `knowledge-vault:`. */
const CLAVES_EQUIVALENTES = Object.freeze([
  `${SECTION_KEY}:`,
  `"${SECTION_KEY}":`,
  `'${SECTION_KEY}':`,
]);

const esComentarioOVacia = (linea) => linea.trim().length === 0 || linea.trimStart().startsWith('#');

/** `true` si la línea abre la sección en columna 0, en cualquiera de sus tres formas. */
function abreSeccion(linea) {
  return CLAVES_EQUIVALENTES.some((clave) => linea === clave || linea.startsWith(`${clave} `));
}

export function locateSection(texto) {
  const bom = texto.startsWith('\ufeff');
  const cuerpo = bom ? texto.slice(1) : texto;
  // El terminador **dominante**: se emite el mismo que ya usa el archivo.
  const eol = cuerpo.includes('\r\n') ? '\r\n' : '\n';
  const lineas = cuerpo.split(/\r?\n/);

  let keyLine = null;

  for (const [i, linea] of lineas.entries()) {
    const limpia = linea.trimEnd();

    // Un separador de documentos en columna 0: no está definido en cuál de los
    // documentos va la sección, así que no se elige.
    if (limpia === '---' || limpia === '...') {
      if (i > 0 || limpia === '...') {
        throw new ConfigYamlError('el config tiene más de un documento YAML; no está definido en cuál va la sección');
      }
      continue;
    }
    if (esComentarioOVacia(linea)) continue;

    if (abreSeccion(limpia)) {
      if (keyLine !== null) {
        throw new ConfigYamlError(`la clave ${SECTION_KEY} aparece más de una vez en primer nivel`);
      }
      // Citada: es la misma clave para YAML, pero insertar dentro con seguridad
      // exigiría normalizarla, y tratarla como ausente anexaría un duplicado.
      if (!limpia.startsWith(`${SECTION_KEY}:`)) {
        throw new ConfigYamlError(`la clave ${SECTION_KEY} está citada; normalizala a la forma sin comillas`);
      }
      const resto = limpia.slice(`${SECTION_KEY}:`.length).trim();
      if (resto.length > 0) {
        throw new ConfigYamlError(
          `${SECTION_KEY} tiene un valor en su misma línea (${JSON.stringify(resto)}); ` +
            'tiene que ser un mapa en bloque para poder insertarle una clave',
        );
      }
      keyLine = i;
      continue;
    }

    // Indentada en cualquier profundidad: solo se acepta en primer nivel.
    if (linea.startsWith(' ') && linea.trimStart().startsWith(`${SECTION_KEY}:`)) {
      throw new ConfigYamlError(`${SECTION_KEY} aparece anidada; solo se acepta como clave de primer nivel`);
    }
  }

  if (keyLine === null) return { present: false, keyLine: null, childIndent: null, valueLine: null, eol, bom };

  return { present: true, keyLine, ...analizarHijas(lineas, keyLine), eol, bom };
}

/** Recorre el bloque hijo: su indentación y dónde está `path_vault`. */
function analizarHijas(lineas, keyLine) {
  let childIndent = null;
  let valueLine = null;

  for (let i = keyLine + 1; i < lineas.length; i += 1) {
    const linea = lineas[i];
    if (linea.length === 0) continue;
    // Vuelve a columna 0 → terminó el bloque.
    if (!/^[ \t]/.test(linea)) break;
    if (linea.includes('\t')) {
      throw new ConfigYamlError('el bloque usa tabuladores para indentar, y YAML los prohíbe');
    }

    const sangria = linea.slice(0, linea.length - linea.trimStart().length);
    // Un comentario indentado no fija la indentación de las hermanas: puede estar
    // alineado de cualquier forma y sigue siendo legítimo.
    if (linea.trimStart().startsWith('#')) continue;
    if (childIndent === null) childIndent = sangria;

    if (linea.trimStart().startsWith(`${VALUE_KEY}:`)) {
      if (valueLine !== null) {
        throw new ConfigYamlError(`${VALUE_KEY} aparece más de una vez dentro de ${SECTION_KEY}`);
      }
      valueLine = i;
    }
  }

  return { childIndent: childIndent ?? '  ', valueLine };
}

/** C0, DEL y C1: los que un escalar citado admitiría escapados y acá se rechazan. */
const CONTROL_RE = /[\u0000-\u001f\u007f-\u009f]/;

/**
 * El valor como escalar **double-quoted**, siempre.
 *
 * No hay rama "si el path es simple, lo emito plano": una sola forma de emisión no
 * tiene una segunda forma que se pueda equivocar. Y la forma plana es peligrosa —
 * `resolveVaultRoot` valida rutas, no YAML, así que acepta `#`, `:` y saltos de
 * línea. Un `/vaults/proyecto#1` plano se lee `/vaults/proyecto`, y el archivado
 * verificado por hash termina en un directorio que el usuario no pidió.
 *
 * Se escapan solo `\` y `"`, que es lo mínimo que la forma exige. Eso hace que el
 * resultado sea también un string JSON válido, y por eso el test puede releerlo con
 * `JSON.parse` sin escribir un lector aparte.
 */
export function emitQuoted(valor) {
  if (typeof valor !== 'string' || valor.length === 0) {
    throw new ConfigYamlError(`${VALUE_KEY} tiene que ser una cadena no vacía`);
  }
  if (CONTROL_RE.test(valor)) {
    throw new ConfigYamlError(
      `${VALUE_KEY} contiene un carácter de control; una ruta con un salto de línea o un tabulador ` +
        'corrompería el config',
    );
  }
  return `"${valor.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

/** Desenvuelve un escalar citado; un valor plano se devuelve recortado. */
function desenvolver(crudo) {
  const v = crudo.trim();
  if (v.length === 0) return null;
  if (v.startsWith('"') && v.endsWith('"') && v.length >= 2) {
    return v.slice(1, -1).replace(/\\"/g, '"').replace(/\\\\/g, '\\');
  }
  if (v.startsWith("'") && v.endsWith("'") && v.length >= 2) {
    return v.slice(1, -1).replace(/''/g, "'");
  }
  // Plano: lo que un humano escribió a mano. Se lee, pero al escribir se cita.
  return v;
}

export function readPathVault(texto) {
  const ubicacion = locateSection(texto);
  if (!ubicacion.present || ubicacion.valueLine === null) return null;

  const cuerpo = ubicacion.bom ? texto.slice(1) : texto;
  const linea = cuerpo.split(/\r?\n/)[ubicacion.valueLine];
  return desenvolver(linea.slice(linea.indexOf(':') + 1));
}

/**
 * Inserta o reemplaza `path_vault`, **por líneas**.
 *
 * Nunca un round-trip: parsear el YAML a memoria y volver a serializarlo perdería
 * los comentarios, reordenaría las claves y normalizaría las comillas. Insertar
 * líneas preserva todo lo demás **por construcción**, que es más fuerte que
 * preservarlo con cuidado.
 */
export function upsertPathVault(texto, root) {
  const valor = emitQuoted(root);
  const ubicacion = locateSection(texto);
  const { eol, bom } = ubicacion;
  const prefijo = bom ? '\ufeff' : '';
  const cuerpo = bom ? texto.slice(1) : texto;

  // Caso 2 y 1: la sección no está → anexar al final.
  if (!ubicacion.present) {
    const base = cuerpo.length === 0 ? '' : cuerpo.endsWith(eol) ? cuerpo : `${cuerpo}${eol}`;
    return {
      text: `${prefijo}${base}${SECTION_KEY}:${eol}  ${VALUE_KEY}: ${valor}${eol}`,
      changed: true,
    };
  }

  const lineas = cuerpo.split(/\r?\n/);

  // Caso 4: la clave ya está → reemplazar el valor de esa línea y nada más.
  if (ubicacion.valueLine !== null) {
    const actual = lineas[ubicacion.valueLine];
    if (desenvolver(actual.slice(actual.indexOf(':') + 1)) === root) {
      return { text: texto, changed: false };
    }
    const sangria = actual.slice(0, actual.length - actual.trimStart().length);
    lineas[ubicacion.valueLine] = `${sangria}${VALUE_KEY}: ${valor}`;
    return { text: `${prefijo}${lineas.join(eol)}`, changed: true };
  }

  // Caso 3: la sección está sin la clave → primera hija, con la indentación de sus
  // hermanas (o dos espacios si no tiene ninguna).
  lineas.splice(ubicacion.keyLine + 1, 0, `${ubicacion.childIndent}${VALUE_KEY}: ${valor}`);
  return { text: `${prefijo}${lineas.join(eol)}`, changed: true };
}
