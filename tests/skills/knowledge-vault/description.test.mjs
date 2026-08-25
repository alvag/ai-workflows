/**
 * La `description` como router (AC-15).
 *
 * La fila que prueba este criterio **no busca una frase literal**. Buscar el
 * texto que uno mismo va a escribir es una guarda que se satisface escribiéndola:
 * pasa siempre y no mide nada. Acá se evalúa el corpus congelado contra la
 * descripción real, y se mide su longitud contra el límite del spec.
 *
 * El corpus vive aparte —`fixtures/frases-enrutamiento.mjs`— porque es el dato
 * congelado; esto es el evaluador, y tiene su propio control positivo.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

import { positivas, negativas, normalizar } from './fixtures/frases-enrutamiento.mjs';

const SKILL = path.resolve('skills/knowledge-vault/SKILL.md');
const LIMITE = 1024;

/**
 * Extrae la `description` del frontmatter y la pliega como lo haría YAML: es un
 * escalar plegado (`>-`), así que cada salto simple se vuelve un espacio. Sin
 * plegar, un término partido entre dos líneas no se encontraría nunca y la
 * medición de longitud contaría la indentación.
 */
function leerDescripcion(texto) {
  const lineas = texto.split('\n');
  const inicio = lineas.findIndex((l) => l.startsWith('description: >-'));
  assert.notEqual(inicio, -1, 'el frontmatter no declara description como escalar plegado');
  const cuerpo = [];
  for (const linea of lineas.slice(inicio + 1)) {
    if (!linea.startsWith('  ')) break;
    cuerpo.push(linea.trim());
  }
  assert.ok(cuerpo.length > 0, 'la description quedó vacía');
  return cuerpo.join(' ');
}

/** Términos de la entrada que faltan en la descripción normalizada. */
function faltantes(entrada, normalizada) {
  return entrada.terminos.filter((t) => !normalizada.includes(normalizar(t)));
}

/** Términos de la entrada que **están** en la descripción normalizada. */
function presentes(entrada, normalizada) {
  return entrada.terminos.filter((t) => normalizada.includes(normalizar(t)));
}

const descripcion = leerDescripcion(await fs.readFile(SKILL, 'utf8'));
const normalizada = normalizar(descripcion);

test('[AC-15] la descripción cubre todas las frases positivas', () => {
  const sinCubrir = positivas
    .map((e) => ({ frase: e.frase, faltan: faltantes(e, normalizada) }))
    .filter((r) => r.faltan.length > 0);
  assert.deepEqual(sinCubrir, [], 'hay frases que no enrutarían');
  // El corpus tiene que ser el congelado, no uno vacío que pasa por vacuidad.
  assert.ok(positivas.length >= 6, `el corpus positivo trae ${positivas.length} frases`);
});

test('[AC-15] ninguna frase negativa queda cubierta', () => {
  const coladas = [];
  for (const entrada of negativas) {
    if (entrada.clase === 'ausente') {
      const hay = presentes(entrada, normalizada);
      if (hay.length > 0) coladas.push(`${entrada.frase} → aparece ${hay.join(', ')}`);
      continue;
    }
    // `negada`: sus palabras SÍ están, justamente porque la descripción las
    // niega. Un término ausente no probaría nada acá; lo que se exige es el
    // literal de la negación.
    assert.equal(entrada.clase, 'negada', `clase desconocida: ${entrada.clase}`);
    if (!normalizada.includes(normalizar(entrada.negacion))) {
      coladas.push(`${entrada.frase} → falta la negación "${entrada.negacion}"`);
    }
  }
  assert.deepEqual(coladas, [], 'hay frases que enrutarían y no deberían');
  assert.ok(negativas.length >= 6, `el corpus negativo trae ${negativas.length} frases`);
});

test('[AC-15] declara el quinto verbo, conserva la cláusula y entra en el límite', () => {
  for (const verbo of ['archive', 'migrate', 'index', 'config', 'retire']) {
    assert.ok(normalizada.includes(verbo), `la descripción no declara "${verbo}"`);
  }
  assert.ok(
    normalizada.includes('no invocarla espontaneamente'),
    'se perdió la cláusula que impide la invocación espontánea',
  );
  assert.ok(
    descripcion.length <= LIMITE,
    `la descripción mide ${descripcion.length} y el límite es ${LIMITE}`,
  );
});

test('[AC-15] el evaluador sabe ponerse rojo en las dos direcciones', () => {
  // Control positivo. Sin esto, un verde no distingue "la descripción cubre el
  // corpus" de "el evaluador no compara nada".
  const sintetica = normalizar('Archiva un flujo. No invocarla espontáneamente.');
  assert.deepEqual(faltantes({ terminos: ['boveda'] }, sintetica), ['boveda']);
  assert.deepEqual(faltantes({ terminos: ['archiva'] }, sintetica), []);
  assert.deepEqual(presentes({ terminos: ['flujo', 'diff'] }, sintetica), ['flujo']);
  // Y la longitud: el límite tiene que poder violarse.
  assert.ok('x'.repeat(LIMITE + 1).length > LIMITE);
});
