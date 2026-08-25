/**
 * Los cuatro verbos, sus estados y sus códigos de salida.
 *
 * Es una **tabla** y no una función porque su valor está en ser estable: quien
 * automatiza `kv` ramifica sobre el código de salida, y mover un estado de
 * familia le rompe el guion sin que nada avise.
 *
 * Se redujo de dieciocho códigos a ocho al irse `restore`, `doctor`, `inventory`
 * y todo el aparato de retiro: los códigos que quedaron sin ningún estado no se
 * conservan "por compatibilidad" —no había nada con qué ser compatible— pero los
 * que sí quedaron **conservan su número**, para no reescribirle el significado a
 * un `9` que ya quería decir "el destino no verifica".
 */

export class ContractError extends Error {
  constructor(code, message, { path: target = null, detail = null } = {}) {
    super(message);
    this.name = 'ContractError';
    this.code = code;
    this.path = target;
    this.detail = detail;
  }
}

export const VERBS = Object.freeze(['archive', 'migrate', 'index', 'config']);

const STATUS_BY_EXIT_CODE = Object.freeze({
  0: ['ARCHIVED', 'ALREADY_ARCHIVED', 'INDEX_OK', 'BATCH_OK', 'DRY_RUN', 'VAULT_CONFIGURED', 'VAULT_SET'],
  // Un lote incompleto **no** sale 0: migrar 49 de 50 deja un vault que ningún
  // criterio distingue de uno completo, y ese es justo el error caro.
  1: ['INTERNAL_ERROR', 'BATCH_PARTIAL', 'BATCH_FAILED'],
  2: ['USAGE'],
  3: ['CONFIG_INVALID'],
  4: ['PRECONDITION_NOT_MET'],
  5: ['NO_VAULT'],
  8: ['SOURCE_UNAVAILABLE'],
  9: ['VERIFY_FAILED', 'COPY_FAILED', 'PUBLISH_FAILED'],
});

const EXIT_CODE_BY_STATUS = new Map();
for (const [code, statuses] of Object.entries(STATUS_BY_EXIT_CODE)) {
  for (const status of statuses) {
    if (EXIT_CODE_BY_STATUS.has(status)) throw new Error(`estado duplicado en la tabla: ${status}`);
    EXIT_CODE_BY_STATUS.set(status, Number(code));
  }
}

export const STATUSES = Object.freeze([...EXIT_CODE_BY_STATUS.keys()]);
export const SUCCESS_STATUSES = Object.freeze(new Set(STATUS_BY_EXIT_CODE[0]));

const STATES_BY_VERB = Object.freeze({
  archive: Object.freeze(['ARCHIVED', 'ALREADY_ARCHIVED']),
  migrate: Object.freeze(['BATCH_OK', 'BATCH_PARTIAL', 'BATCH_FAILED', 'DRY_RUN']),
  index: Object.freeze(['INDEX_OK']),
  config: Object.freeze(['VAULT_CONFIGURED', 'VAULT_SET']),
});

export function statesForVerb(verb) {
  return STATES_BY_VERB[verb] ?? [];
}

export function isStatus(value) {
  return EXIT_CODE_BY_STATUS.has(value);
}

export function exitCodeFor(status) {
  const code = EXIT_CODE_BY_STATUS.get(status);
  if (code === undefined) {
    throw new ContractError('INTERNAL_ERROR', `${JSON.stringify(status)} no es un estado de la tabla`);
  }
  return code;
}
