/**
 * Serializa el frontmatter del nodo de un flujo.
 *
 * **El parser hermano no es YAML y no tiene escapes.** `cleanValue` hace tres
 * cosas irreversibles —recorta, descarta un comentario `#` precedido de espacio
 * y saca comillas envolventes— y no ofrece ninguna secuencia que las revierta.
 *
 * Por eso este módulo **rechaza** en vez de escapar. Escapar exige que el lector
 * desescape; sin esa mitad, un valor "escapado" se lee distinto del original y el
 * archivo se ve perfectamente bien mientras miente. Y este frontmatter es la
 * única sede del resumen y del estado observado del flujo: justo los dos datos
 * que no pueden mutar en silencio.
 *
 * Las cuatro clases irrepresentables están **medidas** contra el parser:
 *
 * | Se emite           | Se lee         |
 * |--------------------|----------------|
 * | `"envuelto"`       | `envuelto`     |
 * | `con # numeral`    | `con`          |
 * | `#empieza`         | vacío          |
 * | `  con espacios  ` | `con espacios` |
 *
 * Contra el corpus real —los 45 encabezados de flujo que existen— ninguna de las
 * cuatro aparece; los `:` y las comillas interiores, que sí aparecen, vuelven
 * idénticos y no hace falta hacerles nada.
 *
 * Módulo **puro**: no toca el disco.
 */

import { parseFrontmatter } from './frontmatter.mjs';

/** La misma forma de clave que reconoce el parser. */
const CLAVE_RE = /^[A-Za-z0-9_-]+$/;
/** C0, DEL y C1: ninguno sobrevive a una línea de texto. */
const CONTROL_RE = /[\u0000-\u001F\u007F-\u009F]/;

export class FrontmatterEmitError extends Error {
  constructor(message, { key = null, value = null } = {}) {
    super(message);
    this.name = 'FrontmatterEmitError';
    this.code = 'FRONTMATTER_UNREPRESENTABLE';
    this.key = key;
    this.value = value;
  }
}

function rechazar(message, key, value) {
  throw new FrontmatterEmitError(message, { key, value });
}

function validarClave(clave) {
  if (typeof clave !== 'string' || !CLAVE_RE.test(clave)) {
    rechazar(
      `la clave ${JSON.stringify(clave)} no es una clave que el parser reconozca (${CLAVE_RE.source})`,
      clave,
      null,
    );
  }
}

function validarValor(clave, valor) {
  if (typeof valor !== 'string') rechazar(`el valor de ${clave} no es una cadena`, clave, valor);
  if (CONTROL_RE.test(valor)) {
    // El salto de línea es el que más se intenta escapar, y el que peor sale:
    // partiría el valor en una línea que el parser leería como otra clave.
    rechazar(`el valor de ${clave} tiene un carácter de control y no cabe en una línea`, clave, valor);
  }
  if (valor.includes('#')) {
    rechazar(`el valor de ${clave} tiene un # y el parser lo leería como comentario`, clave, valor);
  }
  if (valor !== valor.trim()) {
    rechazar(`el valor de ${clave} empieza o termina en espacio, que el parser recorta`, clave, valor);
  }
  if (valor.length >= 2 && (valor[0] === '"' || valor[0] === "'") && valor.at(-1) === valor[0]) {
    rechazar(`el valor de ${clave} está envuelto en comillas, que el parser saca`, clave, valor);
  }
}

/**
 * @param {Record<string,string>} fields campos escalares, en el orden de emisión.
 * @returns {string} el bloque completo, con sus marcas y su salto final.
 */
export function emitFrontmatter(fields) {
  if (fields === null || typeof fields !== 'object') {
    rechazar('emitFrontmatter espera un objeto de campos', null, fields);
  }
  const entradas = Object.entries(fields);
  for (const [clave, valor] of entradas) {
    validarClave(clave);
    validarValor(clave, valor);
  }

  const texto = `---\n${entradas.map(([k, v]) => `${k}: ${v}\n`).join('')}---\n`;

  // El control que vuelve estructural la promesa de round-trip: en vez de confiar
  // en que las validaciones de arriba cubren todo lo que `cleanValue` transforma,
  // se relee lo recién escrito. Una clase irrepresentable que se escapara de las
  // reglas muere acá, y no en el vault seis meses después.
  const leido = parseFrontmatter(texto);
  if (!leido.ok) rechazar('el bloque emitido no se puede volver a parsear', null, null);
  if (leido.duplicated.size > 0) {
    rechazar(`claves duplicadas: ${[...leido.duplicated].join(', ')}`, null, null);
  }
  for (const [clave, valor] of entradas) {
    if (leido.keys.get(clave) !== valor) {
      rechazar(
        `${clave} no sobrevive el round-trip: se emitió ${JSON.stringify(valor)} y se lee ` +
          `${JSON.stringify(leido.keys.get(clave))}`,
        clave,
        valor,
      );
    }
  }
  return texto;
}
