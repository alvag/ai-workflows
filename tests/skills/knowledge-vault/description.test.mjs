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

import { VERBS } from '../../../skills/knowledge-vault/scripts/lib/contracts.mjs';
import { positivas, negativas, normalizar } from './fixtures/frases-enrutamiento.mjs';

const SKILL = path.resolve('skills/knowledge-vault/SKILL.md');
const REFERENCIA = path.resolve('skills/knowledge-vault/reference.md');
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
  // La lista se **deriva** de la tabla del contrato. Transcribirla acá dejaría
  // el test verde el día que aparece un verbo que la descripción no nombra, que
  // es justo el día que hay que detectar.
  for (const verbo of VERBS) {
    assert.ok(normalizada.includes(verbo), `la descripción no declara "${verbo}"`);
  }
  assert.ok(VERBS.length >= 5, `el contrato declara ${VERBS.length} verbos`);
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

/**
 * Los verbos que la matriz de `reference.md` documenta, leídos de su tabla.
 *
 * Se **derivan** del documento en vez de transcribirse: una lista copiada a mano
 * queda verde el día que la tabla se desactualiza, que es justo el día que hay
 * que detectar.
 */
function verbosDeLaMatriz(texto) {
  const desde = texto.indexOf('## Matriz por verbo');
  assert.notEqual(desde, -1, 'reference.md no tiene su matriz por verbo');
  const hasta = texto.indexOf('\n## ', desde + 1);
  const tabla = texto.slice(desde, hasta === -1 ? undefined : hasta);
  return [...tabla.matchAll(/^\| `([a-z-]+)` \|/gm)].map((m) => m[1]);
}

test('[AC-15] el detalle al que apunta la descripción existe de verdad', async () => {
  // La descripción manda a `reference.md` por el detalle de cada verbo. Un
  // puntero a un documento que no los documenta es peor que no tener puntero:
  // el agente lo sigue, no encuentra nada, y no tiene forma de saber si el verbo
  // no existe o si la documentación se quedó atrás.
  assert.ok(normalizada.includes('reference.md'), 'la descripción ya no apunta a reference.md');

  const referencia = await fs.readFile(REFERENCIA, 'utf8');
  assert.deepEqual(verbosDeLaMatriz(referencia).sort(), [...VERBS].sort());

  // Y estar en la tabla no es estar documentado: el verbo que destruye tiene su
  // sección propia, porque su contrato no entra en una fila.
  assert.match(referencia, /^#+ .*`retire`/m, 'reference.md no le dedica una sección al verbo que destruye');
});

test('[AC-15] el chequeo del puntero sabe ponerse rojo', () => {
  // Control positivo: es exactamente la forma que tenía el defecto —una matriz
  // con un verbo de menos mientras la descripción los declaraba todos—.
  const conCuatro = [
    '## Matriz por verbo', '',
    '| Verbo | Obligatorias |', '|---|---|',
    '| `archive` | x |', '| `migrate` | x |', '| `index` | x |', '| `config` | x |', '',
    '## Otra sección', '',
  ].join('\n');
  assert.deepEqual(verbosDeLaMatriz(conCuatro), ['archive', 'migrate', 'index', 'config']);
  assert.notDeepEqual(verbosDeLaMatriz(conCuatro).sort(), [...VERBS].sort());
});

/**
 * Los verbos que la tabla del **`SKILL.md`** documenta.
 *
 * Su tabla no tiene título propio —vive bajo un encabezado que también cubre otra
 * cosa—, así que se la reconoce por su cabecera literal en vez de por una sección,
 * y se lee hasta la primera línea que no es fila. Anclar por sección la haría
 * frágil justo ante el cambio que hay que detectar.
 */
function verbosDeLaTablaDelSkill(texto) {
  const cabecera = texto.indexOf('| Verbo | Qué hace | Estados |');
  assert.notEqual(cabecera, -1, 'SKILL.md no tiene su tabla de verbos');
  const filas = texto.slice(cabecera).split('\n');
  const verbos = [];
  for (const fila of filas.slice(2)) {
    if (!fila.startsWith('|')) break;
    const m = fila.match(/^\| `([a-z-]+)[ `]/);
    if (m) verbos.push(m[1]);
  }
  return [...new Set(verbos)];
}

test('[AC-15] la tabla del SKILL.md documenta los seis verbos, no sólo la de reference', async () => {
  // El mismo defecto tuvo dos sedes. Se arregló en `reference.md` y la guarda se
  // escribió sobre ese archivo, así que el `SKILL.md` siguió con cuatro filas
  // mientras la descripción declaraba seis: un agente que lo abriera para ver qué
  // puede hacer la skill no encontraba ni `retire` ni `identity`.
  const skill = await fs.readFile(SKILL, 'utf8');
  assert.deepEqual(verbosDeLaTablaDelSkill(skill).sort(), [...VERBS].sort());
});

test('[AC-15] el chequeo de la tabla del SKILL.md sabe ponerse rojo', () => {
  // Control positivo, con la forma exacta que tenía el defecto.
  const conCuatro = [
    '| Verbo | Qué hace | Estados |', '|---|---|---|',
    '| `archive --from <x>` | archiva | `ARCHIVED` |',
    '| `migrate --from <x>` | lote | `BATCH_OK` |',
    '| `index` | índices | `INDEX_OK` |',
    '| `config --config <x>` | config | `VAULT_SET` |', '',
    'texto suelto que corta la tabla',
  ].join('\n');
  assert.deepEqual(verbosDeLaTablaDelSkill(conCuatro), ['archive', 'migrate', 'index', 'config']);
  assert.notDeepEqual(verbosDeLaTablaDelSkill(conCuatro).sort(), [...VERBS].sort());
});

/** Numerales en español, para comparar el título contra la cantidad real. */
const NUMERAL = ['cero', 'un', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez'];

test('[AC-15] el título de la sección de verbos cuenta los que hay', async () => {
  // Tercera sede del mismo defecto. Primero se desactualizó la matriz de
  // `reference.md`, después la tabla del `SKILL.md`, y al arreglar esa tabla el
  // **título** de su sección siguió diciendo "Los cuatro verbos" con seis filas
  // debajo. Un párrafo más no lo iba a evitar: lo evita este caso.
  const skill = await fs.readFile(SKILL, 'utf8');
  const m = skill.match(/^## Los ([a-zé]+) verbos$/m);
  assert.ok(m, 'SKILL.md no tiene la sección "## Los <n> verbos"');
  assert.equal(m[1], NUMERAL[VERBS.length], `el título dice "${m[1]}" y hay ${VERBS.length} verbos`);
});

test('[AC-15] el chequeo del título sabe ponerse rojo', () => {
  // Control positivo con la forma exacta del defecto.
  const conCuatro = '## Los cuatro verbos\n';
  const m = conCuatro.match(/^## Los ([a-zé]+) verbos$/m);
  assert.equal(m[1], 'cuatro');
  assert.notEqual(m[1], NUMERAL[VERBS.length]);
});
