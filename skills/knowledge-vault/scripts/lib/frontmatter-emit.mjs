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
 * **El numeral es la excepción, y no por escapes: por entrecomillado.** El parser
 * mira las comillas antes de descartar el comentario, así que un valor citado
 * vuelve literal con su `#` adentro. Un título derivado del encabezado de un
 * documento no lo elige quien archiva —una ronda de feedback que cita el número
 * de su PR lo trae puesto—, así que rechazarlo dejaba flujos inarchivables sin
 * más salida que editar el origen.
 *
 * Las tres clases irrepresentables que quedan están **medidas** contra el parser:
 *
 * | Se emite           | Se lee         |
 * |--------------------|----------------|
 * | `"envuelto"`       | `envuelto`     |
 * | `  con espacios  ` | `con espacios` |
 * | con carácter de control | otra clave, u otra línea |
 *
 * Y una cuarta que depende del contenido: un valor con `#` para el que no queda
 * delimitador seguro (ver `delimitador`).
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

/**
 * El delimitador con el que un valor con `#` se emite entero, o `null` si no hay
 * ninguno seguro.
 *
 * La comilla **simple** es la preferida, y no por gusto: dentro de comillas
 * simples YAML no interpreta ningún escape, así que el valor sale literal para
 * cualquier lector. La doble solo entra cuando el valor ya trae una simple, y
 * ahí exige que no haya ni comilla doble ni barra inversa — dentro de dobles
 * YAML sí procesa escapes, y una ruta como `C:\ruta` volvería inválido el
 * documento aunque el parser de acá lo releyera igual.
 */
function delimitador(valor) {
  if (!valor.includes("'")) return "'";
  if (!valor.includes('"') && !valor.includes('\\')) return '"';
  return null;
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
  if (valor.includes('#') && delimitador(valor) === null) {
    rechazar(
      `el valor de ${clave} tiene un # junto a una comilla simple y, además, una comilla doble o ` +
        'una barra inversa: no queda delimitador que lo devuelva idéntico',
      clave,
      valor,
    );
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

  // Solo se entrecomilla lo que lo necesita: un valor sin `#` se emite tal cual,
  // como siempre, para no reescribir los nodos que ya existen en un vault.
  const emitir = (v) => (v.includes('#') ? `${delimitador(v)}${v}${delimitador(v)}` : v);
  const texto = `---\n${entradas.map(([k, v]) => `${k}: ${emitir(v)}\n`).join('')}---\n`;

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
