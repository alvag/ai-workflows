/**
 * Los seis verbos, sus estados y sus códigos de salida.
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

export const VERBS = Object.freeze(['archive', 'migrate', 'index', 'config', 'retire', 'identity']);

/**
 * Qué banderas acepta cada verbo, y de qué forma: `valor` consume el token
 * siguiente, `booleana` no. Es el espejo en código de la matriz que
 * `reference.md` → "Matriz por verbo" ya tenía congelada, y la **única** sede de
 * la forma: antes vivía aparte, en un `Set` global de `cli.mjs`, que hacía que
 * `identity --dry-run` se parseara como booleana de otro verbo.
 *
 * **No declara obligatoriedad.** Qué bandera es obligatoria lo sigue diciendo
 * cada comando, con su propio mensaje: acá se gobiernan **nombres**, no
 * ausencias. Partirlo así evita dos capas que pueden discrepar sobre lo mismo.
 *
 * Las filas nacen **sin prototipo** a propósito. Sobre un objeto normal —incluso
 * `Object.freeze`— `fila['constructor']` devuelve una función, así que una
 * consulta directa aceptaría `--constructor` y lo descartaría en silencio, que es
 * exactamente el defecto que esta tabla existe para cerrar. `cli.mjs` consulta
 * además con `Object.hasOwn`: el prototipo nulo evita la herencia y `hasOwn` la
 * vuelve explícita para quien lea el código.
 */
const fila = (pares) => Object.freeze(Object.assign(Object.create(null), pares));

export const FLAGS_BY_VERB = Object.freeze(Object.assign(Object.create(null), {
  archive: fila({ from: 'valor', summary: 'valor', config: 'valor', 'vault-root': 'valor' }),
  migrate: fila({
    from: 'valor', summaries: 'valor', config: 'valor', 'vault-root': 'valor',
    'dry-run': 'booleana',
  }),
  index: fila({ config: 'valor', 'vault-root': 'valor' }),
  config: fila({
    config: 'valor', 'set-root': 'valor', 'search-root': 'valor', discover: 'booleana',
  }),
  retire: fila({
    root: 'valor', from: 'valor', config: 'valor', 'vault-root': 'valor',
    'approve-digest': 'valor', 'dry-run': 'booleana',
  }),
  identity: fila({
    declare: 'valor', config: 'valor', 'vault-root': 'valor', propose: 'booleana',
  }),
}));

const STATUS_BY_EXIT_CODE = Object.freeze({
  0: ['ARCHIVED', 'ALREADY_ARCHIVED', 'INDEX_OK', 'BATCH_OK', 'DRY_RUN', 'VAULT_CONFIGURED', 'VAULT_SET',
      'IDENTITY_PROPOSED', 'IDENTITY_DECLARED', 'IDENTITY_ALREADY_DECLARED', 'VAULTS_DISCOVERED'],
  // Un lote incompleto **no** sale 0: migrar 49 de 50 deja un vault que ningún
  // criterio distingue de uno completo, y ese es justo el error caro.
  1: ['INTERNAL_ERROR', 'BATCH_PARTIAL', 'BATCH_FAILED'],
  2: ['USAGE'],
  3: ['CONFIG_INVALID'],
  // `AMBIGUOUS_IDENTITY` entra acá y no en un código propio. Los libres —6 y 7—
  // pertenecieron a verbos retirados, y darles un significado nuevo le
  // reescribiría el sentido a un número que un guion viejo pudo consumir. Y la
  // familia es la correcta: es una precondición que hay que resolver antes de
  // operar, no un fallo de la corrida. Sin esto salía `INTERNAL_ERROR`, que le
  // dice a quien automatiza que encontró un bug en vez de que le falta declarar
  // la identidad.
  4: ['PRECONDITION_NOT_MET', 'AMBIGUOUS_IDENTITY'],
  // `VAULT_ROOT_UNAVAILABLE` acompaña a `NO_VAULT` y no se queda en
  // `INTERNAL_ERROR`, que es donde caía por no estar en esta tabla. La familia es
  // la correcta: las dos dicen "la raíz del vault no sirve para operar" y quien
  // automatiza actúa igual ante ambas —preguntar o degradar—, mientras que un `1`
  // le dice que encontró un bug. Se veía en `config --set-root` con una ruta mal
  // tipeada: el fallo aparecía después, en el `archive` siguiente, como error
  // interno.
  5: ['NO_VAULT', 'VAULT_ROOT_UNAVAILABLE'],
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
  config: Object.freeze(['VAULT_CONFIGURED', 'VAULT_SET', 'VAULTS_DISCOVERED']),
  // El quinto verbo **no agrega códigos**: reusa los que ya existen con el mismo
  // significado. Un `9` que ya quería decir "el destino no verifica" no puede
  // cambiar de sentido porque apareció un verbo nuevo, y quien automatiza `kv`
  // ramifica sobre esos números.
  retire: Object.freeze(['DRY_RUN', 'BATCH_OK', 'BATCH_PARTIAL', 'BATCH_FAILED']),
  identity: Object.freeze(['IDENTITY_PROPOSED', 'IDENTITY_DECLARED', 'IDENTITY_ALREADY_DECLARED']),
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
