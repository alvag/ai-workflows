/**
 * Corpus **congelado** de frases de enrutamiento (AC-15).
 *
 * El criterio dice que la `description` cubre todas las positivas y ninguna de
 * las negativas. "Y frases equivalentes" no sería comprobable: una descripción
 * puede afirmar que las cubre sin que exista ninguna negación observable. Por eso
 * cada entrada declara **qué se mide**, y no se deja al evaluador adivinarlo:
 *
 * - una **positiva** declara los `terminos` que su enrutamiento necesita; todos
 *   tienen que estar en la descripción.
 * - una **negativa** declara **cómo** queda excluida, y hay exactamente dos
 *   formas. `ausente`: ninguno de sus términos aparece, porque la frase cae
 *   fuera del dominio. `negada`: la frase está cerca del dominio y sus palabras
 *   sí aparecen —justamente porque la descripción las está negando—, así que lo
 *   que se exige es el literal de esa negación.
 *
 * La segunda forma existe por una razón medida: un `grep` no distingue una
 * descripción que **ofrece** una capacidad de una que la **niega**, y las dos
 * contienen la misma palabra.
 *
 * Los términos van **sin acentos y en minúscula**: el evaluador normaliza la
 * descripción igual antes de comparar, y se comparan por prefijo para que
 * "consult" cubra "consultable".
 */

export const positivas = [
  { frase: 'archivá este documento', terminos: ['archiv', 'documento'] },
  { frase: 'guardá esto en el vault', terminos: ['guard', 'vault'] },
  { frase: 'sacá este flujo a la bóveda', terminos: ['sac', 'flujo', 'boveda'] },
  { frase: 'quiero consultar lo que se decidió en un flujo', terminos: ['consult', 'decid', 'flujo'] },
  { frase: 'retirá el origen que ya está copiado', terminos: ['retir', 'origen', 'copi'] },
  { frase: 'archivá lo que quedó en .plans/archived/', terminos: ['archiv', '.plans/archived'] },
  { frase: 'dejá esto consultable en markdown versionado', terminos: ['consult', 'markdown', 'git'] },
];

export const negativas = [
  { frase: 'corré los tests de este módulo', clase: 'ausente', terminos: ['test'] },
  { frase: 'abrí un pull request con esto', clase: 'ausente', terminos: ['pull request'] },
  { frase: 'creá la rama del ticket', clase: 'ausente', terminos: ['rama', 'ticket'] },
  { frase: 'revisá este diff línea por línea', clase: 'ausente', terminos: ['diff'] },
  { frase: 'resumime este flujo en un párrafo', clase: 'negada', negacion: 'no resume' },
  { frase: 'enlazá los documentos por contenido', clase: 'negada', negacion: 'no enlaza por contenido' },
  { frase: 'buscá esto por significado, no por palabra', clase: 'negada', negacion: 'indexador semantico' },
];

/** Minúsculas y sin diacríticos: es lo único que el evaluador compara. */
export function normalizar(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}
